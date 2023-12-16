#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# test_ongoing.py
# Run unit tests for ongoing entries in Pygenda
#
# Copyright (C) 2023 Matthew Lewis
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
from datetime import date, datetime, timedelta
from dateutil import tz
from os import remove as os_remove

# Add '..' to path, so this can be run from test directory
import sys
sys.path.append('..')

# Import the modules we need for testing...
from pygenda.pygenda_calendar import Calendar
from pygenda.pygenda_config import Config
from pygenda.pygenda_entryinfo import EntryInfo
from pygenda.pygenda_util import get_local_tz, _set_local_tz as set_local_tz


class TestOngoing(unittest.TestCase):
    maxDiff = None # show unlimited chars when showing diffs
    TESTFILE_NAME = 'test_ongoing_TESTFILE.ics'

    @classmethod
    def setUpClass(cls):
        # Called once before all tests
        # Save local timezone, so running tests will test in your tz
        cls.saved_tz = get_local_tz()
        # Override config options so it uses our test ics file
        Config.set('calendar', 'type', 'icalfile')
        Config.set('calendar', 'filename', cls.TESTFILE_NAME)
        Config.set('calendar', 'display_name', 'Test calendar for test_ongoing')
        Config.set('calendar', 'readonly', None)
        Config.set('calendar', 'entry_type', None)
        Config.set('calendar1', 'type', None) # so only specified file opened


    def setUp(self) -> None:
        # This is called before each individual test function

        # Delete test ics files, so a new one is created
        self._delete_testfile()

        # Reset timezone for next test (might be changed in test)
        set_local_tz(self.saved_tz)

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


    #@unittest.skip
    def test_01_empty(self) -> None:
        # Test empty database
        self.check_ongoing_count(date(1963,11,27), 0)
        self.check_ongoing_count(date(1999,12,31), 0)
        self.check_ongoing_count(date(2000,1,1), 0)
        self.check_ongoing_count(date(2020,1,1), 0)
        self.check_ongoing_count(date(2021,1,1), 0)
        self.check_ongoing_count(date(2020,2,28), 0)
        self.check_ongoing_count(date(2020,2,29), 0)
        self.check_ongoing_count(date(2020,3,1), 0)


    #@unittest.skip
    def test_02_untimed(self) -> None:
        # Test untimed, single-day and multi-day events

        # Simple untimed event
        Calendar.new_entry(EntryInfo(desc='untimed', start_dt=date(2020,2,3)))
        self.check_ongoing_count(date(2020,2,3), 0)
        self.check_ongoing_count(date(2020,2,4), 0)

        # one-day event
        Calendar.new_entry(EntryInfo(desc='one-day', start_dt=date(2020,2,10), end_dt=date(2020,2,11)))
        self.check_ongoing_count(date(2020,2,10), 0)
        self.check_ongoing_count(date(2020,2,11), 0)

        # two-day event
        Calendar.new_entry(EntryInfo(desc='two-day', start_dt=date(2020,2,16), end_dt=date(2020,2,18)))
        self.check_ongoing_count(date(2020,2,16), 0)
        self.check_ongoing_count(date(2020,2,17), 1)
        self.check_ongoing_count(date(2020,2,18), 0)


    #@unittest.skip
    def test_03_timed(self) -> None:
        # Test timed events, with duration & with endtime

        # Simple timed event
        Calendar.new_entry(EntryInfo(desc='timed', start_dt=datetime(2021,3,4,10,30)))
        self.check_ongoing_count(date(2021,3,4), 0)
        self.check_ongoing_count(date(2021,3,5), 0)

        # Timed event, short duration (doesn't cross midnight)
        Calendar.new_entry(EntryInfo(desc='timed short duration', start_dt=datetime(2021,3,8,11,45), duration=timedelta(minutes=30)))
        self.check_ongoing_count(date(2021,3,8), 0)
        self.check_ongoing_count(date(2021,3,9), 0)

        # Timed event, medium duration (once across midnight)
        Calendar.new_entry(EntryInfo(desc='timed med duration', start_dt=datetime(2021,3,13,19,30), duration=timedelta(hours=10)))
        self.check_ongoing_count(date(2021,3,13), 0)
        self.check_ongoing_count(date(2021,3,14), 1)
        self.check_ongoing_count(date(2021,3,15), 0)

        # Timed event, long duration (cross midnight multiple times)
        Calendar.new_entry(EntryInfo(desc='timed long duration', start_dt=datetime(2021,3,19,13,0), duration=timedelta(days=15, hours=13)))
        self.check_ongoing_count(date(2021,3,19), 0)
        dt = date(2021,3,20)
        for i in range(16):
            self.check_ongoing_count(dt, 1)
            dt += timedelta(days=1)
        self.check_ongoing_count(date(2021,4,4), 1) # also checked in loop
        self.check_ongoing_count(date(2021,4,5), 0)

        # Timed event, endtime short (doesn't cross midnight)
        Calendar.new_entry(EntryInfo(desc='timed short endtime', start_dt=datetime(2021,4,8,10,40), end_dt=datetime(2021,4,8,18,49)))
        self.check_ongoing_count(date(2021,4,8), 0)
        self.check_ongoing_count(date(2021,4,9), 0)

        # Timed event, endtime medium (once across midnight)
        Calendar.new_entry(EntryInfo(desc='timed med endtime', start_dt=datetime(2021,4,13,18,15), end_dt=datetime(2021,4,14,18,15)))
        self.check_ongoing_count(date(2021,4,13), 0)
        self.check_ongoing_count(date(2021,4,14), 1)
        self.check_ongoing_count(date(2021,4,15), 0)

        # Timed event, long duration (cross midnight multiple times)
        Calendar.new_entry(EntryInfo(desc='timed long endtime', start_dt=datetime(2021,4,19,13,0), end_dt=datetime(2021,5,1,2,0)))
        self.check_ongoing_count(date(2021,4,19), 0)
        dt = date(2021,4,20)
        for i in range(12):
            self.check_ongoing_count(dt, 1)
            dt += timedelta(days=1)
        self.check_ongoing_count(date(2021,5,1), 1) # also checked in loop
        self.check_ongoing_count(date(2021,5,2), 0)


    #@unittest.skip
    def test_04_overlapping(self) -> None:
        # Test overlapping events
        Calendar.new_entry(EntryInfo(desc='overlapping 1', start_dt=datetime(2021,5,25), end_dt=datetime(2021,6,4)))
        Calendar.new_entry(EntryInfo(desc='overlapping 2', start_dt=datetime(2021,5,27,23,59), duration=timedelta(days=10)))
        Calendar.new_entry(EntryInfo(desc='overlapping 3', start_dt=date(2021,5,28)))
        Calendar.new_entry(EntryInfo(desc='overlapping 4', start_dt=datetime(2021,6,1,17,45)))
        Calendar.new_entry(EntryInfo(desc='overlapping 5', start_dt=datetime(2021,5,30,19,0), end_dt=datetime(2021,5,31,0,0)))
        self.check_ongoing_count(date(2021,5,25), 0)
        dt = date(2021,5,26)
        for i in range(2): # 26,27
            self.check_ongoing_count(dt, 1)
            dt += timedelta(days=1)
        for i in range(7): # 28,29,30,31,1,2,3
            self.check_ongoing_count(dt, 2)
            dt += timedelta(days=1)
        for i in range(3): # 4,5,6
            self.check_ongoing_count(dt, 1)
            dt += timedelta(days=1)
        self.check_ongoing_count(date(2021,6,6), 1) # already checked in loop
        self.check_ongoing_count(date(2021,6,7), 0)


    #@unittest.skip
    def test_05_midnight(self) -> None:
        # Test cases starting/ending at midnight
        # Timed event at midnight
        Calendar.new_entry(EntryInfo(desc='at midnight', start_dt=datetime(2021,6,9,0,0)))
        self.check_ongoing_count(date(2021,6,9), 0)
        self.check_ongoing_count(date(2021,6,10), 0)

        # Event ending at midnight
        Calendar.new_entry(EntryInfo(desc='ends midnight', start_dt=datetime(2021,6,12,19,10), end_dt=datetime(2021,6,13,0,0)))
        self.check_ongoing_count(date(2021,6,12), 0)
        self.check_ongoing_count(date(2021,6,13), 0)

        # Multi-day event ending at midnight
        Calendar.new_entry(EntryInfo(desc='ends midnight in two days', start_dt=datetime(2021,6,16,14,0,0), end_dt=datetime(2021,6,19,0,0)))
        self.check_ongoing_count(date(2021,6,16), 0)
        self.check_ongoing_count(date(2021,6,17), 1)
        self.check_ongoing_count(date(2021,6,18), 1)
        self.check_ongoing_count(date(2021,6,19), 0)

        # Event with duration ending at midnight
        Calendar.new_entry(EntryInfo(desc='duration to midnight', start_dt=datetime(2021,6,21,17,30), duration=timedelta(hours=6, minutes=30)))
        self.check_ongoing_count(date(2021,6,21), 0)
        self.check_ongoing_count(date(2021,6,22), 0)

        # Multi-day event with duration ending at midnight
        Calendar.new_entry(EntryInfo(desc='duration to midnight', start_dt=datetime(2021,6,25,11,15), duration=timedelta(days=2, hours=12, minutes=45)))
        self.check_ongoing_count(date(2021,6,25), 0)
        self.check_ongoing_count(date(2021,6,26), 1)
        self.check_ongoing_count(date(2021,6,27), 1)
        self.check_ongoing_count(date(2021,6,28), 0)


    #@unittest.skip
    def test_06_timezone(self) -> None:
        # Test cases with non-local timezone

        # Just has a timezone, to check it even works
        tz_LON = tz.gettz('Europe/London')
        self.assertTrue(tz_LON) # check not None
        Calendar.new_entry(EntryInfo(desc='with timezone', start_dt=datetime(2021,7,4,12,0,tzinfo=tz_LON)))
        self.check_ongoing_count(date(2021,7,4), 0)
        self.check_ongoing_count(date(2021,7,5), 0)

        # With an endtime, not crossing midnight
        Calendar.new_entry(EntryInfo(desc='with timezone & endtime', start_dt=datetime(2021,7,6,12,0,tzinfo=tz_LON), end_dt=datetime(2021,7,6,13,0,tzinfo=tz_LON)))
        self.check_ongoing_count(date(2021,7,6), 0)
        self.check_ongoing_count(date(2021,7,7), 0)

        # With an endtime, crossing midnight
        Calendar.new_entry(EntryInfo(desc='with timezone, crossing midnight', start_dt=datetime(2021,7,8,12,0,tzinfo=tz_LON), end_dt=datetime(2021,7,9,11,59,tzinfo=tz_LON)))
        self.check_ongoing_count(date(2021,7,8), 0)
        self.check_ongoing_count(date(2021,7,9), 1)
        self.check_ongoing_count(date(2021,7,10), 0)

        # With an endtime, crossing midnight locally
        tz_SAM = tz.gettz('Pacific/Samoa') # UTC-11
        self.assertTrue(tz_SAM) # check not None
        Calendar.new_entry(EntryInfo(desc='with westerly non-local timezone & endtime', start_dt=datetime(2021,7,10,0,5,tzinfo=tz_SAM), end_dt=datetime(2021,7,10,23,55,tzinfo=tz_SAM)))
        self.check_ongoing_count(date(2021,7,10), 0)
        self.check_ongoing_count(date(2021,7,11), 1)
        self.check_ongoing_count(date(2021,7,12), 0)

        # We want to test somewhere that is ahead of local time, so
        # let's take the most easterly timezone we know of.
        tz_NZ = tz.gettz('Pacific/Auckland')
        self.assertTrue(tz_NZ) # check not None

        # Check to see if local timezone is same as event timezone,
        # and if so change local tz to something "neutral".
        if get_local_tz().utcoffset(datetime(2021,7,12,12))>=timedelta(hours=12):
            set_local_tz(tz_LON)

        Calendar.new_entry(EntryInfo(desc='with easterly non-local timezone & endtime', start_dt=datetime(2021,7,13,0,5,tzinfo=tz_NZ), end_dt=datetime(2021,7,13,23,55,tzinfo=tz_NZ)))
        self.check_ongoing_count(date(2021,7,12), 0)
        self.check_ongoing_count(date(2021,7,13), 1)
        self.check_ongoing_count(date(2021,7,14), 0)


    #@unittest.skip
    def test_07_timezone_duration(self) -> None:
        # Test cases with non-local timezone using duration

        tz_LON = tz.gettz('Europe/London')
        self.assertTrue(tz_LON) # check not None

        # With a duration, not crossing midnight
        Calendar.new_entry(EntryInfo(desc='with timezone & duration', start_dt=datetime(2021,7,6,12,0,tzinfo=tz_LON), duration=timedelta(hours=1)))
        self.check_ongoing_count(date(2021,7,6), 0)
        self.check_ongoing_count(date(2021,7,7), 0)

        # With an endtime, crossing midnight
        Calendar.new_entry(EntryInfo(desc='with timezone, crossing midnight', start_dt=datetime(2021,7,8,12,0,tzinfo=tz_LON), duration=timedelta(hours=24)))
        self.check_ongoing_count(date(2021,7,8), 0)
        self.check_ongoing_count(date(2021,7,9), 1)
        self.check_ongoing_count(date(2021,7,10), 0)

        # With an endtime, crossing midnight locally
        tz_SAM = tz.gettz('Pacific/Samoa') # UTC-11
        self.assertTrue(tz_SAM) # check not None
        Calendar.new_entry(EntryInfo(desc='with westerly non-local timezone & endtime', start_dt=datetime(2021,7,10,0,5,tzinfo=tz_SAM), duration=timedelta(hours=23, minutes=50)))
        self.check_ongoing_count(date(2021,7,10), 0)
        self.check_ongoing_count(date(2021,7,11), 1)
        self.check_ongoing_count(date(2021,7,12), 0)

        # We want to test somewhere that is ahead of local time, so
        # let's take the most easterly timezone we know of.
        tz_NZ = tz.gettz('Pacific/Auckland')
        self.assertTrue(tz_NZ) # check not None

        # Check to see if local timezone is same as event timezone,
        # and if so change local tz to something "neutral".
        if get_local_tz().utcoffset(datetime(2021,7,12,12))>=timedelta(hours=12):
            set_local_tz(tz_LON)

        Calendar.new_entry(EntryInfo(desc='with easterly non-local timezone & endtime', start_dt=datetime(2021,7,13,0,5,tzinfo=tz_NZ), duration=timedelta(hours=23, minutes=50)))
        self.check_ongoing_count(date(2021,7,12), 0)
        self.check_ongoing_count(date(2021,7,13), 1)
        self.check_ongoing_count(date(2021,7,14), 0)


    #@unittest.skip
    def test_08_new_year(self) -> None:
        # Test cases over new year

        Calendar.new_entry(EntryInfo(desc='Stopping new year 2024', start_dt=datetime(2023,12,31,11,58), end_dt=datetime(2024,1,1,0,0)))
        self.check_ongoing_count(date(2023,12,31), 0)
        self.check_ongoing_count(date(2024,1,1), 0)
        self.check_ongoing_count(date(2024,1,2), 0)

        Calendar.new_entry(EntryInfo(desc='Starting new year 2024', start_dt=datetime(2024,1,1,0,0), end_dt=datetime(2024,1,1,23,0)))
        self.check_ongoing_count(date(2023,12,31), 0)
        self.check_ongoing_count(date(2024,1,1), 0)
        self.check_ongoing_count(date(2024,1,2), 0)

        Calendar.new_entry(EntryInfo(desc='Over new year 2024', start_dt=datetime(2023,12,31,11,58), end_dt=datetime(2024,1,1,0,1)))
        self.check_ongoing_count(date(2023,12,31), 0)
        self.check_ongoing_count(date(2024,1,1), 1)
        self.check_ongoing_count(date(2024,1,2), 0)

        Calendar.new_entry(EntryInfo(desc='Stopping new year 2023 (duration)', start_dt=datetime(2022,12,31,11,11), duration=timedelta(hours=12,minutes=49)))
        self.check_ongoing_count(date(2022,12,31), 0)
        self.check_ongoing_count(date(2023,1,1), 0)
        self.check_ongoing_count(date(2023,1,2), 0)

        Calendar.new_entry(EntryInfo(desc='Over new year 2023 (duration)', start_dt=datetime(2022,12,31,11,11), duration=timedelta(hours=12,minutes=50)))
        self.check_ongoing_count(date(2022,12,31), 0)
        self.check_ongoing_count(date(2023,1,1), 1)
        self.check_ongoing_count(date(2023,1,2), 0)

        # day entries
        Calendar.new_entry(EntryInfo(desc='Stopping new year 2022', start_dt=date(2021,12,30), end_dt=date(2022,1,1)))
        self.check_ongoing_count(date(2021,12,30), 0)
        self.check_ongoing_count(date(2021,12,31), 1)
        self.check_ongoing_count(date(2022,1,1), 0)
        self.check_ongoing_count(date(2022,1,2), 0)

        Calendar.new_entry(EntryInfo(desc='Starting new year 2022', start_dt=date(2022,1,1), end_dt=date(2022,1,2)))
        self.check_ongoing_count(date(2021,12,31), 1)
        self.check_ongoing_count(date(2022,1,1), 0)
        self.check_ongoing_count(date(2022,1,2), 0)

        Calendar.new_entry(EntryInfo(desc='Over new year 2022', start_dt=date(2021,12,31), end_dt=date(2022,1,2)))
        self.check_ongoing_count(date(2021,12,31), 1)
        self.check_ongoing_count(date(2022,1,1), 1)
        self.check_ongoing_count(date(2022,1,2), 0)

        Calendar.new_entry(EntryInfo(desc='Week-long over new year 2022', start_dt=date(2021,12,29), end_dt=date(2022,1,5)))
        self.check_ongoing_count(date(2021,12,29), 0)
        self.check_ongoing_count(date(2021,12,30), 1)
        self.check_ongoing_count(date(2021,12,31), 2)
        self.check_ongoing_count(date(2022,1,1), 2)
        self.check_ongoing_count(date(2022,1,2), 1)
        self.check_ongoing_count(date(2022,1,3), 1)
        self.check_ongoing_count(date(2022,1,4), 1)
        self.check_ongoing_count(date(2022,1,5), 0)

        # Over multiple years
        Calendar.new_entry(EntryInfo(desc='Event over new years 2020 & 2021', start_dt=date(2019,11,12), end_dt=date(2021,3,1)))
        self.check_ongoing_count(date(2019,11,12), 0)
        self.check_ongoing_count(date(2019,11,13), 1)
        self.check_ongoing_count(date(2019,11,30), 1)
        self.check_ongoing_count(date(2019,12,1), 1)
        self.check_ongoing_count(date(2019,12,31), 1)
        self.check_ongoing_count(date(2020,1,1), 1)
        self.check_ongoing_count(date(2020,1,31), 1)
        self.check_ongoing_count(date(2020,2,1), 1)
        self.check_ongoing_count(date(2020,2,28), 1)
        self.check_ongoing_count(date(2020,2,29), 1) # leap day
        self.check_ongoing_count(date(2020,3,1), 1)
        self.check_ongoing_count(date(2020,7,18), 1)
        self.check_ongoing_count(date(2020,11,12), 1)
        self.check_ongoing_count(date(2020,11,13), 1)
        self.check_ongoing_count(date(2020,11,30), 1)
        self.check_ongoing_count(date(2020,12,1), 1)
        self.check_ongoing_count(date(2020,12,31), 1)
        self.check_ongoing_count(date(2021,1,1), 1)
        self.check_ongoing_count(date(2021,1,31), 1)
        self.check_ongoing_count(date(2021,2,1), 1)
        self.check_ongoing_count(date(2021,2,28), 1)
        self.check_ongoing_count(date(2021,3,1), 0)
        self.check_ongoing_count(date(2021,3,2), 0)
        self.check_ongoing_count(date(2021,3,31), 0)


    #@unittest.skip
    def test_09_daylight_saving_start(self) -> None:
        # Test cases with daylight saving (so also has timezone)

        tz_BER = tz.gettz('Europe/Berlin')
        self.assertTrue(tz_BER) # check not None
        set_local_tz(tz_BER)

        Calendar.new_entry(EntryInfo(desc='over DST start, within day', start_dt=datetime(2024,3,31,0,30,tzinfo=tz_BER), end_dt=datetime(2024,3,31,23,55,tzinfo=tz_BER)))
        self.check_ongoing_count(date(2024,3,31), 0)
        self.check_ongoing_count(date(2024,4,1), 0)

        Calendar.new_entry(EntryInfo(desc='over DST start, less than day', start_dt=datetime(2024,3,31,0,30,tzinfo=tz_BER), end_dt=datetime(2024,4,1,0,1,tzinfo=tz_BER)))
        self.check_ongoing_count(date(2024,3,31), 0)
        self.check_ongoing_count(date(2024,4,1), 1)
        self.check_ongoing_count(date(2024,4,2), 0)

        Calendar.new_entry(EntryInfo(desc='over DST start, duration within day', start_dt=datetime(2023,3,26,0,30,tzinfo=tz_BER), duration=timedelta(hours=22)))
        self.check_ongoing_count(date(2023,3,26), 0)
        self.check_ongoing_count(date(2023,3,27), 0)

        Calendar.new_entry(EntryInfo(desc='over DST start, duration over day', start_dt=datetime(2023,3,26,0,30,tzinfo=tz_BER), duration=timedelta(hours=23)))
        self.check_ongoing_count(date(2023,3,26), 0)
        self.check_ongoing_count(date(2023,3,27), 1)
        self.check_ongoing_count(date(2023,3,28), 0)

        Calendar.new_entry(EntryInfo(desc='over DST start, day event', start_dt=date(2022,3,27), end_dt=date(2022,3,28)))
        self.check_ongoing_count(date(2022,3,27), 0)
        self.check_ongoing_count(date(2022,3,28), 0)

        Calendar.new_entry(EntryInfo(desc='over DST start, 2-day event', start_dt=date(2022,3,27), end_dt=date(2022,3,29)))
        self.check_ongoing_count(date(2022,3,27), 0)
        self.check_ongoing_count(date(2022,3,28), 1)
        self.check_ongoing_count(date(2022,3,29), 0)

        Calendar.new_entry(EntryInfo(desc='over DST start, 4-day event', start_dt=date(2022,3,26), end_dt=date(2022,3,30)))
        self.check_ongoing_count(date(2022,3,26), 0)
        self.check_ongoing_count(date(2022,3,27), 1)
        self.check_ongoing_count(date(2022,3,28), 2)
        self.check_ongoing_count(date(2022,3,29), 1)
        self.check_ongoing_count(date(2022,3,30), 0)

        Calendar.new_entry(EntryInfo(desc='over DST start, day event from duration', start_dt=date(2021,3,27), duration=timedelta(days=1)))
        self.check_ongoing_count(date(2021,3,27), 0)
        self.check_ongoing_count(date(2021,3,28), 0)

        Calendar.new_entry(EntryInfo(desc='over DST start, 2-day event from duration', start_dt=date(2021,3,27), duration=timedelta(days=2)))
        self.check_ongoing_count(date(2021,3,27), 0)
        self.check_ongoing_count(date(2021,3,28), 1)
        self.check_ongoing_count(date(2021,3,29), 0)

        Calendar.new_entry(EntryInfo(desc='over DST start, 4-day event from duration', start_dt=date(2021,3,26), duration=timedelta(days=4)))
        self.check_ongoing_count(date(2021,3,26), 0)
        self.check_ongoing_count(date(2021,3,27), 1)
        self.check_ongoing_count(date(2021,3,28), 2)
        self.check_ongoing_count(date(2021,3,29), 1)
        self.check_ongoing_count(date(2021,3,30), 0)


    #@unittest.skip
    def test_10_daylight_saving_end(self) -> None:
        # Test cases with daylight saving (so also has timezone)

        tz_CHI = tz.gettz('America/Chicago')
        self.assertTrue(tz_CHI) # check not None
        set_local_tz(tz_CHI)

        Calendar.new_entry(EntryInfo(desc='over DST end, within day', start_dt=datetime(2023,11,5,0,30,tzinfo=tz_CHI), end_dt=datetime(2023,11,5,23,55,tzinfo=tz_CHI)))
        self.check_ongoing_count(date(2023,11,5), 0)
        self.check_ongoing_count(date(2023,11,6), 0)

        Calendar.new_entry(EntryInfo(desc='over DST end, duration within day', start_dt=datetime(2022,11,6,0,30,tzinfo=tz_CHI), duration=timedelta(hours=23, minutes=59)))
        self.check_ongoing_count(date(2022,11,6), 0)
        self.check_ongoing_count(date(2022,11,7), 0)

        Calendar.new_entry(EntryInfo(desc='over DST end, duration one day', start_dt=datetime(2022,11,6,0,30,tzinfo=tz_CHI), duration=timedelta(days=1)))
        self.check_ongoing_count(date(2022,11,6), 0)
        self.check_ongoing_count(date(2022,11,7), 1)
        self.check_ongoing_count(date(2022,11,8), 0)

        Calendar.new_entry(EntryInfo(desc='over DST end, day event', start_dt=date(2021,11,7), end_dt=date(2021,11,8)))
        self.check_ongoing_count(date(2021,11,7), 0)
        self.check_ongoing_count(date(2021,11,8), 0)

        Calendar.new_entry(EntryInfo(desc='over DST end, 2-day event', start_dt=date(2021,11,7), end_dt=date(2021,11,9)))
        self.check_ongoing_count(date(2021,11,7), 0)
        self.check_ongoing_count(date(2021,11,8), 1)
        self.check_ongoing_count(date(2021,11,9), 0)

        Calendar.new_entry(EntryInfo(desc='over DST end, 4-day event', start_dt=date(2021,11,6), end_dt=date(2021,11,10)))
        self.check_ongoing_count(date(2021,11,6), 0)
        self.check_ongoing_count(date(2021,11,7), 1)
        self.check_ongoing_count(date(2021,11,8), 2)
        self.check_ongoing_count(date(2021,11,9), 1)
        self.check_ongoing_count(date(2021,11,10), 0)

        Calendar.new_entry(EntryInfo(desc='over DST end, day event from duration', start_dt=date(2020,11,1), duration=timedelta(days=1)))
        self.check_ongoing_count(date(2020,11,1), 0)
        self.check_ongoing_count(date(2020,11,2), 0)

        Calendar.new_entry(EntryInfo(desc='over DST end, 2-day event from duration', start_dt=date(2020,11,1), duration=timedelta(days=2)))
        self.check_ongoing_count(date(2020,11,1), 0)
        self.check_ongoing_count(date(2020,11,2), 1)
        self.check_ongoing_count(date(2020,11,3), 0)

        Calendar.new_entry(EntryInfo(desc='over DST end, 4-day event from duration', start_dt=date(2020,10,31), duration=timedelta(days=4)))
        self.check_ongoing_count(date(2020,10,31), 0)
        self.check_ongoing_count(date(2020,11,1), 1)
        self.check_ongoing_count(date(2020,11,2), 2)
        self.check_ongoing_count(date(2020,11,3), 1)
        self.check_ongoing_count(date(2020,11,4), 0)


    def check_ongoing_count(self, dt:date, count:int) -> None:
        # Helper function checks number of ongoing entries
        ol = Calendar.ongoing_list(dt)
        #print(ol)
        self.assertEqual(len(ol), count)


# Run all tests if this file is executed as main
if __name__ == '__main__':
    unittest.main()
