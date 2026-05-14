#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# test_prevnext.py
# Run unit tests for previous/next repeat calculations in Pygenda
#
# Copyright (C) 2026 Matthew Lewis
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
from datetime import datetime, date, time, timedelta
from dateutil import tz
import icalendar
from dateutil.rrule import rrulestr
from copy import deepcopy
from sys import version_info as python_version
from typing import Optional

# Add '..' to path, so this can be run from test directory
import sys
sys.path.append('..')

# Import pygenda modules...
from pygenda.pygenda_calendar import previous_next_occurrence
from pygenda.pygenda_util import get_local_tz, _set_local_tz as set_local_tz, date_to_datetime


class TestPrevNext(unittest.TestCase):
    maxDiff = None # show unlimited chars when showing diffs

    @classmethod
    def setUpClass(cls):
        # Called once before all tests
        # Save local timezone, so running tests will test in your tz
        cls.local_tz_saved = get_local_tz()


    def setUp(self) -> None:
        # This is called before each individual test function
        # Reset timezone for next test (might be changed in test)
        set_local_tz(self.local_tz_saved)


    #@unittest.skip
    def test_01_yearly_basic(self) -> None:
        # Create simple yearly repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1842,7,20),
            rrule = {'FREQ':['YEARLY']})

        self.check_prevnext(event, date(56,1,1), None, date(1842,7,20))
        self.check_prevnext(event, datetime(875,6,1,12,59,29), None, date(1842,7,20))
        self.check_prevnext(event, date(1840,1,1), None, date(1842,7,20))
        self.check_prevnext(event, date(1842,1,1), None, date(1842,7,20))
        self.check_prevnext(event, date(1842,7,19), None, date(1842,7,20))
        self.check_prevnext(event, datetime(1842,7,19,23,59,59), None, date(1842,7,20))
        self.check_prevnext(event, date(1842,7,20), None,date(1842,7,20))
        self.check_prevnext(event, datetime(1842,7,20,0), None,date(1842,7,20))
        self.check_prevnext(event, datetime(1842,7,20,0,0,1), date(1842,7,20),date(1843,7,20))
        self.check_prevnext(event, date(1842,7,21), date(1842,7,20),date(1843,7,20))
        self.check_prevnext(event, datetime(1842,7,21,14,34), date(1842,7,20),date(1843,7,20))
        self.check_prevnext(event, date(1842,8,1), date(1842,7,20),date(1843,7,20))
        self.check_prevnext(event, date(1842,12,31), date(1842,7,20),date(1843,7,20))
        self.check_prevnext(event, date(1843,1,1), date(1842,7,20),date(1843,7,20))
        self.check_prevnext(event, date(1843,7,1), date(1842,7,20),date(1843,7,20))
        self.check_prevnext(event, date(1843,7,19), date(1842,7,20),date(1843,7,20))
        self.check_prevnext(event, datetime(1843,7,19,23,59), date(1842,7,20),date(1843,7,20))
        self.check_prevnext(event, date(1843,7,20), date(1842,7,20),date(1843,7,20))
        self.check_prevnext(event, date(1843,7,21), date(1843,7,20),date(1844,7,20))
        self.check_prevnext(event, date(1843,12,31), date(1843,7,20),date(1844,7,20))
        self.check_prevnext(event, datetime(1843,12,31,0), date(1843,7,20),date(1844,7,20))
        self.check_prevnext(event, datetime(1843,12,31,23,59,59), date(1843,7,20),date(1844,7,20))
        self.check_prevnext(event, date(1844,1,1), date(1843,7,20),date(1844,7,20))
        self.check_prevnext(event, datetime(1844,1,1,0), date(1843,7,20),date(1844,7,20))
        self.check_prevnext(event, date(1844,7,19), date(1843,7,20),date(1844,7,20))
        self.check_prevnext(event, date(1844,7,20), date(1843,7,20),date(1844,7,20))
        self.check_prevnext(event, date(1844,7,21), date(1844,7,20),date(1845,7,20))
        self.check_prevnext(event, date(1844,12,12), date(1844,7,20),date(1845,7,20))
        self.check_prevnext(event, date(2025,1,1), date(2024,7,20),date(2025,7,20))
        self.check_prevnext(event, date(2025,7,19), date(2024,7,20),date(2025,7,20))
        self.check_prevnext(event, date(2025,7,20), date(2024,7,20),date(2025,7,20))
        self.check_prevnext(event, datetime(2025,7,20,0), date(2024,7,20),date(2025,7,20))
        self.check_prevnext(event, datetime(2025,7,20,0,0,1), date(2025,7,20),date(2026,7,20))
        self.check_prevnext(event, date(2025,7,21), date(2025,7,20),date(2026,7,20))
        self.check_prevnext(event, date(2025,12,31), date(2025,7,20),date(2026,7,20))
        self.check_prevnext(event, date(3187,1,1), date(3186,7,20),date(3187,7,20))
        self.check_prevnext(event, date(3187,7,19), date(3186,7,20),date(3187,7,20))
        self.check_prevnext(event, datetime(3187,7,19,23,59,59), date(3186,7,20),date(3187,7,20))
        self.check_prevnext(event, date(3187,7,20), date(3186,7,20),date(3187,7,20))
        self.check_prevnext(event, datetime(3187,7,20,0), date(3186,7,20),date(3187,7,20))
        self.check_prevnext(event, datetime(3187,7,20,0,0,1), date(3187,7,20),date(3188,7,20))
        self.check_prevnext(event, date(3187,7,21), date(3187,7,20),date(3188,7,20))
        self.check_prevnext(event, date(3187,12,31), date(3187,7,20),date(3188,7,20))


    #@unittest.skip
    def test_02_yearly_timed(self) -> None:
        # Create timed yearly repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1993,12,24,14,15), # time 14:15
            rrule = {'FREQ':['YEARLY']})

        self.check_prevnext(event, date(1066,1,1), None, datetime(1993,12,24,14,15))
        self.check_prevnext(event, date(1990,1,1), None, datetime(1993,12,24,14,15))
        self.check_prevnext(event, datetime(1990,5,17,22,55), None, datetime(1993,12,24,14,15))
        self.check_prevnext(event, date(1993,1,1), None, datetime(1993,12,24,14,15))
        self.check_prevnext(event, date(1993,12,8), None, datetime(1993,12,24,14,15))
        self.check_prevnext(event, date(1993,12,24), None, datetime(1993,12,24,14,15))
        self.check_prevnext(event, datetime(1993,12,24,0,0), None, datetime(1993,12,24,14,15))
        self.check_prevnext(event, datetime(1993,12,24,0,0,1), None, datetime(1993,12,24,14,15))
        self.check_prevnext(event, datetime(1993,12,24,14,15), None, datetime(1993,12,24,14,15))
        self.check_prevnext(event, datetime(1993,12,24,14,15,1), datetime(1993,12,24,14,15), datetime(1994,12,24,14,15))
        self.check_prevnext(event, date(1993,12,25), datetime(1993,12,24,14,15), datetime(1994,12,24,14,15))
        self.check_prevnext(event, date(1994,1,1), datetime(1993,12,24,14,15), datetime(1994,12,24,14,15))
        self.check_prevnext(event, date(1994,10,23), datetime(1993,12,24,14,15), datetime(1994,12,24,14,15))
        self.check_prevnext(event, date(1994,12,24), datetime(1993,12,24,14,15), datetime(1994,12,24,14,15))
        self.check_prevnext(event, datetime(1994,12,24,0,0), datetime(1993,12,24,14,15), datetime(1994,12,24,14,15))
        self.check_prevnext(event, datetime(1994,12,24,14,15), datetime(1993,12,24,14,15), datetime(1994,12,24,14,15))
        self.check_prevnext(event, datetime(1994,12,24,14,15,1), datetime(1994,12,24,14,15), datetime(1995,12,24,14,15))
        self.check_prevnext(event, date(1994,12,25), datetime(1994,12,24,14,15), datetime(1995,12,24,14,15))
        self.check_prevnext(event, date(2510,1,1), datetime(2509,12,24,14,15), datetime(2510,12,24,14,15))
        self.check_prevnext(event, date(2510,12,24), datetime(2509,12,24,14,15), datetime(2510,12,24,14,15))
        self.check_prevnext(event, datetime(2510,12,24,0,0), datetime(2509,12,24,14,15), datetime(2510,12,24,14,15))
        self.check_prevnext(event, datetime(2510,12,24,14,15), datetime(2509,12,24,14,15), datetime(2510,12,24,14,15))
        self.check_prevnext(event, datetime(2510,12,24,14,15,1), datetime(2510,12,24,14,15), datetime(2511,12,24,14,15))
        self.check_prevnext(event, date(2510,12,25), datetime(2510,12,24,14,15), datetime(2511,12,24,14,15))


    #@unittest.skip
    def test_03_yearly_interval(self) -> None:
        # Create yearly event with interval>1
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2001,7,28),
            rrule = {'FREQ':['YEARLY'], 'INTERVAL':[3]})

        self.check_prevnext(event, date(1700,1,1), None, date(2001,7,28))
        self.check_prevnext(event, date(2001,1,1), None, date(2001,7,28))
        self.check_prevnext(event, date(2001,7,28), None, date(2001,7,28))
        self.check_prevnext(event, datetime(2001,7,28,0,0), None, date(2001,7,28))
        self.check_prevnext(event, datetime(2001,7,28,0,1), date(2001,7,28), date(2004,7,28))
        self.check_prevnext(event, date(2001,7,29), date(2001,7,28), date(2004,7,28))
        self.check_prevnext(event, date(2002,7,28), date(2001,7,28), date(2004,7,28))
        self.check_prevnext(event, date(2004,1,1), date(2001,7,28), date(2004,7,28))
        self.check_prevnext(event, date(2004,7,28), date(2001,7,28), date(2004,7,28))
        self.check_prevnext(event, datetime(2004,7,28,0,0), date(2001,7,28), date(2004,7,28))
        self.check_prevnext(event, datetime(2004,7,28,0,1), date(2004,7,28), date(2007,7,28))
        self.check_prevnext(event, date(2004,7,29), date(2004,7,28), date(2007,7,28))
        self.check_prevnext(event, date(2004,1,1), date(2001,7,28), date(2004,7,28))
        self.check_prevnext(event, date(2004,7,28), date(2001,7,28), date(2004,7,28))
        self.check_prevnext(event, datetime(2004,7,28,0,0), date(2001,7,28), date(2004,7,28))
        self.check_prevnext(event, datetime(2004,7,28,0,1), date(2004,7,28), date(2007,7,28))
        self.check_prevnext(event, date(2004,7,29), date(2004,7,28), date(2007,7,28))
        self.check_prevnext(event, date(2166,1,1), date(2163,7,28), date(2166,7,28))
        self.check_prevnext(event, date(2166,7,28), date(2163,7,28), date(2166,7,28))
        self.check_prevnext(event, datetime(2166,7,28,0,0), date(2163,7,28), date(2166,7,28))
        self.check_prevnext(event, datetime(2166,7,28,0,1), date(2166,7,28), date(2169,7,28))
        self.check_prevnext(event, date(2166,7,29), date(2166,7,28), date(2169,7,28))


    #@unittest.skip
    def test_04_yearly_interval_leapday(self) -> None:
        # Create yearly repeating event (on leapday, interval 6)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1456,2,29),
            rrule = {'FREQ':['YEARLY'], 'INTERVAL':[6]})

        self.check_prevnext(event, date(1400,1,1), None, date(1456,2,29))
        self.check_prevnext(event, date(1456,2,29), None, date(1456,2,29))
        self.check_prevnext(event, date(1456,3,1), date(1456,2,29), date(1468,2,29))
        self.check_prevnext(event, date(1460,2,29), date(1456,2,29), date(1468,2,29))
        self.check_prevnext(event, date(1464,2,29), date(1456,2,29), date(1468,2,29))
        self.check_prevnext(event, date(1468,2,29), date(1456,2,29), date(1468,2,29))
        self.check_prevnext(event, date(1468,3,1), date(1468,2,29), date(1480,2,29))
        self.check_prevnext(event, date(1590,5,29), date(1588,2,29), date(1600,2,29)) # 1600 *is* leap year
        self.check_prevnext(event, date(1890,5,29), date(1888,2,29), date(1912,2,29)) # 1900 *not* leap year
        self.check_prevnext(event, date(2170,5,29), date(2164,2,29), date(2176,2,29))


    #@unittest.skip
    def test_05_yearly_count(self) -> None:
        # Create yearly repeating event with occurence count
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1981,11,16),
            rrule = {'FREQ':['YEARLY'], 'COUNT':[27]})

        self.check_prevnext(event, date(1800,10,14), None, date(1981,11,16))
        self.check_prevnext(event, datetime(1850,10,14,3,38), None, date(1981,11,16))
        self.check_prevnext(event, date(1981,1,1), None, date(1981,11,16))
        self.check_prevnext(event, datetime(1981,10,16,16,16), None, date(1981,11,16))
        self.check_prevnext(event, datetime(1981,11,15,23,59,59), None, date(1981,11,16))
        self.check_prevnext(event, date(1981,11,16), None, date(1981,11,16))
        self.check_prevnext(event, datetime(1981,11,16,0,0), None, date(1981,11,16))
        self.check_prevnext(event, datetime(1981,11,16,0,1), date(1981,11,16), date(1982,11,16))
        self.check_prevnext(event, date(1981,11,17), date(1981,11,16), date(1982,11,16))
        self.check_prevnext(event, datetime(1982,11,15,23,59,59), date(1981,11,16), date(1982,11,16))
        self.check_prevnext(event, date(1982,11,16), date(1981,11,16), date(1982,11,16))
        self.check_prevnext(event, datetime(1982,11,16,0,0), date(1981,11,16), date(1982,11,16))
        self.check_prevnext(event, datetime(1982,11,16,0,0,1), date(1982,11,16), date(1983,11,16))
        self.check_prevnext(event, date(1982,11,17), date(1982,11,16), date(1983,11,16))
        self.check_prevnext(event, datetime(2007,11,15,23,59,59), date(2006,11,16), date(2007,11,16))
        self.check_prevnext(event, date(2007,11,16), date(2006,11,16), date(2007,11,16))
        self.check_prevnext(event, datetime(2007,11,16,0,0), date(2006,11,16), date(2007,11,16))
        self.check_prevnext(event, datetime(2007,11,16,0,1), date(2007,11,16), None)
        self.check_prevnext(event, date(2007,11,17), date(2007,11,16), None)
        self.check_prevnext(event, datetime(2008,3,7,22,45), date(2007,11,16), None)
        self.check_prevnext(event, date(2008,11,16), date(2007,11,16), None)
        self.check_prevnext(event, date(2008,11,17), date(2007,11,16), None)
        self.check_prevnext(event, datetime(2040,5,5,7,32), date(2007,11,16), None)
        self.check_prevnext(event, date(2050,11,17), date(2007,11,16), None)


    #@unittest.skip
    def test_06_yearly_until(self) -> None:
        # Create yearly repeating event with repeat-until
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2022,7,20),
            rrule = {'FREQ':['YEARLY'], 'UNTIL':[date(2030,7,20)]})

        self.check_prevnext(event, date(1800,10,14), None, date(2022,7,20))
        self.check_prevnext(event, datetime(1850,10,14,3,38), None, date(2022,7,20))
        self.check_prevnext(event, date(2022,1,1), None, date(2022,7,20))
        self.check_prevnext(event, datetime(2022,5,16,16,16), None, date(2022,7,20))
        self.check_prevnext(event, datetime(2022,7,19,23,59,59), None, date(2022,7,20))
        self.check_prevnext(event, date(2022,7,20), None, date(2022,7,20))
        self.check_prevnext(event, datetime(2022,7,20,0,0), None, date(2022,7,20))
        self.check_prevnext(event, datetime(2022,7,20,0,1), date(2022,7,20), date(2023,7,20))
        self.check_prevnext(event, date(2022,7,21), date(2022,7,20), date(2023,7,20))
        self.check_prevnext(event, datetime(2023,7,19,23,59,59), date(2022,7,20), date(2023,7,20))
        self.check_prevnext(event, date(2023,7,20), date(2022,7,20), date(2023,7,20))
        self.check_prevnext(event, datetime(2023,7,20,0,0), date(2022,7,20), date(2023,7,20))
        self.check_prevnext(event, datetime(2023,7,20,0,0,1), date(2023,7,20), date(2024,7,20))
        self.check_prevnext(event, date(2023,7,21), date(2023,7,20), date(2024,7,20))
        self.check_prevnext(event, datetime(2030,7,19,23,59,59), date(2029,7,20), date(2030,7,20))
        self.check_prevnext(event, date(2030,7,20), date(2029,7,20), date(2030,7,20))
        self.check_prevnext(event, datetime(2030,7,20,0,0), date(2029,7,20), date(2030,7,20))
        self.check_prevnext(event, datetime(2030,7,20,0,1), date(2030,7,20), None)
        self.check_prevnext(event, date(2030,7,21), date(2030,7,20), None)
        self.check_prevnext(event, datetime(2031,3,7,22,45), date(2030,7,20), None)
        self.check_prevnext(event, date(2031,7,20), date(2030,7,20), None)
        self.check_prevnext(event, date(2031,7,21), date(2030,7,20), None)
        self.check_prevnext(event, datetime(2040,5,5,7,32), date(2030,7,20), None)
        self.check_prevnext(event, date(2050,7,21), date(2030,7,20), None)


    #@unittest.skip
    def test_07_yearly_timezone(self) -> None:
        # Create timed yearly repeating event with timezone
        tz_SAM = tz.gettz('Pacific/Samoa') # UTC-11
        self.assertTrue(tz_SAM) # check not None

        # Check to see if local timezone more west than event timezone,
        # and if so change local tz to something "neutral".
        if get_local_tz().utcoffset(datetime(2021,8,1,1))<=timedelta(hours=-10):
            set_local_tz(tz.gettz('Europe/London'))

        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1960,12,31,23,16,4,tzinfo=tz_SAM),
            rrule = {'FREQ':['YEARLY']})

        self.check_prevnext(event, date(1800,10,14), None, datetime(1960,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1960,12,1), None, datetime(1960,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1960,12,1), None, datetime(1960,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1961,1,1), None, datetime(1960,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1961,1,1), None, datetime(1960,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1960,12,31,23,16,4,tzinfo=tz_SAM), None, datetime(1960,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1960,12,31,23,16,5,tzinfo=tz_SAM), datetime(1960,12,31,23,16,4,tzinfo=tz_SAM), datetime(1961,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1961,1,2), datetime(1960,12,31,23,16,4,tzinfo=tz_SAM), datetime(1961,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1961,1,2), datetime(1960,12,31,23,16,4,tzinfo=tz_SAM), datetime(1961,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1962,1,1), datetime(1960,12,31,23,16,4,tzinfo=tz_SAM), datetime(1961,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1962,1,1), datetime(1960,12,31,23,16,4,tzinfo=tz_SAM), datetime(1961,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1961,12,31,23,16,4,tzinfo=tz_SAM), datetime(1960,12,31,23,16,4,tzinfo=tz_SAM), datetime(1961,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1961,12,31,23,16,5,tzinfo=tz_SAM), datetime(1961,12,31,23,16,4,tzinfo=tz_SAM), datetime(1962,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1962,1,2), datetime(1961,12,31,23,16,4,tzinfo=tz_SAM), datetime(1962,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1962,1,2), datetime(1961,12,31,23,16,4,tzinfo=tz_SAM), datetime(1962,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, date(2022,1,1), datetime(2020,12,31,23,16,4,tzinfo=tz_SAM), datetime(2021,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(2022,1,1), datetime(2020,12,31,23,16,4,tzinfo=tz_SAM), datetime(2021,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(2021,12,31,23,16,4,tzinfo=tz_SAM), datetime(2020,12,31,23,16,4,tzinfo=tz_SAM), datetime(2021,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(2021,12,31,23,16,5,tzinfo=tz_SAM), datetime(2021,12,31,23,16,4,tzinfo=tz_SAM), datetime(2022,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, date(2022,1,2), datetime(2021,12,31,23,16,4,tzinfo=tz_SAM), datetime(2022,12,31,23,16,4,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(2022,1,2), datetime(2021,12,31,23,16,4,tzinfo=tz_SAM), datetime(2022,12,31,23,16,4,tzinfo=tz_SAM))


    #@unittest.skip
    def test_08_yearly_timezone(self) -> None:
        # Create timed yearly repeating event with timezone, in summer
        tz_SAM = tz.gettz('Pacific/Samoa') # UTC-11
        self.assertTrue(tz_SAM) # check not None

        # Check to see if local timezone more west than event timezone,
        # and if so change local tz to something "neutral".
        if get_local_tz().utcoffset(datetime(2021,8,1,1))<=timedelta(hours=-10):
            set_local_tz(tz.gettz('Europe/London'))

        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1975,7,15,23,19,30,tzinfo=tz_SAM),
            rrule = {'FREQ':['YEARLY']})

        self.check_prevnext(event, date(1800,10,14), None, datetime(1975,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1975,1,1), None, datetime(1975,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1975,1,1), None, datetime(1975,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1975,7,15), None, datetime(1975,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1975,7,15), None, datetime(1975,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1975,7,16), None, datetime(1975,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1975,7,16), None, datetime(1975,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1975,7,15,23,19,30,tzinfo=tz_SAM), None, datetime(1975,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1975,7,15,23,19,31,tzinfo=tz_SAM), datetime(1975,7,15,23,19,30,tzinfo=tz_SAM), datetime(1976,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1975,7,17), datetime(1975,7,15,23,19,30,tzinfo=tz_SAM), datetime(1976,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1975,7,17), datetime(1975,7,15,23,19,30,tzinfo=tz_SAM), datetime(1976,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1976,7,15), datetime(1975,7,15,23,19,30,tzinfo=tz_SAM), datetime(1976,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1976,7,15), datetime(1975,7,15,23,19,30,tzinfo=tz_SAM), datetime(1976,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1976,7,16), datetime(1975,7,15,23,19,30,tzinfo=tz_SAM), datetime(1976,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1976,7,16), datetime(1975,7,15,23,19,30,tzinfo=tz_SAM), datetime(1976,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1976,7,15,23,19,30,tzinfo=tz_SAM), datetime(1975,7,15,23,19,30,tzinfo=tz_SAM), datetime(1976,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1976,7,15,23,19,31,tzinfo=tz_SAM), datetime(1976,7,15,23,19,30,tzinfo=tz_SAM), datetime(1977,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, date(1976,7,17), datetime(1976,7,15,23,19,30,tzinfo=tz_SAM), datetime(1977,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(1976,7,17), datetime(1976,7,15,23,19,30,tzinfo=tz_SAM), datetime(1977,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, date(2030,7,15), datetime(2029,7,15,23,19,30,tzinfo=tz_SAM), datetime(2030,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(2030,7,15), datetime(2029,7,15,23,19,30,tzinfo=tz_SAM), datetime(2030,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, date(2030,7,16), datetime(2029,7,15,23,19,30,tzinfo=tz_SAM), datetime(2030,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(2030,7,16), datetime(2029,7,15,23,19,30,tzinfo=tz_SAM), datetime(2030,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(2030,7,15,23,19,30,tzinfo=tz_SAM), datetime(2029,7,15,23,19,30,tzinfo=tz_SAM), datetime(2030,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(2030,7,15,23,19,31,tzinfo=tz_SAM), datetime(2030,7,15,23,19,30,tzinfo=tz_SAM), datetime(2031,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, date(2030,7,17), datetime(2030,7,15,23,19,30,tzinfo=tz_SAM), datetime(2031,7,15,23,19,30,tzinfo=tz_SAM))
        self.check_prevnext(event, datetime(2030,7,17), datetime(2030,7,15,23,19,30,tzinfo=tz_SAM), datetime(2031,7,15,23,19,30,tzinfo=tz_SAM))


    #@unittest.skip
    def test_09_yearly_thanksgiving(self) -> None:
        # Create yearly repeating event on weekday of month.
        # Thanksgiving (US) - 4th Thursday of November.
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1942,11,26),
            dt_end = date(1942,11,26), # all day event
            rrule = {'FREQ':['YEARLY'],'BYMONTH':['11'],'BYDAY':['4TH']})

        self.check_prevnext(event, datetime(1900,3,17), None, date(1942,11,26))
        self.check_prevnext_transition(event, date(1942,11,26), None, date(1943,11,25))
        self.check_prevnext(event, datetime(1942,11,27), date(1942,11,26), date(1943,11,25))
        self.check_prevnext(event, datetime(1943,11,1,13,56), date(1942,11,26), date(1943,11,25))
        self.check_prevnext(event, date(1943,11,5), date(1942,11,26), date(1943,11,25))
        self.check_prevnext_transition(event, date(1943,11,25), date(1942,11,26), date(1944,11,23))
        self.check_prevnext(event, date(1944,12,21), date(1944,11,23), date(1945,11,22))
        self.check_prevnext(event, date(1945,12,1), date(1945,11,22), date(1946,11,28))
        self.check_prevnext(event, date(2000,5,3), date(1999,11,25), date(2000,11,23))
        self.check_prevnext(event, datetime(2030,7,31,23,59), date(2029,11,22), date(2030,11,28))


    #@unittest.skip
    def test_10_yearly_invalid_day(self) -> None:
        # Create yearly repeating event with a bad BYDAY argument
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2023,4,25),
            rrule = {'FREQ':['YEARLY'],'BYMONTH':['4'],'BYDAY':['4TH','4QX']})

        # Test in period raises ValueError
        self.assertRaises(ValueError, previous_next_occurrence, event, date(2023,1,1))


    #@unittest.skip
    def test_11_yearly_bydayinmonth_timed(self) -> None:
        # Create yearly repeating event on weekday-of-month with time.
        # Also throw in an exdate.
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2002,4,1,14,31),
            rrule = {'FREQ':['YEARLY'],'BYMONTH':['4'],'BYDAY':['1MO']},
            exdates = {datetime(2029,4,2,14,31)})

        self.check_prevnext(event, date(2000,4,23), None, datetime(2002,4,1,14,31))
        self.check_prevnext_transition(event, datetime(2002,4,1,14,31), None, datetime(2003,4,7,14,31))
        self.check_prevnext(event, date(2003,4,1), datetime(2002,4,1,14,31), datetime(2003,4,7,14,31))
        self.check_prevnext_transition(event, datetime(2003,4,7,14,31), datetime(2002,4,1,14,31), datetime(2004,4,5,14,31))
        self.check_prevnext(event, date(2004,4,1), datetime(2003,4,7,14,31), datetime(2004,4,5,14,31))
        self.check_prevnext_transition(event, datetime(2004,4,5,14,31), datetime(2003,4,7,14,31), datetime(2005,4,4,14,31))

        # Around the exdate:
        self.check_prevnext(event, date(2028,4,1), datetime(2027,4,5,14,31), datetime(2028,4,3,14,31))
        self.check_prevnext_transition(event, datetime(2028,4,3,14,31), datetime(2027,4,5,14,31), datetime(2030,4,1,14,31))
        self.check_prevnext(event, date(2029,4,1), datetime(2028,4,3,14,31), datetime(2030,4,1,14,31))
        self.check_prevnext_transition(event, datetime(2029,4,2,14,31), datetime(2028,4,3,14,31), datetime(2030,4,1,14,31), isOcc=False)
        self.check_prevnext_transition(event, datetime(2030,4,1,14,31), datetime(2028,4,3,14,31), datetime(2031,4,7,14,31))
        self.check_prevnext(event, date(2031,4,1), datetime(2030,4,1,14,31), datetime(2031,4,7,14,31))
        self.check_prevnext_transition(event, datetime(2031,4,7,14,31), datetime(2030,4,1,14,31), datetime(2032,4,5,14,31))


    #@unittest.skip
    def test_12_yearly_bydayinmonth_twice(self) -> None:
        # Create yearly repeating event on two months
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2013,2,12),
            rrule = {'FREQ':['YEARLY'],'BYMONTH':['2','6'],'BYDAY':['2TU']})

        self.check_prevnext(event, date(2000,4,23), None, date(2013,2,12))
        self.check_prevnext_transition(event, date(2013,2,12), None, date(2013,6,11))
        self.check_prevnext_transition(event, date(2013,6,11), date(2013,2,12), date(2014,2,11))
        self.check_prevnext_transition(event, date(2014,2,11), date(2013,6,11), date(2014,6,10))
        self.check_prevnext_transition(event, date(2014,6,10), date(2014,2,11), date(2015,2,10))
        self.check_prevnext_transition(event, date(2060,2,10), date(2059,6,10), date(2060,6,8))
        self.check_prevnext_transition(event, date(2060,6,8), date(2060,2,10), date(2061,2,8))


    #@unittest.skip
    def test_13_monthly_basic(self) -> None:
        # Create simple monthly repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1999,4,20),
            rrule = {'FREQ':['MONTHLY']})

        self.check_prevnext(event, date(1998,6,23), None, date(1999,4,20))
        self.check_prevnext(event, date(1999,1,1), None, date(1999,4,20))
        self.check_prevnext_transition(event, date(1999,4,20), None, date(1999,5,20))
        self.check_prevnext_transition(event, date(1999,5,20), date(1999,4,20), date(1999,6,20))
        self.check_prevnext_transition(event, date(1999,6,20), date(1999,5,20), date(1999,7,20))
        self.check_prevnext_transition(event, date(1999,7,20), date(1999,6,20), date(1999,8,20))
        self.check_prevnext_transition(event, date(1999,12,20), date(1999,11,20), date(2000,1,20))
        self.check_prevnext_transition(event, date(2000,1,20), date(1999,12,20), date(2000,2,20))
        self.check_prevnext_transition(event, date(2000,2,20), date(2000,1,20), date(2000,3,20))
        self.check_prevnext_transition(event, date(2000,4,20), date(2000,3,20), date(2000,5,20))
        self.check_prevnext_transition(event, date(2049,12,20), date(2049,11,20), date(2050,1,20))
        self.check_prevnext_transition(event, date(2050,1,20), date(2049,12,20), date(2050,2,20))
        self.check_prevnext_transition(event, date(2050,2,20), date(2050,1,20), date(2050,3,20))
        self.check_prevnext_transition(event, date(2050,3,20), date(2050,2,20), date(2050,4,20))
        self.check_prevnext_transition(event, date(2050,4,20), date(2050,3,20), date(2050,5,20))


    #@unittest.skip
    def test_14_monthly_timed_interval(self) -> None:
        # Create monthly timed repeating event, interval 2
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1965,9,16,22,18),
            rrule = {'FREQ':['MONTHLY'], 'INTERVAL':[2]})

        self.check_prevnext(event, date(1960,1,1), None, datetime(1965,9,16,22,18))
        self.check_prevnext_transition(event, datetime(1965,9,16,22,18), None, datetime(1965,11,16,22,18))
        self.check_prevnext_transition(event, datetime(1965,10,16,22,18), datetime(1965,9,16,22,18), datetime(1965,11,16,22,18), isOcc=False)
        self.check_prevnext_transition(event, datetime(1965,11,16,22,18), datetime(1965,9,16,22,18), datetime(1966,1,16,22,18))
        self.check_prevnext_transition(event, datetime(1965,12,16,22,18), datetime(1965,11,16,22,18), datetime(1966,1,16,22,18), isOcc=False)
        self.check_prevnext_transition(event, datetime(1966,1,16,22,18), datetime(1965,11,16,22,18), datetime(1966,3,16,22,18))
        self.check_prevnext_transition(event, datetime(1966,2,16,22,18), datetime(1966,1,16,22,18), datetime(1966,3,16,22,18), isOcc=False)
        self.check_prevnext_transition(event, datetime(1966,3,16,22,18), datetime(1966,1,16,22,18), datetime(1966,5,16,22,18))
        self.check_prevnext_transition(event, datetime(2041,7,16,22,18), datetime(2041,5,16,22,18), datetime(2041,9,16,22,18))
        self.check_prevnext_transition(event, datetime(2041,8,16,22,18), datetime(2041,7,16,22,18), datetime(2041,9,16,22,18), isOcc=False)
        self.check_prevnext_transition(event, datetime(2041,9,16,22,18), datetime(2041,7,16,22,18), datetime(2041,11,16,22,18))
        self.check_prevnext_transition(event, datetime(2041,10,16,22,18), datetime(2041,9,16,22,18), datetime(2041,11,16,22,18), isOcc=False)
        self.check_prevnext_transition(event, datetime(2041,11,16,22,18), datetime(2041,9,16,22,18), datetime(2042,1,16,22,18))
        self.check_prevnext_transition(event, datetime(2041,12,16,22,18), datetime(2041,11,16,22,18), datetime(2042,1,16,22,18), isOcc=False)
        self.check_prevnext_transition(event, datetime(2042,1,16,22,18), datetime(2041,11,16,22,18), datetime(2042,3,16,22,18))
        self.check_prevnext_transition(event, datetime(2042,2,16,22,18), datetime(2042,1,16,22,18), datetime(2042,3,16,22,18), isOcc=False)
        self.check_prevnext_transition(event, datetime(2042,3,16,22,18), datetime(2042,1,16,22,18), datetime(2042,5,16,22,18))


    #@unittest.skip
    def test_15_monthly_timed_exdate(self) -> None:
        # Create timed monthly repeating event, with exception
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1998,3,28,12,3), # time 12:03
            rrule = {'FREQ':['MONTHLY']},
            exdates = {datetime(2063,7,28,12,3)})

        self.check_prevnext(event, date(1995,12,12), None, datetime(1998,3,28,12,3))
        self.check_prevnext_transition(event, datetime(1998,3,28,12,3), None, datetime(1998,4,28,12,3))
        self.check_prevnext_transition(event, datetime(1998,4,28,12,3), datetime(1998,3,28,12,3), datetime(1998,5,28,12,3))
        self.check_prevnext_transition(event, datetime(1998,5,28,12,3), datetime(1998,4,28,12,3), datetime(1998,6,28,12,3))
        self.check_prevnext_transition(event, datetime(1998,6,28,12,3), datetime(1998,5,28,12,3), datetime(1998,7,28,12,3))
        self.check_prevnext_transition(event, datetime(1999,1,28,12,3), datetime(1998,12,28,12,3), datetime(1999,2,28,12,3))
        self.check_prevnext_transition(event, datetime(1999,2,28,12,3), datetime(1999,1,28,12,3), datetime(1999,3,28,12,3))
        self.check_prevnext_transition(event, datetime(1999,3,28,12,3), datetime(1999,2,28,12,3), datetime(1999,4,28,12,3))
        self.check_prevnext_transition(event, datetime(1999,12,28,12,3), datetime(1999,11,28,12,3), datetime(2000,1,28,12,3))
        self.check_prevnext_transition(event, datetime(2000,1,28,12,3), datetime(1999,12,28,12,3), datetime(2000,2,28,12,3))
        self.check_prevnext_transition(event, datetime(2000,2,28,12,3), datetime(2000,1,28,12,3), datetime(2000,3,28,12,3))
        self.check_prevnext_transition(event, datetime(2000,3,28,12,3), datetime(2000,2,28,12,3), datetime(2000,4,28,12,3))
        self.check_prevnext_transition(event, datetime(2051,12,28,12,3), datetime(2051,11,28,12,3), datetime(2052,1,28,12,3))
        self.check_prevnext_transition(event, datetime(2052,1,28,12,3), datetime(2051,12,28,12,3), datetime(2052,2,28,12,3))
        self.check_prevnext_transition(event, datetime(2052,2,28,12,3), datetime(2052,1,28,12,3), datetime(2052,3,28,12,3))
        self.check_prevnext_transition(event, datetime(2052,3,28,12,3), datetime(2052,2,28,12,3), datetime(2052,4,28,12,3))
        self.check_prevnext_transition(event, datetime(2063,5,28,12,3), datetime(2063,4,28,12,3), datetime(2063,6,28,12,3))
        self.check_prevnext_transition(event, datetime(2063,6,28,12,3), datetime(2063,5,28,12,3), datetime(2063,8,28,12,3))
        self.check_prevnext_transition(event, datetime(2063,7,28,12,3), datetime(2063,6,28,12,3), datetime(2063,8,28,12,3), False)
        self.check_prevnext_transition(event, datetime(2063,8,28,12,3), datetime(2063,6,28,12,3), datetime(2063,9,28,12,3))
        self.check_prevnext_transition(event, datetime(2063,9,28,12,3), datetime(2063,8,28,12,3), datetime(2063,10,28,12,3))
        self.check_prevnext_transition(event, datetime(2064,5,28,12,3), datetime(2064,4,28,12,3), datetime(2064,6,28,12,3))
        self.check_prevnext_transition(event, datetime(2064,6,28,12,3), datetime(2064,5,28,12,3), datetime(2064,7,28,12,3))
        self.check_prevnext_transition(event, datetime(2064,7,28,12,3), datetime(2064,6,28,12,3), datetime(2064,8,28,12,3))
        self.check_prevnext_transition(event, datetime(2064,8,28,12,3), datetime(2064,7,28,12,3), datetime(2064,9,28,12,3))
        self.check_prevnext_transition(event, datetime(2064,9,28,12,3), datetime(2064,8,28,12,3), datetime(2064,10,28,12,3))


    #@unittest.skip
    def test_16_monthly_timed_29th_exdate(self) -> None:
        # Create timed monthly repeating event
        # (with the potential to fall on a leap-day)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1998,3,29,12,3), # time 12:03
            rrule = {'FREQ':['MONTHLY']},
            exdates = {datetime(2063,7,29,12,3), datetime(2065,7,29,12,3)})

        self.check_prevnext(event, date(1997,4,12), None, datetime(1998,3,29,12,3))
        self.check_prevnext_transition(event, datetime(1998,3,29,12,3), None, datetime(1998,4,29,12,3))
        self.check_prevnext_transition(event, datetime(1998,4,29,12,3), datetime(1998,3,29,12,3), datetime(1998,5,29,12,3))
        self.check_prevnext_transition(event, datetime(1998,5,29,12,3), datetime(1998,4,29,12,3), datetime(1998,6,29,12,3))
        self.check_prevnext_transition(event, datetime(1999,1,29,12,3), datetime(1998,12,29,12,3), datetime(1999,3,29,12,3))
        self.check_prevnext_transition(event, datetime(1999,2,28,12,3), datetime(1999,1,29,12,3), datetime(1999,3,29,12,3), False)
        self.check_prevnext_transition(event, datetime(1999,3,29,12,3), datetime(1999,1,29,12,3), datetime(1999,4,29,12,3))
        self.check_prevnext_transition(event, datetime(2000,1,29,12,3), datetime(1999,12,29,12,3), datetime(2000,2,29,12,3))
        self.check_prevnext_transition(event, datetime(2000,2,29,12,3), datetime(2000,1,29,12,3), datetime(2000,3,29,12,3))
        self.check_prevnext_transition(event, datetime(2000,3,29,12,3), datetime(2000,2,29,12,3), datetime(2000,4,29,12,3))
        self.check_prevnext_transition(event, datetime(2001,1,29,12,3), datetime(2000,12,29,12,3), datetime(2001,3,29,12,3))
        self.check_prevnext_transition(event, datetime(2001,3,1,12,3), datetime(2001,1,29,12,3), datetime(2001,3,29,12,3), False)
        self.check_prevnext_transition(event, datetime(2001,3,29,12,3), datetime(2001,1,29,12,3), datetime(2001,4,29,12,3))
        self.check_prevnext_transition(event, datetime(2004,1,29,12,3), datetime(2003,12,29,12,3), datetime(2004,2,29,12,3))
        self.check_prevnext_transition(event, datetime(2004,2,29,12,3), datetime(2004,1,29,12,3), datetime(2004,3,29,12,3))
        self.check_prevnext_transition(event, datetime(2004,3,29,12,3), datetime(2004,2,29,12,3), datetime(2004,4,29,12,3))
        self.check_prevnext_transition(event, datetime(2062,6,29,12,3), datetime(2062,5,29,12,3), datetime(2062,7,29,12,3))
        self.check_prevnext_transition(event, datetime(2062,7,29,12,3), datetime(2062,6,29,12,3), datetime(2062,8,29,12,3))
        self.check_prevnext_transition(event, datetime(2062,8,29,12,3), datetime(2062,7,29,12,3), datetime(2062,9,29,12,3))
        self.check_prevnext_transition(event, datetime(2063,6,29,12,3), datetime(2063,5,29,12,3), datetime(2063,8,29,12,3))
        self.check_prevnext_transition(event, datetime(2063,7,29,12,3), datetime(2063,6,29,12,3), datetime(2063,8,29,12,3), False)
        self.check_prevnext_transition(event, datetime(2063,8,29,12,3), datetime(2063,6,29,12,3), datetime(2063,9,29,12,3))
        self.check_prevnext_transition(event, datetime(2064,6,29,12,3), datetime(2064,5,29,12,3), datetime(2064,7,29,12,3))
        self.check_prevnext_transition(event, datetime(2064,7,29,12,3), datetime(2064,6,29,12,3), datetime(2064,8,29,12,3))
        self.check_prevnext_transition(event, datetime(2064,8,29,12,3), datetime(2064,7,29,12,3), datetime(2064,9,29,12,3))
        self.check_prevnext_transition(event, datetime(2065,6,29,12,3), datetime(2065,5,29,12,3), datetime(2065,8,29,12,3))
        self.check_prevnext_transition(event, datetime(2065,7,29,12,3), datetime(2065,6,29,12,3), datetime(2065,8,29,12,3), False)
        self.check_prevnext_transition(event, datetime(2065,8,29,12,3), datetime(2065,6,29,12,3), datetime(2065,9,29,12,3))
        self.check_prevnext_transition(event, datetime(2066,6,29,12,3), datetime(2066,5,29,12,3), datetime(2066,7,29,12,3))
        self.check_prevnext_transition(event, datetime(2066,7,29,12,3), datetime(2066,6,29,12,3), datetime(2066,8,29,12,3))
        self.check_prevnext_transition(event, datetime(2066,8,29,12,3), datetime(2066,7,29,12,3), datetime(2066,9,29,12,3))
        self.check_prevnext_transition(event, datetime(2100,1,29,12,3), datetime(2099,12,29,12,3), datetime(2100,3,29,12,3))
        self.check_prevnext_transition(event, datetime(2100,3,1,12,3), datetime(2100,1,29,12,3), datetime(2100,3,29,12,3), False)
        self.check_prevnext_transition(event, datetime(2100,3,29,12,3), datetime(2100,1,29,12,3), datetime(2100,4,29,12,3))


    #@unittest.skip
    def test_17_monthly_count(self) -> None:
        # Create monthly repeating event with occurence count
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2018,9,8),
            rrule = {'FREQ':['MONTHLY'], 'COUNT':[7]})

        self.check_prevnext(event, date(1953,6,21), None, date(2018,9,8))
        self.check_prevnext(event, date(2017,2,28), None, date(2018,9,8))
        self.check_prevnext_transition(event, date(2018,9,8), None, date(2018,10,8))
        self.check_prevnext_transition(event, date(2018,10,8), date(2018,9,8), date(2018,11,8))
        self.check_prevnext_transition(event, date(2018,11,8), date(2018,10,8), date(2018,12,8))
        self.check_prevnext_transition(event, date(2018,12,8), date(2018,11,8), date(2019,1,8))
        self.check_prevnext_transition(event, date(2019,1,8), date(2018,12,8), date(2019,2,8))
        self.check_prevnext_transition(event, date(2019,2,8), date(2019,1,8), date(2019,3,8))
        self.check_prevnext_transition(event, date(2019,3,8), date(2019,2,8), None)
        self.check_prevnext(event, date(2032,3,25), date(2019,3,8), None)


    #@unittest.skip
    def test_18_monthly_interval_until(self) -> None:
        # Create bi-monthly repeating event with repeat-until
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1979,4,27),
            rrule = {'FREQ':['MONTHLY'], 'INTERVAL':[2], 'UNTIL':[date(2014,2,27)]})

        self.check_prevnext(event, date(1968,6,21), None, date(1979,4,27))
        self.check_prevnext(event, date(1979,1,2), None, date(1979,4,27))
        self.check_prevnext_transition(event, date(1979,4,27), None, date(1979,6,27))
        self.check_prevnext_transition(event, date(1979,6,27), date(1979,4,27), date(1979,8,27))
        self.check_prevnext_transition(event, date(1979,8,27), date(1979,6,27), date(1979,10,27))
        self.check_prevnext_transition(event, date(1979,10,27), date(1979,8,27), date(1979,12,27))
        self.check_prevnext_transition(event, date(1979,12,27), date(1979,10,27), date(1980,2,27))
        self.check_prevnext_transition(event, date(1980,2,27), date(1979,12,27), date(1980,4,27))
        self.check_prevnext_transition(event, date(2013,10,27), date(2013,8,27), date(2013,12,27))
        self.check_prevnext_transition(event, date(2013,12,27), date(2013,10,27), date(2014,2,27))
        self.check_prevnext_transition(event, date(2014,2,27), date(2013,12,27), None)
        self.check_prevnext(event, date(2023,6,6), date(2014,2,27), None)


    #@unittest.skip
    def test_19_monthly_timezone_until_movesday(self) -> None:
        # Create timed monthly repeating event with timezone.
        # Set timezone far west & late in day, so for most local
        # timezones it is shifted into the next day.
        tz_AN = tz.gettz('America/Anchorage')
        self.assertTrue(tz_AN) # check not None
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2023,1,30,23,18,tzinfo=tz_AN),
            rrule = {'FREQ':['MONTHLY'],'UNTIL':[datetime(2030,7,30,23,18,tzinfo=tz_AN)]})

        # Check to see if local time more west than event zone,
        # and if so change local tz to something "neutral".
        if get_local_tz().utcoffset(datetime(2021,8,1,1))<=timedelta(hours=-8):
            set_local_tz(tz.gettz('Europe/London'))

        self.check_prevnext(event, date(1999,7,12), None, datetime(2023,1,30,23,18,tzinfo=tz_AN))
        self.check_prevnext(event, date(2021,1,1), None, datetime(2023,1,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2023,1,30,23,18,tzinfo=tz_AN), None, datetime(2023,3,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2023,2,28,23,18,tzinfo=tz_AN), datetime(2023,1,30,23,18,tzinfo=tz_AN), datetime(2023,3,30,23,18,tzinfo=tz_AN), False)
        self.check_prevnext_transition(event, datetime(2023,3,30,23,18,tzinfo=tz_AN), datetime(2023,1,30,23,18,tzinfo=tz_AN), datetime(2023,4,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2023,4,30,23,18,tzinfo=tz_AN), datetime(2023,3,30,23,18,tzinfo=tz_AN), datetime(2023,5,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2023,5,30,23,18,tzinfo=tz_AN), datetime(2023,4,30,23,18,tzinfo=tz_AN), datetime(2023,6,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2023,6,30,23,18,tzinfo=tz_AN), datetime(2023,5,30,23,18,tzinfo=tz_AN), datetime(2023,7,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2023,7,30,23,18,tzinfo=tz_AN), datetime(2023,6,30,23,18,tzinfo=tz_AN), datetime(2023,8,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2023,8,30,23,18,tzinfo=tz_AN), datetime(2023,7,30,23,18,tzinfo=tz_AN), datetime(2023,9,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2023,9,30,23,18,tzinfo=tz_AN), datetime(2023,8,30,23,18,tzinfo=tz_AN), datetime(2023,10,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2023,10,30,23,18,tzinfo=tz_AN), datetime(2023,9,30,23,18,tzinfo=tz_AN), datetime(2023,11,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2023,11,30,23,18,tzinfo=tz_AN), datetime(2023,10,30,23,18,tzinfo=tz_AN), datetime(2023,12,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2023,12,30,23,18,tzinfo=tz_AN), datetime(2023,11,30,23,18,tzinfo=tz_AN), datetime(2024,1,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2024,1,30,23,18,tzinfo=tz_AN), datetime(2023,12,30,23,18,tzinfo=tz_AN), datetime(2024,3,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2024,2,29,23,18,tzinfo=tz_AN), datetime(2024,1,30,23,18,tzinfo=tz_AN), datetime(2024,3,30,23,18,tzinfo=tz_AN), False)
        self.check_prevnext_transition(event, datetime(2024,3,30,23,18,tzinfo=tz_AN), datetime(2024,1,30,23,18,tzinfo=tz_AN), datetime(2024,4,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2030,1,30,23,18,tzinfo=tz_AN), datetime(2029,12,30,23,18,tzinfo=tz_AN), datetime(2030,3,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2030,2,28,23,18,tzinfo=tz_AN), datetime(2030,1,30,23,18,tzinfo=tz_AN), datetime(2030,3,30,23,18,tzinfo=tz_AN), False)
        self.check_prevnext_transition(event, datetime(2030,3,30,23,18,tzinfo=tz_AN), datetime(2030,1,30,23,18,tzinfo=tz_AN), datetime(2030,4,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2030,4,30,23,18,tzinfo=tz_AN), datetime(2030,3,30,23,18,tzinfo=tz_AN), datetime(2030,5,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2030,5,30,23,18,tzinfo=tz_AN), datetime(2030,4,30,23,18,tzinfo=tz_AN), datetime(2030,6,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2030,6,30,23,18,tzinfo=tz_AN), datetime(2030,5,30,23,18,tzinfo=tz_AN), datetime(2030,7,30,23,18,tzinfo=tz_AN))
        self.check_prevnext_transition(event, datetime(2030,7,30,23,18,tzinfo=tz_AN), datetime(2030,6,30,23,18,tzinfo=tz_AN), None)
        self.check_prevnext(event, date(2030,8,2), datetime(2030,7,30,23,18,tzinfo=tz_AN), None)
        self.check_prevnext(event, date(2030,10,5), datetime(2030,7,30,23,18,tzinfo=tz_AN), None)


    #@unittest.skip
    def test_20_monthly_byday(self) -> None:
        # Create monthly repeating event "by 2nd to last Friday"
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1959,2,20),
            rrule = {'FREQ':['MONTHLY'],'BYDAY':['-2FR']})

        self.check_prevnext(event, date(1900,5, 12), None, date(1959,2,20))
        self.check_prevnext_transition(event, date(1959,2,20), None, date(1959,3,20))
        self.check_prevnext_transition(event, date(1959,3,20), date(1959,2,20), date(1959,4,17))
        self.check_prevnext_transition(event, date(1959,4,17), date(1959,3,20), date(1959,5,22))
        self.check_prevnext_transition(event, date(1959,5,22), date(1959,4,17), date(1959,6,19))
        self.check_prevnext_transition(event, date(1959,6,19), date(1959,5,22), date(1959,7,24))
        self.check_prevnext_transition(event, date(1998,7,24), date(1998,6,19), date(1998,8,21))
        self.check_prevnext_transition(event, date(1998,8,21), date(1998,7,24), date(1998,9,18))
        self.check_prevnext_transition(event, date(1998,9,18), date(1998,8,21), date(1998,10,23))
        self.check_prevnext_transition(event, date(1998,10,23), date(1998,9,18), date(1998,11,20))
        self.check_prevnext_transition(event, date(1999,12,24), date(1999,11,19), date(2000,1,21))
        self.check_prevnext_transition(event, date(2000,1,21), date(1999,12,24), date(2000,2,18))
        self.check_prevnext_transition(event, date(2000,2,18), date(2000,1,21), date(2000,3,24))
        self.check_prevnext_transition(event, date(2030,3,22), date(2030,2,15), date(2030,4,19))


    #@unittest.skip
    def test_21_monthly_byday_timed_duration(self) -> None:
        # Create monthly repeating event "byday" with time + duration
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2010,6,17,23,30),
            dt_end = datetime(2010,6,18,1,30),
            rrule = {'FREQ':['MONTHLY'],'BYDAY':['3TH']})

        self.check_prevnext(event, date(1948, 2, 29), None, datetime(2010,6,17,23,30))
        self.check_prevnext_transition(event, datetime(2010,6,17,23,30), None, datetime(2010,7,15,23,30))
        self.check_prevnext_transition(event, datetime(2010,7,15,23,30), datetime(2010,6,17,23,30), datetime(2010,8,19,23,30))
        self.check_prevnext_transition(event, datetime(2010,8,19,23,30), datetime(2010,7,15,23,30), datetime(2010,9,16,23,30))
        self.check_prevnext_transition(event, datetime(2010,9,16,23,30), datetime(2010,8,19,23,30), datetime(2010,10,21,23,30))
        self.check_prevnext_transition(event, datetime(2010,12,16,23,30), datetime(2010,11,18,23,30), datetime(2011,1,20,23,30))
        self.check_prevnext_transition(event, datetime(2011,1,20,23,30), datetime(2010,12,16,23,30), datetime(2011,2,17,23,30))
        self.check_prevnext_transition(event, datetime(2029,12,20,23,30), datetime(2029,11,15,23,30), datetime(2030,1,17,23,30))
        self.check_prevnext_transition(event, datetime(2030,1,17,23,30), datetime(2029,12,20,23,30), datetime(2030,2,21,23,30))
        self.check_prevnext_transition(event, datetime(2030,2,21,23,30), datetime(2030,1,17,23,30), datetime(2030,3,21,23,30))
        self.check_prevnext_transition(event, datetime(2030,3,21,23,30), datetime(2030,2,21,23,30), datetime(2030,4,18,23,30))


    #@unittest.skip
    def test_22_monthly_tuesdaysinmonth(self) -> None:
        # Use monthly/byday to repeat on all Tuesdays every other month
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1996,11,5),
            rrule = {'FREQ':['MONTHLY'], 'INTERVAL':[2], 'BYDAY':['TU']})

        self.check_prevnext(event, date(1812,2,29), None, date(1996,11,5))
        self.check_prevnext_transition(event, date(1996,11,5), None, date(1996,11,12))
        self.check_prevnext_transition(event, date(1996,11,12), date(1996,11,5), date(1996,11,19))
        self.check_prevnext_transition(event, date(1996,11,19), date(1996,11,12), date(1996,11,26))
        self.check_prevnext_transition(event, date(1996,11,26), date(1996,11,19), date(1997,1,7))
        self.check_prevnext_transition(event, date(1997,1,7), date(1996,11,26), date(1997,1,14))
        self.check_prevnext_transition(event, date(1997,1,14), date(1997,1,7), date(1997,1,21))
        self.check_prevnext_transition(event, date(1997,1,21), date(1997,1,14), date(1997,1,28))
        self.check_prevnext_transition(event, date(1997,1,28), date(1997,1,21), date(1997,3,4))
        self.check_prevnext_transition(event, date(1997,3,4), date(1997,1,28), date(1997,3,11))
        self.check_prevnext_transition(event, date(2034,5,30), date(2034,5,23), date(2034,7,4))
        self.check_prevnext_transition(event, date(2034,7,4), date(2034,5,30), date(2034,7,11))
        self.check_prevnext_transition(event, date(2034,7,11), date(2034,7,4), date(2034,7,18))
        self.check_prevnext_transition(event, date(2034,7,18), date(2034,7,11), date(2034,7,25))
        self.check_prevnext_transition(event, date(2034,7,25), date(2034,7,18), date(2034,9,5))
        self.check_prevnext_transition(event, date(2034,9,5), date(2034,7,25), date(2034,9,12))


    #@unittest.skip
    def test_23_monthly_friday13th(self) -> None:
        # Create monthly/byday to repeat every Friday 13th
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2000,10,13),
            rrule = {'FREQ':['MONTHLY'], 'BYMONTHDAY':['13'], 'BYDAY':['FR']})

        self.check_prevnext(event, date(1973,7,7), None, date(2000,10,13))
        self.check_prevnext_transition(event, date(2000,10,13), None, date(2001,4,13))
        self.check_prevnext_transition(event, date(2001,4,13), date(2000,10,13), date(2001,7,13))
        self.check_prevnext_transition(event, date(2001,7,13), date(2001,4,13), date(2002,9,13))
        self.check_prevnext_transition(event, date(2002,9,13), date(2001,7,13), date(2002,12,13))
        self.check_prevnext_transition(event, date(2002,12,13), date(2002,9,13), date(2003,6,13))
        self.check_prevnext_transition(event, date(2031,6,13), date(2030,12,13), date(2032,2,13))


    #@unittest.skip
    def test_24_weekly_basic(self) -> None:
        # Create simple weekly repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2050,4,11), # Monday
            rrule = {'FREQ':['WEEKLY']})

        self.check_prevnext(event, date(1940,4,11), None, date(2050,4,11))
        self.check_prevnext_transition(event, date(2050,4,11), None, date(2050,4,18))
        self.check_prevnext_transition(event, date(2050,4,18), date(2050,4,11), date(2050,4,25))
        self.check_prevnext_transition(event, date(2050,4,25), date(2050,4,18), date(2050,5,2))
        self.check_prevnext_transition(event, date(2050,5,2), date(2050,4,25), date(2050,5,9))
        self.check_prevnext_transition(event, date(2050,5,9), date(2050,5,2), date(2050,5,16))

        self.check_prevnext_transition(event, date(2060,12,20), date(2060,12,13), date(2060,12,27))
        self.check_prevnext_transition(event, date(2060,12,27), date(2060,12,20), date(2061,1,3))
        self.check_prevnext_transition(event, date(2061,1,3), date(2060,12,27), date(2061,1,10))
        self.check_prevnext_transition(event, date(2061,1,10), date(2061,1,3), date(2061,1,17))


    #@unittest.skip
    def test_25_weekly_timed(self) -> None:
        # Create weekly repeating event at midnight
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1950,4,19,0,0), # Midnight
            rrule = {'FREQ':['WEEKLY']})

        self.check_prevnext(event, date(1940,12,1), None, datetime(1950,4,19,0,0))
        self.check_prevnext_transition(event, datetime(1950,4,19,0,0), None, datetime(1950,4,26,0,0))
        self.check_prevnext_transition(event, datetime(1950,4,26,0,0), datetime(1950,4,19,0,0), datetime(1950,5,3,0,0))
        self.check_prevnext_transition(event, datetime(1950,5,3,0,0), datetime(1950,4,26,0,0), datetime(1950,5,10,0,0))
        self.check_prevnext_transition(event, datetime(1950,5,10,0,0), datetime(1950,5,3,0,0), datetime(1950,5,17,0,0))
        self.check_prevnext_transition(event, datetime(1950,5,17,0,0), datetime(1950,5,10,0,0), datetime(1950,5,24,0,0))
        self.check_prevnext_transition(event, datetime(1950,5,24,0,0), datetime(1950,5,17,0,0), datetime(1950,5,31,0,0))
        self.check_prevnext_transition(event, datetime(1950,5,31,0,0), datetime(1950,5,24,0,0), datetime(1950,6,7,0,0))
        self.check_prevnext_transition(event, datetime(1950,6,7,0,0), datetime(1950,5,31,0,0), datetime(1950,6,14,0,0))
        self.check_prevnext_transition(event, datetime(2026,5,6,0,0), datetime(2026,4,29,0,0), datetime(2026,5,13,0,0))
        self.check_prevnext_transition(event, datetime(2026,5,13,0,0), datetime(2026,5,6,0,0), datetime(2026,5,20,0,0))
        self.check_prevnext_transition(event, datetime(2026,5,20,0,0), datetime(2026,5,13,0,0), datetime(2026,5,27,0,0))
        self.check_prevnext_transition(event, datetime(2032,12,22,0,0), datetime(2032,12,15,0,0), datetime(2032,12,29,0,0))
        self.check_prevnext_transition(event, datetime(2032,12,29,0,0), datetime(2032,12,22,0,0), datetime(2033,1,5,0,0))
        self.check_prevnext_transition(event, datetime(2033,1,5,0,0), datetime(2032,12,29,0,0), datetime(2033,1,12,0,0))
        self.check_prevnext_transition(event, datetime(2033,1,12,0,0), datetime(2033,1,5,0,0), datetime(2033,1,19,0,0))


    #@unittest.skip
    def test_26_weekly_interval(self) -> None:
        # Create weekly repeating event with interval>1
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2000,2,29),
            rrule = {'FREQ':['WEEKLY'], 'INTERVAL':[3]})

        self.check_prevnext(event, date(1994,12,3), None, date(2000,2,29))
        self.check_prevnext_transition(event, date(2000,2,29), None, date(2000,3,21))
        self.check_prevnext_transition(event, date(2000,3,7), date(2000,2,29), date(2000,3,21), False)
        self.check_prevnext_transition(event, date(2000,3,14), date(2000,2,29), date(2000,3,21), False)
        self.check_prevnext_transition(event, date(2000,3,21), date(2000,2,29), date(2000,4,11))
        self.check_prevnext_transition(event, date(2000,3,28), date(2000,3,21), date(2000,4,11), False)
        self.check_prevnext_transition(event, date(2000,4,4), date(2000,3,21), date(2000,4,11), False)
        self.check_prevnext_transition(event, date(2000,4,11), date(2000,3,21), date(2000,5,2))
        self.check_prevnext_transition(event, date(2000,5,2), date(2000,4,11), date(2000,5,23))
        self.check_prevnext_transition(event, date(2000,5,23), date(2000,5,2), date(2000,6,13))
        self.check_prevnext_transition(event, date(2000,6,13), date(2000,5,23), date(2000,7,4))
        self.check_prevnext_transition(event, date(2000,7,4), date(2000,6,13), date(2000,7,25))
        self.check_prevnext_transition(event, date(2003,12,16), date(2003,11,25), date(2004,1,6))
        self.check_prevnext_transition(event, date(2019,12,10), date(2019,11,19), date(2019,12,31))
        self.check_prevnext_transition(event, date(2019,12,31), date(2019,12,10), date(2020,1,21))
        self.check_prevnext_transition(event, date(2028,12,19), date(2028,11,28), date(2029,1,9))


    #@unittest.skip
    def test_27_weekly_thrice_exdate(self) -> None:
        # Create thrice biweekly repeating event with exception dates
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2024,2,15),
            rrule = {'FREQ':['WEEKLY'], 'INTERVAL':[2], 'BYDAY':['TH','SA','SU']},
            exdates = {date(2024,12,19),date(2024,5,16),date(2024,9,26),date(2024,9,28),date(2024,9,29),date(2024,11,23)} # Note May 16th wouldn't occur anyway
            )

        self.check_prevnext(event, date(2001,5,1), None, date(2024,2,15))
        self.check_prevnext_transition(event, date(2024,2,15), None, date(2024,2,17))
        self.check_prevnext_transition(event, date(2024,2,17), date(2024,2,15), date(2024,2,18))
        self.check_prevnext_transition(event, date(2024,2,18), date(2024,2,17), date(2024,2,29))
        self.check_prevnext_transition(event, date(2024,2,18), date(2024,2,17), date(2024,2,29))
        self.check_prevnext_transition(event, date(2024,2,29), date(2024,2,18), date(2024,3,2))
        self.check_prevnext_transition(event, date(2024,3,2), date(2024,2,29), date(2024,3,3))
        self.check_prevnext_transition(event, date(2024,3,3), date(2024,3,2), date(2024,3,14))
        self.check_prevnext_transition(event, date(2024,3,14), date(2024,3,3), date(2024,3,16))
        self.check_prevnext_transition(event, date(2024,3,16), date(2024,3,14), date(2024,3,17))
        self.check_prevnext_transition(event, date(2024,3,17), date(2024,3,16), date(2024,3,28))
        self.check_prevnext_transition(event, date(2024,3,28), date(2024,3,17), date(2024,3,30))
        self.check_prevnext_transition(event, date(2024,3,30), date(2024,3,28), date(2024,3,31))
        self.check_prevnext_transition(event, date(2024,3,31), date(2024,3,30), date(2024,4,11))
        self.check_prevnext_transition(event, date(2024,4,11), date(2024,3,31), date(2024,4,13))
        self.check_prevnext_transition(event, date(2024,4,13), date(2024,4,11), date(2024,4,14))
        self.check_prevnext_transition(event, date(2024,4,14), date(2024,4,13), date(2024,4,25))
        self.check_prevnext_transition(event, date(2024,4,25), date(2024,4,14), date(2024,4,27))
        self.check_prevnext_transition(event, date(2024,4,27), date(2024,4,25), date(2024,4,28))
        self.check_prevnext_transition(event, date(2024,4,28), date(2024,4,27), date(2024,5,9))
        self.check_prevnext_transition(event, date(2024,5,9), date(2024,4,28), date(2024,5,11))
        self.check_prevnext_transition(event, date(2024,5,11), date(2024,5,9), date(2024,5,12))
        self.check_prevnext_transition(event, date(2024,5,12), date(2024,5,11), date(2024,5,23))
        self.check_prevnext_transition(event, date(2024,5,23), date(2024,5,12), date(2024,5,25))
        self.check_prevnext_transition(event, date(2024,5,16), date(2024,5,12), date(2024,5,23), False)
        self.check_prevnext_transition(event, date(2024,5,25), date(2024,5,23), date(2024,5,26))
        self.check_prevnext_transition(event, date(2024,9,12), date(2024,9,1), date(2024,9,14))
        self.check_prevnext_transition(event, date(2024,9,14), date(2024,9,12), date(2024,9,15))
        self.check_prevnext_transition(event, date(2024,9,15), date(2024,9,14), date(2024,10,10))
        self.check_prevnext_transition(event, date(2024,9,26), date(2024,9,15), date(2024,10,10), False)
        self.check_prevnext_transition(event, date(2024,9,27), date(2024,9,15), date(2024,10,10), False)
        self.check_prevnext_transition(event, date(2024,9,28), date(2024,9,15), date(2024,10,10), False)
        self.check_prevnext_transition(event, date(2024,9,29), date(2024,9,15), date(2024,10,10), False)
        self.check_prevnext_transition(event, date(2024,10,10), date(2024,9,15), date(2024,10,12))
        self.check_prevnext_transition(event, date(2024,10,12), date(2024,10,10), date(2024,10,13))
        self.check_prevnext_transition(event, date(2024,11,10), date(2024,11,9), date(2024,11,21))
        self.check_prevnext_transition(event, date(2024,11,21), date(2024,11,10), date(2024,11,24))
        self.check_prevnext_transition(event, date(2024,11,23), date(2024,11,21), date(2024,11,24), False)
        self.check_prevnext_transition(event, date(2024,11,24), date(2024,11,21), date(2024,12,5))
        self.check_prevnext_transition(event, date(2024,12,5), date(2024,11,24), date(2024,12,7))
        self.check_prevnext_transition(event, date(2024,12,7), date(2024,12,5), date(2024,12,8))
        self.check_prevnext_transition(event, date(2024,12,8), date(2024,12,7), date(2024,12,21))
        self.check_prevnext_transition(event, date(2024,12,19), date(2024,12,8), date(2024,12,21), False)
        self.check_prevnext_transition(event, date(2024,12,21), date(2024,12,8), date(2024,12,22))
        self.check_prevnext_transition(event, date(2024,12,22), date(2024,12,21), date(2025,1,2))
        self.check_prevnext_transition(event, date(2025,1,2), date(2024,12,22), date(2025,1,4))
        self.check_prevnext_transition(event, date(2025,1,4), date(2025,1,2), date(2025,1,5))
        self.check_prevnext_transition(event, date(2025,1,5), date(2025,1,4), date(2025,1,16))
        self.check_prevnext_transition(event, date(2025,1,16), date(2025,1,5), date(2025,1,18))
        self.check_prevnext_transition(event, date(2025,1,18), date(2025,1,16), date(2025,1,19))
        self.check_prevnext_transition(event, date(2025,1,19), date(2025,1,18), date(2025,1,30))


    #@unittest.skip
    def test_28_daily_basic(self) -> None:
        # Create simple daily repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2000,1,1),
            rrule = {'FREQ':['DAILY']})

        self.check_prevnext(event, date(1847,6,18), None, date(2000,1,1))
        self.check_prevnext(event, date(1999,12,1), None, date(2000,1,1))
        self.check_prevnext_transition(event, date(2000,1,1), None, date(2000,1,2))
        self.check_prevnext_transition(event, date(2000,1,2), date(2000,1,1), date(2000,1,3))
        self.check_prevnext_transition(event, date(2000,1,3), date(2000,1,2), date(2000,1,4))
        self.check_prevnext_transition(event, date(2000,1,4), date(2000,1,3), date(2000,1,5))
        self.check_prevnext_transition(event, date(2000,12,31), date(2000,12,30), date(2001,1,1))
        self.check_prevnext_transition(event, date(2001,1,1), date(2000,12,31), date(2001,1,2))
        self.check_prevnext_transition(event, date(2045,5,14), date(2045,5,13), date(2045,5,15))


    # Helper methods
    @staticmethod
    def create_event(summary:str, dt_st:date, rrule:dict, dt_end:date=None, exdates=None) -> icalendar.Event:
        # Helper function to create a repeating event
        event = icalendar.Event()
        event.add('SUMMARY', summary)
        event.add('DTSTART', dt_st)
        if dt_end is not None:
            event.add('DT_END', dt_end)
        event.add('RRULE', rrule)
        if exdates is not None:
            for exd in exdates:
                event.add('EXDATE', exd)
        return event


    def check_prevnext(self, event:icalendar.Event, dt:date, dt_prev:Optional[date], dt_next:Optional[date]) -> None:
        # Helper function checks prev/next
        calc_prev, calc_next = previous_next_occurrence(event, dt)
        if isinstance(dt_prev, datetime):
            dt_prev = date_to_datetime(dt_prev, tz=get_local_tz())
        self.assertEqual(calc_prev, dt_prev)
        if isinstance(dt_next, datetime):
            dt_next = date_to_datetime(dt_next, tz=get_local_tz())
        self.assertEqual(calc_next, dt_next)


    def check_prevnext_transition(self, event:icalendar.Event, dt:date, dt_earlier:Optional[date], dt_later:Optional[date], isOcc:bool=True) -> None:
        # Helper function checks triples around `dt`
        if isinstance (dt, datetime):
            self.check_prevnext(event, dt - timedelta(seconds=1), dt_earlier, dt if isOcc else dt_later)
            self.check_prevnext(event, dt, dt_earlier, dt if isOcc else dt_later)
            self.check_prevnext(event, dt + timedelta(seconds=1), dt if isOcc else dt_earlier, dt_later)
            if dt.tzinfo is None:
                # Check special case: in Python 3.5, can't call astimezone() if tz==None
                dateonly = dt.date()
            else:
                dateonly = dt.astimezone(get_local_tz()).date()
            self.check_prevnext(event, dateonly - timedelta(days=1), dt_earlier, dt if isOcc else dt_later)
            self.check_prevnext(event, dateonly, dt_earlier, dt if isOcc else dt_later)
            self.check_prevnext(event, dateonly + timedelta(days=1), dt if isOcc else dt_earlier, dt_later)
        else:
            self.check_prevnext(event, dt, dt_earlier, dt if isOcc else dt_later)
            if (dt_earlier is None or dt-dt_earlier != timedelta(days=1)):
                # Test that previous occ from one day earlier is dt_earlier
                # (Skip this test if dt_earlier is one day earlier)
                self.check_prevnext(event, dt - timedelta(days=1), dt_earlier, dt if isOcc else dt_later)
            self.check_prevnext(event, dt + timedelta(days=1), dt if isOcc else dt_earlier, dt_later)
            withtime = datetime.combine(dt,time())
            self.check_prevnext(event, withtime, dt_earlier, dt if isOcc else dt_later)
            self.check_prevnext(event, withtime - timedelta(seconds=1), dt_earlier, dt if isOcc else dt_later)
            self.check_prevnext(event, withtime + timedelta(seconds=1), dt if isOcc else dt_earlier, dt_later)


# Run all tests if this file is executed as main
if __name__ == '__main__':
    unittest.main()
