#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Run unit tests for repeating entry calculations in Pygenda
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
#

import unittest
from datetime import datetime, date, time, timedelta
from dateutil import tz
import icalendar
from dateutil.rrule import rrulestr
from copy import deepcopy
from sys import version_info as python_version
from tzlocal import get_localzone

# Add '..' to path, so this can be run from test directory
import sys
sys.path.append('..')

# Import the module we want to test...
from pygenda.pygenda_calendar import repeats_in_range


# Set this to True to skip some slow tests.
# Do NOT set this when checking releases!
QUICK_TEST = False


class TestRepeats(unittest.TestCase):
    maxDiff = None # show unlimited chars when showing diffs
    LOCAL_TZ = get_localzone()
    if not hasattr(LOCAL_TZ,'unwrap_shim') and hasattr(LOCAL_TZ,'zone'):
        # Old tzlocal API, so need to create tzinfo object
        LOCAL_TZ = tz.gettz(LOCAL_TZ.zone)

    def test_yearly_basic(self) -> None:
        # Create simple yearly repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1842,7,20),
            rrule = {'FREQ':['YEARLY']})

        # Test null periods
        self.check_count(event, date(1840,1,1), date(1841,1,1), 0)
        self.check_count(event, date(1840,1,1), date(1842,1,1), 0)
        self.check_count(event, date(1984,7,21), date(1985,7,20), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1842,1,1), date(1843,1,1), 1)
        self.check_count_rrule(event, date(1840,1,1), date(1843,1,1), 1)
        self.check_count_rrule(event, date(1990,2,10), date(2002,12,13), 13)


    def test_yearly_timed(self) -> None:
        # Create timed yearly repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1993,12,24,14,15), # time 14:15
            rrule = {'FREQ':['YEARLY']})

        # Test null periods
        self.check_count(event, date(1980,1,1), date(1993,12,24), 0)
        self.check_count(event, date(1993,12,25), date(1994,12,24), 0)
        self.check_count(event, date(2025,12,25), date(2026,12,24), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1993,1,1), date(1994,1,1), 1)
        self.check_count_rrule(event, date(1998,1,1), date(2050,1,1), 52)
        self.check_count_rrule(event, date(3126,2,10), date(3208,12,5), 82)


    def test_yearly_interval(self) -> None:
        # Create yearly event with interval>1
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2001,7,28),
            rrule = {'FREQ':['YEARLY'], 'INTERVAL':[3]})

        # Test null periods
        self.check_count(event, date(1400,1,1), date(1999,1,1), 0)
        self.check_count(event, date(2005,1,1), date(2007,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2005,1,1), date(2050,1,1),15)
        self.check_count_rrule(event, date(1980,1,1), date(2050,1,1),17)


    def test_yearly_zerointerval(self) -> None:
        # Create yearly event with interval==0 (i.e. bad event)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2001,7,28),
            rrule = {'FREQ':['YEARLY'], 'INTERVAL':[0]})

        # Test null periods
        self.check_count(event, date(1400,1,1), date(1999,1,1), 0)
        self.check_count(event, date(2001,1,1), date(2001,7,28), 0)

        # Test zero interval gives exception
        self.assertRaises(ValueError, repeats_in_range, event, date(2001,1,1), date(2002,1,1))


    def test_yearly_interval_leapday(self) -> None:
        # Create yearly repeating event (on leapday, interval 6)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1456,2,29),
            rrule = {'FREQ':['YEARLY'], 'INTERVAL':[6]})

        # Test null periods
        self.check_count(event, date(1400,1,1), date(1456,1,1), 0)
        self.check_count(event, date(1456,3,1), date(1468,2,29), 0)
        self.check_count(event, date(1948,3,1), date(1960,2,29), 0)
        self.check_count(event, date(1797,1,1), date(1804,1,1), 0)
        self.check_count(event, date(1897,1,1), date(1904,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1420,1,1), date(1480,1,1), 2)
        self.check_count_rrule(event, date(1960,1,1), date(2050,1,1), 8)


    def test_yearly_count(self) -> None:
        # Create yearly repeating event with occurence count
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1981,11,16),
            rrule = {'FREQ':['YEARLY'], 'COUNT':[27]})

        # Test null periods
        self.check_count(event, date(1970,1,1), date(1981,1,1), 0)
        self.check_count(event, date(1980,1,1), date(1981,11,16), 0)
        self.check_count(event, date(2008,1,1), date(2020,1,1), 0)
        self.check_count(event, date(2007,11,17), date(2008,12,1), 0)
        self.check_count(event, date(1983,11,17), date(1984,11,16), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1981,1,1), date(1982,1,1), 1)
        self.check_count_rrule(event, date(1970,1,1), date(2025,1,1), 27)
        self.check_count_rrule(event, date(1960,1,1), date(1982,1,1), 1)
        self.check_count_rrule(event, date(1983,11,16), date(1984,11,17), 2)


    def test_yearly_until(self) -> None:
        # Create yearly repeating event with repeat-until
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1962,7,20),
            rrule = {'FREQ':['YEARLY'], 'UNTIL':[date(1970,7,20)]})

        # Test null periods
        self.check_count(event, date(1960,1,1), date(1961,1,1), 0)
        self.check_count(event, date(1960,1,1), date(1962,1,1), 0)
        self.check_count(event, date(1967,7,21), date(1968,7,20), 0)
        self.check_count(event, date(1980,2,10), date(2002,12,13), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1962,1,1), date(1963,1,1), 1)
        self.check_count_rrule(event, date(1960,1,1), date(1972,1,1), 9)
        self.check_count_rrule(event, date(1960,1,1), date(1963,1,1), 1)
        self.check_count_rrule(event, date(1967,7,21), date(1968,7,21), 1)
        self.check_count_rrule(event, date(1970,1,1), date(1971,1,1), 1)
        self.check_count_rrule(event, date(1970,1,1), date(1975,1,1), 1)


    def test_yearly_timezone(self) -> None:
        # Create timed yearly repeating event with timezone
        tz_SAM = tz.gettz('Pacific/Samoa') # UTC-11
        self.assertTrue(tz_SAM) # check not None
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1960,12,31,23,16,4,tzinfo=tz_SAM),
            rrule = {'FREQ':['YEARLY']})

        # Test null periods
        self.check_count(event, date(1950,1,1), date(1960,1,1), 0)
        self.check_count(event, date(1960,1,1), date(1960,12,31), 0)
        # NB timezone means event occurs 1961-01-01 UCT (for most people)
        self.check_count(event, date(1960,1,1), date(1961,1,1), 0)
        self.check_count(event, date(1961,1,2), date(1962,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1961,1,1), date(1961,1,7), 1)
        self.check_count_rrule(event, date(2023,1,1), date(2024,1,1), 1)
        self.check_count_rrule(event, date(3066,1,1), date(3066,1,7), 1)


    def test_monthly_basic(self) -> None:
        # Create simple monthly repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1999,4,20),
            rrule = {'FREQ':['MONTHLY']})

        # Test null periods
        self.check_count(event, date(1999,1,1), date(1999,4,1), 0)
        self.check_count(event, date(1999,4,21), date(1999,5,20), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1999,4,20), date(1999,5,20), 1)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 9)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 12)


    def test_monthly_endofmonth(self) -> None:
        # Create monthly repeating event starting at end of month
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1999,12,31),
            rrule = {'FREQ':['MONTHLY']})

        # Test null periods
        self.check_count(event, date(1999,1,1), date(1999,12,31), 0)
        self.check_count(event, date(2000,2,1), date(2000,3,31), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1999,1,1), date(2010,1,1), 71)
        self.check_count_rrule(event, date(2010,1,1), date(2010,2,1), 1)


    def test_monthly_timed_exdate(self) -> None:
        # Create timed monthly repeating event
        # (with the potential to fall on a leap-day)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1998,3,28,12,3), # time 12:03
            rrule = {'FREQ':['MONTHLY']},
            exdates = {datetime(2063,7,28,12,3), date(2065,7,28)})

        # Test null periods
        self.check_count(event, date(1997,1,1), date(1998,3,28), 0)
        self.check_count(event, date(1998,3,29), date(1998,4,28), 0)
        self.check_count(event, date(2046,12,29), date(2047,1,28), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1998,1,1), date(1999,1,1), 10)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 12)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 12)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 12)
        self.check_count_rrule(event, date(2063,1,1), date(2064,1,1), 11)
        self.check_count_rrule(event, date(2065,1,1), date(2066,1,1), 11)
        self.check_count_rrule(event, date(2100,1,1), date(2101,1,1), 12)
        self.check_count_rrule(event, date(2112,1,1), date(2113,1,1), 12)


    def test_monthly_timed_29th_exdate(self) -> None:
        # Create timed monthly repeating event
        # (with the potential to fall on a leap-day)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1998,3,29,12,3), # time 12:03
            rrule = {'FREQ':['MONTHLY']},
            exdates = {datetime(2063,7,29,12,3), date(2065,7,29)})

        # Test null periods
        self.check_count(event, date(1997,1,1), date(1998,3,29), 0)
        self.check_count(event, date(1998,3,30), date(1998,4,29), 0)
        self.check_count(event, date(2046,12,30), date(2047,1,29), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1998,1,1), date(1999,1,1), 10)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 11)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 12)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 11)
        self.check_count_rrule(event, date(2063,1,1), date(2064,1,1), 10)
        self.check_count_rrule(event, date(2065,1,1), date(2066,1,1), 10)
        self.check_count_rrule(event, date(2100,1,1), date(2101,1,1), 11)
        self.check_count_rrule(event, date(2112,1,1), date(2113,1,1), 12)


    def test_monthly_interval_29th(self) -> None:
        # Create monthly repeating event on 29th, with interval>1
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1997,8,29),
            rrule = {'FREQ':['MONTHLY'], 'INTERVAL':[6]})

        # Test null periods
        self.check_count(event, date(1999,1,1), date(1999,7,1), 0)
        self.check_count(event, date(2100,1,1), date(2100,7,1), 0)
        self.check_count(event, date(2000,1,1), date(2000,2,29), 0)

        # Test some non-null periods
        self.check_count_rrule(event, date(1997,1,1), date(1998,1,1), 1)
        self.check_count_rrule(event, date(2000,1,1), date(2000,7,1), 1)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 2)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 1)
        self.check_count_rrule(event, date(1999,1,1), date(2010,1,1), 14)


    def test_monthly_count(self) -> None:
        # Create monthly repeating event with occurence count
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2018,9,8),
            rrule = {'FREQ':['MONTHLY'], 'COUNT':[7]})

        # Test null periods
        self.check_count(event, date(2000,1,1), date(2018,9,8), 0)
        self.check_count(event, date(2019,3,9), date(2050,1,1), 0)
        self.check_count(event, date(2018,12,9), date(2019,1,8), 0)
        self.check_count(event, date(2019,1,9), date(2019,2,8), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2018,1,1), date(2020,1,1), 7)
        self.check_count_rrule(event, date(2000,1,1), date(2018,9,9), 1)
        self.check_count_rrule(event, date(2018,9,3), date(2018,9,10), 1)
        self.check_count_rrule(event, date(2018,1,1), date(2019,1,1), 4)
        self.check_count_rrule(event, date(2019,1,1), date(2020,1,1), 3)


    def test_monthly_interval_until(self) -> None:
        # Create bi-monthly repeating event with repeat-until
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1979,4,27),
            rrule = {'FREQ':['MONTHLY'], 'INTERVAL':[2], 'UNTIL':[date(1982,2,27)]})

        # Test null periods
        self.check_count(event, date(1979,1,1), date(1979,4,27), 0)
        self.check_count(event, date(1982,2,28), date(1990,1,1), 0)
        self.check_count(event, date(1979,4,28), date(1979,6,27), 0)
        self.check_count(event, date(1979,12,28), date(1980,2,27), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1979,1,1), date(1980,1,1), 5)
        self.check_count_rrule(event, date(1980,1,1), date(1981,1,1), 6)
        self.check_count_rrule(event, date(1981,1,1), date(1982,1,1), 6)
        self.check_count_rrule(event, date(1982,1,1), date(1983,1,1), 1)
        self.check_count_rrule(event, date(1970,1,1), date(1990,1,1), 18)


    def test_monthly_timezone_until(self) -> None:
        # Create timed monthly repeating event with timezone
        tz_SY = tz.gettz('Australia/Sydney')
        self.assertTrue(tz_SY) # check not None
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2023,1,30,17,33,tzinfo=tz_SY),
            rrule = {'FREQ':['MONTHLY'],'UNTIL':[datetime(2030,7,30,17,33,tzinfo=tz_SY)]})

        # Test null periods
        self.check_count(event, date(2022,1,1), date(2023,1,1), 0)
        self.check_count(event, date(2023,1,1), date(2023,1,30), 0)
        self.check_count(event, date(2030,7,31), date(2031,1,1), 0)
        self.check_count(event, date(2023,1,31), date(2023,2,6), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2023,1,1), date(2023,1,31), 1)
        self.check_count_rrule(event, date(2023,1,1), date(2024,1,1), 11)
        self.check_count_rrule(event, date(2030,1,1), date(2031,1,1), 6)
        self.check_count_rrule(event, date(2030,1,1), date(2030,7,30), 5)
        self.check_count_rrule(event, date(2030,1,1), date(2030,7,31), 6)


    def test_monthly_timezone_until_movesday(self) -> None:
        # Create timed monthly repeating event with timezone.
        # Set timezone far west & late in day, so for most local
        # timezones it is shifted into the next day.
        tz_AN = tz.gettz('America/Anchorage')
        self.assertTrue(tz_AN) # check not None
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2023,1,30,23,18,tzinfo=tz_AN),
            rrule = {'FREQ':['MONTHLY'],'UNTIL':[datetime(2030,7,30,23,18,tzinfo=tz_AN)]})

        # Test null periods
        self.check_count(event, date(2022,1,1), date(2023,1,1), 0)
        self.check_count(event, date(2023,1,1), date(2023,1,30), 0)
        self.check_count(event, date(2023,1,1), date(2023,1,31), 0)
        self.check_count(event, date(2023,2,1), date(2023,2,7), 0)
        self.check_count(event, date(2030,8,1), date(2032,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2023,1,1), date(2023,2,1), 1)
        self.check_count_rrule(event, date(2023,1,1), date(2024,1,1), 11)
        self.check_count_rrule(event, date(2029,7,31), date(2029,8,1), 1) # next day
        self.check_count_rrule(event, date(2030,7,31), date(2031,1,1), 1) # last occ
        self.check_count_rrule(event, date(2030,1,1), date(2031,1,1), 6)
        self.check_count_rrule(event, date(2030,1,1), date(2030,7,30), 5)
        self.check_count_rrule(event, date(2030,1,1), date(2030,7,31), 5)
        self.check_count_rrule(event, date(2030,1,1), date(2030,8,1), 6)


    def test_weekly_basic(self) -> None:
        # Create simple weekly repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2050,4,11), # Monday
            rrule = {'FREQ':['WEEKLY']})

        # Test null periods
        self.check_count(event, date(1900,1,1), date(2000,1,1), 0)
        self.check_count(event, date(2050,1,1), date(2050,4,11), 0)
        self.check_count(event, date(2050,4,12), date(2050,4,18), 0)
        self.check_count(event, date(2050,4,19), date(2050,4,25), 0)

        # Test some non-null periods
        self.check_count_rrule(event, date(2040,1,1), date(2050,4,12), 1)
        self.check_count_rrule(event, date(2040,1,1), date(2050,5,1), 3)
        self.check_count_rrule(event, date(2060,2,10), date(2060,10,17), 35)


    def test_weekly_interval(self) -> None:
        # Create weekly repeating event with interval>1
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2000,2,29),
            rrule = {'FREQ':['WEEKLY'], 'INTERVAL':[3]})

        # Test null periods
        self.check_count(event, date(1990,1,1), date(2000,1,1), 0)
        self.check_count(event, date(2000,1,1), date(2000,2,29), 0)
        self.check_count(event, date(2000,3,1), date(2000,3,21), 0)
        self.check_count(event, date(2000,3,22), date(2000,4,11), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2000,2,29), date(2000,3,21), 1)
        self.check_count_rrule(event, date(2004,1,1), date(2004,4,1), 5)


    def test_weekly_interval_timed(self) -> None:
        # Create timed tri-weekly repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2021,5,19,10,43,22), # time 10:43:22
            rrule = {'FREQ':['WEEKLY'], 'INTERVAL':[3]})

        # Test null periods
        self.check_count(event, date(2021,1,1), date(2021,5,19), 0)
        self.check_count(event, date(2021,5,20), date(2021,6,9), 0)
        self.check_count(event, date(2021,6,10), date(2021,6,30), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2021,1,1), date(2021,5,20), 1)
        self.check_count_rrule(event, date(2021,1,1), date(2022,1,1), 11)
        self.check_count_rrule(event, date(2022,1,1), date(2023,1,1), 18)
        self.check_count_rrule(event, date(2023,1,1), date(2024,1,1), 17)


    def test_weekly_count(self) -> None:
        # Create bi-weekly repeating event with occurence count
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2013,3,8), # Friday
            rrule = {'FREQ':['WEEKLY'], 'INTERVAL':[2], 'COUNT':[10]})

        # Test null periods
        self.check_count(event, date(2010,1,1), date(2013,3,8), 0)
        self.check_count(event, date(2013,3,9), date(2013,3,22), 0)
        self.check_count(event, date(2013,3,23), date(2013,4,5), 0)
        self.check_count(event, date(2013,7,13), date(2014,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2013,1,1), date(2014,1,1), 10)
        self.check_count_rrule(event, date(2013,1,1), date(2013,3,9), 1)
        self.check_count_rrule(event, date(2013,7,12), date(2014,1,1), 1)
        self.check_count_rrule(event, date(2013,6,28), date(2014,1,1), 2)


    def test_weekly_interval_until(self) -> None:
        # Create weekly repeating event with repeat-until
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2031,11,10), # Monday
            rrule = {'FREQ':['WEEKLY'], 'UNTIL':[date(2033,5,20)]})

        # Test null periods
        self.check_count(event, date(2028,1,1), date(2031,11,10), 0)
        self.check_count(event, date(2033,5,17), date(2040,1,1), 0)
        self.check_count(event, date(2031,11,11), date(2031,11,17), 0)
        self.check_count(event, date(2031,12,30), date(2032,1,5), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2031,1,1), date(2032,1,1), 8)
        self.check_count_rrule(event, date(2032,1,1), date(2033,1,1), 52)
        self.check_count_rrule(event, date(2033,1,1), date(2034,1,1), 20)
        self.check_count_rrule(event, date(2031,11,11), date(2033,5,15), 78)


    def test_weekly_timezone_until(self) -> None:
        # Create timed weekly repeating event with timezone
        tz_NY = tz.gettz('America/New_York')
        self.assertTrue(tz_NY) # check not None
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2020,2,15,11,13,tzinfo=tz_NY),
            rrule = {'FREQ':['WEEKLY'],'UNTIL':[datetime(2022,7,16,11,19,tzinfo=tz_NY)]})

        # Test null periods
        self.check_count(event, date(2019,1,1), date(2020,2,15), 0)
        self.check_count(event, date(2019,1,1), date(2020,2,15), 0)
        self.check_count(event, date(2019,1,1), date(2020,2,15), 0)
        self.check_count(event, date(2022,7,17), date(2022,9,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2020,1,1), date(2020,2,16), 1)
        self.check_count_rrule(event, date(2020,1,1), date(2020,3,1), 3)
        self.check_count_rrule(event, date(2020,1,1), date(2021,1,1), 46)
        self.check_count_rrule(event, date(2021,1,1), date(2022,1,1), 52)
        self.check_count_rrule(event, date(2022,1,1), date(2023,1,1), 29)


    def test_weekly_twice(self) -> None:
        # Create twice weekly repeating event on Tuesday & Thursday
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2023,4,25,19,15),
            rrule = {'FREQ':['WEEKLY'], 'BYDAY':['TU','TH']})

        # Test null periods
        self.check_count(event, date(2022,1,1), date(2023,1,1), 0)
        self.check_count(event, date(2023,1,1), date(2023,4,25), 0)
        self.check_count(event, date(2023,4,26), date(2023,4,27), 0)
        self.check_count(event, date(2023,4,28), date(2023,5,2), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2023,4,24), date(2023,5,1), 2)
        self.check_count_rrule(event, date(2023,4,1), date(2023,5,1), 2)
        self.check_count_rrule(event, date(2023,1,1), date(2024,1,1), 72)
        self.check_count_rrule(event, date(2024,1,1), date(2025,1,1), 105)


    def test_weekly_thrice_exdate(self) -> None:
        # Create thrice biweekly repeating event with exception dates
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2024,2,15),
            rrule = {'FREQ':['WEEKLY'], 'INTERVAL':[2], 'BYDAY':['TH','SA','SU']},
            exdates = {date(2024,12,19),date(2024,5,16),date(2024,9,26),date(2024,9,28),date(2024,9,29),date(2024,11,23)} # Note May 16th wouldn't occur anyway
            )

        # Test null periods
        self.check_count(event, date(2023,1,1), date(2024,1,1), 0)
        self.check_count(event, date(2024,1,1), date(2024,2,15), 0)
        self.check_count(event, date(2024,2,16), date(2024,2,17), 0)
        self.check_count(event, date(2024,2,19), date(2024,2,29), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2024,2,12), date(2024,2,19), 3)
        self.check_count_rrule(event, date(2024,2,26), date(2024,3,4), 3)
        self.check_count_rrule(event, date(2024,2,1), date(2024,3,1), 4)
        self.check_count_rrule(event, date(2024,1,1), date(2025,1,1), 64)
        self.check_count_rrule(event, date(2025,1,1), date(2026,1,1), 78)


    def test_daily_basic(self) -> None:
        # Create simple daily repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2000,1,1),
            rrule = {'FREQ':['DAILY']})

        # Test null periods
        self.check_count(event, date(1999,1,1), date(2000,1,1), 0)
        self.check_count(event, date(2000,1,1), date(2000,1,1), 0)
        self.check_count(event, date(2001,1,1), date(2001,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1999,12,28), date(2000,1,4), 3)
        self.check_count_rrule(event, date(2000,2,10), date(2000,2,17), 7)


    def test_daily_interval(self) -> None:
        # Create daily repeating event with interval>1
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1999,9,13),
            rrule = {'FREQ':['DAILY'], 'INTERVAL':[3]})

        # Test null periods
        self.check_count(event, date(1998,8,1), date(1999,9,13), 0)
        self.check_count(event, date(1999,9,14), date(1999,9,16), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 37)
        self.check_count_rrule(event, date(1999,11,9), date(2000,2,29), 38)


    def test_daily_interval_timed(self) -> None:
        # Create timed daily repeating event
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2023,7,27,11,7,41), # time 11:07:41
            rrule = {'FREQ':['DAILY'], 'INTERVAL':[5]})

        # Test null periods
        self.check_count(event, date(2023,1,1), date(2023,7,27), 0)
        self.check_count(event, date(2023,7,28), date(2023,8,1), 0)
        self.check_count(event, date(2023,8,2), date(2023,8,6), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2023,1,1), date(2023,7,28), 1)
        self.check_count_rrule(event, date(2023,7,27), date(2023,8,2), 2)
        self.check_count_rrule(event, date(2023,1,1), date(2024,1,1), 32)
        self.check_count_rrule(event, date(2024,1,1), date(2025,1,1), 73)
        self.check_count_rrule(event, date(2025,1,1), date(2026,1,1), 73)


    def test_daily_interval_count(self) -> None:
        # Create daily repeating event with occurence count
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1988,1,6),
            rrule = {'FREQ':['DAILY'], 'INTERVAL':[13], 'COUNT':[70]})

        # Test null periods
        self.check_count(event, date(1987,1,1), date(1988,1,6), 0)
        self.check_count(event, date(1988,1,7), date(1988,1,19), 0)
        self.check_count(event, date(1988,1,20), date(1988,2,1), 0)
        self.check_count(event, date(1990,6,22), date(1995,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1988,1,1), date(1990,7,1), 70)
        self.check_count_rrule(event, date(1988,1,1), date(1988,2,1), 2)
        self.check_count_rrule(event, date(1988,1,1), date(1989,1,1), 28)


    def test_daily_interval_until(self) -> None:
        # Create daily repeating event with repeat-until
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2019,2,6), # Wednesday
            rrule = {'FREQ':['DAILY'], 'INTERVAL':[9], 'UNTIL':[date(2021,5,5)]})

        # Test null periods
        self.check_count(event, date(2019,1,1), date(2019,2,6), 0)
        self.check_count(event, date(2021,5,6), date(2023,1,1), 0)
        self.check_count(event, date(2019,2,7), date(2019,2,15), 0)
        self.check_count(event, date(2019,2,16), date(2019,2,24), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2019,1,1), date(2020,1,1), 37)
        self.check_count_rrule(event, date(2020,1,1), date(2021,1,1), 41)
        self.check_count_rrule(event, date(2021,1,1), date(2022,1,1), 14)
        self.check_count_rrule(event, date(2018,1,1), date(2023,1,1), 92)


    def test_daily_timezone(self) -> None:
        # Create timed daily repeating event with timezone
        tz_MAD = tz.gettz('Europe/Madrid')
        self.assertTrue(tz_MAD) # check not None
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2014,10,11,10,45,tzinfo=tz_MAD),
            rrule = {'FREQ':['DAILY']})

        # Test null periods
        self.check_count(event, date(2013,1,1), date(2014,10,11), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2013,1,1), date(2014,10,12), 1)
        self.check_count_rrule(event, date(2014,1,1), date(2015,1,1), 82)


    def test_hourly_basic(self) -> None:
        # Create simple hourly repeating event (with a start time)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2000,1,1,9,30), # start time 09:30
            rrule = {'FREQ':['HOURLY']})

        # Test null periods
        self.check_count(event, date(2000,1,1), date(2000,1,1), 0)

        # Test non-zero periods
        self.check_count_rrule(event, date(2001,2,10), date(2001,2,11), 24)
        self.check_count_rrule(event, date(2000,12,31), date(2001,1,2), 48)


    def test_hourly_untimed(self) -> None:
        # Create simple hourly repeating event with no time
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2000,1,1), # NB: No start time (not sure this is valid ical!)
            rrule = {'FREQ':['HOURLY']})

        # Test null periods
        self.check_count(event, date(2000,1,1), date(2000,1,1), 0)
        self.check_count(event, date(1999,12,1), date(2000,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2000,1,1), date(2000,1,2), 24)
        self.check_count_rrule(event, date(1999,12,29), date(2000,1,5), 24*4)
        self.check_count_rrule(event, date(2001,2,10), date(2001,2,11), 24)


    def test_hourly_interval_timed(self) -> None:
        # Create hourly repeating event with interval>1
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2010,10,30,17,57), # time 17:57, day before clocks go back
            rrule = {'FREQ':['HOURLY'], 'INTERVAL':[5]})

        # Test null periods
        self.check_count(event, date(2010,1,1), date(2010,10,30), 0)
        self.check_count(event, date(2009,1,1), date(2010,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2010,10,30), date(2010,10,31), 2)
        self.check_count_rrule(event, date(2010,10,31), date(2010,11,1), 5)
        self.check_count_rrule(event, date(2010,10,31), date(2010,11,2), 10)
        self.check_count_rrule(event, date(2010,11,1), date(2010,11,2), 5)
        self.check_count_rrule(event, date(2010,1,1), date(2011,1,1), 300)


    def test_hourly_interval_untimed(self) -> None:
        # Create hourly repeating event with interval>1, but no start time
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2011,11,14), # NB: No start time (not sure this is valid ical!)
            rrule = {'FREQ':['HOURLY'], 'INTERVAL':[7]})

        # Test null periods
        self.check_count(event, date(2010,1,1), date(2011,1,1), 0)
        self.check_count(event, date(2010,12,10), date(2011,11,14), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2011,11,14), date(2011,11,15), 4)
        self.check_count_rrule(event, date(2011,11,15), date(2011,11,16), 3)


    def test_hourly_interval_count(self) -> None:
        # Create hourly repeating event with occurence count
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1968,4,27,11,47), # Time 11:47
            rrule = {'FREQ':['HOURLY'], 'INTERVAL':[29], 'COUNT':[70]})

        # Test null periods
        self.check_count(event, date(1968,1,1), date(1968,4,27), 0)
        self.check_count(event, date(1968,7,20), date(1969,1,1), 0)
        self.check_count(event, date(1968,4,30), date(1968,5,1), 0)
        self.check_count(event, date(1968,5,6), date(1968,5,7), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1968,1,1), date(1969,1,1), 70)
        self.check_count_rrule(event, date(1968,4,27), date(1968,5,1), 3)
        self.check_count_rrule(event, date(1968,5,1), date(1968,5,8), 6)


    def test_hourly_interval_until(self) -> None:
        # Create hourly repeating event with repeat-until
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2022,6,7,22,16,28), # Time 22:16:28
            rrule = {'FREQ':['HOURLY'], 'INTERVAL':[9], 'UNTIL':[datetime(2022,7,5,7,16,28)]})

        # Test null periods
        self.check_count(event, date(2022,1,1), date(2022,6,7), 0)
        self.check_count(event, date(2022,7,6), date(2023,1,1), 0)
        self.check_count(event, date(2022,7,1), date(2022,7,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2022,1,1), date(2023,1,1), 74)
        self.check_count_rrule(event, date(2022,6,7), date(2022,6,8), 1)
        self.check_count_rrule(event, date(2022,6,8), date(2022,6,9), 2)
        self.check_count_rrule(event, date(2022,6,9), date(2022,6,10), 3)
        self.check_count_rrule(event, date(2022,7,5), date(2022,7,6), 1)


    def test_minutely_basic(self) -> None:
        # Create simple minutely repeating event (with a start time)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2015,4,11,11,14,36), # start time 11:14:36
            rrule = {'FREQ':['MINUTELY']})

        # Test null periods
        self.check_count(event, date(2012,12,10), date(2014,11,17), 0)
        self.check_count(event, date(2012,12,10), date(2015,4,11), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2012,12,10), date(2015,4,12), 60*12+46)
        self.check_count_rrule(event, date(2015,5,1), date(2015,5,2), 60*24)


    def test_minutely_untimed(self) -> None:
        # Create minutely repeating event with no start time
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2025,6,13), # No start time (not sure this is valid ical!)
            rrule = {'FREQ':['MINUTELY']})

        # Test null periods
        self.check_count(event, date(2022,12,10), date(2024,11,17), 0)
        self.check_count(event, date(2025,6,1), date(2025,6,13), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2025,6,13), date(2025,6,14), 60*24)
        self.check_count_rrule(event, date(2025,6,12), date(2025,6,14), 60*24)
        self.check_count_rrule(event, date(2025,6,12), date(2025,6,15), 60*48)


    def test_minutely_interval(self) -> None:
        # Create minutely repeating event with interval>1
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2019,5,31,16,59,59), # start time 16:59:59
            rrule = {'FREQ':['MINUTELY'], 'INTERVAL':[23]})

        # Test null periods
        self.check_count(event, date(2019,1,1), date(2019,3,1), 0)
        self.check_count(event, date(2019,4,24), date(2019,5,31), 0)

        # Test non-null period counts
        self.check_count_rrule(event, date(2019,5,31), date(2019,6,1), 19)
        self.check_count_rrule(event, date(2019,6,10), date(2019,6,11), 63)
        self.check_count_rrule(event, date(2019,6,12), date(2019,6,14), 126)


    def test_minutely_interval_count(self) -> None:
        # Create minutely repeating event with occurence count
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1999,3,29,21,39), # Time 21:39
            rrule = {'FREQ':['MINUTELY'], 'INTERVAL':[52], 'COUNT':[995]})

        # Test null periods
        self.check_count(event, date(1999,1,1), date(1999,3,29), 0)
        self.check_count(event, date(1999,5,5), date(2000,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 995)
        self.check_count_rrule(event, date(1999,3,29), date(1999,3,30), 3)
        self.check_count_rrule(event, date(1999,3,30), date(1999,3,31), 28)
        self.check_count_rrule(event, date(1999,3,31), date(1999,4,1), 28)
        self.check_count_rrule(event, date(1999,4,1), date(1999,4,2), 27)
        self.check_count_rrule(event, date(1999,4,2), date(1999,4,3), 28)
        self.check_count_rrule(event, date(1999,5,4), date(1999,5,5), 23)
        self.check_count_rrule(event, date(1999,3,1), date(1999,4,1), 59)
        self.check_count_rrule(event, date(1999,4,1), date(1999,5,1), 830)
        self.check_count_rrule(event, date(1999,5,1), date(1999,6,1), 106)


    def test_minutely_interval_until(self) -> None:
        # Create minutely repeating event with repeat-until
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2024,3,22,6,38,4), # Time 6:38:04
            rrule = {'FREQ':['MINUTELY'], 'INTERVAL':[1567], 'UNTIL':[datetime(2024,8,19,10,23,51)]})

        # Test null periods
        self.check_count(event, date(2022,1,1), date(2024,3,22), 0)
        self.check_count(event, date(2024,8,19), date(2025,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2024,1,1), date(2025,1,1), 138)
        self.check_count_rrule(event, date(2024,3,1), date(2024,4,1), 9)
        self.check_count_rrule(event, date(2024,4,1), date(2024,5,1), 28)
        self.check_count_rrule(event, date(2024,5,1), date(2024,6,1), 28)
        self.check_count_rrule(event, date(2024,6,1), date(2024,7,1), 28)
        self.check_count_rrule(event, date(2024,7,1), date(2024,8,1), 29)
        self.check_count_rrule(event, date(2024,8,1), date(2024,9,1), 16)


    def test_secondly_basic(self) -> None:
        # Create simple repeating event (with a start time)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2017,8,31,23,54,46), # start time 23:54:46
            rrule = {'FREQ':['SECONDLY']})

        # Test null periods
        self.check_count(event, date(2017,1,24), date(2017,8,31), 0)
        self.check_count(event, date(2017,10,15), date(2017,10,15), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2017,1,24), date(2017,9,1), 60*5+14)
        self.check_count_rrule(event, date(2017,8,31), date(2017,9,1), 60*5+14)
        self.check_count_rrule(event, date(2017,9,1), date(2017,9,2), 60*60*24)
        if QUICK_TEST:
            return
        self.check_count_rrule(event, date(2017,9,1), date(2017,9,3), 60*60*48)
        # Test daylight-saving change (25hrs in last Sunday of October):
        # This is slow, but important to test that it's correct
        self.check_count_rrule(event, date(2017,10,29), date(2017,10,30), 60*60*25)
        # Don't use check_count_rrule() here because it's so slow:
        self.check_count(event, date(2017,12,31), date(2018,1,2), 60*60*48)


    def test_secondly_untimed(self) -> None:
        # Create secondly repeating event with no start time
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1924,2,29), # No start time (not sure this is valid ical!)
            rrule = {'FREQ':['SECONDLY']})

        # Test null periods
        self.check_count(event, date(1840,7,31), date(1852,2,29), 0)
        self.check_count(event, date(1924,1,1), date(1924,2,29), 0)
        self.check_count(event, date(1924,2,1), date(1924,2,29), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1924,2,1), date(1924,3,1), 60*60*24)
        if QUICK_TEST:
            return
        self.check_count_rrule(event, date(1924,2,29), date(1924,3,1), 60*60*24)
        self.check_count_rrule(event, date(1924,3,2), date(1924,3,4), 60*60*48)
        # Don't use check_count_rrule() here because it's so slow:
        self.check_count(event, date(2137,6,12), date(2137,6,14), 60*60*48)


    def test_secondly_interval(self) -> None:
        # Create secondly repeating event with interval>1
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2022,2,22,22,22,22), # start time 22:22:22
            rrule = {'FREQ':['SECONDLY'], 'INTERVAL':[2222]})

        # Test null periods
        self.check_count(event, date(1463,1,1), date(1464,1,1), 0)
        self.check_count(event, date(2022,2,2), date(2022,2,22), 0)
        self.check_count(event, date(2022,2,22), date(2022,2,22), 0)
        self.check_count(event, date(2034,1,1), date(2034,1,1), 0)

        # Test non-null period counts
        self.check_count_rrule(event, date(2022,2,22), date(2022,2,23), 3)
        self.check_count_rrule(event, date(2022,2,1), date(2022,2,23), 3)
        self.check_count_rrule(event, date(2022,2,1), date(2022,2,24), 42)
        if QUICK_TEST:
            return
        self.check_count_rrule(event, date(2034,1,1), date(2035,1,1), 14193)


    def test_secondly_interval_count(self) -> None:
        # Create secondly repeating event with occurence count
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2021,6,24,7,1,1), # Time 7:01:01
            rrule = {'FREQ':['SECONDLY'], 'INTERVAL':[91314], 'COUNT':[1582]})

        # Test null periods
        self.check_count(event, date(2021,1,1), date(2021,6,24), 0)
        self.check_count(event, date(2026,1,21), date(2027,1,1), 0)
        self.check_count(event, date(2021,7,7), date(2021,7,8), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2021,1,1), date(2027,1,1), 1582)
        if QUICK_TEST:
            return
        self.check_count_rrule(event, date(2021,1,1), date(2022,1,1), 181)
        self.check_count_rrule(event, date(2022,1,1), date(2023,1,1), 345)
        self.check_count_rrule(event, date(2023,1,1), date(2024,1,1), 346)
        self.check_count_rrule(event, date(2024,1,1), date(2025,1,1), 346)
        self.check_count_rrule(event, date(2025,1,1), date(2026,1,1), 345)
        self.check_count_rrule(event, date(2026,1,1), date(2027,1,1), 19)


    def test_secondly_interval_until(self) -> None:
        # Create secondly repeating event with repeat-until
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2019,1,5,13,13,58), # Time 13:13:58
            rrule = {'FREQ':['SECONDLY'], 'INTERVAL':[127], 'UNTIL':[datetime(2021,4,29,22,41,36)]})

        # Test null periods
        self.check_count(event, date(2019,1,1), date(2019,1,5), 0)
        self.check_count(event, date(2021,4,30), date(2022,1,1), 0)
        self.check_count(event, date(2020,2,28), date(2020,2,28), 0)
        self.check_count(event, date(2021,4,30), date(2021,5,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2019,1,1), date(2019,1,6), 306)
        self.check_count_rrule(event, date(2019,1,1), date(2020,1,1), 245219)
        if QUICK_TEST:
            return
        self.check_count_rrule(event, date(2020,1,1), date(2021,1,1), 248995) #leap yr
        self.check_count_rrule(event, date(2021,1,1), date(2021,1,2), 681)
        self.check_count_rrule(event, date(2019,3,31), date(2019,4,1), 652) # Clocks go fwd
        self.check_count_rrule(event, date(2021,4,29), date(2021,4,30), 643) # Last day
        self.check_count_rrule(event, date(2021,1,1), date(2022,1,1), 80892) # Includes clocks going fwd


    # Helper methods
    @staticmethod
    def create_event(summary:str, dt_st:date, dt_end=None, rrule=None, exdates=None) -> icalendar.Event:
        # Helper function to create a repeating event
        event = icalendar.Event()
        event.add('SUMMARY', summary)
        event.add('DTSTART', dt_st)
        if dt_end is not None:
            event.add('DT_END', dt_end)
        if rrule is not None:
            event.add('RRULE', rrule)
        if exdates is not None:
            for exd in exdates:
                event.add('EXDATE', exd)
        return event


    def check_count(self, event:icalendar.Event, dt_st:date, dt_end:date, expected:int) -> None:
        # Helper function checks number of repeats in given period
        self.assertTrue((dt_end-dt_st)>=timedelta(0)) # consistency check range
        from_reps_in_rng = repeats_in_range(event, dt_st, dt_end)
        self.assertEqual(len(from_reps_in_rng), expected)


    def check_count_rrule(self, event:icalendar.Event, dt_st:date, dt_end:date, expected:int) -> None:
        # Helper function checks number of repeats in given period
        # and also uses dateutil.rrule to test exact date/datetimes
        self.assertTrue((dt_end-dt_st)>=timedelta(0)) # consistency check range

        # First check using count
        from_reps_in_rng = repeats_in_range(event, dt_st, dt_end)
        self.assertEqual(len(from_reps_in_rng), expected)

        # Then check using rrule to make sure repeat dates/times as expected
        ev_rr = deepcopy(event['RRULE']) # Deep copy so can change elements
        event_st = deepcopy(event['DTSTART'].dt)
        timed_event = isinstance(event_st, datetime)

        if timed_event and 'UNTIL' in ev_rr:
            # Need to specify UNTIL value in UTC
            until = ev_rr['UNTIL'][0]
            if isinstance(until,datetime) and until.tzinfo is None:
                until = until.replace(tzinfo=self.LOCAL_TZ)
            if isinstance(until,datetime):
                until = until.astimezone(tz.gettz('UTC')) # Convert to UTC
                ev_rr['UNTIL'][0] = until

        rrstr = ev_rr.to_ical().decode('utf-8')
        hr_min_sec_rep = event['RRULE']['FREQ'][0] in ['HOURLY','MINUTELY','SECONDLY']
        if hr_min_sec_rep and not timed_event:
            # Start time needs to be a datetime - set to midnight
            event_st = datetime(event_st.year,event_st.month,event_st.day)
            timed_event = True
        if timed_event and event_st.tzinfo is None:
            event_st = event_st.replace(tzinfo=self.LOCAL_TZ)
        if hr_min_sec_rep:
            # We might need to handle things like summer time starting.
            # So we work in UTC and then convert back later.
            event_tz = event_st.tzinfo # save timezone
            event_st = event_st.astimezone(tz.gettz('UTC'))
        rr = rrulestr(rrstr, dtstart=event_st, forceset=True)
        if 'EXDATE' in event and timed_event:
            if isinstance(event['EXDATE'],list):
                exdtlist = [ d for dlist in event['EXDATE'] for d in dlist.dts ]
            else:
                exdtlist = event['EXDATE'].dts
            for exd in exdtlist:
                if isinstance(exd.dt,datetime):
                    exdt = exd.dt
                else:
                    exdt = datetime.combine(exd.dt, event_st.time())
                if exdt.tzinfo is None:
                    exdt = exdt.replace(tzinfo=self.LOCAL_TZ)
                rr.exdate(exdt)
        # Convert date limits to datetimes limits for rrule
        dt_st_for_rrule = datetime(dt_st.year, dt_st.month, dt_st.day)
        dt_end_for_rrule = datetime(dt_end.year, dt_end.month, dt_end.day) - timedelta(microseconds=1)
        if timed_event:
            dt_st_for_rrule = dt_st_for_rrule.astimezone(self.LOCAL_TZ) if dt_st_for_rrule.tzinfo else dt_st_for_rrule.replace(tzinfo=self.LOCAL_TZ)
            dt_end_for_rrule = dt_end_for_rrule.astimezone(self.LOCAL_TZ) if dt_end_for_rrule.tzinfo else dt_end_for_rrule.replace(tzinfo=self.LOCAL_TZ)

        from_rrule = rr.between(after=dt_st_for_rrule, before=dt_end_for_rrule, inc=True)

        if hr_min_sec_rep:
            # Convert rrule result back to original timezone
            from_rrule = [d.astimezone(event_tz) if d.tzinfo else d.replace(tzinfo=event_tz) for d in from_rrule]
        if not timed_event:
            from_rrule = [d.date() for d in from_rrule] # convert datetimes to dates

        self.assertEqual(from_reps_in_rng, from_rrule)


# Run all tests if this file is executed as main
if __name__ == '__main__':
    unittest.main()
