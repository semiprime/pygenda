# -*- coding: utf-8 -*-
#
# pygenda_calendar.py
# Connects to agenda data provider - either an iCal file, a CalDAV server,
# or an Evolution Data Server.
#
# Copyright (C) 2022-2024 Matthew Lewis
#
# This file is part of Pygenda.
#
# Pygenda is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# Pygenda is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pygenda. If not, see <https://www.gnu.org/licenses/>.


from icalendar import Calendar as iCalendar, Event as iEvent, Todo as iTodo, Alarm as iAlarm, vRecur
from datetime import timedelta, datetime as dt_datetime, time as dt_time, date as dt_date, timezone
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrulestr
from dateutil import tz as du_tz
from sys import stderr
from uuid import uuid1
from pathlib import Path
from functools import reduce
from os import stat as os_stat, chmod as os_chmod, rename as os_rename, path as os_path
import stat
from time import monotonic as time_monotonic
import tempfile
from typing import Optional, Union, Tuple, List
from copy import deepcopy
from math import ceil
from calendar import monthrange

# Pygenda components
from .pygenda_config import Config
from .pygenda_util import dt_lt, dt_lte, datetime_to_date, date_to_datetime, get_local_tz, dt_add_delta, utc_now_stamp
from .pygenda_entryinfo import EntryInfo


# Interface base class to connect to different data sources.
# Used by Calendar class (below).
class CalendarConnector:
    cal = None # type:iCalendar
    displayname = None # type:str
    flags = 0

    READONLY = 1
    TYPE_EVENT = 2
    TYPE_TODO = 4
    TYPE_ALL = 6

    def is_readonly(self) -> bool:
        # Return True if connector is read-only
        return (self.flags & CalendarConnector.READONLY)!=0

    def stores_events(self) -> bool:
        # Return True if calendar stores events
        return (self.flags & CalendarConnector.TYPE_EVENT)!=0

    def stores_todos(self) -> bool:
        # Return True if calendar stores todo entries
        return (self.flags & CalendarConnector.TYPE_TODO)!=0

    def add_entry(self, entry:Union[iEvent,iTodo]) -> Union[iEvent,iTodo]:
        # Add a new entry component to the calendar data and store it.
        # Return reference to new entry (possibly different to one passed in).
        print('Warning: Add entry not implemented', file=stderr)
        return entry

    def update_entry(self, entry:Union[iEvent,iTodo]) -> None:
        # Update an entry component in the calendar data and store it.
        print('Warning: Update entry not implemented', file=stderr)

    def delete_entry(self, entry:Union[iEvent,iTodo]) -> None:
        # Delete entry component to the calendar data and remove from store.
        print('Warning: Delete entry not implemented', file=stderr)


# Singleton class for calendar data access/manipulation
class Calendar:
    STATUS_LIST_EVENT = ('TENTATIVE','CONFIRMED','CANCELLED')
    STATUS_LIST_TODO = ('NEEDS-ACTION','IN-PROCESS','COMPLETED','CANCELLED')

    calConnectors = None # type:List[CalendarConnector]
    _default_connector_event = None # type:int
    _default_connector_todo = None # type:int
    _entry_norep_list_sorted = None
    _entry_rep_list = None
    _entry_norep_xover_list_sorted = None # type:Optional[list]
    _todo_list = None

    @classmethod
    def init(cls) -> None:
        # Calendar connector initialisation.
        # Can take a long time, since it loads/sorts calendar data.
        # Best called in background after GUI is started, or startup can be slow.

        # Map calendar types to config parsing functions
        CTMAP = {
            'icalfile': cls._parse_config_icalfile,
            'caldav': cls._parse_config_caldav,
            'evolution': cls._parse_config_evolution,
            }

        # Map entry types to flags
        ETMAP = {
            'event': CalendarConnector.TYPE_EVENT,
            'todo': CalendarConnector.TYPE_TODO,
            'all': CalendarConnector.TYPE_ALL
            }

        # Local connector create function to save duplicating code
        def do_create_conn(sect:str, caltype:str) -> None:
            caltype = caltype.lower()
            assert(caltype in CTMAP)

            # Compute flags from config
            flags = CalendarConnector.READONLY if Config.get_bool(sect,'readonly') else 0
            entype = Config.get(sect,'entry_type')
            if entype is None:
                flags |= CalendarConnector.TYPE_ALL
            else:
                entype = entype.lower()
                assert(entype in ETMAP)
                flags |= ETMAP[entype]

            # Create new connector
            conn = CTMAP[caltype](sect, flags)
            if conn.cal.is_broken:
                print('Warning: Non-conformant ical data, '+sect, file=stderr)

            # Set display name (might already be set by constructor)
            dn = Config.get(sect, 'display_name')
            if dn is not None:
                conn.displayname = dn
            elif not conn.displayname: # Don't want empty display name
                conn.displayname = sect

            # Add _cal_idx attribute so we can find calendar from entry.
            # Also "fix tz": make sure entry timezones are detailed.
            calidx = len(cls.calConnectors)
            if conn.stores_events():
                for ev in conn.cal.walk('VEVENT'):
                    ev._cal_idx = calidx
                    cls._fix_tz(ev)
            if conn.stores_todos():
                for td in conn.cal.walk('VTODO'):
                    td._cal_idx = calidx
                    cls._fix_tz(td)

            # Finally, append our new connector to the list
            cls.calConnectors.append(conn)


        # Re-initialise connections and saved lists so init()
        # can be called more tn once if necessary
        cls.calConnectors = []
        cls._default_connector_event = None # type:ignore[assignment]
        cls._default_connector_todo = None # type:ignore[assignment]
        cls._entry_norep_list_sorted = None
        cls._entry_rep_list = None
        cls._entry_norep_xover_list_sorted = None
        cls._todo_list = None

        caltype = Config.get('calendar','type')
        if caltype is not None:
            do_create_conn('calendar', caltype)

        # look for 'calendar1', 'calendar2' etc.
        i = len(cls.calConnectors) # if no 'calendar' start at 'calendar0'
        while True:
            sect = 'calendar'+str(i)
            caltype = Config.get(sect, 'type')
            if caltype is None:
                break
            do_create_conn(sect, caltype)
            i += 1

        if i==0:
            # No calendar or calendar0 - default to a file
            do_create_conn('calendar', 'icalfile')

        # Set default connectors for events and todos if not already set
        if cls._default_connector_event is None:
            mask = CalendarConnector.READONLY | CalendarConnector.TYPE_EVENT # type:ignore[unreachable]
            for i,c in enumerate(cls.calConnectors):
                if c.flags&mask == CalendarConnector.TYPE_EVENT:
                    cls._default_connector_event = i
                    break
        if cls._default_connector_todo is None:
            mask = CalendarConnector.READONLY | CalendarConnector.TYPE_TODO # type:ignore[unreachable]
            for i,c in enumerate(cls.calConnectors):
                if c.flags&mask == CalendarConnector.TYPE_TODO:
                    cls._default_connector_todo = i
                    break


    @staticmethod
    def _parse_config_icalfile(calsect:str, flags:int) -> CalendarConnector:
        # Reads config setting for an icalfile and returns an
        # appropriate calendar connector object
        filename = Config.get(calsect,'filename')
        # Use either the provided filename or a default name.
        if filename is None:
             filename = '{}/{}'.format(Config.CONFIG_DIR,Config.DEFAULT_ICAL_FILENAME)
        else:
             # Expand '~' (so it can be used in config file)
             filename =  os_path.expanduser(filename)
        # Create a connector for that file
        return CalendarConnectorICalFile(filename, flags)


    @staticmethod
    def _parse_config_caldav(calsect:str, flags:int) -> CalendarConnector:
        # Reads config setting for a CalDAV server and returns an
        # appropriate calendar connector object
        caldav_server = Config.get(calsect, 'server')
        user = Config.get(calsect, 'username')
        passwd = Config.get(calsect, 'password')
        calname = Config.get(calsect, 'calendar')
        return CalendarConnectorCalDAV(caldav_server,user,passwd,calname,flags)


    @staticmethod
    def _parse_config_evolution(calsect:str, flags:int) -> CalendarConnector:
        uid = Config.get(calsect, 'uid')
        return CalendarConnectorEvolution(uid, flags)


    @staticmethod
    def _fix_tz(entry:Union[iEvent,iTodo]) -> None:
        # Function to set timezones for entry dates.
        # Modifies entry dates in-place.
        for l in ('DTSTART','DTEND','DUE'):
            if l in entry:
                prop = entry[l]
                if 'TZID' in prop.params:
                    # A du_tz object can hold complex TZ info, including
                    # DST changes. So we want to use one with our datetime.
                    tzid = prop.params['TZID']
                    tz = du_tz.gettz(tzid) # A du_tz based on info from OS.
                    if tz is not None:
                        prop.dt = prop.dt.astimezone(tz)


    @staticmethod
    def gen_uid() -> str:
        # Generate a UID for iCal elements (required element)
        uid = uuid1() # based on MAC addr, time & random element
        return str(uid)


    @classmethod
    def calendar_displaynames_event_rw(cls) -> List:
        # Returns display names for calendars for storing Events.
        # To be used, for example, in the Event dialog.
        mask = CalendarConnector.READONLY | CalendarConnector.TYPE_EVENT
        dnlist = [ (i,c.displayname) for i,c in enumerate(cls.calConnectors) if (c.flags & mask)==CalendarConnector.TYPE_EVENT ]
        return dnlist


    @classmethod
    def calendar_displaynames_todo_rw(cls) -> List:
        # Returns display names for calendars for storing Todos.
        # To be used, for example, in the Todo dialog.
        mask = CalendarConnector.READONLY | CalendarConnector.TYPE_TODO
        dnlist = [ (i,c.displayname) for i,c in enumerate(cls.calConnectors) if (c.flags & mask)==CalendarConnector.TYPE_TODO ]
        return dnlist


    @classmethod
    def calendar_displayname(cls, en:Union[iEvent,iTodo]) -> str:
        # Returns display names for given entry en
        dn = cls.calConnectors[en._cal_idx].displayname # type:str
        return dn


    @classmethod
    def calendar_readonly(cls, en:Union[iEvent,iTodo]) -> bool:
        # Returns True if calendar of entry is readonly
        ro = cls.calConnectors[en._cal_idx].is_readonly() # type:bool
        return ro


    @classmethod
    def new_entry(cls, e_inf:EntryInfo) -> Union[iEvent,iTodo]:
        # Add a new iCal entry with content from entry info object
        # Return a reference to the new entry.
        if cls.calConnectors[e_inf.cal_idx].is_readonly():
            raise ValueError('Tried to add entry to calendar set as read-only')

        if e_inf.type==EntryInfo.TYPE_EVENT:
            if not cls.calConnectors[e_inf.cal_idx].stores_events():
                raise ValueError('Tried to add event to calendar that doesn\'t store events')
            en = iEvent()
        elif e_inf.type==EntryInfo.TYPE_TODO:
            if not cls.calConnectors[e_inf.cal_idx].stores_todos():
                raise ValueError('Tried to add todo to calendar that doesn\'t store todos')
            en = iTodo()
            cls._todo_list = None # Clear todo cache as modified
        else:
            raise ValueError('Unrecognized entry type')
        en.add('UID', Calendar.gen_uid()) # Required
        cls._update_timestamps(en, is_new=True)
        en.add('SUMMARY', e_inf.desc)

        if e_inf.start_dt is not None:
            en.add('DTSTART', e_inf.start_dt)
            cls._event_add_end_dur_from_info(en, e_inf)
            # Repeats - only add these if entry has a date(time)
            if e_inf.rep_type is not None and e_inf.rep_inter>0:
                cls._event_add_repeat_from_info(en, e_inf)
                cls._entry_rep_list = None # Clear rep cache as modified
            else:
                cls._entry_norep_list_sorted = None # Clear norep cache, mod'd
                if cls._is_xover_entry(en):
                    cls._entry_norep_xover_list_sorted = None

        cls._entry_set_status_from_info(en, e_inf)
        cls._event_set_location_from_info(en, e_inf)
        if e_inf.categories:
            # Convert to list - to work around bug passing set to old icalendar
            en.add('CATEGORIES', list(e_inf.categories))
        if e_inf.priority:
            en.add('PRIORITY', e_inf.priority)
        if e_inf.duedate:
            en.add('DUE', e_inf.duedate)
        if e_inf.longdesc:
            en.add('DESCRIPTION', e_inf.longdesc)

        cls._entry_set_alarms_from_info(en, e_inf)

        entry = cls.calConnectors[e_inf.cal_idx].add_entry(en) # Write to store
        entry._cal_idx = e_inf.cal_idx
        return entry


    @classmethod
    def paste_entry(cls, exen:Union[iEvent,iTodo], e_type:int=None, dt_start:dt_date=None, e_cats:Union[list,bool,None]=True)-> Union[iEvent,iTodo]:
        # Paste - a wrapper fn around _new_entry_from_example()
        r = cls._new_entry_from_example(exen, e_type=e_type, dt_start=dt_start, e_cats=e_cats)
        return r


    @classmethod
    def import_entry(cls, exen:Union[iEvent,iTodo], cal_idx:int)-> Union[iEvent,iTodo]:
        # Import - a wrapper fn around _new_entry_from_example()
        return cls._new_entry_from_example(exen, e_cats=None, cal_idx=cal_idx, use_ex_uid_created=True, use_ex_rpts=True, use_ex_alarms=False)


    @staticmethod
    def _en_add_elt_from_en(tgt_en:Union[iEvent,iTodo], src_en:Union[iEvent,iTodo], elt:str, fallback:str=None):
        # Add src_en[elt] to tgt_en (if it exists).
        # If elt not present in src_en, and fallback provided, use fallback.
        # Used by _new_entry_from_example()
        if elt in src_en:
            tgt_en.add(elt, src_en[elt])
        elif fallback is not None:
            tgt_en.add(elt, fallback)

    @classmethod
    def _new_entry_from_example(cls, exen:Union[iEvent,iTodo], e_type:int=None, dt_start:dt_date=None, e_cats:Union[list,bool,None]=True, cal_idx:int=None, use_ex_uid_created:bool=False, use_ex_rpts:bool=False, use_ex_alarms:bool=True)-> Union[iEvent,iTodo]:
        # Add a new iCal entry to store given example iEvent as a "template".
        # Used to implement pasting entries and importing entries.
        # Arguments:
        #   e_type: Change type of entry to e_type (e.g. paste into todo list)
        #   dt_start: Override date/time with dt_start (e.g. paste to new date)
        #   e_cats==True: "Use exen categories"; False/None: "no categories";
        #           list[str]: "Use these categories"
        #   use_ex_uid_created: Use exen UID, create/mod times (e.g. importing)
        #   use_ex_rpts: Use exen repeat information (RRULE etc.)
        #   use_ex_alarms: Use exen alarms (e.g. pasting)
        # Return a reference to the new entry.

        if e_type==EntryInfo.TYPE_EVENT or (e_type is None and isinstance(exen,iEvent)):
            en_is_event = True
            if cal_idx is None:
                cal_idx = cls._default_connector_event
            if not cls.calConnectors[cal_idx].stores_events():
                raise ValueError('Tried to add event to calendar that doesn\'t store events')
            en = iEvent()
        elif e_type==EntryInfo.TYPE_TODO or (e_type is None and isinstance(exen,iTodo)):
            en_is_event = False
            if cal_idx is None:
                cal_idx = cls._default_connector_todo
            if not cls.calConnectors[cal_idx].stores_todos():
                raise ValueError('Tried to add todo to calendar that doesn\'t store todos')
            en = iTodo()
        else:
            raise ValueError('Unrecognized iCal entry type')

        if cls.calConnectors[cal_idx].is_readonly():
            raise ValueError('Tried to add entry to calendar set as read-only')

        if use_ex_uid_created and 'UID' in exen:
            cls._en_add_elt_from_en(en, exen, 'UID')
        else:
            # UID is required, so add one
            en.add('UID', Calendar.gen_uid())

        if use_ex_uid_created:
            # DTSTAMP should be time of import/paste.
            # Creation/last modified likely to be sometime in the past.
            utcnow = utc_now_stamp()
            en.add('DTSTAMP', utcnow) # Required elt
            cls._en_add_elt_from_en(en, exen, 'CREATED')
            cls._en_add_elt_from_en(en, exen, 'LAST-MODIFIED')
        else:
            cls._update_timestamps(en, is_new=True)

        cls._en_add_elt_from_en(en, exen, 'SUMMARY', fallback='_')
        new_dt_start = None
        new_dt_start_tzid = None
        en_repeats = False
        if en_is_event:
            # Some entry elements only relevant if an event (may change later)
            ex_dt_start = None
            ex_dt_start_tzid = None
            if 'DTSTART' in exen:
                ex_dt_start = exen['DTSTART'].dt
                params = exen['DTSTART'].params
                if 'TZID' in params:
                    ex_dt_start_tzid = params['TZID']
                    tz = du_tz.gettz(ex_dt_start_tzid) # A du_tz from OS info
                    if tz is not None:
                        ex_dt_start = ex_dt_start.astimezone(tz)
            if dt_start:
                if ex_dt_start:
                    src_date_local = ex_dt_start
                    if isinstance(src_date_local, dt_datetime) and src_date_local.tzinfo is not None:
                        # Pasting. Target dt is in *local* timezone.
                        # Hence to get correct offset, need to convert
                        # example entry's datetime to local time too.
                        src_date_local = src_date_local.astimezone(get_local_tz())
                    if not isinstance(dt_start, dt_datetime):
                        # Target is just a date, so make delta a numer of days
                        src_date_local = datetime_to_date(src_date_local)
                    date_delta = dt_start - src_date_local
                    new_dt_start = ex_dt_start + date_delta
                    new_dt_start_tzid = None if isinstance(dt_start, dt_datetime) else ex_dt_start_tzid
                else:
                    new_dt_start = dt_start
                    new_dt_start_tzid = None
            elif ex_dt_start:
                new_dt_start = ex_dt_start
                new_dt_start_tzid = ex_dt_start_tzid
            else:
                raise ValueError('Event has no date/time')
            en.add('DTSTART', new_dt_start, parameters={'TZID':new_dt_start_tzid} if new_dt_start_tzid else None)
            if ex_dt_start and 'DTEND' in exen:
                ex_dt_end = exen['DTEND'].dt
                ex_dt_end_tzid = None
                if 'TZID' in exen['DTEND'].params:
                    ex_dt_end_tzid = exen['DTEND'].params['TZID']
                    end_tz = du_tz.gettz(ex_dt_end_tzid) # A du_tz from OS info
                    if end_tz is not None:
                        ex_dt_end = ex_dt_end.astimezone(end_tz)
                new_dt_end_tzid = ex_dt_end_tzid
                if dt_start:
                    delta = new_dt_start - ex_dt_start
                    new_dt_end = ex_dt_end + delta
                else:
                    # No dt_start, so just importing date/times directly
                    new_dt_end = ex_dt_end
                en.add('DTEND', new_dt_end, parameters={'TZID':new_dt_end_tzid} if new_dt_end_tzid else None)
            else:
                cls._en_add_elt_from_en(en, exen, 'DURATION')
            if use_ex_rpts and 'RRULE' in exen:
                en_repeats = True
                cls._en_add_elt_from_en(en, exen, 'RRULE')
                cls._en_add_elt_from_en(en, exen, 'EXDATE')
            if use_ex_alarms:
                alms = exen.walk('VALARM')
                for alm in alms:
                    en.add_component(deepcopy(alm)) # Not sure need dc (safer)

        cls._en_add_elt_from_en(en, exen, 'LOCATION')
        if e_cats is True:
            cls._en_add_elt_from_en(en, exen, 'CATEGORIES')
        elif e_cats:
            # Convert to list - to work around bug passing set to old icalendar
            en.add('CATEGORIES', list(e_cats))
        cls._en_add_elt_from_en(en, exen, 'PRIORITY')
        if 'STATUS' in exen:
            # Only add status if it is valid for entry type
            sl = cls.STATUS_LIST_EVENT if en_is_event else cls.STATUS_LIST_TODO
            exen_status = exen['STATUS']
            if exen_status in sl:
                en.add('STATUS', exen_status)
        if not en_is_event: # is Todo (spec says DUE is not allowed in events)
            cls._en_add_elt_from_en(en, exen, 'DUE')
        cls._en_add_elt_from_en(en, exen, 'DESCRIPTION')

        en = cls.calConnectors[cal_idx].add_entry(en) # Write to store
        en._cal_idx = cal_idx

        # Clear appropriate lists
        if new_dt_start is not None:
            if en_repeats:
                cls._entry_rep_list = None
            else:
                cls._entry_norep_list_sorted = None
                if cls._is_xover_entry(en):
                    cls._entry_norep_xover_list_sorted = None
        if not en_is_event: # is Todo
            cls._todo_list = None # Clear todo cache as modified
        return en


    @classmethod
    def update_entry(cls, en:Union[iEvent,iTodo], e_inf:EntryInfo) -> None:
        # Update entry using details from EntryInfo e_inf.

        # First check entry is not in or being moved to a read-only calendar
        if cls.calendar_readonly(en):
            raise ValueError('Tried to update entry from calendar set readonly')
        if cls.calConnectors[e_inf.cal_idx].is_readonly():
            raise ValueError('Tried to update entry into calendar set readonly')

        if isinstance(en, iEvent):
            if not cls.calConnectors[e_inf.cal_idx].stores_events():
                raise ValueError('Tried to update event into calendar that doesn\'t store events')
        elif isinstance(en, iTodo):
            if not cls.calConnectors[e_inf.cal_idx].stores_todos():
                raise ValueError('Tried to update todo into calendar that doesn\'t store todos')
        else:
            raise ValueError('Unrecognized entry type')

        clear_rep = False
        clear_norep = False

        if 'UID' not in en:
            en.add('UID', Calendar.gen_uid()) # Should be present

        cls._update_timestamps(en, is_new=False)
        cls._update_entry_field(en, 'SUMMARY', e_inf.desc)
        cls._update_entry_field(en, 'PRIORITY', e_inf.priority)
        cls._update_entry_field(en, 'DUE', e_inf.duedate)
        cls._update_entry_field(en, 'DESCRIPTION', e_inf.longdesc)

        # For Categories, we need to convert to a list,
        # to work around bug passing set to old icalendar.
        cls._update_entry_field(en, 'CATEGORIES', None if e_inf.categories is None else list(e_inf.categories))

        # DTSTART - delete & re-add so type (DATE vs. DATE-TIME) is correct
        # (Also, Q: if comparing DTSTARTs with different TZs, how does != work?)
        had_date = 'DTSTART' in en
        if had_date:
            del(en['DTSTART'])
        if e_inf.start_dt is not None:
            en.add('DTSTART', e_inf.start_dt)

        # Duration or Endtime - first delete existing
        cls._del_entry_field(en, 'DURATION')
        cls._del_entry_field(en, 'DTEND')
        # Then add new end time/duration (if needed)
        cls._event_add_end_dur_from_info(en, e_inf)

        # Repeats (including exception dates)
        if 'RRULE' in en:
            del(en['RRULE'])
            clear_rep = True
        elif had_date:
            # Previously had start time, but no repeats
            clear_norep = True
        cls._del_entry_field(en, 'EXDATE')
        if e_inf.rep_type is not None and e_inf.rep_inter>0:
            cls._event_add_repeat_from_info(en, e_inf)
            clear_rep = True
        elif e_inf.start_dt is not None:
            # Now has start time, but no repeats
            clear_norep = True

        # Other properties: status (cancelled, tentative, etc.), location
        cls._entry_set_status_from_info(en, e_inf)
        cls._event_set_location_from_info(en, e_inf)

        # First delete alarms before adding requested ones
        alms = en.walk('VALARM')
        for alm in alms:
            en.subcomponents.remove(alm)
        cls._entry_set_alarms_from_info(en, e_inf)

        # This needs optimising - some cases cause too much cache flushing !!
        if clear_norep:
            cls._entry_norep_list_sorted = None
            cls._entry_norep_xover_list_sorted = None
        if clear_rep:
            cls._entry_rep_list = None
        if e_inf.type==EntryInfo.TYPE_TODO or isinstance(en, iTodo):
            cls._todo_list = None

        if en._cal_idx == e_inf.cal_idx:
            cls.calConnectors[e_inf.cal_idx].update_entry(en) # Write to store
        else:
            # Need to move entry to new calendar.
            # Write new then delete old - to reduce chance of data loss.
            old_cal_idx = en._cal_idx
            new_en = cls.calConnectors[e_inf.cal_idx].add_entry(en)
            new_en._cal_idx = e_inf.cal_idx
            cls.calConnectors[old_cal_idx].delete_entry(en)


    @staticmethod
    def _del_entry_field(en:Union[iEvent,iTodo], fname:str) -> None:
        # Helper function to delete an entry field if it exists.
        if fname in en:
            del(en[fname])


    @staticmethod
    def _update_entry_field(en:Union[iEvent,iTodo], fname:str, val) -> None:
        # Helper function to update an entry field, or add if it doesn't
        # exist. Use delete-and-recreate since seems more reliable
        # (e.g. for datetimes, some combinations of modules lose the
        # timezone marker if you do en[fname]=val).
        # Note: if val is None, then existing entry is deleted.
        if fname in en:
            del(en[fname])
        if val is not None:
            en.add(fname, val)


    @staticmethod
    def _update_timestamps(en:Union[iEvent,iTodo], is_new:bool) -> None:
        # Update entry fields recording modified time: DTSTAMP.
        # if is_new, add CREATED; if not new, update LAST-MODIFIED.
        # All these fields use UTC.
        utcnow = utc_now_stamp()
        Calendar._update_entry_field(en, 'DTSTAMP', utcnow) # Required elt
        if is_new:
            en.add('CREATED', utcnow) # Optional elt
        else:
            Calendar._update_entry_field(en, 'LAST-MODIFIED', utcnow) # Opt


    @staticmethod
    def _event_add_end_dur_from_info(ev:iEvent, e_inf:EntryInfo) -> None:
        # Adds end time or duration to an event from EntryInfo.
        # How it does this depends on whether event is timed or not

        # If entry is timed, check for an end-time/duration & add if present
        # Note: don't add both an end-time & duration - at most one
        if isinstance(e_inf.start_dt, dt_datetime):
            if e_inf.end_dt is not None:
                if isinstance(e_inf.end_dt, dt_datetime):
                    if e_inf.end_dt > e_inf.start_dt:#need end_dt after start_dt
                        ev.add('DTEND', e_inf.end_dt)
                elif isinstance(e_inf.end_dt, dt_time):
                    end_dttm = dt_datetime.combine(e_inf.start_dt.date(),e_inf.end_dt)
                    if end_dttm != e_inf.start_dt: # require end time to be after start time
                        if end_dttm < e_inf.start_dt:
                            end_dttm += timedelta(days=1)
                        ev.add('DTEND', end_dttm)
            elif e_inf.duration is not None and isinstance(e_inf.duration, timedelta):
                if e_inf.duration.total_seconds()>0: # require duration > 0
                    ev.add('DURATION', e_inf.duration)
        elif isinstance(e_inf.start_dt, dt_date):
            # start is a date (not time) => this might be a day entry
            if isinstance(e_inf.end_dt, dt_date):
                if e_inf.end_dt >= e_inf.start_dt: # sanity check
                    ev.add('DTEND', e_inf.end_dt)
            elif isinstance(e_inf.duration, timedelta):
                # RFC 5545 Sect 3.8.2.5 says duration must be whole no of days
                if e_inf.duration.seconds == e_inf.duration.microseconds == 0:
                    ev.add('DURATION', e_inf.duration)


    @staticmethod
    def _event_add_repeat_from_info(ev:iEvent, e_inf:EntryInfo) -> None:
        # Adds FREQ and EXDATE fields to event.
        # Assume these fields are empty (so either it's a
        # new entry or the delete happens elsewhere).
        rr_options = {'FREQ':[e_inf.rep_type]}
        if e_inf.rep_inter != 1:
            rr_options['INTERVAL'] = [e_inf.rep_inter]
        if e_inf.rep_until is not None:
            if isinstance(e_inf.start_dt,dt_datetime) and not isinstance(e_inf.rep_until,dt_datetime):
                # If start is a datetime, until needs to be a datetime
                dt_until = dt_datetime.combine(e_inf.rep_until,e_inf.start_dt.time())
            else:
                dt_until = e_inf.rep_until
            rr_options['UNTIL'] = [dt_until]
        elif e_inf.rep_count is not None:
            rr_options['COUNT'] = [e_inf.rep_count]
        if e_inf.rep_byday is not None:
            rr_options['BYDAY'] = [e_inf.rep_byday]
        if e_inf.rep_bymonth is not None:
            rr_options['BYMONTH'] = [e_inf.rep_bymonth]
        if e_inf.rep_bymonthday is not None:
            rr_options['BYMONTHDAY'] = [e_inf.rep_bymonthday]
        ev.add('RRULE', rr_options)

        # Add exception date/times
        if e_inf.rep_exceptions:
            d_prm = {'VALUE':'DATE'} # ? Bug in icalendar 4.0.9 means we need to add VALUE parameter
            # Adding multiple EXDATE fields seems to be most compatible
            for rex in e_inf.rep_exceptions:
                ev.add('EXDATE', rex, parameters=None if isinstance(rex,dt_datetime) else d_prm)

        # For repeats, spec says DTSTART should correspond to RRULE
        # https://icalendar.org/iCalendar-RFC-5545/3-8-5-3-recurrence-rule.html
        # So check DTSTART is consistent with RRULE, and possibly adjust.
        # This ignores exceptions, since they are an extra layer.
        fst_occ = first_occ(ev['RRULE'].to_ical().decode('utf-8'),e_inf.start_dt)
        if fst_occ!=e_inf.start_dt:
            print('Notice: rewriting DTSTART to be consistent with RRULE', file=stderr)
            del(ev['DTSTART'])
            ev.add('DTSTART', fst_occ)
            # May also need to change end date
            if 'DTEND' in ev:
                d = fst_occ - e_inf.start_dt
                end = ev['DTEND'].dt + d
                del(ev['DTEND'])
                ev.add('DTEND', end)


    @staticmethod
    def _entry_set_status_from_info(en:Union[iEvent,iTodo], e_inf:EntryInfo) -> None:
        # Set entry status (cancelled, tentative etc.) from e_inf.
        Calendar._del_entry_field(en, 'STATUS')
        Calendar._add_status_entry(en, e_inf.status)


    @staticmethod
    def _event_set_location_from_info(ev:iEvent, e_inf:EntryInfo) -> None:
        # Set event location (text string) from e_inf.
        Calendar._del_entry_field(ev, 'LOCATION')
        if e_inf.location:
            ev.add('LOCATION', e_inf.location)


    @staticmethod
    def _entry_set_alarms_from_info(en:Union[iEvent,iTodo], e_inf:EntryInfo) -> None:
        # Set entry alarms from e_inf
        for al in e_inf.alarms:
            v_alm = iAlarm()
            v_alm.add('TRIGGER', al.tdelta)
            v_alm.add('ACTION', al.action)
            desc = al.desc
            summ = al.summary
            attee = al.attendee
            if al.action=='DISPLAY':
                # Description required for Display
                if desc is None:
                    desc = ''
            elif al.action=='EMAIL':
                # Description, Summary, Attendee required for Email
                if desc is None:
                    desc = ''
                if summ is None:
                    summ = ''
                if attee is None:
                    attee = ''
            if desc is not None:
                v_alm.add('DESCRIPTION', desc)
            if summ is not None:
                v_alm.add('SUMMARY', summ)
            if attee is not None:
                v_alm.add('ATTENDEE', attee)
            if al.attach is not None:
                v_alm.add('ATTACH', al.attach)
            en.add_component(v_alm)


    @classmethod
    def delete_entry(cls, entry:Union[iEvent,iTodo]) -> None:
        # Delete given entry.
        if cls.calendar_readonly(entry):
            raise ValueError('Tried to delete entry from calendar set readonly')

        # Need to clear cache containing the entry...
        if 'DTSTART' in entry:
            if 'RRULE' in entry:
                cls._entry_rep_list = None
            else:
                cls._entry_norep_list_sorted = None
                cls._entry_norep_xover_list_sorted = None
        if type(entry)==iTodo:
            cls._todo_list = None

        cls.calConnectors[entry._cal_idx].delete_entry(entry)


    @classmethod
    def set_toggle_status_entry(cls, entry:Union[iEvent,iTodo], stat:Optional[str]) -> None:
        # Set entry STATUS to stat & save entry.
        # If STATUS is set and equals stat, toggle it off.
        if cls.calendar_readonly(entry):
            raise ValueError('Tried to update status of entry in read-only calendar')
        if 'STATUS' in entry:
            if stat==entry['STATUS']:
                stat = None # If on, we toggle it off
            del(entry['STATUS'])
        elif stat is None:
            # No existing status & requesting set to none, so do nothing
            return
        cls._add_status_entry(entry, stat)
        cls._update_timestamps(entry, is_new=False)
        cls.calConnectors[entry._cal_idx].update_entry(entry) # Write to store


    @staticmethod
    def _add_status_entry(entry:Union[iEvent,iTodo], stat:Optional[str]) -> None:
        # Set entry STATUS to stat.
        # Assumes entry['STATUS'] does not exist.
        # Only allows spec'ed values (o/w leaves unchanged).
        if stat=='COMPLETED':
            # PERCENT-COMPLETE automatically set to 100, so can delete
            Calendar._del_entry_field(entry, 'PERCENT-COMPLETE')
        else:
            if 'PERCENT-COMPLETE' in entry and entry['PERCENT-COMPLETE']==100:
                entry['PERCENT-COMPLETE'] = 99 # Stop it being == 100
            Calendar._del_entry_field(entry, 'COMPLETED')
        if (isinstance(entry,iEvent) and stat in Calendar.STATUS_LIST_EVENT) \
           or (isinstance(entry,iTodo) and stat in Calendar.STATUS_LIST_TODO):
                entry.add('STATUS', stat)


    @classmethod
    def _update_entry_norep_list(cls) -> None:
        # Re-build _entry_norep_list_sorted, if it has been cleared (==None)
        if cls._entry_norep_list_sorted is None:
            # Get events with no repeat rule
            cls._entry_norep_list_sorted = []
            for conn in cls.calConnectors:
                if conn.stores_events():
                    evs = conn.cal.walk('VEVENT')
                    cls._entry_norep_list_sorted.extend([e for e in evs if 'RRULE' not in e])
            cls._entry_norep_list_sorted.sort()


    @classmethod
    def _update_entry_rep_list(cls) -> None:
        # Re-build _entry_rep_list, if it has been cleared (==None)
        # Possible optimisation: sort most -> least frequent
        # (so don't get last one inserting loads into array) 
        if cls._entry_rep_list is None:
            cls._entry_rep_list = []
            for conn in cls.calConnectors:
                if conn.stores_events():
                    evs = conn.cal.walk('VEVENT')
                    cls._entry_rep_list.extend([e for e in evs if 'RRULE' in e and e['RRULE'] is not None])


    @classmethod
    def _update_entry_norep_xover_list_sorted(cls) -> None:
        # Re-build _entry_norep_xover_list_sorted, if it is cleared (==None)
        if cls._entry_norep_xover_list_sorted is None:
            cls._entry_norep_xover_list_sorted = []
            for conn in cls.calConnectors:
                evs = conn.cal.walk('vEvent')
                cls._entry_norep_xover_list_sorted.extend([e for e in evs if 'RRULE' not in e and cls._is_xover_entry(e)])
            cls._entry_norep_xover_list_sorted.sort()


    @staticmethod
    def _is_xover_entry(e:iEvent) -> bool:
        # Helper function to determine if simple/non-repeating entry
        # crosses over from one (localtime) day to the next
        if 'DTEND' in e:
            st = e['DTSTART'].dt
            end = e['DTEND'].dt
            if isinstance(st, dt_datetime):
                st = date_to_datetime(st, True).astimezone(get_local_tz())
                end = date_to_datetime(end, True).astimezone(get_local_tz())
        elif 'DURATION' in e:
            st = e['DTSTART'].dt
            if isinstance(st, dt_datetime):
                st = date_to_datetime(st, True).astimezone(get_local_tz())
            end = dt_add_delta(st, e['DURATION'].dt)
        else:
            return False
        enddate = datetime_to_date(end)
        if not isinstance(end,dt_datetime) or end.time()==dt_time(hour=0,minute=0,second=0):
            enddate -= timedelta(days=1)
        return datetime_to_date(st) < enddate # type:ignore[no-any-return]


    @classmethod
    def occurrence_list(cls, start:dt_date, stop:dt_date, include_single:bool=True, include_repeated:bool=True) -> list:
        # Return list of occurences in range start <= . < stop.
        # Designed to be called by View classes to get events in range.
        # An "occurrence" is a pair: (event,datetime)
        #  for repeating entries, datetime may not be the DTSTART entry
        # Needs to also return events that last/end over range??
        ret_list = []
        if include_single:
            cls._update_entry_norep_list()
            # bisect to find starting point
            ii = 0
            llen = len(cls._entry_norep_list_sorted)
            top = llen
            while ii<top:
                mid = (ii+top)//2
                if dt_lt(cls._entry_norep_list_sorted[mid]['DTSTART'].dt,start):
                    ii = mid+1
                else:
                    top = mid
            # ii is now the start, append occs to ret_list
            while ii < llen:
                e = cls._entry_norep_list_sorted[ii]
                e_st = e['DTSTART'].dt
                if dt_lte(stop, e_st):
                    break
                ret_list.append((e,e_st))
                ii += 1
        if include_repeated:
            cls._update_entry_rep_list()
            for e in cls._entry_rep_list:
                merge_repeating_entries_sort(ret_list,e,start,stop)
        return ret_list


    @classmethod
    def ongoing_list(cls, dt:dt_date, include_single:bool=True, include_repeated:bool=True) -> list:
        # Return list of events that are ongoing at datetime 'dt'
        ret_list = []
        if include_single:
            # Naive implementation - scope for optimisation here!!
            cls._update_entry_norep_xover_list_sorted()
            for e in cls._entry_norep_xover_list_sorted:#type:ignore[union-attr]
                e_st = e['DTSTART'].dt
                if dt_lte(dt, e_st):
                    break # List is sorted, so we can stop search here
                if 'DTEND' in e:
                    e_end = e['DTEND'].dt
                else: # 'DURATION' in e
                    e_end = dt_add_delta(e_st, e['DURATION'].dt)
                if dt_lt(dt, e_end):
                    ret_list.append((e,e_st))
        return ret_list


    @classmethod
    def get_entry_by_uid(cls, uid:str) -> Union[iEvent,iTodo,None]:
        # Return entry corresponding to UID.
        # Assumes UID only occurs once in all calendars.
        # Used when importing ical files to check if entry already
        # exists, so no particular need to be super-speedy.
        for conn in cls.calConnectors:
            if conn.stores_events():
                evs = conn.cal.walk('VEVENT')
                for ev in evs:
                    if 'UID' in ev and ev['UID']==uid:
                        return ev
            if conn.stores_todos():
                tds = conn.cal.walk('VTODO')
                for td in tds:
                    if 'UID' in td and td['UID']==uid:
                        return td
        return None


    @classmethod
    def _update_todo_list(cls) -> None:
        # Re-build _todo_list, if it has been cleared (==None)
        if cls._todo_list is None:
            # Get events with no repeat rule & sort
            cls._todo_list = []
            for conn in cls.calConnectors:
                if conn.stores_todos():
                    cls._todo_list.extend(conn.cal.walk('VTODO'))
            # !! Should really sort elsewhere - in View??
            cls._todo_list.sort(key=cls._todo_sortindex_priority)


    @staticmethod
    def _todo_sortindex_priority(t:iTodo) -> Tuple[int,dt_datetime,dt_datetime]:
        # Return sort keys used to sort todos by priority
        key_pri = t['PRIORITY'] if 'PRIORITY' in t else 10
        key_dtime = date_to_datetime(t['DUE'].dt).timestamp() if 'DUE' in t else float('inf')
        key_ctime = t['CREATED'].dt.timestamp() if 'CREATED' in t else 0
        return key_pri, key_dtime, key_ctime


    @classmethod
    def todo_list(cls) -> list:
        # Return list of "todo"s
        # !! Not sure if we need to track list - to review later when/if there is filtering
        cls._update_todo_list()
        return cls._todo_list


    @classmethod
    def search(cls, txt:str) -> list:
        # Searches through entries for text string 'txt'.
        # !! Simple version - need to add options
        ret_list = []
        txt_n = txt.casefold() # !! also need to remove accents !!
        # Non-repeating entries
        cls._update_entry_norep_list()
        for ev in cls._entry_norep_list_sorted:
            if 'SUMMARY' in ev and txt_n in ev['SUMMARY'].casefold():
                ret_list.append(ev)
        # Repeating entries
        cls._update_entry_rep_list()
        for ev in cls._entry_rep_list:
            if 'SUMMARY' in ev and txt_n in ev['SUMMARY'].casefold():
                ret_list.append(ev)
        # Todo entries
        cls._update_todo_list()
        for td in cls._todo_list:
            if 'SUMMARY' in td and txt_n in td['SUMMARY'].casefold():
                ret_list.append(td)
        return ret_list


    @staticmethod
    def caldatetime_tree_to_dt_list(ed) -> list:
        # Utility function to map a "tree" of dates (arg `ed`)
        # (as returned by icalendar when retrieving EXDATE)
        # to a flat list of Python date/datetimes.
        if isinstance(ed, list):
            exdate_list = [ed[i].dts[j] for i in range(len(ed)) for j in range(len(ed[i].dts))]
        else:
            exdate_list = ed.dts
        return [d.dt for d in exdate_list]


#
# Connector class for iCal files
#
class CalendarConnectorICalFile(CalendarConnector):
    BACKUP_PERIOD = 90 # seconds
    BACKUP_EXT = 'bak'
    NEWFILE_EXT = 'new'

    def __init__(self, filename:str, flags:int):
        self._filename = filename
        self.flags = flags
        if Path(filename).exists():
            # We want to read all entries here, even ones we can't handle
            # (e.g. journal entries), so that when the iCal data is written
            # back to the file nothing is lost.
            with open(filename, 'rb') as file:
                self.cal = iCalendar.from_ical(file.read())
            if os_stat(filename).st_mode&stat.S_IWUSR == 0:
                # File is readonly, set flags so this is respected
                self.flags |= CalendarConnector.READONLY
        elif self.is_readonly():
            raise ValueError('Can\'t create an iCal file in read-only mode')
        else: # Create empty calendar file
            self.cal = iCalendar()
            # These aren't added automatically and spec requires them:
            self.cal.add('PRODID', '-//Semiprime//Pygenda//EN')
            self.cal.add('VERSION', '2.0')
        self._backup_saved_time = float('-inf') # so first change creates backup


    def _save_file(self) -> None:
        # Save file to disk/storage. Called after any entry updated.
        # Implementation tries to minimise possibility/extent of data loss.
        file_exists = False
        try:
            mode = os_stat(self._filename).st_mode
            file_exists = True
        except FileNotFoundError:
            mode = stat.S_IRUSR|stat.S_IWUSR # Default - private to user

        # We don't want to just write over current file - it will be
        # zero-length for a time, so a crash would lose data.
        # We save to a new file, so a crash before the write completes
        # will leave original file in place to be opened on restart.
        realfile = os_path.realpath(self._filename)
        tfdir = os_path.dirname(realfile)
        tfpre = '{:s}.{:s}-{:s}-'.format(os_path.basename(realfile),self.NEWFILE_EXT,dt_datetime.now().strftime('%Y%m%d%H%M%S'))
        with tempfile.NamedTemporaryFile(mode='wb', prefix=tfpre, dir=tfdir, delete=False) as tf:
            temp_filename = tf.name
            os_chmod(temp_filename, mode)
            tf.write(self.cal.to_ical())

        # Possibly make a backup of original file before overwriting
        if file_exists and time_monotonic() - self._backup_saved_time > self.BACKUP_PERIOD:
            os_rename(self._filename, '{:s}.{:s}'.format(self._filename,self.BACKUP_EXT))
            self._backup_saved_time = time_monotonic() # re-read time
        # Rename temp saved version to desired name
        os_rename(temp_filename, realfile)


    def add_entry(self, entry:Union[iEvent,iTodo]) -> Union[iEvent,iTodo]:
        # Add a new entry component to the file data and write file.
        self.cal.add_component(entry)
        self._save_file()
        return entry


    def update_entry(self, entry:Union[iEvent,iTodo]) -> None:
        # Update an entry component in the calendar data and store it.
        # Entry is a component of the file data, so it's already updated.
        # We just need to write the file data.
        self._save_file()


    def delete_entry(self, entry:Union[iEvent,iTodo]) -> None:
        # Delete entry component to the file data and write file.
        self.cal.subcomponents.remove(entry)
        self._save_file()


#
# Connector class for CalDAV server
# This works by reading all the data from the server on startup, and
# using its copy to calculate query responses. I did it this way
# because, on testing, querying the server directly was too slow:
# using the Radicale server on the Gemini, a simple query with a
# range of a week took more than 3 seconds (0.5 seconds on a laptop).
#
class CalendarConnectorCalDAV(CalendarConnector):
    def __init__(self, url:str, user:str, passwd:str, calname:Optional[str], flags:int):
        import caldav # Postponed import, so Pygenda can be used without caldav

        client = caldav.DAVClient(url=url, username=user, password=passwd)
        try:
            principal = client.principal()
        except Exception as excep:
            print('Error: Can\'t connect to CalDAV server at {:s}. Message: {:s}'.format(url,str(excep)), file=stderr)
            raise

        self.flags = flags
        if calname is None:
            calendars = principal.calendars()
            if len(calendars) > 0:
                self.calendar = calendars[0]
            elif self.is_readonly():
                raise ValueError('No CalDAV calendars found; can\'t create in read-only mode')
            else:
                # Create a calendar with default name
                self.calendar = principal.make_calendar(name='pygenda')
        else:
            # Open or create named calendar
            try:
                self.calendar = principal.calendar(calname)
            except caldav.lib.error.NotFoundError:
                if self.is_readonly():
                    raise
                self.calendar = principal.make_calendar(name=calname)

        self.cal = iCalendar()
        # Make list of references to events for convenient access
        if self.stores_events():
            events = self.calendar.events()
            for ev in events:
                # Each icalendar_instance is a calendar containing the event.
                # We want to extract the event itself, so walk() & take the 1st.
                vevent = ev.icalendar_instance.walk('VEVENT')[0]
                vevent.__conn_entry = ev # Sneakily add ev, for rapid access
                self.cal.add_component(vevent)
        # ... and todos
        if self.stores_todos():
            todos = self.calendar.todos(sort_keys=(), include_completed=True)
            for td in todos:
                vtodo = td.icalendar_instance.walk('VTODO')[0]
                vtodo.__conn_entry = td # Sneakily add td, for rapid access
                self.cal.add_component(vtodo)


    def add_entry(self, entry:Union[iEvent,iTodo]) -> Union[iEvent,iTodo]:
        # Create a new entry component on the server, and locally.
        vcstr = 'BEGIN:VCALENDAR\r\n{:s}END:VCALENDAR\r\n'.format(entry.to_ical().decode()) # !! Should we specify encoding for decode()?
        try:
            if isinstance(entry,iTodo):
                conn_entry = self.calendar.save_todo(vcstr)
            else: # an iEvent
                conn_entry = self.calendar.save_event(vcstr)
        except Exception as excep:
            # !! While code is in development, just exit on failure.
            # May change to something "friendlier" later...
            print('Error creating entry on CalDAV server. Message: {:s}'.format(str(excep)), file=stderr)
            exit(-1)

        # Save to local store
        # Add embedded entry, so we can modify & save directly
        newentry = conn_entry.icalendar_instance.walk()[1]
        newentry.__conn_entry = conn_entry
        self.cal.add_component(newentry)
        return newentry


    def update_entry(self, entry:Union[iEvent,iTodo]) -> None:
        # Update an entry component in the calendar data and store it.
        # Entry struct has been modified, so can just send update to server.
        try:
            entry.__conn_entry.save() # Write to server
        except Exception as excep:
            # !! While code is in development, just exit on failure.
            # May change to something "friendlier" later...
            print('Error updating entry on CalDAV server. Message: {:s}'.format(str(excep)), file=stderr)
            exit(-1)


    def delete_entry(self, entry:Union[iEvent,iTodo]) -> None:
        # Delete entry component from server and in local copy.
        try:
            entry.__conn_entry.delete() # delete from server
        except Exception as excep:
            # !! While code is in development, just exit on failure.
            # May change to something "friendlier" later...
            print('Error deleting entry on CalDAV server. Message: {:s}'.format(str(excep)), file=stderr)
            exit(-1)
        self.cal.subcomponents.remove(entry) # delete local copy


#
# Connector class for Evolution Data server
#
class CalendarConnectorEvolution(CalendarConnector):
    CONNECTION_TIMEOUT = 5
    __eds_client = None # type:ECal.Client # type:ignore[name-defined]

    def __init__(self, uid:Optional[str], flags:int):
        # Postponed import
        global ECal, ICalGLib
        from gi import require_version as gi_require_version
        gi_require_version('EDataServer', '1.2')
        from gi.repository import EDataServer
        gi_require_version('ECal', '2.0')
        from gi.repository import ECal
        gi_require_version('ICalGLib', '3.0')
        from gi.repository import ICalGLib

        self.flags = flags
        if self.stores_events() == self.stores_todos():
            raise ValueError('Evolution calendar needs to store exactly one of Events or Todos')

        registry = EDataServer.SourceRegistry.new_sync()
        # Get enabled sources storing the correct type
        if self.stores_events():
            extn = EDataServer.SOURCE_EXTENSION_CALENDAR
            src_type = ECal.ClientSourceType.EVENTS # type:ignore[name-defined]
        else:
            extn = EDataServer.SOURCE_EXTENSION_TASK_LIST
            src_type = ECal.ClientSourceType.TASKS # type:ignore[name-defined]

        if uid is None:
            # Provide a list of uids to help the user
            print('Warning: Calendar uid not set, please choose from the list below', file=stderr)
            srcs = EDataServer.SourceRegistry.list_enabled(registry, extn)
            for src in srcs:
                print('  ', src.get_uid(), ':', src.get_display_name(), file=stderr)
            raise ValueError('EDS calendar uid not set')

        src = EDataServer.SourceRegistry.ref_source(registry, uid)
        if src is None:
            raise ValueError('EDS calendar uid "{:s}" not found'.format(uid))
        if not EDataServer.SourceRegistry.check_enabled(registry, src):
            raise ValueError('EDS calendar uid "{:s}" not enabled'.format(uid))

        self.__eds_client = ECal.Client().connect_sync(source=src, source_type=src_type, wait_for_connected_seconds=self.CONNECTION_TIMEOUT) # type:ignore[name-defined]
        if self.__eds_client is None:
            raise ValueError('Error connecting to EDS calendar uid "{:s}"'.format(uid))

        # Read source properties to set some connector properties
        self.displayname = src.get_display_name()
        if not src.get_writable():
            self.flags |= CalendarConnector.READONLY

        suc,comps = self.__eds_client.get_object_list_sync('#t')# Search #t=True
        if not suc:
            raise ValueError('Failed getting components from EDS calendar')

        # Create an iCalendar object from the retrieved components
        self.cal = iCalendar()
        for comp in comps:
            ical_comp = iCalendar.from_ical(comp.as_ical_string())
            self.cal.add_component(ical_comp)


    def add_entry(self, entry:Union[iEvent,iTodo]) -> Union[iEvent,iTodo]:
        # Create a new entry component on the server, and locally.
        en_str = entry.to_ical().decode('utf-8')
        comp = ICalGLib.Component.new_from_string(en_str) # type:ignore[name-defined]
        suc = self.__eds_client.create_object_sync(comp, ECal.OperationFlags.NONE) # type:ignore[name-defined]
        if not suc:
            # !! While code is in development, just exit on failure.
            # May change to something "friendlier" later...
            print('Error creating entry on Evolution Data Server')
            exit(-1)

        # Save to local store
        self.cal.add_component(entry)
        return entry


    def update_entry(self, entry:Union[iEvent,iTodo]) -> None:
        # Update an entry component in the calendar data and store it.
        # Entry struct has been modified, so can just send update to server.
        en_str = entry.to_ical().decode('utf-8')
        comp = ICalGLib.Component.new_from_string(en_str) # type:ignore[name-defined]
        suc = self.__eds_client.modify_object_sync(comp, ECal.ObjModType.ALL, ECal.OperationFlags.NONE) # type:ignore[name-defined]
        if not suc:
            # !! While code is in development, just exit on failure.
            # May change to something "friendlier" later...
            print('Error updating entry on Evolution Data Server')
            exit(-1)


    def delete_entry(self, entry:Union[iEvent,iTodo]) -> None:
        # Delete entry component from server and in local copy.
        suc = self.__eds_client.remove_object_sync(entry['UID'], None, ECal.ObjModType.ALL, ECal.OperationFlags.NONE) # type:ignore[name-defined]
        if not suc:
            # !! While code is in development, just exit on failure.
            # May change to something "friendlier" later...
            print('Error deleting entry on Evolution Data Server')
            exit(-1)
        self.cal.subcomponents.remove(entry) # delete local copy


#
# Helper class for repeats_in_range() function (below)
#
class RepeatInfo:
    DAY_ABBR = ('MO','TU','WE','TH','FR','SA','SU')
    SUBDAY_REPEATS = ('HOURLY','MINUTELY','SECONDLY')

    _isby_weekday_in_month = False
    start_in_rng = None # type: dt_date

    def __init__(self, event:iEvent, start:dt_date, stop:dt_date):
        # Note: start argument is INclusive, stop is EXclusive
        e_dtst = event['DTSTART']
        if 'TZID' in e_dtst.params:
            raise RepeatUnsupportedError('Unsupported repeat with TZID')
        self.dtstart = e_dtst.dt
        rrule = event['RRULE']
        self.subday_rpt = rrule['FREQ'][0] in self.SUBDAY_REPEATS
        self.timed_rpt = self.subday_rpt or isinstance(self.dtstart, dt_datetime)
        if self.timed_rpt:
            # Make sure time and timezone are set
            self.start = date_to_datetime(self.dtstart, True)
            if self.subday_rpt:
                # Need to do calculations in UTC (e.g. for summer time changes)
                self.start = self.start.astimezone(timezone.utc)
            try:
                start = date_to_datetime(start, True).astimezone(timezone.utc)
            except OverflowError:
                if start.year==1:
                    # Underflow due to timezone, set start to earliest time pos
                    start = dt_datetime(1,1,1,tzinfo=timezone.utc)
                else:
                    raise
            stop = date_to_datetime(stop, True).astimezone(timezone.utc)
        else:
            self.start = self.dtstart

        # Quickly eliminate some out-of-range cases
        if stop is not None and dt_lte(stop, self.start):
            # self.start_in_rng left with default value of None
            return
        if start is not None and 'UNTIL' in rrule and dt_lt(rrule['UNTIL'][0],start):
            # self.start_in_rng left with default value of None
            return

        if rrule['FREQ'][0]=='YEARLY' and self.start.month==2 and self.start.day==29 and ('BYMONTH' not in rrule or 'BYDAY' not in rrule):
            raise RepeatUnsupportedError('Unsupported YEARLY (29/2) {} in RRULE'.format(self.start))

        self._set_freq(rrule)
        if 'EXDATE' in event:
            self._set_exdates(event['EXDATE'])
        else:
            self.exdates = None
        if self._isby_weekday_in_month:
            self._set_start_in_rng_byweekdayinmonth(start)
        else:
            self._set_start_in_rng(start)
        self._set_stop(rrule, stop)


    def _set_freq(self, rrule:vRecur) -> None:
        # Set repeat frequency (self.delta).
        # Called during construction.
        freq = rrule['FREQ'][0]
        interval = int(rrule['INTERVAL'][0]) if 'INTERVAL' in rrule else 1
        if interval <= 0: # Protect against corrupt data giving infinite loops
            raise ValueError('Zero interval for repeat')
        if 'BYMONTH' in rrule and len(rrule['BYMONTH'])>1:
            raise RepeatUnsupportedError('Unsupported multi-BYMONTH {} in RRULE'.format(rrule['BYMONTH']))
        if 'BYDAY' in rrule and freq not in {'YEARLY','MONTHLY','WEEKLY'}:
            raise RepeatUnsupportedError('Unsupported BYDAY for {} repeat'.format(freq))
        if 'BYYEARDAY' in rrule:
            raise RepeatUnsupportedError('Unsupported BYYEARDAY in RRULE')
        if 'BYMONTHDAY' in rrule:
            if (freq!='YEARLY' or 'BYMONTH' not in rrule):
                raise RepeatUnsupportedError('Unsupported BYMONTHDAY in RRULE (not YEARLY/BYMONTH)')
            # If we get here, it's YEARLY/BYMONTH/BYMONTHDAY
            if len(rrule['BYMONTH'])>1:
                raise RepeatUnsupportedError('Unsupported BYMONTHDAY, multi-BYMONTH in RRULE')
            if len(rrule['BYMONTHDAY'])>1:
                raise RepeatUnsupportedError('Unsupported multi-BYMONTHDAY in RRULE')
            bmd_day = int(rrule['BYMONTHDAY'][0])
            bmd_month = int(rrule['BYMONTH'][0])
            if bmd_day!=self.start.day or bmd_month!=self.start.month:
                raise RepeatUnsupportedError('Unsupported YEARLY/BYMONTH/BYMONTHDAY != DTSTART in RRULE')

        if 'BYSETPOS' in rrule:
            raise RepeatUnsupportedError('Unsupported BYSETPOS in RRULE')
        if 'BYHOUR' in rrule:
            raise RepeatUnsupportedError('Unsupported BYHOUR in RRULE')
        if 'BYMINUTE' in rrule:
            raise RepeatUnsupportedError('Unsupported BYMINUTE in RRULE')
        if 'BYSECOND' in rrule:
            raise RepeatUnsupportedError('Unsupported BYSECOND in RRULE')
        if 'BYWEEKNO' in rrule:
            raise RepeatUnsupportedError('Unsupported BYWEEKNO in RRULE')
        if freq=='YEARLY':
            self._set_yearly(rrule, interval)
        elif freq=='MONTHLY':
            self._set_monthly(rrule, interval)
        elif freq=='WEEKLY':
            self._set_weekly(rrule, interval)
        elif freq=='DAILY':
            self._set_daily(interval)
        elif freq=='HOURLY':
            self._set_hourly(interval)
        elif freq=='MINUTELY':
            self._set_minutely(interval)
        elif freq=='SECONDLY':
            self._set_secondly(interval)
        else: # unrecognised freq - skip entry
            raise RepeatUnsupportedError('Unknown FREQ {:s} in RRULE'.format(freq))


    def _set_yearly(self, rrule:vRecur, interval:int) -> None:
        # Called on construction if a simple yearly repeat
        self.delta = relativedelta(years=interval)
        if 'BYDAY' in rrule:
            if 'BYMONTH' not in rrule:
                raise RepeatUnsupportedError('YEARLY repeat with BYDAY without BYMONTH')
            bymonth = rrule['BYMONTH']
            if len(bymonth)>1:
                raise RepeatUnsupportedError('YEARLY repeat with multiple BYMONTH values')
            if int(bymonth[0]) != self.dtstart.month:
                raise RepeatUnsupportedError('YEARLY BYMONTH/BYDAY repeat with month not matching DTSTART')
            self._set_byweekdayinmonth(rrule['BYDAY'])


    def _set_monthly(self, rrule:vRecur, interval:int) -> None:
        # Called on construction if a simple monthly repeat
        self.delta = relativedelta(months=interval)
        if 'BYDAY' in rrule:
            self._set_byweekdayinmonth(rrule['BYDAY'])
        elif self.start.day>28:
            raise RepeatUnsupportedError('Unsupported MONTHLY (day>28) {} in RRULE'.format(self.start))


    def _set_byweekdayinmonth(self, rrule_byday:list) -> None:
        # Set variables for BYDAY rrule for "by weekday in month" repeats.
        # E.g. '-1SU' -> last Sunday of month
        if len(rrule_byday)!=1:
            raise RepeatUnsupportedError('Unsupported multiple days in BYDAY in RRULE')
        byday_rule = rrule_byday[0]
        try:
            self.byday_day = self.DAY_ABBR.index(byday_rule[-2:])
            self.byday_idx = int(byday_rule[:-2])
        except ValueError:
            raise RepeatUnsupportedError('Unsupported BYDAY {} in MONTHLY/YEARLY repeat'.format(byday_rule))
        abs_byday = abs(self.byday_idx)
        if abs_byday==0 or abs_byday>5:
            print('Notice: Impossible BYDAY rule: {}'.format(byday_rule), file=stderr)
            raise RepeatImpossibleError()
        if (abs_byday==5):
            raise RepeatUnsupportedError('Unsupported BYDAY {} in MONTHLY/YEARLY repeat'.format(byday_rule))
        # Test to see if DTSTART matches RRULE
        if self.firstday_to_byweekdayinmonth(self.dtstart.replace(day=1)) != self.dtstart:
            raise RepeatUnsupportedError('Given start date does not match RRULE')
        self._isby_weekday_in_month = True


    def _set_weekly(self, rrule:vRecur, interval:int) -> None:
        # Called on construction if a weekly repeat.
        # Try to also handle cases where rrule gives multiple days/startweek.
        days_in_week = 0 # bitmask to be created
        diw_from_st = 1<<self.start.weekday()
        if 'BYDAY' in rrule:
            for d in rrule['BYDAY']:
                try:
                    days_in_week |= 1<<self.DAY_ABBR.index(d)
                except ValueError:
                     raise RepeatUnsupportedError('Unsupported WEEKLY/BYDAY {} in RRULE'.format(rrule['BYDAY']))
            if days_in_week and not days_in_week&diw_from_st:
                # ?? Days are listed, but start day is not among them
                # Ambiguous - raise error
                raise ValueError('First day of weekly repeat not included in repeat day')
        if days_in_week==0 or days_in_week == diw_from_st:
            # Just one day, so a simple delta will work.
            self.delta = timedelta(days=7*interval)
            return

        # Get start of week if present, otherwise default is Monday
        # Don't bother if interval == 1 since makes no difference
        st_wk = 1
        if interval>1 and 'WKST' in rrule:
            st_wk <<= self.DAY_ABBR.index(rrule['WKST'][0])

        # Accumulte list of deltas to add to loop through days
        self.delta = []
        diw_bit = diw_from_st
        i = 0
        while True:
            i += 1
            diw_bit = (diw_bit<<1)%127 # rotate bits left
            if diw_bit==st_wk:
                i+=7*(interval-1)
            if diw_bit & days_in_week:
                self.delta.append(timedelta(days=i))
                i = 0
            if diw_bit==diw_from_st:
                break


    def _set_daily(self, interval:int) -> None:
        # Called on construction if a simple daily repeat
        self.delta = timedelta(days=interval)


    def _set_hourly(self, interval:int) -> None:
        # Called on construction if a simple hourly repeat
        self.delta = timedelta(hours=interval)


    def _set_minutely(self, interval:int) -> None:
        # Called on construction if a simple minutely repeat
        self.delta = timedelta(minutes=interval)


    def _set_secondly(self, interval:int) -> None:
        # Called on construction if a simple secondly repeat
        self.delta = timedelta(seconds=interval)


    def _set_exdates(self, exdate) -> None:
        # Initialise object's exdates variable, given an exdate structure.
        # exdate argument is in format of exdate from an ical event, it
        # might be a list, or might not...
        if self.timed_rpt:
            conv = lambda x:date_to_datetime(x.dt,True) if isinstance (x.dt,dt_datetime) else x.dt
        else:
            conv = lambda x:x.dt
        if isinstance(exdate,list):
            l = [dl.dts for dl in exdate]
            self.exdates = set([conv(t[i]) for t in l for i in range(len(t))])
        else:
            l = exdate.dts
            self.exdates = set([conv(t) for t in l])


    def _set_start_in_rng(self, start:dt_date) -> None:
        # Set start date within given range (so will be on/after 'dtstart')
        # N.B. At this point 'start' may be a date or datetime (matching timed_rpt)
        self.start_in_rng = self.start # first occurence of event
        if isinstance(self.delta, list):
            self.delta_index = 0
        if start is not None:
            # We try to jump to first entry in range
            # First compute d, distance from the range
            if isinstance(self.delta, list):
                # Note: lists of deltas only used (so far) for weekly repeats
                d = start - self.start
                if d>timedelta(0): # start provided was after first repeat, so inc
                    # Want to do as much as possible in one increment
                    per = reduce(lambda x,y:x+y,self.delta) # sum of delta
                    s = d//per
                    self.start_in_rng += per * s
                # After approximate jump, clear any extras.
                i = 0
                while dt_lt(self.start_in_rng,start) or self.is_exdate(self.start_in_rng):
                    self.start_in_rng += self.delta[i]
                    i = (i+1)%len(self.delta)
                self.delta_index = i
            else: # single delta
                self._do_initial_jump(start)
                # After approximate jump, clear any extras.
                while dt_lt(self.start_in_rng,start) or self.is_exdate(self.start_in_rng):
                    self.start_in_rng += self.delta


    def _set_start_in_rng_byweekdayinmonth(self, start:dt_date) -> None:
        # Set start date within given range (so will be on/after 'dtstart')
        # N.B. At this point 'start' may be a date or datetime (matching timed_rpt)
        self.start_in_rng = self.start.replace(day=1) # first 1st of month for of event
        if start is not None:
            self._do_initial_jump(start.replace(day=1))
            # After approximate jump, clear any extras.
            while dt_lt(self.firstday_to_byweekdayinmonth(self.start_in_rng),start):
                self.start_in_rng += self.delta
            while self.is_exdate(self.firstday_to_byweekdayinmonth(self.start_in_rng)):
                self.start_in_rng += self.delta


    def _do_initial_jump(self, target:dt_date) -> None:
        # Used by _set_start_in_rng_***() functions to initialise repeats.
        # Updates self.start_in_rng to get close to target date/time based on
        # jumps of self.delta (which must be a timedelta or a relativedelta).
        d = target - self.start_in_rng
        if d > timedelta(0): # start provided was after first repeat, so inc
            # Want to do as much as possible in one increment
            if isinstance(self.delta, timedelta):
                s = ceil(d/self.delta)
            else:
                # self.delta is a relativedelta (=> yearly or monthly repeat)
                d = relativedelta(target, self.start_in_rng)
                s = ceil((d.years*12 + d.months)/(self.delta.years*12 + self.delta.months))
            self.start_in_rng += self.delta * s


    def _set_stop(self, rrule:vRecur, stop:dt_date) -> None:
        # Set stop date in range (i.e. before 'stop' parameter).
        # Note, 'stop' parameter is exclusive (this is more usual)
        # but 'UNTIL' field in iCal is inclusive (according to standard).
        # Internally RepeatInfo class will use an exclusive stop, so:
        #   - Name it stop_exc for clarity
        #   - Take care when using 'UNTIL'
        # N.B. At this point 'stop' may be a date or datetime (matching timed_rpt)
        until = rrule['UNTIL'][0] if 'UNTIL' in rrule else None
        if self.timed_rpt and until:
            until = date_to_datetime(until, True).astimezone(timezone.utc)
        if until is None or (stop is not None and dt_lte(stop, until)):
            # Repeats go beyond stop date - just use stop parameter
            # if timed entry, make stop include timezone
            self.stop_exc = stop
        elif isinstance(until, dt_datetime):
            self.stop_exc = until + timedelta(milliseconds=1)
        else:
            # until is a date only
            self.stop_exc = dt_datetime.combine(until,dt_time(microsecond=1))
        count = rrule['COUNT'][0] if 'COUNT' in rrule else None
        if count is not None:
            if self.exdates is not None:
                raise RepeatUnsupportedError('Unsupported COUNT & EXDATE') # !! fix me
            if self._isby_weekday_in_month:
                last_by_count = self.start.replace(day=1) + (self.delta*(count-1))
                last_by_count = self.firstday_to_byweekdayinmonth(last_by_count)
            elif isinstance(self.delta, list):
                di,md = divmod(count-1, len(self.delta))
                last_by_count = self.start
                last_by_count += di*reduce(lambda x,y:x+y,self.delta) # sum()
                if md:
                    last_by_count += reduce(lambda x,y:x+y,self.delta[:md])
            else:
                last_by_count = self.start + (self.delta*(count-1))
            if self.stop_exc is None or dt_lt(last_by_count,self.stop_exc):
                self.stop_exc = last_by_count+timedelta(milliseconds=1) if isinstance(last_by_count,dt_datetime) else dt_datetime.combine(last_by_count,dt_time(microsecond=1))
        if self.stop_exc is None:
            raise RuntimeError('Unbounded repeats will lead to infinite list')


    def is_exdate(self, dt:dt_date) -> bool:
        # Returns True if dt is an excluded date, False otherwise.
        if self.exdates is None:
            return False
        if dt in self.exdates:
            return True
        # RFC-5545 is not very clear here - just says exclude 'any start
        # DATE-TIME values specified by "EXDATE" properties' (Sec 3.8.5.1).
        # What about DATE values if entry has a start time?
        # Examining other applications, have decided: if dt is a datetime,
        # and repeat is daily/weekly/monthly/yearly, return True if date
        # component is in exdates.
        return self.timed_rpt and not self.subday_rpt and dt.date() in self.exdates


    def firstday_to_byweekdayinmonth(self, dt:dt_date) -> dt_date:
        # Function to map dt giving first day of the month to the
        # "byday" repeat day (e.g. "last Sunday of the month").
        # Assumes the byday has been set up in the class variables
        # byday_idx and byday_day.
        # *Precondition*: dt is 1st day of month where we want to get the date
        if self.byday_idx>0:
            retday = 1+(self.byday_day-dt.weekday())%7+(self.byday_idx-1)*7
        else:
            retday = monthrange(dt.year,dt.month)[1] # no of days in month
            lastday_idx = (dt.weekday()+retday-1)%7 # daynumber of last day
            delta = (self.byday_day-lastday_idx)%7
            if delta!=0:
                retday += delta-7
            retday += (self.byday_idx+1)*7
        return dt.replace(day=retday)


    def __iter__(self) -> 'RepeatIter_simpledelta':
        # Return an iterator for this RepeatInfo
        if self._isby_weekday_in_month:
            return RepeatIter_byweekdayinmonth(self)
        if self.start_in_rng is not None and isinstance(self.delta, list):
            return RepeatIter_multidelta(self)
        return RepeatIter_simpledelta(self)


# Exception used to indicate need to used fallback repeat calculation
class RepeatUnsupportedError(Exception):
    pass

# Exception used to indicate a repeat can never occur, e.g. 32nd day of Jan
class RepeatImpossibleError(Exception):
    pass


class RepeatIter_simpledelta:
    # Iterator class for RepeatInfo where we can just use a simple delta.

    def __init__(self, rinfo:RepeatInfo):
        self.rinfo = rinfo
        self.dt = rinfo.start_in_rng

    def __iter__(self) -> 'RepeatIter_simpledelta':
        # Standard method for iterators
        return self

    def __next__(self) -> dt_date:
        # Return date/dattime for next occurence in range.
        # Excluded dates are taken into account.
        # Raises StopIteration at end of occurence list.
        if self.dt is None or dt_lte(self.rinfo.stop_exc,self.dt):
            raise StopIteration
        r = self.dt
        while True:
            self.dt += self.rinfo.delta
            if not self.rinfo.is_exdate(self.dt):
                break
        if self.rinfo.subday_rpt:
            r = r.astimezone(get_local_tz())
        return r


class RepeatIter_multidelta(RepeatIter_simpledelta):
    # Iterator class for RepeatInfo where we have different deltas
    # (e.g. we may have different gaps between occurences, such as
    # a weekly repeat that occurs on Mondays and Wednesdays).

    def __init__(self, rinfo:RepeatInfo):
        super().__init__(rinfo)
        self.i = rinfo.delta_index

    def __next__(self) -> dt_date:
        # Return date/datetime for next occurence in range.
        # Excluded dates are taken into account.
        # Raises StopIteration at end of occurence list.
        if self.dt is None or dt_lte(self.rinfo.stop_exc,self.dt):
            raise StopIteration
        r = self.dt
        while True:
            self.dt += self.rinfo.delta[self.i]
            self.i = (self.i+1)%len(self.rinfo.delta)
            if not self.rinfo.is_exdate(self.dt):
                break
        if self.rinfo.subday_rpt:
            r = r.astimezone(get_local_tz())
        return r


class RepeatIter_byweekdayinmonth(RepeatIter_simpledelta):
    # Iterator class for RepeatInfo where the repeat is by weekday in month.
    # E.g. first Saturday of every month; or last Friday in October.

    def __init__(self, rinfo:RepeatInfo):
        self.rinfo = rinfo
        self.dt_toret = self.rinfo.firstday_to_byweekdayinmonth(rinfo.start_in_rng)
        self.dt_ref = rinfo.start_in_rng

    def __next__(self) -> dt_date:
        # Return date/datetime for next occurence in range.
        # Excluded dates are taken into account.
        # Raises StopIteration at end of occurence list.
        if self.dt_toret is None or dt_lte(self.rinfo.stop_exc, self.dt_toret):
            raise StopIteration
        ret = self.dt_toret
        while True:
            self.dt_ref += self.rinfo.delta
            self.dt_toret = self.rinfo.firstday_to_byweekdayinmonth(self.dt_ref)
            if not self.rinfo.is_exdate(self.dt_toret):
                break
        if self.rinfo.subday_rpt:
            ret = ret.astimezone(get_local_tz())
        return ret


def merge_repeating_entries_sort(target:list, ev:iEvent, start:dt_date, stop:dt_date) -> None:
    # Given a sorted list of occurrences, 'target', and a single
    # repeating event 'ev', splice the repeats of ev from 'start'
    # to 'stop' into 'target', keeping it sorted.
    # !! A potential spot for optimisation?
    try:
        ev_reps = repeats_in_range(ev, start, stop)
    except ValueError as err:
        print('Warning: {:s} - ignoring repeat'.format(str(err)), file=stderr)
        dt_st = ev['DTSTART'].dt
        if dt_lt(dt_st,start) or dt_lte(stop,dt_st):
            return
        ev_reps = [dt_st]
    i,j = 0,0
    end_i = len(target)
    end_j = len(ev_reps)
    while i<end_i and j<end_j:
        if dt_lt(ev_reps[j],target[i][1]):
            target.insert(i,(ev,ev_reps[j]))
            j += 1
            end_i +=1
        i += 1
    if j<end_j:
        target.extend([(ev,dt) for dt in ev_reps[j:]])


def first_occ(rrstr:str, dtstart:dt_date) -> dt_date:
    # Returns the date or datetime of the first occurrence of an event,
    # given an rrule and an (earliest possible) start date.
    # Does not take account of excluded dates.
    rr = rrulestr(rrstr, dtstart=dtstart)
    has_time = isinstance(dtstart, dt_datetime)
    st = dtstart if has_time else dt_datetime.combine(dtstart, dt_time())
    ret = rr.after(st, inc=True)
    if ret and not has_time:
        ret = ret.date()
    return ret


def repeats_in_range_with_rrstr(ev:iEvent, start:dt_date, stop:dt_date) -> list:
    # Get repeat dates within given range using dateutil.rrule module.
    # Slow, but comprehensive. Used as a fallback from repeats_in_range()
    # when quick methods can't be used.
    # Repeats are super clunky.
    # Can caching results help?
    dt = ev['DTSTART'].dt
    rr_for_str = ev['RRULE'] # reference to rrule
    is_hr_min_sec = rr_for_str['FREQ'][0] in RepeatInfo.SUBDAY_REPEATS
    is_timed = is_hr_min_sec or isinstance(dt,dt_datetime)
    until_set = False
    if is_timed:
        dt = date_to_datetime(dt,True) # Ensure timed & with timezone
        if 'UNTIL' in rr_for_str:
            # Make sure until is timed with timezone
            until = date_to_datetime(rr_for_str['UNTIL'][0],True)
            until = until.astimezone(timezone.utc) # rrulestr needs UTC
            rr_for_str = deepcopy(rr_for_str) # So we don't modify the event
            rr_for_str['UNTIL'][0] = until
            until_set = True
    if is_hr_min_sec:
        # We get rrule to do calculations in UTC, so summer time changes
        # don't cause errors. We'll convert back to local time later.
        dt = dt.astimezone(timezone.utc)
    rrstr = rr_for_str.to_ical().decode('utf-8')
    # Hacky workaround because in some package/version combinations,
    # icalendar.to_ical(), returned UNTIL value lacks timezone 'Z'.
    if until_set:
        i_until_st = rrstr.find('UNTIL=')+6
        i_until_end = rrstr.find(';', i_until_st)
        if i_until_end == -1:
            i_until_end = len(rrstr)
        i_until_z = rrstr.find('Z', i_until_st)
        if i_until_z == -1 or i_until_z > i_until_end:
            rrstr = rrstr[:i_until_end] + 'Z' + rrstr[i_until_end:]
    has_exd = 'EXDATE' in ev
    rr = rrulestr(rrstr,dtstart=dt,forceset=has_exd)
    st = date_to_datetime(start, is_timed)
    sp = date_to_datetime(stop, is_timed)
    sp -= timedelta(milliseconds=1)
    ret = rr.between(after=st,before=sp,inc=True)
    if not is_timed:
        ret = [d.date() for d in ret]
    elif is_hr_min_sec:
        # After doing calculations in UTC, convert results to local time
        ret = [d.astimezone(get_local_tz()) for d in ret]
    if has_exd:
        exdate_list = Calendar.caldatetime_tree_to_dt_list(ev['EXDATE'])
        for exdt in exdate_list:
            if is_timed:
                if isinstance(exdt, dt_datetime):
                    exdt = date_to_datetime(exdt, True)
                    ret = [d for d in ret if d!=exdt]
                else:
                    ret = [d for d in ret if d.date()!=exdt]
            else:
                ret = [d for d in ret if d!=exdt]
    return ret


def repeats_in_range(ev:iEvent, start:dt_date, stop:dt_date) -> list:
    # Given a repeating event ev, return list of occurrences from
    # dates start to stop. N.B. start/stop must be dates, not datetimes.
    if isinstance(start,dt_datetime) or isinstance(stop,dt_datetime):
        raise TypeError('Start/stop must be dates, not datetimes')
    try:
        r_info = RepeatInfo(ev, start, stop)
    except RepeatImpossibleError:
        return list() # empty list
    except RepeatUnsupportedError as err:
        # RepeatInfo doesn't handle this type of repeat.
        # Fall back to using rrule - more complete, but slower for simple repeats
        print('Notice: Fallback to unoptimised repeat for "{:s}" ({:s})'.format(ev['SUMMARY'],str(err)), file=stderr)
        return repeats_in_range_with_rrstr(ev, start, stop)
    ret = list(iter(r_info))
    # Uncomment the next two lines to test calculated values (slow!)
    #if ret != repeats_in_range_with_rrstr(ev, start, stop):
    #    print('Error: Wrong repeats for "{:s}"'.format(ev['SUMMARY']), file=stderr)
    return ret
