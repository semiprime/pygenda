#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# test_import_paste.py
# Unit tests for importing/pasting events.
# (Both of these use the Calendar.new_entry_from_example() function.)
#
# Copyright (C) 2024 Matthew Lewis
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
#

import unittest
from datetime import date, time, datetime, timezone, timedelta
from dateutil import tz
from os import remove as os_remove
from icalendar import Calendar as iCalendar, Event as iEvent, Todo as iTodo, Alarm as iAlarm

# Add '..' to path, so this can be run from test directory
import sys
sys.path.append('..')

# Import Pygenda modules...
from pygenda.pygenda_calendar import Calendar
from pygenda.pygenda_config import Config
from pygenda.pygenda_entryinfo import EntryInfo
from pygenda.pygenda_util import get_local_tz, _set_local_tz as set_local_tz


class TestImportPaste(unittest.TestCase):
    maxDiff = None # show unlimited chars when showing diffs
    TESTFILE_NAME = 'test_import_paste_TESTFILE.ics'
    UID_BASE = 'Pygenda-test-import-paste-5415-'
    uid_index = 0

    @classmethod
    def setUpClass(cls):
        # Called once before all tests
        # Override config options so it uses our test ics file
        Config.set('calendar', 'type', 'icalfile')
        Config.set('calendar', 'filename', cls.TESTFILE_NAME)
        Config.set('calendar', 'display_name', 'Test calendar for test_entries')
        Config.set('calendar', 'readonly', None)
        Config.set('calendar', 'entry_type', None)
        Config.set('calendar1', 'type', None) # so only specified file opened

        # Save local timezone, so running tests will test in your tz
        cls.local_tz_saved = get_local_tz()


    def setUp(self) -> None:
        # This is called before each individual test function

        # Reset timezone for next test (might be changed in test)
        set_local_tz(self.local_tz_saved)

        # Delete test ics files, so an empty one is created
        self._delete_testfile()

        # Call init to create the calendar
        Calendar.init()


    @classmethod
    def tearDownClass(cls) -> None:
        # This is called after final test
        cls._delete_testfile()


    @classmethod
    def _delete_testfile(cls) -> None:
        # Helper function for setup/teardown
        try:
            os_remove(cls.TESTFILE_NAME)
        except FileNotFoundError:
            pass


    @staticmethod
    def _past_timestamp() -> datetime:
        # Return a time in the past for use as a timestamp
        t =  datetime.now(timezone.utc).replace(microsecond=0)
        t -= timedelta(seconds=2)
        return t


    @classmethod
    def _new_event(cls, desc:str, start:date, end:date=None, status:str=None, rfreq:str=None, longdesc:str=None, location:str=None, alarm:iAlarm=None) -> iEvent:
        # Helper function to create an event
        ev = iEvent()
        ev.add('SUMMARY', desc)
        # we need to read & store tzid from start date for these tests.
        # (This should be done in Pygenda when it creates/imports events.)
        st_tznm = cls._get_tzname_from_datetime(start)
        ev.add('DTSTART', start, parameters={'TZID':st_tznm} if st_tznm else None)
        if end is not None:
            end_tznm = cls._get_tzname_from_datetime(end)
            ev.add('DTEND', end, parameters={'TZID':end_tznm} if end_tznm else None)
        if status is not None:
            ev.add('STATUS', status)
        if rfreq is not None:
            ev.add('RRULE', {'FREQ':[rfreq]})
        if longdesc is not None:
            ev.add('DESCRIPTION', longdesc)
        if location is not None:
            ev.add('LOCATION', location)
        if alarm is not None:
            ev.add_component(alarm)

        ev.add('UID', cls.UID_BASE+str(cls.uid_index))
        cls.uid_index += 1
        stamp = cls._past_timestamp()
        ev.add('CREATED', stamp)
        ev.add('DTSTAMP', stamp)
        return ev


    @classmethod
    def _new_todo(cls, desc:str, cats:tuple=(), due:date=None, priority:int=None, status:str=None, longdesc:str=None) -> iTodo:
        # Helper function to create a todo
        if type(cats) != tuple:
            raise(ValueError('Error - cats needs to be a tuple'))
        td = iTodo()
        td.add('SUMMARY', desc)
        td.add('UID', cls.UID_BASE+str(cls.uid_index))
        cls.uid_index += 1
        stamp = cls._past_timestamp()
        td.add('CREATED', stamp)
        td.add('DTSTAMP', stamp)
        if cats:
            td.add('CATEGORIES', list(cats))
        if due is not None:
            td.add('DUE', due)
        if priority is not None:
            td.add('PRIORITY', priority)
        if status is not None:
            td.add('STATUS', status)
        if longdesc is not None:
            td.add('DESCRIPTION', longdesc)
        return td


    @staticmethod
    def _get_tzname_from_datetime(dt) -> str:
        # Helper fn return a string with the name of the timezone.
        # Returns None if no timezone, unrecognized tz, or dt is a date.
        tzname = None
        if isinstance(dt, datetime) and dt.tzinfo is not None:
            tzinfo_str = str(dt.tzinfo)
            idx = -1
            for i in range(2): # Find second-to-last '/'
                idx = tzinfo_str.rfind('/', 0, idx)
                if idx == -1: # '/' not found
                    break
            if idx != -1:
                tzname = tzinfo_str[idx+1:-2]
        return tzname


    @staticmethod
    def _do_import(en):
        # Perform import call as would happen in application
        Calendar.import_entry(en, cal_idx=0)


    @staticmethod
    def _do_paste_event(en, targ_date:date):
        # Perform paste call as would happen in "event" views
        Calendar.paste_entry(en, e_type=EntryInfo.TYPE_EVENT, dt_start=targ_date)


    @staticmethod
    def _do_paste_todo(en, targ_cats:list=None):
        # Perform paste call as would happen in Todo view
        Calendar.paste_entry(en, e_type=EntryInfo.TYPE_TODO, e_cats=targ_cats)


    def _get_saved_version(self, en):
        # Read and return version of entry from file
        with open(self.TESTFILE_NAME, 'rb') as file:
            cal = iCalendar.from_ical(file.read())

        for ev in cal.walk('VEVENT'):
            if ev['UID'] == en['UID']:
                return ev

        for td in cal.walk('VTODO'):
            if td['UID'] == en['UID']:
                return td

        return None


    #@unittest.skip
    def test_import_01_event_simple(self) -> None:
        # Import simple event
        SHORT_DESC = 'Test event'
        DT_ST = date(2020,1,5)
        ev = self._new_event(SHORT_DESC, DT_ST)
        self._do_import(ev)

        # Test imported entry
        l = Calendar.occurrence_list(date(2020,1,1), date(2021,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST)
        imported = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DTSTART'].dt, DT_ST)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(imported)
        self.check_stamps(imported, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_ST)


    #@unittest.skip
    def test_import_02_event_timed(self) -> None:
        # Import basic timed event
        SHORT_DESC = 'Test event timed'
        DT_ST = datetime(2021,2,5,12,13,14)
        ev = self._new_event(SHORT_DESC, DT_ST)
        self._do_import(ev)

        # Test imported entry
        l = Calendar.occurrence_list(date(2021,1,1), date(2022,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST)
        imported = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DTSTART'].dt, DT_ST)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(imported)
        self.check_stamps(imported, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_ST)


    #@unittest.skip
    def test_import_03_event_time_end(self) -> None:
        # Import event with start & end times
        SHORT_DESC = 'Test event start & end times'
        DT_ST = datetime(2021,4,21,11,18)
        DT_END = datetime(2021,4,21,14,32)
        ev = self._new_event(SHORT_DESC, DT_ST, end=DT_END)
        self._do_import(ev)

        # Test imported entry
        l = Calendar.occurrence_list(date(2021,1,1), date(2022,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST)
        imported = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DTSTART'].dt, DT_ST)
        self.assertEqual(imported['DTEND'].dt, DT_END)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(imported)
        self.check_stamps(imported, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_ST)
        self.assertEqual(ev_saved['DTEND'].dt, DT_END)


    #@unittest.skip
    def test_import_04_event_day(self) -> None:
        # Import day event
        SHORT_DESC = 'Test day event'
        DT_ST = date(1981,5,1)
        DT_END = date(1981,5,2)
        ev = self._new_event(SHORT_DESC, DT_ST, end=DT_END)
        self._do_import(ev)

        # Test imported entry
        l = Calendar.occurrence_list(date(1981,1,1), date(1982,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST)
        imported = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DTSTART'].dt, DT_ST)
        self.assertEqual(imported['DTEND'].dt, DT_END)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(imported)
        self.check_stamps(imported, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_ST)
        self.assertEqual(ev_saved['DTEND'].dt, DT_END)


    #@unittest.skip
    def test_import_05_event_timezone(self) -> None:
        # Import timezoned event
        SHORT_DESC = 'Test event timezone NY'
        tz_NY = tz.gettz('America/New_York')
        self.assertTrue(tz_NY) # check not None
        DT_ST = datetime(2023,7,3,0,30,tzinfo=tz_NY)
        ev = self._new_event(SHORT_DESC, DT_ST)
        self._do_import(ev)

        # Test imported entry
        l = Calendar.occurrence_list(date(2023,1,1), date(2024,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST)
        imported = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DTSTART'].dt, DT_ST)
        self.assertEqual(imported['DTSTART'].params['TZID'], 'America/New_York')

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(imported)
        self.check_stamps(imported, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_ST)
        self.assertEqual(ev_saved['DTSTART'].params['TZID'], 'America/New_York')


    #@unittest.skip
    def test_import_06_event_timezone_end(self) -> None:
        # Import timezoned event with timezoned end time
        SHORT_DESC = 'Test event timezone Brazil'
        tz_AC = tz.gettz('Brazil/Acre')
        self.assertTrue(tz_AC) # check not None
        DT_ST = datetime(2024,2,3,10,30,tzinfo=tz_AC)
        DT_END = datetime(2024,2,3,11,30,tzinfo=tz_AC)
        ev = self._new_event(SHORT_DESC, DT_ST, end=DT_END)
        self._do_import(ev)

        # Test imported entry
        l = Calendar.occurrence_list(date(2024,1,1), date(2025,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST)
        imported = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DTSTART'].dt, DT_ST)
        self.assertEqual(imported['DTEND'].dt, DT_END)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(imported)
        self.check_stamps(imported, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_ST)
        self.assertEqual(ev_saved['DTSTART'].params['TZID'], 'Brazil/Acre')
        self.assertEqual(ev_saved['DTEND'].dt, DT_END)
        self.assertEqual(ev_saved['DTEND'].params['TZID'], 'Brazil/Acre')


    #@unittest.skip
    def test_import_07_event_status(self) -> None:
        # Import event with a status
        SHORT_DESC = u'Test event with status'
        DT_ST = datetime(2014,10,1,23,59)
        STATUS = 'CANCELLED'
        ev = self._new_event(SHORT_DESC, DT_ST, status=STATUS)
        self._do_import(ev)

        # Test imported entry
        l = Calendar.occurrence_list(date(2014,1,1), date(2015,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST)
        imported = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DTSTART'].dt, DT_ST)
        self.assertEqual(imported['STATUS'], STATUS)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(imported)
        self.check_stamps(imported, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_ST)
        self.assertEqual(ev_saved['STATUS'], STATUS)


    #@unittest.skip
    def test_import_08_event_longdesc(self) -> None:
        # Import event with a long description
        SHORT_DESC = u'Test event with long desc & non-ascii like θ'
        LONG_DESC = u"""Big long description with some newlines
Like that one
and non-ascii characters like ë & ☉
"""
        DT_ST = date(2023,9,9)
        ev = self._new_event(SHORT_DESC, DT_ST, longdesc=LONG_DESC)
        self._do_import(ev)

        # Test imported entry
        l = Calendar.occurrence_list(date(2023,1,1), date(2024,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST)
        imported = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DTSTART'].dt, DT_ST)
        self.assertEqual(imported['DESCRIPTION'], LONG_DESC)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(imported)
        self.check_stamps(imported, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_ST)
        self.assertEqual(ev_saved['DESCRIPTION'], LONG_DESC)


    #@unittest.skip
    def test_import_09_event_location(self) -> None:
        # Import event with a location
        SHORT_DESC = 'Test event with a location'
        LOCATION = 'Liverpool'
        DT_ST = date(2026,1,8)
        ev = self._new_event(SHORT_DESC, DT_ST, location=LOCATION)
        self._do_import(ev)

        # Test imported entry
        l = Calendar.occurrence_list(date(2026,1,1), date(2027,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST)
        imported = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DTSTART'].dt, DT_ST)
        self.assertEqual(imported['LOCATION'], LOCATION)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(imported)
        self.check_stamps(imported, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_ST)
        self.assertEqual(ev_saved['LOCATION'], LOCATION)


    #@unittest.skip
    def test_import_10_event_repeating(self) -> None:
        # Import repeating event
        SHORT_DESC = 'Test repeating event'
        DT_ST = date(1989,6,19)
        ev = self._new_event(SHORT_DESC, DT_ST, rfreq="YEARLY")
        self._do_import(ev)

        # Test imported entry
        l = Calendar.occurrence_list(date(1980,1,1), date(1989,1,1))
        self.assertEqual(len(l), 0)
        l = Calendar.occurrence_list(date(1989,1,1), date(2010,1,1))
        self.assertEqual(len(l), 21)
        l = Calendar.occurrence_list(date(1989,1,1), date(1990,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST)
        imported = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DTSTART'].dt, DT_ST)
        self.assertEqual(imported['RRULE']['FREQ'][0], 'YEARLY')

        l = Calendar.occurrence_list(date(1991,1,1), date(1992,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST.replace(year=1991))

        l = Calendar.occurrence_list(date(2005,1,1), date(2006,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST.replace(year=2005))

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(imported)
        self.check_stamps(imported, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_ST)
        self.assertEqual(ev_saved['RRULE']['FREQ'][0], 'YEARLY')


    #@unittest.skip
    def test_import_11_event_alarm(self) -> None:
        # Import event with alarm
        # Note: current behaviour is to discard the alarm!!
        SHORT_DESC = 'Test event with alarm'
        DT_ST = datetime(2025,2,14,10,20)
        alm = iAlarm()
        alm.add('TRIGGER', timedelta(minutes=-10))
        alm.add('ACTION', 'AUDIO')
        ev = self._new_event(SHORT_DESC, DT_ST, alarm=alm)
        self.assertEqual(len(ev.walk('VALARM')), 1)
        self._do_import(ev)

        # Test imported entry
        l = Calendar.occurrence_list(date(2025,1,1), date(2026,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_ST)
        imported = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DTSTART'].dt, DT_ST)
        self.assertEqual(len(imported.walk('VALARM')), 0)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(imported)
        self.check_stamps(imported, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_ST)
        self.assertEqual(len(ev_saved.walk('VALARM')), 0)


    #@unittest.skip
    def test_import_12_todo_simple(self) -> None:
        # Import simple todo
        SHORT_DESC = 'Test todo'
        td = self._new_todo(SHORT_DESC)
        self._do_import(td)

        # Test imported entry
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        imported = l[0] # Simple list (not occs) for todos
        self.check_stamps(td, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)

        # Test version saved to disk is also OK
        td_saved = self._get_saved_version(imported)
        self.check_stamps(imported, td_saved, same_obj=True)
        self.assertEqual(td_saved['SUMMARY'], SHORT_DESC)


    #@unittest.skip
    def test_import_13_todo_wipe_categories(self) -> None:
        # Test todo import will remove categories
        SHORT_DESC = 'Test import todo with categories'
        td = self._new_todo(SHORT_DESC, cats=('cat1',))
        self.assertEqual(td['CATEGORIES'].cats[0], 'cat1')
        self._do_import(td)

        # Test imported entry
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        imported = l[0]
        self.check_stamps(td, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertNotIn('CATEGORIES', imported)

        # Test version saved to disk is also OK
        td_saved = self._get_saved_version(imported)
        self.check_stamps(imported, td_saved, same_obj=True)
        self.assertEqual(td_saved['SUMMARY'], SHORT_DESC)
        self.assertNotIn('CATEGORIES', td_saved)


    #@unittest.skip
    def test_import_14_todo_priority_status(self) -> None:
        # Import todo with priority & status
        SHORT_DESC = 'Test todo with priority & status'
        PRIORITY = 3
        STATUS = 'IN-PROCESS'
        td = self._new_todo(SHORT_DESC, priority=PRIORITY, status=STATUS)
        self._do_import(td)

        # Test imported entry
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        imported = l[0] # Simple list (not occs) for todos
        self.check_stamps(td, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['PRIORITY'], PRIORITY)
        self.assertEqual(imported['STATUS'], STATUS)

        # Test version saved to disk is also OK
        td_saved = self._get_saved_version(imported)
        self.check_stamps(imported, td_saved, same_obj=True)
        self.assertEqual(td_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(td_saved['PRIORITY'], PRIORITY)
        self.assertEqual(td_saved['STATUS'], STATUS)


    #@unittest.skip
    def test_import_15_todo_duedate(self) -> None:
        # Import todo with due date
        SHORT_DESC = 'Test todo with due date'
        DT_DUE = date(2018,12,24)
        td = self._new_todo(SHORT_DESC, due=DT_DUE)
        self._do_import(td)

        # Test imported entry
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        imported = l[0] # Simple list (not occs) for todos
        self.check_stamps(td, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DUE'].dt, DT_DUE)

        # Test version saved to disk is also OK
        td_saved = self._get_saved_version(imported)
        self.check_stamps(imported, td_saved, same_obj=True)
        self.assertEqual(td_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(td_saved['DUE'].dt, DT_DUE)


    #@unittest.skip
    def test_import_16_todo_longdesc(self) -> None:
        # Import todo with longdesc
        SHORT_DESC = 'Test todo with long description'
        LONG_DESC = u'Lørem ipsum dolor sit åmet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ût enim ad minim veñam, quis nostrud exercitation üllamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit eße cillum dolore eu fugiat nulla pariatur. Excepteur sint occæcat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.'
        td = self._new_todo(SHORT_DESC, longdesc=LONG_DESC)
        self._do_import(td)

        # Test imported entry
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        imported = l[0] # Simple list (not occs) for todos
        self.check_stamps(td, imported)
        self.assertEqual(imported['SUMMARY'], SHORT_DESC)
        self.assertEqual(imported['DESCRIPTION'], LONG_DESC)

        # Test version saved to disk is also OK
        td_saved = self._get_saved_version(imported)
        self.check_stamps(imported, td_saved, same_obj=True)
        self.assertEqual(td_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(td_saved['DESCRIPTION'], LONG_DESC)


    #@unittest.skip
    def test_paste_01_event_simple(self) -> None:
        # Paste a simple event
        SHORT_DESC = 'Test event'
        DT_ST = date(2020,1,5)
        ev = self._new_event(SHORT_DESC, DT_ST)
        DT_TARG = date(2023,7,11)
        self._do_paste_event(ev, DT_TARG)

        # Test no entry exists where event was pasted from
        l = Calendar.occurrence_list(date(2020,1,1), date(2021,1,1))
        self.assertEqual(len(l), 0)

        # Test pasted entry
        l = Calendar.occurrence_list(date(2023,1,1), date(2024,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_TARG)
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt, DT_TARG)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_TARG)


    #@unittest.skip
    def test_paste_02_event_time(self) -> None:
        # Paste event with a time
        SHORT_DESC = 'Test event with time'
        DT_ST = datetime(1993,9,30,12,35)
        ev = self._new_event(SHORT_DESC, DT_ST)
        DT_TARG = date(2024,1,1)
        self._do_paste_event(ev, DT_TARG)
        DT_WANT = datetime(2024,1,1,12,35)

        # Test no entry exists where event was pasted from
        l = Calendar.occurrence_list(date(1993,1,1), date(1994,1,1))
        self.assertEqual(len(l), 0)

        # Test pasted entry
        l = Calendar.occurrence_list(date(2024,1,1), date(2025,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_WANT)
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt, DT_WANT)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_WANT)


    #@unittest.skip
    def test_paste_03_event_endtime(self) -> None:
        # Paste event with start & end time
        SHORT_DESC = 'Test event with start/end times'
        DT_ST = datetime(2010,2,28,23,15)
        DT_END = datetime(2010,3,1,0,30)
        ev = self._new_event(SHORT_DESC, DT_ST, end=DT_END)
        DT_TARG = date(1999,12,31)
        self._do_paste_event(ev, DT_TARG)
        DT_WANT_ST = datetime(1999,12,31,23,15)
        DT_WANT_END = datetime(2000,1,1,0,30)

        # Test no entry exists where event was pasted from
        l = Calendar.occurrence_list(date(2010,1,1), date(2011,1,1))
        self.assertEqual(len(l), 0)

        # Test pasted entry
        l = Calendar.occurrence_list(date(1999,1,1), date(2000,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_WANT_ST)
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt, DT_WANT_ST)
        self.assertEqual(pasted['DTEND'].dt, DT_WANT_END)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_WANT_ST)
        self.assertEqual(ev_saved['DTEND'].dt, DT_WANT_END)


    #@unittest.skip
    def test_paste_04_event_multiday(self) -> None:
        # Paste multi-day event
        SHORT_DESC = 'Test 4-day event'
        DT_ST = date(2014,10,10)
        DT_END = date(2014,10,15)
        ev = self._new_event(SHORT_DESC, DT_ST, end=DT_END)
        DT_TARG = date(2015,1,31)
        self._do_paste_event(ev, DT_TARG)
        DT_WANT_END = date(2015,2,5)

        # Test no entry exists where event was pasted from
        l = Calendar.occurrence_list(date(2014,1,1), date(2015,1,1))
        self.assertEqual(len(l), 0)

        # Test pasted entry
        l = Calendar.occurrence_list(date(2015,1,1), date(2015,2,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_TARG)
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt, DT_TARG)
        self.assertEqual(pasted['DTEND'].dt, DT_WANT_END)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_TARG)
        self.assertEqual(ev_saved['DTEND'].dt, DT_WANT_END)


    #@unittest.skip
    def test_paste_05_event_timezone(self) -> None:
        # Paste timezoned event
        SHORT_DESC = 'Test event timezone NY'
        tz_NY = tz.gettz('America/New_York')
        self.assertTrue(tz_NY) # check not None
        DT_ST = datetime(2023,7,3,18,30,tzinfo=tz_NY)
        ev = self._new_event(SHORT_DESC, DT_ST)
        DT_TARG = date(2023,7,5)
        self._do_paste_event(ev, DT_TARG)

        # Test pasted entry
        l = Calendar.occurrence_list(DT_TARG, DT_TARG+timedelta(days=1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1].time(), DT_ST.time())
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt.time(), DT_ST.time())
        self.assertEqual(pasted['DTSTART'].params['TZID'], 'America/New_York')

        # Paste another - to winter
        DT_TARG2 = date(2023,12,13)
        self._do_paste_event(ev, DT_TARG2)

        # Should be two events in the year now
        l = Calendar.occurrence_list(date(2023,1,1), date(2024,1,1))
        self.assertEqual(len(l), 2)

        # Test second pasted entry
        l = Calendar.occurrence_list(DT_TARG2, DT_TARG2+timedelta(days=1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1].time(), DT_ST.time())
        pasted2 = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted2, new_copy=True)
        self.assertNotEqual(pasted['UID'], pasted2['UID'])
        self.assertEqual(pasted2['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted2['DTSTART'].dt.time(), DT_ST.time())
        self.assertEqual(pasted2['DTSTART'].params['TZID'], 'America/New_York')

        # Test both versions saved to disk are OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, pasted['DTSTART'].dt)
        self.assertEqual(ev_saved['DTSTART'].params['TZID'], 'America/New_York')
        ev_saved2 = self._get_saved_version(pasted2)
        self.check_stamps(pasted2, ev_saved2, same_obj=True)
        self.assertEqual(ev_saved2['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved2['DTSTART'].dt, pasted2['DTSTART'].dt)
        self.assertEqual(ev_saved2['DTSTART'].params['TZID'],'America/New_York')

        # Test local times of all pasted entries
        set_local_tz(tz.gettz('Europe/Paris'))
        self.assertEqual(pasted['DTSTART'].dt.time(), time(18,30))
        self.assertEqual(pasted['DTSTART'].dt.astimezone(get_local_tz()).time(), time(0,30))
        self.assertEqual(pasted2['DTSTART'].dt.time(), time(18,30))
        self.assertEqual(pasted2['DTSTART'].dt.astimezone(get_local_tz()).time(), time(0,30))

        self.assertEqual(ev_saved['DTSTART'].dt.time(), time(18,30))
        self.assertEqual(ev_saved['DTSTART'].dt.astimezone(get_local_tz()).time(), time(0,30))
        self.assertEqual(ev_saved2['DTSTART'].dt.time(), time(18,30))
        self.assertEqual(ev_saved2['DTSTART'].dt.astimezone(get_local_tz()).time(), time(0,30))


    #@unittest.skip
    def test_paste_06_event_timezone_endtime(self) -> None:
        # Paste timezoned event
        SHORT_DESC = 'Test event timezone NY with endtime'
        tz_NY = tz.gettz('America/New_York')
        self.assertTrue(tz_NY) # check not None
        DT_ST = datetime(2000,3,3,0,59,tzinfo=tz_NY)
        DT_END = datetime(2000,5,17,23,1,tzinfo=tz_NY)
        ev = self._new_event(SHORT_DESC, DT_ST, end=DT_END)
        DT_TARG = date(2000,5,16)
        self._do_paste_event(ev, DT_TARG)

        # Test pasted entry
        l = Calendar.occurrence_list(DT_TARG, DT_TARG+timedelta(days=1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1].time(), DT_ST.time())
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt.time(), DT_ST.time())
        self.assertEqual(pasted['DTSTART'].params['TZID'], 'America/New_York')
        self.assertEqual(pasted['DTEND'].dt.time(), DT_END.time())
        self.assertEqual(pasted['DTEND'].params['TZID'], 'America/New_York')

        # Test version saved to disk is OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, pasted['DTSTART'].dt)
        self.assertEqual(ev_saved['DTSTART'].params['TZID'], 'America/New_York')
        self.assertEqual(ev_saved['DTEND'].dt, pasted['DTEND'].dt)
        self.assertEqual(ev_saved['DTEND'].params['TZID'], 'America/New_York')

        # Test local times of all pasted entries
        set_local_tz(tz.gettz('Europe/Paris'))
        self.assertEqual(pasted['DTSTART'].dt.time(), time(0,59))
        self.assertEqual(pasted['DTSTART'].dt.astimezone(get_local_tz()).time(), time(6,59))
        self.assertEqual(ev_saved['DTSTART'].dt.time(), time(0,59))
        self.assertEqual(ev_saved['DTSTART'].dt.astimezone(get_local_tz()).time(), time(6,59))
        self.assertEqual(pasted['DTEND'].dt.time(), time(23,1))
        self.assertEqual(pasted['DTEND'].dt.astimezone(get_local_tz()).time(), time(5,1))
        self.assertEqual(ev_saved['DTEND'].dt.time(), time(23,1))
        self.assertEqual(ev_saved['DTEND'].dt.astimezone(get_local_tz()).time(), time(5,1))


    #@unittest.skip
    def test_paste_07_event_status(self) -> None:
        # Paste event with a status
        SHORT_DESC = u'Test event with status'
        DT_ST = date(2025,10,31)
        STATUS = 'TENTATIVE'
        ev = self._new_event(SHORT_DESC, DT_ST, status=STATUS)
        DT_TARG = date(2025,11,1)
        self._do_paste_event(ev, DT_TARG)

        # Test no entry exists where event was pasted from
        l = Calendar.occurrence_list(date(2025,10,1), date(2025,11,1))
        self.assertEqual(len(l), 0)

        # Test pasted entry
        l = Calendar.occurrence_list(date(2025,11,1), date(2025,12,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_TARG)
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt, DT_TARG)
        self.assertEqual(pasted['STATUS'], STATUS)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_TARG)
        self.assertEqual(ev_saved['STATUS'], STATUS)


    #@unittest.skip
    def test_paste_08_event_longdesc(self) -> None:
        # Paste event with a long description
        SHORT_DESC = u'Test event with long desc & non-ascii like €'
        LONG_DESC = u"""Big long description with some newlines
Like this one
and non-ascii characters like é & â
"""
        DT_ST = datetime(2032,10,10,12,0)
        ev = self._new_event(SHORT_DESC, DT_ST, longdesc=LONG_DESC)
        DT_TARG = date(2124,2,29) # leap day
        DT_WANT_ST = datetime(2124,2,29,12,0)
        self._do_paste_event(ev, DT_TARG)

        # Test no entry exists where event was pasted from
        l = Calendar.occurrence_list(date(2032,1,1), date(2033,1,1))
        self.assertEqual(len(l), 0)

        # Test pasted entry
        l = Calendar.occurrence_list(date(2124,1,1), date(2125,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_WANT_ST)
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt, DT_WANT_ST)
        self.assertEqual(pasted['DESCRIPTION'], LONG_DESC)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_WANT_ST)
        self.assertEqual(ev_saved['DESCRIPTION'], LONG_DESC)


    #@unittest.skip
    def test_paste_09_event_location(self) -> None:
        # Paste event with a location
        SHORT_DESC = u'Test event with a location'
        LOCATION = 'Liverpool'
        DT_ST = date(2026,1,8)
        ev = self._new_event(SHORT_DESC, DT_ST, location=LOCATION)
        DT_TARG = date(2026,1,10)
        self._do_paste_event(ev, DT_TARG)

        # Test no entry exists where event was pasted from
        l = Calendar.occurrence_list(date(2026,1,1), date(2026,1,10))
        self.assertEqual(len(l), 0)

        # Test pasted entry
        l = Calendar.occurrence_list(date(2026,1,1), date(2027,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_TARG)
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt, DT_TARG)
        self.assertEqual(pasted['LOCATION'], LOCATION)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_TARG)
        self.assertEqual(ev_saved['LOCATION'], LOCATION)


    #@unittest.skip
    def test_paste_10_event_alarm(self) -> None:
        # Paste event with alarm
        SHORT_DESC = 'Test event with alarm'
        DT_ST = datetime(2030,7,21,23,30)
        alm = iAlarm()
        alm.add('TRIGGER', timedelta(minutes=-10))
        alm.add('ACTION', 'AUDIO')
        ev = self._new_event(SHORT_DESC, DT_ST, alarm=alm)
        self.assertEqual(len(ev.walk('VALARM')), 1)
        DT_TARG = date(2030,7,22)
        self._do_paste_event(ev, DT_TARG)

        # Test no entry exists where event was pasted from
        l = Calendar.occurrence_list(date(2030,1,1), date(2030,7,22))
        self.assertEqual(len(l), 0)

        # Test pasted entry
        l = Calendar.occurrence_list(date(2030,1,1), date(2031,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1].date(), DT_TARG)
        self.assertEqual(l[0][1].time(), DT_ST.time())
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt.date(), DT_TARG)
        self.assertEqual(pasted['DTSTART'].dt.time(), DT_ST.time())
        pasted_alms = pasted.walk('VALARM')
        self.assertEqual(len(pasted_alms), 1)
        pasted_alm = pasted_alms[0]
        self.assertEqual(pasted_alm['TRIGGER'].dt, timedelta(minutes=-10))
        self.assertEqual(pasted_alm['ACTION'], 'AUDIO')

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt.date(), DT_TARG)
        self.assertEqual(ev_saved['DTSTART'].dt.time(), DT_ST.time())
        saved_alms = ev_saved.walk('VALARM')
        self.assertEqual(len(saved_alms), 1)
        saved_alm = saved_alms[0]
        self.assertEqual(saved_alm['TRIGGER'].dt, timedelta(minutes=-10))
        self.assertEqual(saved_alm['ACTION'], 'AUDIO')


    @unittest.skip
    def test_paste_11_event_alarm_abs(self) -> None:
        # Paste event with alarm given as absolute time (not offset)
        # SKIP for the moment - absolute time alarms generally not supported
        SHORT_DESC = 'Test event with absolute alarm'
        DT_ST = datetime(2030,7,21,23,30)
        alm = iAlarm()
        alm.add('TRIGGER', DT_ST - timedelta(minutes=15))
        alm.add('ACTION', 'AUDIO')
        ev = self._new_event(SHORT_DESC, DT_ST, alarm=alm)
        self.assertEqual(len(ev.walk('VALARM')), 1)
        DT_TARG = date(2030,7,20)
        self._do_paste_event(ev, DT_TARG)

        # Test no entry exists where event was pasted from
        l = Calendar.occurrence_list(date(2030,7,21), date(2031,1,1))
        self.assertEqual(len(l), 0)

        # Test pasted entry
        l = Calendar.occurrence_list(date(2030,1,1), date(2031,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1].date(), DT_TARG)
        self.assertEqual(l[0][1].time(), DT_ST.time())
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(ev, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt.date(), DT_TARG)
        self.assertEqual(pasted['DTSTART'].dt.time(), DT_ST.time())
        pasted_alms = pasted.walk('VALARM')
        self.assertEqual(len(pasted_alms), 1)
        pasted_alm = pasted_alms[0]
        self.assertEqual(pasted_alm['TRIGGER'].dt, datetime(2030,7,20,23,15))
        self.assertEqual(pasted_alm['ACTION'], 'AUDIO')

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt.date(), DT_TARG)
        self.assertEqual(ev_saved['DTSTART'].dt.time(), DT_ST.time())
        saved_alms = ev_saved.walk('VALARM')
        self.assertEqual(len(saved_alms), 1)
        saved_alm = saved_alms[0]
        self.assertEqual(saved_alm['TRIGGER'].dt, datetime(2030,7,20,23,15))
        self.assertEqual(saved_alm['ACTION'], 'AUDIO')


    #@unittest.skip
    def test_paste_12_todo_simple(self) -> None:
        # Paste simple todo
        SHORT_DESC = 'Test todo'
        td = self._new_todo(SHORT_DESC)
        self._do_paste_todo(td)

        # Test imported entry
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        pasted = l[0] # Simple list (not occs) for todos
        self.check_stamps(td, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)

        # Test version saved to disk is also OK
        td_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, td_saved, same_obj=True)
        self.assertEqual(td_saved['SUMMARY'], SHORT_DESC)


    #@unittest.skip
    def test_paste_13_todo_simple_cat(self) -> None:
        # Paste todo from one cat (list) to another
        SHORT_DESC = 'Test todo in cat1 paste to cat2'
        td = self._new_todo(SHORT_DESC, cats=('cat1',))
        self.assertEqual(td['CATEGORIES'].cats[0], 'cat1')
        self._do_paste_todo(td, targ_cats=('cat2',))

        # Test imported entry
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        pasted = l[0] # Simple list (not occs) for todos
        self.check_stamps(td, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['CATEGORIES'].cats[0], 'cat2')

        # Test version saved to disk is also OK
        td_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, td_saved, same_obj=True)
        self.assertEqual(td_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(td_saved['CATEGORIES'].cats[0], 'cat2')


    #@unittest.skip
    def test_paste_14_todo_priority_status(self) -> None:
        # Paste todo with priority & status
        SHORT_DESC = 'Test todo with priority & status'
        PRIORITY = 3
        STATUS = 'COMPLETED'
        td = self._new_todo(SHORT_DESC, priority=PRIORITY, status=STATUS)
        self._do_paste_todo(td)

        # Test pasted entry
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        pasted = l[0] # Simple list (not occs) for todos
        self.check_stamps(td, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['PRIORITY'], PRIORITY)
        self.assertEqual(pasted['STATUS'], STATUS)

        # Test version saved to disk is also OK
        td_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, td_saved, same_obj=True)
        self.assertEqual(td_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(td_saved['PRIORITY'], PRIORITY)
        self.assertEqual(td_saved['STATUS'], STATUS)


    #@unittest.skip
    def test_paste_15_todo_due_date(self) -> None:
        # Paste todo with due date
        SHORT_DESC = 'Test todo with due date'
        DT_DUE = date(1999,12,31)
        td = self._new_todo(SHORT_DESC, due=DT_DUE)
        self._do_paste_todo(td)

        # Test pasted entry
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        pasted = l[0] # Simple list (not occs) for todos
        self.check_stamps(td, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DUE'].dt, DT_DUE)

        # Test version saved to disk is also OK
        td_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, td_saved, same_obj=True)
        self.assertEqual(td_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(td_saved['DUE'].dt, DT_DUE)


    #@unittest.skip
    def test_paste_16_todo_longdesc(self) -> None:
        # Paste todo with longdesc
        SHORT_DESC = 'Test todo with long description'
        LONG_DESC = u"""

This description has some newlines and unicode emoji.

😉 😂 😋
"""
        td = self._new_todo(SHORT_DESC, longdesc=LONG_DESC)
        self._do_paste_todo(td)

        # Test pasted entry
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        pasted = l[0] # Simple list (not occs) for todos
        self.check_stamps(td, pasted, new_copy=True)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DESCRIPTION'], LONG_DESC)

        # Test version saved to disk is also OK
        td_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, td_saved, same_obj=True)
        self.assertEqual(td_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(td_saved['DESCRIPTION'], LONG_DESC)


    #@unittest.skip
    def test_paste_17_todo_as_event(self) -> None:
        # Paste todo as an event
        SHORT_DESC = 'Test todo (destined to become an event)'
        CATS = ('cat1',)
        DT_DUE = date(2024,3,5)
        PRIORITY = 8
        STATUS = 'NEEDS-ACTION'
        LONG_DESC = 'Long description here'
        td = self._new_todo(SHORT_DESC, cats=CATS, due=DT_DUE, priority=PRIORITY, status=STATUS, longdesc=LONG_DESC)
        self.assertEqual(td['SUMMARY'], SHORT_DESC)
        self.assertEqual(td['CATEGORIES'].cats[0], CATS[0])
        self.assertEqual(td['DUE'].dt, DT_DUE)
        self.assertEqual(td['PRIORITY'], PRIORITY)
        self.assertEqual(td['STATUS'], STATUS)
        self.assertEqual(td['DESCRIPTION'], LONG_DESC)

        DT_TARG = date(2029,7,1)
        self._do_paste_event(td, DT_TARG)

        # Test pasted entry
        l = Calendar.occurrence_list(date(2029,1,1), date(2030,1,1))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][1], DT_TARG)
        pasted = l[0][0] # occurrences, so entry/datetime pair
        self.check_stamps(td, pasted, new_copy=True, same_type=False)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertEqual(pasted['DTSTART'].dt, DT_TARG)
        self.assertEqual(pasted['CATEGORIES'].cats, td['CATEGORIES'].cats)
        self.assertNotIn('DUE', pasted)
        self.assertEqual(pasted['PRIORITY'], PRIORITY)
        self.assertNotIn('STATUS', pasted)
        self.assertEqual(pasted['DESCRIPTION'], LONG_DESC)

        # Test version saved to disk is also OK
        ev_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, ev_saved, same_obj=True)
        self.assertEqual(ev_saved['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev_saved['DTSTART'].dt, DT_TARG)
        self.assertEqual(ev_saved['CATEGORIES'].cats, td['CATEGORIES'].cats)
        self.assertNotIn('DUE', ev_saved)
        self.assertEqual(ev_saved['PRIORITY'], PRIORITY)
        self.assertNotIn('STATUS', ev_saved)
        self.assertEqual(ev_saved['DESCRIPTION'], LONG_DESC)


    #@unittest.skip
    def test_paste_18_event_as_todo(self) -> None:
        # Paste event as a todo
        SHORT_DESC = 'Test event (destined to become a todo)'
        DT_ST = datetime(2024,5,11,17,5)
        DT_END = datetime(2024,5,11,18,55)
        STATUS = 'CONFIRMED'
        LONG_DESC = 'Some long description'
        LOCATION = '221b Baker Street, London, England'
        ev = self._new_event(SHORT_DESC, DT_ST, end=DT_END, status=STATUS, longdesc=LONG_DESC, location=LOCATION)
        self.assertEqual(ev['SUMMARY'], SHORT_DESC)
        self.assertEqual(ev['DTSTART'].dt, DT_ST)
        self.assertEqual(ev['DTEND'].dt, DT_END)
        self.assertEqual(ev['STATUS'], STATUS)
        self.assertEqual(ev['DESCRIPTION'], LONG_DESC)
        self.assertEqual(ev['LOCATION'], LOCATION)

        self._do_paste_todo(ev)

        # Test pasted entry
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        pasted = l[0]
        self.check_stamps(ev, pasted, new_copy=True, same_type=False)
        self.assertEqual(pasted['SUMMARY'], SHORT_DESC)
        self.assertNotIn('DTSTART', pasted)
        self.assertNotIn('DTEND', pasted)
        self.assertNotIn('DUE', pasted)
        self.assertNotIn('STATUS', pasted)
        self.assertEqual(pasted['DESCRIPTION'], LONG_DESC)
        self.assertEqual(pasted['LOCATION'], LOCATION)

        # Test version saved to disk is also OK
        td_saved = self._get_saved_version(pasted)
        self.check_stamps(pasted, td_saved, same_obj=True)
        self.assertEqual(td_saved['SUMMARY'], SHORT_DESC)
        self.assertNotIn('DTSTART', td_saved)
        self.assertNotIn('DTEND', td_saved)
        self.assertNotIn('DUE', td_saved)
        self.assertNotIn('STATUS', td_saved)
        self.assertEqual(td_saved['DESCRIPTION'], LONG_DESC)
        self.assertEqual(td_saved['LOCATION'], LOCATION)


    def check_stamps(self, en1, en2, same_obj=False, new_copy=False, same_type=True) -> None:
        # Helper function to test uids/timestamps of two entries consistent.
        # Assumes en2 derived from en1, so dtstamp of en2 is later.
        # Args:
        #    same_obj: Really should be identical (e.g. save to storage)
        #    new_copy: Split from old (e.g. by copy-pasting) so different
        if same_type:
            self.assertEqual(type(en1), type(en2))
        else:
            self.assertNotEqual(type(en1), type(en2))
        if new_copy:
            self.assertNotEqual(en1['UID'], en2['UID'])
            self.assertLess(en1['CREATED'].dt, en2['CREATED'].dt)
        else:
            self.assertEqual(en1['UID'], en2['UID'])
            self.assertEqual(en1['CREATED'].dt, en2['CREATED'].dt)
        if same_obj:
            self.assertEqual(en1['DTSTAMP'].dt, en2['DTSTAMP'].dt)
        else:
            self.assertLess(en1['DTSTAMP'].dt, en2['DTSTAMP'].dt)


# Run all tests if this file is executed as main
if __name__ == '__main__':
    unittest.main()
