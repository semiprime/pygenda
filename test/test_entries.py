#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# test_entries.py
# Unit tests for events/todos - creation/modification/deletion
#
# Copyright (C) 2023,2024 Matthew Lewis
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
from os import remove as os_remove
from icalendar import Event as iEvent, Todo as iTodo
from time import sleep

# Add '..' to path, so this can be run from test directory
import sys
sys.path.append('..')

# Import the modules we need for testing...
from pygenda.pygenda_calendar import Calendar
from pygenda.pygenda_entryinfo import EntryInfo
from pygenda.pygenda_config import Config


class TestEntries(unittest.TestCase):
    maxDiff = None # show unlimited chars when showing diffs
    TESTFILE_NAME = 'test_entries_TESTFILE.ics'
    uid_list = []

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


    def setUp(self) -> None:
        # This is called before each individual test function

        # Delete test ics files, so a new one is created
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


    #@unittest.skip
    def test_event_01_create_modify(self) -> None:
        # Create and modify a basic event

        ev = Calendar.new_entry(EntryInfo(desc='event 01', start_dt=date(1988,4,2)))
        self.check_entry_timestamps_new(ev)
        self.check_entry_basic_properties(ev, 'event 01', date(1988,4,2))

        sleep(1) # Sleep to check modtime > created time

        # Change date
        Calendar.update_entry(ev,EntryInfo(desc='event 01',start_dt=date(1988,4,3)))
        self.check_entry_timestamps_mod(ev)
        self.check_entry_basic_properties(ev, 'event 01', date(1988,4,3))

        # Change summary
        Calendar.update_entry(ev,EntryInfo(desc='event 01a',start_dt=date(1988,4,3)))
        self.check_entry_timestamps_mod(ev)
        self.check_entry_basic_properties(ev, 'event 01a', date(1988,4,3))

        # Add time
        Calendar.update_entry(ev,EntryInfo(desc='event 01',start_dt=datetime(1988,4,3,12,30,30)))
        self.check_entry_timestamps_mod(ev)
        self.check_entry_basic_properties(ev, 'event 01', datetime(1988,4,3,12,30,30))


    #@unittest.skip
    def test_event_02_delete(self) -> None:
        # Create and delete an event

        ev = Calendar.new_entry(EntryInfo(desc='event 02', start_dt=date(1991,11,18)))
        self.check_entry_timestamps_new(ev)
        self.check_entry_basic_properties(ev, 'event 02', date(1991,11,18))
        l = Calendar.occurrence_list(date(1991,11,18), date(1991,11,19))
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0][0], ev) # l is list of occurrences (ev/dt pairs)

        Calendar.delete_entry(ev)
        l = Calendar.occurrence_list(date(1991,11,18), date(1991,11,19))
        self.assertEqual(len(l), 0)


    #@unittest.skip
    def test_event_03_toggle_status(self) -> None:
        # Test toggle status function
        # Tests bug fixed in c3900e0bbe08

        ev = Calendar.new_entry(EntryInfo(desc='event 03', start_dt=date(1994,7,1)))
        self.check_entry_timestamps_new(ev)
        self.check_entry_basic_properties(ev, 'event 03', date(1994,7,1))

        sleep(1) # Sleep to check modtime > created time

        Calendar.set_toggle_status_entry(ev, None)
        self.check_entry_timestamps_new(ev, uid_new=False)
        self.check_entry_basic_properties(ev, 'event 03', date(1994,7,1))

        Calendar.set_toggle_status_entry(ev, 'CONFIRMED')
        self.check_entry_timestamps_mod(ev)
        self.check_entry_basic_properties(ev, 'event 03', date(1994,7,1), 'CONFIRMED')

        Calendar.set_toggle_status_entry(ev, 'invalid') # => status undefined
        self.check_entry_timestamps_mod(ev)
        self.check_entry_basic_properties(ev, 'event 03', date(1994,7,1))

        Calendar.set_toggle_status_entry(ev, 'TENTATIVE')
        self.check_entry_timestamps_mod(ev)
        self.check_entry_basic_properties(ev, 'event 03', date(1994,7,1), 'TENTATIVE')

        Calendar.set_toggle_status_entry(ev, 'CANCELLED')
        self.check_entry_timestamps_mod(ev)
        self.check_entry_basic_properties(ev, 'event 03', date(1994,7,1), 'CANCELLED')

        # Toggling to current value switches it off
        Calendar.set_toggle_status_entry(ev, 'CANCELLED')
        self.check_entry_timestamps_mod(ev)
        self.check_entry_basic_properties(ev, 'event 03', date(1994,7,1))


    #@unittest.skip
    def test_event_04_paste(self) -> None:
        # Test pasting events

        ev = Calendar.new_entry(EntryInfo(desc='event 04', start_dt=date(2001,4,30)))
        self.check_entry_timestamps_new(ev)
        self.check_entry_basic_properties(ev, 'event 04', date(2001,4,30))

        ev2 = Calendar.paste_entry(ev)
        self.check_entry_timestamps_new(ev2)
        self.check_entry_basic_properties(ev2, 'event 04', date(2001,4,30), expected_count=2)
        self.assertNotEqual(ev['UID'], ev2['UID'])

        # Test ev hasn't been changed by being pasted elsewhere
        self.check_entry_timestamps_new(ev, uid_new=False)
        self.check_entry_basic_properties(ev, 'event 04', date(2001,4,30), expected_count=2)

        # "Paste" to different date
        ev3 = Calendar.paste_entry(ev, dt_start=date(2001,5,2))
        self.check_entry_timestamps_new(ev3)
        self.check_entry_basic_properties(ev3, 'event 04', date(2001,5,2))
        self.assertNotEqual(ev['UID'], ev3['UID'])
        self.assertNotEqual(ev2['UID'], ev3['UID'])

        # Test ev hasn't been changed by being pasted elsewhere
        self.check_entry_timestamps_new(ev, uid_new=False)
        self.check_entry_basic_properties(ev, 'event 04', date(2001,4,30), expected_count=2)

        # Check Calendar finds three events in 3-day range
        occs = Calendar.occurrence_list(date(2001,4,30), date(2001,5,3))
        self.assertEqual(len(occs), 3)


    #@unittest.skip
    def test_event_05_rapid_create(self) -> None:
        # Create multiple events in quick succession
        # Motivation for this test is to test UIDs are unique

        desc_base = 'event 05.'
        dt = date(2008,1,29)
        oneday = timedelta(days=1)
        desc = []
        stdt = []
        for i in range(8):
            desc.append(desc_base+str(i))
            stdt.append(dt)
            dt += oneday

        ev0 = Calendar.new_entry(EntryInfo(desc=desc[0], start_dt=stdt[0]))
        ev1 = Calendar.new_entry(EntryInfo(desc=desc[1], start_dt=stdt[1]))
        ev2 = Calendar.new_entry(EntryInfo(desc=desc[2], start_dt=stdt[2]))
        ev3 = Calendar.new_entry(EntryInfo(desc=desc[3], start_dt=stdt[3]))
        ev4 = Calendar.new_entry(EntryInfo(desc=desc[4], start_dt=stdt[4]))
        ev5 = Calendar.new_entry(EntryInfo(desc=desc[5], start_dt=stdt[5]))
        ev6 = Calendar.new_entry(EntryInfo(desc=desc[6], start_dt=stdt[6]))
        ev7 = Calendar.new_entry(EntryInfo(desc=desc[7], start_dt=stdt[7]))
        self.check_entry_timestamps_new(ev0)
        self.check_entry_basic_properties(ev0, desc[0], stdt[0])
        self.check_entry_timestamps_new(ev1)
        self.check_entry_basic_properties(ev1, desc[1], stdt[1])
        self.check_entry_timestamps_new(ev2)
        self.check_entry_basic_properties(ev2, desc[2], stdt[2])
        self.check_entry_timestamps_new(ev3)
        self.check_entry_basic_properties(ev3, desc[3], stdt[3])
        self.check_entry_timestamps_new(ev4)
        self.check_entry_basic_properties(ev4, desc[4], stdt[4])
        self.check_entry_timestamps_new(ev5)
        self.check_entry_basic_properties(ev5, desc[5], stdt[5])
        self.check_entry_timestamps_new(ev6)
        self.check_entry_basic_properties(ev6, desc[6], stdt[6])
        self.check_entry_timestamps_new(ev7)
        self.check_entry_basic_properties(ev7, desc[7], stdt[7])


    #@unittest.skip
    def test_todo_01_create_modify(self) -> None:
        # Create and modify a basic todo

        td = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc='todo 01'))
        self.check_entry_timestamps_new(td)
        self.check_entry_basic_properties(td, 'todo 01')

        sleep(1) # Sleep to check modtime > created time

        # Change summary
        Calendar.update_entry(td,EntryInfo(type=EntryInfo.TYPE_TODO, desc='todo 01a'))
        self.check_entry_timestamps_mod(td)
        self.check_entry_basic_properties(td, 'todo 01a')

        # Change category
        ei_cat = EntryInfo(type=EntryInfo.TYPE_TODO, desc='todo 01')
        ei_cat.set_categories(('Test',))
        Calendar.update_entry(td, ei_cat)
        self.check_entry_timestamps_mod(td)
        self.check_entry_basic_properties(td, 'todo 01')
        self.assertIn('CATEGORIES', td)
        self.assertEqual(len(td['CATEGORIES'].cats), 1)
        self.assertEqual(td['CATEGORIES'].cats[0], 'Test')

        # Change priority
        ei_pri = EntryInfo(type=EntryInfo.TYPE_TODO, desc='todo 01')
        ei_pri.set_priority(7)
        Calendar.update_entry(td, ei_pri)
        self.check_entry_timestamps_mod(td)
        self.check_entry_basic_properties(td, 'todo 01')
        self.assertNotIn('CATEGORIES', td) # Test categories removed
        self.assertIn('PRIORITY', td)
        self.assertEqual(td['PRIORITY'], 7)

        # Change status
        ei_stat = EntryInfo(type=EntryInfo.TYPE_TODO, desc='todo 01', status='NEEDS-ACTION')
        Calendar.update_entry(td, ei_stat)
        self.check_entry_timestamps_mod(td)
        self.check_entry_basic_properties(td, 'todo 01', stat='NEEDS-ACTION')
        self.assertNotIn('PRIORITY', td) # Test priority removed

        # Non-valid status
        # (Should remove status)
        ei_stat2 = EntryInfo(type=EntryInfo.TYPE_TODO, desc='todo 01', status='TENTATIVE')
        Calendar.update_entry(td, ei_stat2)
        self.check_entry_timestamps_mod(td)
        self.check_entry_basic_properties(td, 'todo 01')


    #@unittest.skip
    def test_todo_02_delete(self) -> None:
        # Create and delete a todo

        td = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc='todo 02'))
        self.check_entry_timestamps_new(td)
        self.check_entry_basic_properties(td, 'todo 02')
        l = Calendar.todo_list()
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0], td)

        Calendar.delete_entry(td)
        l = Calendar.todo_list()
        self.assertEqual(len(l), 0)


    #@unittest.skip
    def test_todo_03_toggle_status(self) -> None:
        # Test toggle status function

        td = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc='todo 03'))
        self.check_entry_timestamps_new(td)
        self.check_entry_basic_properties(td, 'todo 03')

        sleep(1) # Sleep to check modtime > created time

        Calendar.set_toggle_status_entry(td, None)
        self.check_entry_timestamps_new(td, uid_new=False)
        self.check_entry_basic_properties(td, 'todo 03')

        Calendar.set_toggle_status_entry(td, 'COMPLETED')
        self.check_entry_timestamps_mod(td)
        self.check_entry_basic_properties(td, 'todo 03', stat='COMPLETED')

        # Check using a status for events
        Calendar.set_toggle_status_entry(td, 'CONFIRMED')
        self.check_entry_timestamps_mod(td)
        self.check_entry_basic_properties(td, 'todo 03')

        Calendar.set_toggle_status_entry(td, 'IN-PROCESS')
        self.check_entry_timestamps_mod(td)
        self.check_entry_basic_properties(td, 'todo 03', stat='IN-PROCESS')

        Calendar.set_toggle_status_entry(td, 'COMPLETED')
        self.check_entry_timestamps_mod(td)
        self.check_entry_basic_properties(td, 'todo 03', stat='COMPLETED')

        Calendar.set_toggle_status_entry(td, 'NEEDS-ACTION')
        self.check_entry_timestamps_mod(td)
        self.check_entry_basic_properties(td, 'todo 03', stat='NEEDS-ACTION')

        # Toggling to current value switches it off
        Calendar.set_toggle_status_entry(td, 'NEEDS-ACTION')
        self.check_entry_timestamps_mod(td)
        self.check_entry_basic_properties(td, 'todo 03')


    #@unittest.skip
    def test_todo_04_paste(self) -> None:
        # Test pasting todos

        td = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc='todo 04'))
        self.check_entry_timestamps_new(td)
        self.check_entry_basic_properties(td, 'todo 04')

        td2 = Calendar.paste_entry(td)
        self.check_entry_timestamps_new(td2)
        self.check_entry_basic_properties(td2, 'todo 04')
        self.assertNotEqual(td['UID'], td2['UID'])

        # Test td hasn't been changed by being pasted elsewhere
        self.check_entry_timestamps_new(td, uid_new=False)
        self.check_entry_basic_properties(td, 'todo 04')

        # "Paste" to different todo list (category)
        td3 = Calendar.paste_entry(td, e_cats=('some cat',))
        self.check_entry_timestamps_new(td3)
        self.check_entry_basic_properties(td3, 'todo 04')
        self.assertIn('CATEGORIES', td3)
        self.assertEqual(len(td3['CATEGORIES'].cats), 1)
        self.assertEqual(td3['CATEGORIES'].cats[0], 'some cat')
        self.assertNotEqual(td['UID'], td3['UID'])
        self.assertNotEqual(td2['UID'], td3['UID'])

        # Test td hasn't been changed by being pasted elsewhere
        self.check_entry_timestamps_new(td, uid_new=False)
        self.check_entry_basic_properties(td, 'todo 04')

        # "Paste" duplicate in same todo list (category)
        td4 = Calendar.paste_entry(td3, e_cats=True) #True=keep cats
        self.check_entry_timestamps_new(td4)
        self.check_entry_basic_properties(td4, 'todo 04')
        self.assertIn('CATEGORIES', td4)
        self.assertEqual(len(td4['CATEGORIES'].cats), 1)
        self.assertEqual(td4['CATEGORIES'].cats[0], 'some cat')
        self.assertNotEqual(td3['UID'], td4['UID'])

        # "Paste" duplicate td3 from one category to another
        td5 = Calendar.paste_entry(td3, e_cats=('another cat',))
        self.check_entry_timestamps_new(td5)
        self.check_entry_basic_properties(td5, 'todo 04')
        self.assertIn('CATEGORIES', td5)
        self.assertEqual(len(td5['CATEGORIES'].cats), 1)
        self.assertEqual(td5['CATEGORIES'].cats[0], 'another cat')
        self.assertNotEqual(td3['UID'], td5['UID'])

        # Test td3 hasn't been changed by being pasted elsewhere
        self.check_entry_timestamps_new(td3, uid_new=False)
        self.check_entry_basic_properties(td3, 'todo 04')
        self.assertEqual(len(td3['CATEGORIES'].cats), 1)
        self.assertEqual(td3['CATEGORIES'].cats[0], 'some cat')


    #@unittest.skip
    def test_todo_05_rapid_create(self) -> None:
        # Create multiple todos in quick succession

        desc_base = 'todo 05.'
        desc = []
        for i in range(8):
            desc.append(desc_base+str(i))

        td0 = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc=desc[0]))
        td1 = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc=desc[1]))
        td2 = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc=desc[2]))
        td3 = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc=desc[3]))
        td4 = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc=desc[4]))
        td5 = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc=desc[5]))
        td6 = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc=desc[6]))
        td7 = Calendar.new_entry(EntryInfo(type=EntryInfo.TYPE_TODO, desc=desc[7]))
        self.check_entry_timestamps_new(td0)
        self.check_entry_basic_properties(td0, desc[0])
        self.check_entry_timestamps_new(td1)
        self.check_entry_basic_properties(td1, desc[1])
        self.check_entry_timestamps_new(td2)
        self.check_entry_basic_properties(td2, desc[2])
        self.check_entry_timestamps_new(td3)
        self.check_entry_basic_properties(td3, desc[3])
        self.check_entry_timestamps_new(td4)
        self.check_entry_basic_properties(td4, desc[4])
        self.check_entry_timestamps_new(td5)
        self.check_entry_basic_properties(td5, desc[5])
        self.check_entry_timestamps_new(td6)
        self.check_entry_basic_properties(td6, desc[6])
        self.check_entry_timestamps_new(td7)
        self.check_entry_basic_properties(td7, desc[7])


    def check_entry_timestamps_new(self, en, uid_new=True) -> None:
        # Helper function checks new entry timestamps/uid.
        # Also stores list of uids and checks these.
        # Set uid_new=True to check UID new; False to check UID seen.
        self.assertIn('UID', en)
        if uid_new:
            self.assertNotIn(en['UID'], self.uid_list)
            self.uid_list.append(en['UID'])
        else:
            self.assertIn(en['UID'], self.uid_list)
        self.assertIn('DTSTAMP', en)
        self.assertIn('CREATED', en)
        self.assertEqual(en['DTSTAMP'].dt, en['CREATED'].dt)


    def check_entry_timestamps_mod(self, en, uid_new=False) -> None:
        # Helper function checks modified entry timestamps
        # Set uid_new=True to check UID new; False to check UID seen.
        self.assertIn('UID', en)
        if uid_new:
            self.assertNotIn(en['UID'], self.uid_list)
        else:
            self.assertIn(en['UID'], self.uid_list)
        self.assertIn('DTSTAMP', en)
        self.assertIn('CREATED', en)
        self.assertIn('LAST-MODIFIED', en)
        self.assertEqual(en['DTSTAMP'].dt, en['LAST-MODIFIED'].dt)
        self.assertTrue(en['CREATED'].dt < en['DTSTAMP'].dt)


    def check_entry_basic_properties(self, en, summ:str, dtst:datetime=None, stat:str=None, expected_count=1) -> None:
        # Helper function checks new entry timestamps
        self.assertEqual(en['SUMMARY'], summ)
        if isinstance(en, iEvent):
            self.assertIn('DTSTART', en)
            self.assertEqual(en['DTSTART'].dt, dtst)
        else:
            self.assertTrue(isinstance(en, iTodo))
            self.assertNotIn('DTSTART', en)
        if stat is None:
            self.assertNotIn('STATUS', en)
        else:
            self.assertEqual(en['STATUS'], stat)

        if dtst is not None:
            # Get occurence list for one day and check en is in it (once only)
            l = Calendar.occurrence_list(dtst, dtst+timedelta(days=1))
            self.assertEqual(len(l), expected_count)
            found_en = 0
            for e in l:
                if e[0]==en:
                    found_en += 1
            self.assertEqual(found_en, 1)


# Run all tests if this file is executed as main
if __name__ == '__main__':
    unittest.main()
