# -*- coding: utf-8 -*-
#
# pygenda_calendar.py
# Connects to agenda data provider - either an ics file or CalDAV server.
#
# Copyright (C) 2022 Matthew Lewis
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


from icalendar import Calendar as iCalendar, Event as iEvent, vRecur
from datetime import timedelta, datetime as dt_datetime, time as dt_time, date as dt_date, timezone
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrulestr
from sys import stderr
from uuid import uuid1
from pathlib import Path
from functools import reduce
from os import stat as os_stat, chmod as os_chmod, rename as os_rename, path as os_path
import stat
from time import monotonic as time_monotonic
import tempfile
from typing import Optional

# Pygenda components
from .pygenda_config import Config
from .pygenda_util import dt_lt, dt_lte, datetime_to_date
from .pygenda_entryinfo import EntryInfo


# Interface base class to connect to different data sources.
# Used by Calendar class (below).
class CalendarConnector:
	def add_entry(self, event:iEvent) -> None:
		# Add a new entry component to the calendar data and store it.
		print('Warning: Add entry not implemented', file=stderr)

	def update_entry(self, event:iEvent) -> None:
		# Update an entry component in the calendar data and store it.
		print('Warning: Update not implemented', file=stderr)

	def delete_entry(self, event:iEvent) -> None:
		# Delete entry component to the calendar data and remove from store.
		print('Warning: Delete not implemented', file=stderr)


# Singleton class for calendar data access/manipulation
class Calendar:
	_entry_norep_list_sorted = None
	_entry_rep_list = None

	@classmethod
	def init(cls) -> None:
		# Calendar connector initialisation.
		# Can take a long time, since it loads/sorts calendar data.
		# Best called in background after GUI is started, or startup can be slow.
		Config.set_defaults('calendar',{
			'ics_file': None,
			'caldav_server': None,
			'caldav_username': None,
			'caldav_password': None,
			'caldav_calendar': None
		})

		# Read config values to get type of data source connector
		filename = Config.get('calendar','ics_file')
		caldav_server = Config.get('calendar','caldav_server')
		if caldav_server is not None:
			# Use either server or file, not both (at least for now)
			assert(filename is None)
			user = Config.get('calendar','caldav_username')
			passwd = Config.get('calendar','caldav_password')
			calname = Config.get('calendar','caldav_calendar')
			cls.calConnector = CalendarConnectorCalDAV(caldav_server,user,passwd,calname)
		else:
			# If no server given, use an ics file.
			# Use either the provided filename or a default name.
			if filename is None:
				filename = '{}/{}'.format(Config.conf_dirname,Config.DEFAULT_ICS_FILENAME)
			else:
				# Expand '~' (so it can be used in config file)
				filename =  os_path.expanduser(filename)
			# Create a connector for that file
			cls.calConnector = CalendarConnectorICSfile(filename)

		if cls.calConnector.cal.is_broken:
			print('Warning: Non-conformant ical file', file=stderr)


	@staticmethod
	def gen_uid() -> str:
		# Generate a UID for iCal elements (required element)
		uid = 'Pygenda-{}'.format(uuid1())
		return uid


	@classmethod
	def new_entry(cls, e_inf:EntryInfo) -> None:
		# Add a new iCal entry with content from event info object
		ev = iEvent()
		ev.add('UID', Calendar.gen_uid()) # Required
		# DateTime utcnow() function doesn't include TZ, so use now(tz.utc)
		utcnow = dt_datetime.now(timezone.utc)
		ev.add('DTSTAMP', utcnow) # Required
		ev.add('CREATED', utcnow) # Optional
		ev.add('SUMMARY', e_inf.desc)
		ev.add('DTSTART', e_inf.start_dt)
		cls._event_add_end_dur_from_info(ev,e_inf)

		# Repeats
		if e_inf.rep_type is not None and e_inf.rep_inter>0:
			cls._event_add_repeat_from_info(ev,e_inf)
			cls._entry_rep_list = None # Clear rep cache as modified
		else:
			cls._entry_norep_list_sorted = None # Clear norep cache as modified

		cls._event_set_status_from_info(ev, e_inf)
		cls._event_set_location_from_info(ev, e_inf)

		cls.calConnector.add_entry(ev) # Write to store


	@classmethod
	def new_entry_from_example(cls, exev:iEvent, dt_start:dt_date=None) -> None:
		# Add a new iCal entry to store given an iEvent as a "template".
		# Replace UID, timestamp etc. to make it a new event.
		# Potentially override exev's date/time with a new one.
		# Use to implement pasting events into new days/timeslots.
		ev = iEvent()
		ev.add('UID', Calendar.gen_uid()) # Required
		utcnow = dt_datetime.now(timezone.utc)
		ev.add('DTSTAMP', utcnow) # Required
		# Since it has a new UID, we consider it a new entry
		ev.add('CREATED', utcnow) # Optional
		summ = exev['SUMMARY'] if 'SUMMARY' in exev else None
		if not summ:
			summ = 'New entry' # fallback summary
		ev.add('SUMMARY', summ)
		ex_dt_start = exev['DTSTART'].dt if 'DTSTART' in exev else None
		if dt_start:
			if ex_dt_start:
				new_dt_start = ex_dt_start.replace(year=dt_start.year,month=dt_start.month,day=dt_start.day)
			else:
				new_dt_start = dt_start
		elif ex_dt_start:
			new_dt_start = ex_dt_start
		else:
			raise ValueError('Entry has no date/time')
		ev.add('DTSTART', new_dt_start)
		if 'DURATION' in exev:
			ev.add('DURATION', exev['DURATION'])
		elif ex_dt_start and 'DTEND' in exev:
			ex_dt_end = exev['DTEND'].dt
			if isinstance(ex_dt_start,dt_datetime) and (ex_dt_start.tzinfo is None or ex_dt_end.tzinfo is None):
				# If one tzinfo is None, make both None, so subtraction work
				ex_dt_start = ex_dt_start.replace(tzinfo=None)
				ex_dt_end = ex_dt_end.replace(tzinfo=None)
			dur = ex_dt_end - ex_dt_start
			ev.add('DTEND', new_dt_start + dur)
		if 'LOCATION' in exev:
			ev.add('LOCATION', exev['LOCATION'])
		cls.calConnector.add_entry(ev) # Write to store
		cls._entry_norep_list_sorted = None # Clear norep cache as modified


	@classmethod
	def update_entry(cls, ev:iEvent, e_inf:EntryInfo) -> None:
		# Update event using details from EntryInfo e_inf.
		clear_rep = False
		clear_norep = False

		if 'UID' not in ev:
			ev.add('UID', Calendar.gen_uid()) # Should be present
		# DateTime utcnow() function doesn't include TZ, so use now(tz.utc)
		utcnow =  dt_datetime.now(timezone.utc)
		try:
			ev['DTSTAMP'].dt = utcnow
		except KeyError:
			# Entry had no DTSTAMP (note: DTSTAMP required by icalendar spec)
			ev.add('DTSTAMP', utcnow)
		try:
			ev['LAST-MODIFIED'].dt = utcnow
		except KeyError:
			# Entry had no LAST-MODIFIED - add one
			ev.add('LAST-MODIFIED', utcnow)
		try:
			ev['SUMMARY'] = e_inf.desc
		except KeyError:
			# Entry had no SUMMARY
			ev.add('SUMMARY', e_inf.desc)

		# DTSTART - delete & re-add so type (DATE vs. DATE-TIME) is correct
		# (Also, Q: if comparing DTSTARTs with different TZs, how does != work?)
		if 'DTSTART' in ev:
			del(ev['DTSTART'])
		ev.add('DTSTART', e_inf.start_dt)

		# Duration or Endtime - first delete existing
		if 'DURATION' in ev:
			del(ev['DURATION'])
		if 'DTEND' in ev:
			del(ev['DTEND'])
		# Then add new end time/duration (if needed)
		cls._event_add_end_dur_from_info(ev,e_inf)

		# Repeats (including exception dates)
		if 'RRULE' in ev:
			del(ev['RRULE'])
			clear_rep = True
		else:
			clear_norep = True
		if 'EXDATE' in ev:
			del(ev['EXDATE'])
		if e_inf.rep_type is not None and e_inf.rep_inter>0:
			cls._event_add_repeat_from_info(ev,e_inf)
			clear_rep = True
		else:
			clear_norep = True

		# Other properties: status (cancelled, tentative, etc.), location
		cls._event_set_status_from_info(ev, e_inf)
		cls._event_set_location_from_info(ev, e_inf)

		# This needs optimising - some cases cause too much cache flushing !!
		if clear_norep:
			cls._entry_norep_list_sorted = None
		if clear_rep:
			cls._entry_rep_list = None

		cls.calConnector.update_entry(ev) # Write to store


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
		elif isinstance(e_inf.start_dt, dt_date) and isinstance(e_inf.end_dt, dt_date):
			# start & end are both dates (not times) => this is a day entry
			if e_inf.end_dt > e_inf.start_dt: # sanity check
				ev.add('DTEND', e_inf.end_dt)


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
		if e_inf.rep_bymonthday is not None:
			rr_options['BYMONTHDAY'] = [e_inf.rep_bymonthday]
		ev.add('RRULE', rr_options)

		# Add exception date/times
		if e_inf.rep_exceptions:
			e_prm = {'VALUE':'DATE'} # ? Bug in icalendar 4.0.9 means we need to add VALUE parameter
			# Adding multiple EXDATE fields seems to be most compatible
			for rex in e_inf.rep_exceptions:
				ev.add('EXDATE', rex, parameters=e_prm)

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
	def _event_set_status_from_info(ev:iEvent, e_inf:EntryInfo) -> None:
		# Set event status (cancelled, tentative etc.) from e_inf.
		# Only allow known values.
		if 'STATUS' in ev:
			del(ev['STATUS'])
		if e_inf.status in ('TENTATIVE','CONFIRMED','CANCELLED'):
			ev.add('STATUS', e_inf.status)


	@staticmethod
	def _event_set_location_from_info(ev:iEvent, e_inf:EntryInfo) -> None:
		# Set event location (text string) from e_inf.
		if 'LOCATION' in ev:
			del(ev['LOCATION'])
		if e_inf.location:
			ev.add('LOCATION', e_inf.location)


	@classmethod
	def delete_entry(cls, event:iEvent) -> None:
		# Delete given event.
		# Need to clear cache containing the entry...
		if 'RRULE' in event:
			cls._entry_rep_list = None
		else:
			cls._entry_norep_list_sorted = None
		cls.calConnector.delete_entry(event)


	@classmethod
	def set_toggle_status_entry(cls, event:iEvent, stat:Optional[str]) -> None:
		# Set event STATUS to stat.
		# If STATUS is set and equals stat, toggle it off.
		if 'STATUS' in event:
			if stat==event['STATUS']:
				stat = None # If on, we toggle it off
			del(event['STATUS'])
		if stat in ('TENTATIVE','CONFIRMED','CANCELLED'):
			event.add('STATUS', stat)
		cls.calConnector.update_entry(event) # Write to store


	@classmethod
	def _update_entry_norep_list(cls) -> None:
		# Re-build _entry_norep_list_sorted, if it has been cleared (==None)
		if cls._entry_norep_list_sorted is None:
			# Get events with no repeat rule
			evs = cls.calConnector.cal.walk('vEvent')
			cls._entry_norep_list_sorted = [e for e in evs if 'RRULE' not in e]
			cls._entry_norep_list_sorted.sort()


	@classmethod
	def _update_entry_rep_list(cls) -> None:
		# Re-build _entry_rep_list, if it has been cleared (==None)
		# Possible optimisation: sort most -> least frequent
		# (so don't get last one inserting loads into array) 
		if cls._entry_rep_list is None:
			evs = cls.calConnector.cal.walk('vEvent')
			cls._entry_rep_list = [e for e in evs if 'RRULE' in e]


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


#
# Connector class for ICS files
#
class CalendarConnectorICSfile(CalendarConnector):
	BACKUP_PERIOD = 90 # seconds
	BACKUP_EXT = 'bak'
	NEWFILE_EXT = 'new'

	def __init__(self, filename:str):
		self._filename = filename
		if Path(filename).exists():
			with open(filename, 'rb') as file:
				self.cal = iCalendar.from_ical(file.read())
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


	def add_entry(self, event:iEvent) -> None:
		# Add a new entry component to the file data and write file.
		self.cal.add_component(event)
		self._save_file()


	def update_entry(self, event:iEvent) -> None:
		# event is a component of the file data, so it's already updated.
		# We just need to write the file data.
		self._save_file()


	def delete_entry(self, event:iEvent) -> None:
		# Delete entry component to the file data and write file.
		self.cal.subcomponents.remove(event)
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
	def __init__(self, url:str, user:str, passwd:str, calname:Optional[str]):
		import caldav # Postponed import, so Pygenda can be used without caldav

		client = caldav.DAVClient(url=url, username=user, password=passwd)
		try:
			principal = client.principal()
		except Exception as excep:
			print('Error: Can\'t connect to CalDAV server at {:s}. Message: {:s}'.format(url,str(excep)), file=stderr)
			raise
		if calname is None:
			calendars = principal.calendars()
			if len(calendars) > 0:
				self.calendar = calendars[0]
			else:
				# Create a calendar with default name
				self.calendar = principal.make_calendar(name='pygenda')
		else:
			# Open or create named calendar
			try:
				self.calendar = principal.calendar(calname)
			except caldav.lib.error.NotFoundError:
				self.calendar = principal.make_calendar(name=calname)

		# Make list of references to events for convenient access
		events = self.calendar.events()
		self.cal = iCalendar()
		for ev in events:
			# Each icalendar_instance is a calendar containing the event.
			# We want to extract the event itself, so walk() & take the first.
			vevent = ev.icalendar_instance.walk('vEvent')[0]
			vevent.__conn_event = ev # Sneakily add ev, for rapid access later
			self.cal.add_component(vevent)


	def add_entry(self, event:iEvent) -> None:
		# Create a new entry component on the server, and locally.
		vcstr = 'BEGIN:VCALENDAR\r\n{:s}END:VCALENDAR\r\n'.format(event.to_ical().decode()) # !! Should we specify encoding for decode()?
		try:
			conn_event = self.calendar.save_event(vcstr)
		except Exception as excep:
			# !! While code is in development, just exit on failure.
			# May change to something "friendlier" later...
			print('Error creating entry on CalDAV server. Message: {:s}'.format(str(excep)), file=stderr)
			exit(-1)

		# Save to local store
		# Add embedded event, so we can modify & save directly
		newevent = conn_event.icalendar_instance.walk('vEvent')[0]
		newevent.__conn_event = conn_event
		self.cal.add_component(newevent)


	def update_entry(self, event:iEvent) -> None:
		# Event struct has been modified, so can just send update to server.
		try:
			event.__conn_event.save() # Write to server
		except Exception as excep:
			# !! While code is in development, just exit on failure.
			# May change to something "friendlier" later...
			print('Error updating entry on CalDAV server. Message: {:s}'.format(str(excep)), file=stderr)
			exit(-1)


	def delete_entry(self, event:iEvent) -> None:
		# Delete entry component from server and in local copy.
		try:
			event.__conn_event.delete() # delete from server
		except Exception as excep:
			# !! While code is in development, just exit on failure.
			# May change to something "friendlier" later...
			print('Error deleting entry on CalDAV server. Message: {:s}'.format(str(excep)), file=stderr)
			exit(-1)
		self.cal.subcomponents.remove(event) # delete local copy


#
# Helper class for repeats_in_range() function (below)
#
class RepeatInfo:
	DAY_ABBR = ('MO','TU','WE','TH','FR','SA','SU')

	def __init__(self, event:iEvent, start:dt_date, stop:dt_date):
		# Note: start argument is INclusive, stop is EXclusive
		rrule = event['RRULE']
		self.start = event['DTSTART'].dt
		# Quickly eliminate some out-of-range cases
		if stop is not None and dt_lte(stop, self.start):
			self.start_in_rng = None
			return
		if start is not None and 'UNTIL' in rrule and dt_lt(rrule['UNTIL'][0],start):
			self.start_in_rng = None
			return

		dt_st = event['DTSTART'].dt
		if rrule['FREQ'][0]=='MONTHLY' and dt_st.day>28:
			raise ValueError('Unsupported MONTHLY (day>28) {} in RRULE'.format(dt_st))
		if rrule['FREQ'][0]=='YEARLY' and dt_st.month==2 and dt_st.day==29:
			raise ValueError('Unsupported YEARLY (29/2) {} in RRULE'.format(dt_st))

		self._set_freq(rrule)
		if 'EXDATE' in event:
			self._set_exdates(event['EXDATE'])
		else:
			self.exdates = None
		self._set_start_in_rng(start)
		self._set_stop(rrule, stop)


	def _set_freq(self, rrule:vRecur) -> None:
		# Set repeat frequency (self.delta).
		# Called during construction.
		freq = rrule['FREQ'][0]
		interval = int(rrule['INTERVAL'][0]) if 'INTERVAL' in rrule else 1
		if 'BYDAY' in rrule and rrule['BYDAY'][0] not in self.DAY_ABBR:
			raise ValueError('Unsupported BYDAY {} in RRULE'.format(rrule['BYDAY']))
		if 'BYMONTH' in rrule and len(rrule['BYMONTH'])>1:
			raise ValueError('Unsupported multi-BYMONTH {} in RRULE'.format(rrule['BYMONTH']))
		if 'BYYEARDAY' in rrule:
			raise ValueError('Unsupported BYYEARDAY in RRULE')
		if 'BYMONTHDAY' in rrule:
			if (freq!='YEARLY' or 'BYMONTH' not in rrule):
				raise ValueError('Unsupported BYMONTHDAY in RRULE (not YEARLY/BYMONTH)')
			# If we get here, it's YEARLY/BYMONTH/BYMONTHDAY
			if len(rrule['BYMONTH'])>1:
				raise ValueError('Unsupported BYMONTHDAY, multi-BYMONTH in RRULE')
			if len(rrule['BYMONTHDAY'])>1:
				raise ValueError('Unsupported multi-BYMONTHDAY in RRULE')
			bmd_day = int(rrule['BYMONTHDAY'][0])
			bmd_month = int(rrule['BYMONTH'][0])
			if bmd_day!=self.start.day or bmd_month!=self.start.month:
				raise ValueError('Unsupported YEARLY/BYMONTH/BYMONTHDAY != DTSTART in RRULE')
		if 'BYSETPOS' in rrule:
			raise ValueError('Unsupported BYSETPOS in RRULE')
		if 'BYHOUR' in rrule:
			raise ValueError('Unsupported BYHOUR in RRULE')
		if 'BYMINUTE' in rrule:
			raise ValueError('Unsupported BYMINUTE in RRULE')
		if 'BYSECOND' in rrule:
			raise ValueError('Unsupported BYSECOND in RRULE')
		if 'BYWEEKNO' in rrule:
			raise ValueError('Unsupported BYWEEKNO in RRULE')
		if freq=='YEARLY':
			self._set_yearly(interval)
		elif freq=='MONTHLY':
			self._set_monthly(interval)
		elif freq=='WEEKLY':
			self._set_weekly(rrule, interval)
		elif freq=='DAILY':
			self._set_daily(interval)
		elif freq=='HOURLY':
			self._set_hourly(interval)
		elif freq=='MINUTELY':
			self._set_minutely(interval)
		else: # unrecognised freq - skip entry
			raise ValueError('Unknown FREQ {:s} in RRULE'.format(freq))


	def _set_yearly(self, interval:int) -> None:
		# Called on construction if a simple yearly repeat
		self.delta = relativedelta(years=interval)


	def _set_monthly(self, interval:int) -> None:
		# Called on construction if a simple monthly repeat
		self.delta = relativedelta(months=interval)


	def _set_weekly(self, rrule:vRecur, interval:int) -> None:
		# Called on construction if a weekly repeat.
		# Try to also handle cases where rrule gives multiple days/startweek.
		days_in_week = 0 # bitmask to be created
		diw_from_st = 1<<self.start.weekday()
		if 'BYDAY' in rrule:
			for d in rrule['BYDAY']:
				days_in_week |= 1<<self.DAY_ABBR.index(d)
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


	def _set_exdates(self, exdate) -> None:
		# Initialise object's exdates variable, given an exdate structure.
		# exdate argument is in format of exdate from an ical event, it
		# might be a list, or might not...
		if isinstance(exdate,list):
			l = [dl.dts for dl in exdate]
			self.exdates = sorted(set([datetime_to_date(t[i].dt) for t in l for i in range(len(t))]))
		else:
			l = exdate.dts
			self.exdates = sorted(set([datetime_to_date(t.dt) for t in l]))


	def _set_start_in_rng(self, start:dt_date) -> None:
		# Set start date within given range (that is, on/after 'start')
		self.start_in_rng = self.start
		if isinstance(self.delta,list):
			self.delta_index = 0
		if start is not None:
			# We try to jump to first entry in range
			# First compute d, distance from the range
			d = start - datetime_to_date(self.start)
			if isinstance(self.delta,list):
				if d>timedelta(0): # start provided was after first repeat, so inc
					# Want to do as much as possible in one increment
					per = reduce(lambda x,y:x+y,self.delta) # sum of delta
					s = d//per
					self.start_in_rng += per * s
				# After approximate jump, clear any extras.
				# Do this even if d<=0 to catch case when first dates excluded
				i = 0
				while dt_lt(self.start_in_rng,start) or self.is_exdate(self.start_in_rng):
					self.start_in_rng += self.delta[i]
					i = (i+1)%len(self.delta)
				self.delta_index = i
			else: # single delta, could be timedelta or relativedelta
				if d>timedelta(0): # start provided was after first repeat, so inc
					# Want to do as much as possible in one increment
					if isinstance(self.delta,timedelta):
						s = round(d/self.delta)
					else:
						# self.delta is a relativedelta
						sst = self.start
						try:
							# If we have tzinfo, get rid to make relativedelta
							sst = sst.replace(tzinfo=None)
						except TypeError:
							pass
						d = relativedelta(start, sst)
						if self.delta.years>0:
							s = round(d.years/self.delta.years)
						elif self.delta.months>0:
							s = round((d.years*12 + d.months)/self.delta.months)
						else:
							s = 1
					self.start_in_rng += self.delta * s
				# After approximate jump, clear any extras.
				# Do this even if d<=0 to catch case when first dates excluded
				while dt_lt(self.start_in_rng,start) or self.is_exdate(self.start_in_rng):
					self.start_in_rng += self.delta


	def _set_stop(self, rrule:vRecur, stop:dt_date) -> None:
		# Set stop date in range (i.e. before 'stop' parameter).
		# Note, 'stop' parameter is exclusive (this is more usual)
		# but 'UNTIL' field in iCal is inclusive (according to standard).
		# Internally RepeatInfo class will use an exclusive stop, so:
		#   - Name it stop_exc for clarity
		#   - Take care when using 'UNTIL'
		until = rrule['UNTIL'][0] if 'UNTIL' in rrule else None
		if until is None or (stop is not None and dt_lte(stop, until)):
			self.stop_exc = stop
		elif isinstance(until, dt_datetime):
			self.stop_exc = until+timedelta(milliseconds=1)
		else:
			# dt_datetime is a date only
			self.stop_exc = dt_datetime.combine(until,dt_time(microsecond=1))
		count = rrule['COUNT'][0] if 'COUNT' in rrule else None
		if count is not None:
			if self.exdates is not None:
				raise ValueError('Unsupported COUNT & EXDATE') # !! fix me
			if isinstance(self.delta, list):
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
		# Returns True if dt is in exdates, False otherwise.
		# Special case: if dt is a datetime, returns True if date
		# component is in exdates.
		if self.exdates is None:
			return False
		if isinstance(dt,dt_datetime) and dt.date() in self.exdates:
			return True
		return dt in self.exdates


	def __iter__(self) -> 'RepeatIter_simpledelta':
		# Return an iterator for this RepeatInfo
		if self.start_in_rng is not None and isinstance(self.delta, list):
			return RepeatIter_multidelta(self)
		return RepeatIter_simpledelta(self)


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
		return r


class RepeatIter_multidelta(RepeatIter_simpledelta):
	# Iterator class for RepeatInfo where we have different deltas
	# (e.g. we may have different gaps between occurences, such as
	# a weekly repeat that occurs on Mondays and Wednesdays).

	def __init__(self, rinfo:RepeatInfo):
		super().__init__(rinfo)
		self.i = rinfo.delta_index

	def __next__(self) -> dt_date:
		# Return date/dattime for next occurence in range.
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
		return r


def merge_repeating_entries_sort(target:list, ev:iEvent, start:dt_date, stop:dt_date) -> None:
	# Given a sorted list of occurrences, 'target', and a single
	# repeating event 'ev', splice the repeats of ev from 'start'
	# to 'stop' into 'target', keeping it sorted.
	ev_reps = repeats_in_range(ev, start, stop)
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
	rrstr = ev['RRULE'].to_ical().decode('utf-8')
	dt = ev['DTSTART'].dt
	hastime = isinstance(dt,dt_datetime)
	exd = 'EXDATE' in ev
	rr = rrulestr(rrstr,dtstart=dt,forceset=exd)
	st = dt_datetime.combine(start, dt_time()) # set time to midnight
	sp = dt_datetime.combine(stop, dt_time())
	if hastime:
		# Could add tzinfo to combine() calls above, but this allows Python<3.6
		st = st.replace(tzinfo=dt.tzinfo)
		sp = sp.replace(tzinfo=dt.tzinfo)
	sp -= timedelta(milliseconds=1)
	ret = rr.between(after=st,before=sp,inc=True)
	if not hastime:
		ret = [d.date() for d in ret]
	if exd:
		exdate_list = [ev['EXDATE'][i].dts[j] for i in range(len(ev['EXDATE'])) for j in range(len(ev['EXDATE'][i].dts))] if isinstance(ev['EXDATE'], list) else ev['EXDATE'].dts
		if hastime:
			for de in exdate_list:
				if isinstance(de.dt,dt_datetime):
					ret = [d for d in ret if d!=de.dt]
				else:
					ret = [d for d in ret if d.date()!=de.dt]
		else:
			for de in exdate_list:
				if not isinstance(de.dt,dt_datetime):
					ret = [d for d in ret if d!=de.dt]
	return ret


def repeats_in_range(ev:iEvent, start:dt_date, stop:dt_date) -> list:
	# Given a repeating event ev, return list of occurrences from
	# dates start to stop.
	try:
		r_info = RepeatInfo(ev, start, stop)
	except ValueError as err:
		# RepeatInfo doesn't handle this type of repeat.
		# Fall back to using rrule - more complete, but slower for simple repeats
		print('Notice: Fallback to unoptimised repeat for "{:s}" ({:s})'.format(ev['SUMMARY'],str(err)), file=stderr)
		return repeats_in_range_with_rrstr(ev, start, stop)
	ret = list(iter(r_info))
	# Uncomment the next two lines to test calculated values (slow!)
	#if ret != repeats_in_range_with_rrstr(ev, start, stop):
	#	print('Error: Wrong repeats for "{:s}"'.format(ev['SUMMARY']), file=stderr)
	return ret
