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


    def test_yearly_thanksgiving(self) -> None:
        # Create yearly repeating event on weekday of month.
        # Thanksgiving (US) - 4th Thursday of November.
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1942,11,26),
            dt_end = date(1942,11,26), # all day event
            rrule = {'FREQ':['YEARLY'],'BYMONTH':['11'],'BYDAY':['4TH']})

        # Test null periods
        self.check_count(event, date(1941,1,1), date(1942,1,1), 0)
        self.check_count(event, date(1942,1,1), date(1942,11,26), 0)
        self.check_count(event, date(1942,11,27), date(1943,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1942,11,26), date(1942,11,27), 1)
        self.check_count_rrule(event, date(1942,1,1), date(1943,1,1), 1)
        self.check_count_rrule(event, date(1943,1,1), date(1944,1,1), 1)
        self.check_count_rrule(event, date(1944,1,1), date(1945,1,1), 1)
        self.check_count_rrule(event, date(1987,1,1), date(1988,1,1), 1)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 1)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 1)
        self.check_count_rrule(event, date(2050,1,1), date(2051,1,1), 1)
        self.check_count_rrule(event, date(3014,1,1), date(3015,1,1), 1)


    def test_yearly_invalid_day(self) -> None:
        # Create yearly repeating event with a bad BYDAY argument
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2023,4,25),
            rrule = {'FREQ':['YEARLY'],'BYMONTH':['4'],'BYDAY':['4TH','4QX']})

        # Test before start
        self.check_count(event, date(2022,1,1), date(2023,1,1), 0)
        self.check_count(event, date(2023,1,1), date(2023,4,25), 0)

        # First occurence of invalid event
        #self.check_count(event, date(2023,4,25), date(2023,4,26), 1)

        # Test in period raises ValueError
        self.assertRaises(ValueError, repeats_in_range, event, date(2023,4,26), date(2023,4,27))


    def test_yearly_bydayinmonth_timed(self) -> None:
        # Create yearly repeating event on weekday-of-month with time.
        # Also throw in some exdates.
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2002,4,1,14,31),
            rrule = {'FREQ':['YEARLY'],'BYMONTH':['4'],'BYDAY':['1MO']},
            exdates = {datetime(2029,4,2,14,31), date(2008,4,7)})

        # Test null periods
        self.check_count(event, date(2001,1,1), date(2002,1,1), 0)
        self.check_count(event, date(2002,1,1), date(2002,4,1), 0)
        self.check_count(event, date(2002,4,2), date(2003,1,1), 0)
        self.check_count(event, date(2003,1,1), date(2003,4,7), 0)
        self.check_count(event, date(2003,4,8), date(2004,1,1), 0)
        self.check_count(event, date(2008,1,1), date(2009,1,1), 0) # exdate
        self.check_count(event, date(2029,1,1), date(2030,1,1), 0) # exdate

        # Test non-null periods
        self.check_count_rrule(event, date(2002,1,1), date(2003,1,1), 1)
        self.check_count_rrule(event, date(2002,4,1), date(2003,4,2), 1)
        self.check_count_rrule(event, date(2003,1,1), date(2004,1,1), 1)
        self.check_count_rrule(event, date(2003,4,7), date(2003,4,8), 1)
        self.check_count_rrule(event, date(2004,1,1), date(2005,1,1), 1)
        self.check_count_rrule(event, date(2005,1,1), date(2006,1,1), 1)
        self.check_count_rrule(event, date(2006,1,1), date(2007,1,1), 1)
        self.check_count_rrule(event, date(2007,1,1), date(2008,1,1), 1)
        self.check_count_rrule(event, date(2009,1,1), date(2010,1,1), 1)
        self.check_count_rrule(event, date(2030,1,1), date(2031,1,1), 1)


    def test_yearly_bydayinmonth_twice(self) -> None:
        # Create yearly repeating event on two months
        # Thanksgiving (US) - 4th Thursday of November.
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2013,2,12),
            rrule = {'FREQ':['YEARLY'],'BYMONTH':['2','6'],'BYDAY':['2TU']})

        # Test null periods
        self.check_count(event, date(2012,1,1), date(2013,1,1), 0)
        self.check_count(event, date(2013,1,1), date(2013,2,12), 0)
        self.check_count(event, date(2013,2,13), date(2013,6,11), 0)
        self.check_count(event, date(2013,6,12), date(2014,1,1), 0)
        self.check_count(event, date(2014,1,1), date(2014,2,11), 0)
        self.check_count(event, date(2014,2,12), date(2014,6,10), 0)
        self.check_count(event, date(2014,6,11), date(2015,1,1), 0)
        self.check_count(event, date(2016,1,1), date(2016,2,9), 0)
        self.check_count(event, date(2016,2,10), date(2016,6,14), 0)
        self.check_count(event, date(2016,6,15), date(2017,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2013,1,1), date(2014,1,1), 2)
        self.check_count_rrule(event, date(2013,2,12), date(2013,2,13), 1)
        self.check_count_rrule(event, date(2013,6,11), date(2013,6,12), 1)
        self.check_count_rrule(event, date(2014,1,1), date(2015,1,1), 2)
        self.check_count_rrule(event, date(2014,2,11), date(2014,2,12), 1)
        self.check_count_rrule(event, date(2014,6,10), date(2014,6,11), 1)
        self.check_count_rrule(event, date(2016,1,1), date(2017,1,1), 2)
        self.check_count_rrule(event, date(2016,2,9), date(2016,2,10), 1)
        self.check_count_rrule(event, date(2016,6,14), date(2016,6,15), 1)
        self.check_count_rrule(event, date(2023,1,1), date(2024,1,1), 2)
        self.check_count_rrule(event, date(2050,1,1), date(2051,1,1), 2)


    def test_yearly_bydayinmonth_timed_timezone_until(self) -> None:
        # Create bi-annual repeating event on weekday-of-month with time + zone.
        tz_NZ = tz.gettz('Pacific/Auckland')
        self.assertTrue(tz_NZ) # check not None
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1982,11,17,0,16,tzinfo=tz_NZ),
            dt_end = datetime(1982,11,18,0,16,tzinfo=tz_NZ),
            rrule = {'FREQ':['YEARLY'], 'BYMONTH':['11'], 'BYDAY':['-2WE'], 'INTERVAL':[2], 'UNTIL':[datetime(2026,11,18,0,16,tzinfo=tz_NZ)]})

        # Test null periods
        self.check_count(event, date(1980,1,1), date(1981,1,1), 0)
        self.check_count(event, date(1981,1,1), date(1982,1,1), 0)
        self.check_count(event, date(1982,1,1), date(1982,11,16), 0)
        self.check_count(event, date(1982,11,17), date(1983,1,1), 0)
        self.check_count(event, date(1983,1,1), date(1984,1,1), 0)
        self.check_count(event, date(1984,1,1), date(1984,11,20), 0)
        self.check_count(event, date(1984,11,21), date(1985,1,1), 0)
        self.check_count(event, date(1985,1,1), date(1986,1,1), 0)
        self.check_count(event, date(1999,1,1), date(2000,1,1), 0)
        self.check_count(event, date(2001,1,1), date(2002,1,1), 0)
        self.check_count(event, date(2027,1,1), date(2028,1,1), 0)

        # Test non-null periods
        # Note events will seem to fall 1 day ahead of Wednesday, because
        # of timezone (unless test is run in New Zealand/Aus etc...).
        # Not sure of best way to improve this test.
        self.check_count_rrule(event, date(1982,1,1), date(1983,1,1), 1)
        self.check_count_rrule(event, date(1982,11,16), date(1983,11,17), 1)
        self.check_count_rrule(event, date(1984,1,1), date(1985,1,1), 1)
        self.check_count_rrule(event, date(1984,11,20), date(1984,11,21), 1)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 1)
        self.check_count_rrule(event, date(2000,11,21), date(2000,11,22), 1)
        self.check_count_rrule(event, date(2026,1,1), date(2027,1,1), 1)
        self.check_count_rrule(event, date(2026,11,17), date(2026,11,18), 1)


    def test_yearly_bydayinmonth_timed_timezone_count(self) -> None:
        # Create bi-annual repeating event on weekday-of-month with time + zone.
        tz_SAM = tz.gettz('Pacific/Samoa') # UTC-11
        self.assertTrue(tz_SAM) # check not None
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1997,8,9,23,16,tzinfo=tz_SAM),
            rrule = {'FREQ':['YEARLY'], 'BYMONTH':['8'], 'BYDAY':['2SA'], 'INTERVAL':[5], 'COUNT':[20]})

        # Test null periods
        self.check_count(event, date(1996,1,1), date(1997,1,1), 0)
        self.check_count(event, date(1997,1,1), date(1997,8,10), 0)
        self.check_count(event, date(1997,8,11), date(1998,1,1), 0)
        self.check_count(event, date(1998,1,1), date(1999,1,1), 0)
        self.check_count(event, date(1999,1,1), date(2000,1,1), 0)
        self.check_count(event, date(2000,1,1), date(2001,1,1), 0)
        self.check_count(event, date(2001,1,1), date(2002,1,1), 0)
        self.check_count(event, date(2093,1,1), date(2097,1,1), 0)
        self.check_count(event, date(2097,1,1), date(2098,1,1), 0)
        self.check_count(event, date(2098,1,1), date(2150,1,1), 0)

        # Test non-null periods
        # Note events will seem to fall 1 day behind of Saturday, because
        # of timezone (unless test is run in Samoa...).
        # Not sure of best way to improve this test.
        self.check_count_rrule(event, date(1997,1,1), date(1998,1,1), 1)
        self.check_count_rrule(event, date(1997,8,10), date(1997,8,11), 1)
        self.check_count_rrule(event, date(2002,1,1), date(2003,1,1), 1)
        self.check_count_rrule(event, date(2002,8,11), date(2002,8,12), 1)
        self.check_count_rrule(event, date(2007,8,12), date(2007,8,13), 1)
        self.check_count_rrule(event, date(2012,8,12), date(2012,8,13), 1)
        self.check_count_rrule(event, date(2017,8,13), date(2017,8,14), 1)
        self.check_count_rrule(event, date(2022,8,14), date(2022,8,15), 1)
        self.check_count_rrule(event, date(2027,8,15), date(2027,8,16), 1)
        self.check_count_rrule(event, date(2092,1,1), date(2093,1,1), 1)
        self.check_count_rrule(event, date(2092,8,10), date(2092,8,11), 1)


    def test_yearly_bydayinmonth_nonincludedstart(self) -> None:
        # Create yearly byday/month repeat where DTSTART is not a repeat date.
        # According to the spec this should not happen & behaviour is undefined.
        # https://icalendar.org/iCalendar-RFC-5545/3-8-5-3-recurrence-rule.html
        # However, we want to make sure it is detected & rrule module is used.
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2017,3,28), # last Tuesday of March, but repeats are in April!
            rrule = {'FREQ':['YEARLY'],'BYMONTH':['4'],'BYDAY':['-1TU']})

        # Test null periods
        self.check_count(event, date(2016,1,1), date(2017,1,1), 0)
        self.check_count(event, date(2017,1,1), date(2017,3,5), 0)
        self.check_count(event, date(2017,1,1), date(2017,4,1), 0)
        self.check_count(event, date(2017,1,1), date(2017,4,25), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2017,4,25), date(2017,4,26), 1)
        self.check_count_rrule(event, date(2017,4,1), date(2017,5,1), 1)
        self.check_count_rrule(event, date(2017,1,1), date(2018,1,1), 1)
        self.check_count_rrule(event, date(2018,1,1), date(2019,1,1), 1)
        self.check_count_rrule(event, date(2037,1,1), date(2038,1,1), 1)


    def test_yearly_bydayinmonth_starting_gt28(self) -> None:
        # Create repeating event "by last Mon in month" starting >28th
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2017,1,30),
            rrule = {'FREQ':['YEARLY'],'BYMONTH':['1'],'BYDAY':['-1MO']})

        # Test null periods
        self.check_count(event, date(2016,1,1), date(2017,1,1), 0)
        self.check_count(event, date(2017,1,1), date(2017,1,30), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(2017,1,1), date(2018,1,1), 1)
        self.check_count_rrule(event, date(2017,1,30), date(2017,1,31), 1)
        self.check_count_rrule(event, date(2018,1,1), date(2019,1,1), 1)
        self.check_count_rrule(event, date(2018,1,29), date(2018,1,30), 1)
        self.check_count_rrule(event, date(2019,1,1), date(2020,1,1), 1)
        self.check_count_rrule(event, date(2019,1,28), date(2019,1,29), 1)
        self.check_count_rrule(event, date(2020,1,1), date(2021,1,1), 1)
        self.check_count_rrule(event, date(2020,1,27), date(2020,1,28), 1)
        self.check_count_rrule(event, date(2021,1,1), date(2022,1,1), 1)
        self.check_count_rrule(event, date(2021,1,25), date(2021,1,26), 1)
        self.check_count_rrule(event, date(2050,1,1), date(2051,1,1), 1)
        self.check_count_rrule(event, date(2050,1,31), date(2050,2,1), 1)


    def test_yearly_bydayinmonth_fifth(self) -> None:
        # Create tri-yearly repeating event "by 5th Wednesday in month".
        # (This will use the dateutil.rrule module internally.)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2012,5,30,1,5),
            rrule = {'FREQ':['YEARLY'],'BYMONTH':['5'],'BYDAY':['5WE'],'INTERVAL':[3]})

        # Test null periods
        self.check_count(event, date(2008,1,1), date(2012,1,1), 0)
        self.check_count(event, date(2012,1,1), date(2012,5,30), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(2012,1,1), date(2013,1,1), 1)
        self.check_count(event, date(2013,1,1), date(2014,1,1), 0)
        self.check_count(event, date(2014,1,1), date(2015,1,1), 0)
        self.check_count(event, date(2015,1,1), date(2016,1,1), 0)
        self.check_count(event, date(2016,1,1), date(2017,1,1), 0)
        self.check_count(event, date(2017,1,1), date(2018,1,1), 0)
        self.check_count_rrule(event, date(2018,1,1), date(2019,1,1), 1)
        self.check_count(event, date(2019,1,1), date(2020,1,1), 0)
        self.check_count(event, date(2020,1,1), date(2021,1,1), 0)
        self.check_count(event, date(2021,1,1), date(2022,1,1), 0)
        self.check_count(event, date(2022,1,1), date(2023,1,1), 0)
        self.check_count(event, date(2023,1,1), date(2024,1,1), 0)
        self.check_count_rrule(event, date(2024,1,1), date(2025,1,1), 1)
        self.check_count(event, date(2025,1,1), date(2026,1,1), 0)
        self.check_count(event, date(2026,1,1), date(2027,1,1), 0)
        self.check_count(event, date(2027,1,1), date(2028,1,1), 0)
        self.check_count(event, date(2028,1,1), date(2029,1,1), 0)
        self.check_count(event, date(2029,1,1), date(2030,1,1), 0)
        self.check_count_rrule(event, date(2030,1,1), date(2031,1,1), 1)
        self.check_count(event, date(2031,1,1), date(2032,1,1), 0)
        self.check_count(event, date(2032,1,1), date(2033,1,1), 0)
        self.check_count(event, date(2033,1,1), date(2034,1,1), 0)
        self.check_count(event, date(2034,1,1), date(2035,1,1), 0)
        self.check_count(event, date(2035,1,1), date(2036,1,1), 0)
        self.check_count(event, date(2036,1,1), date(2037,1,1), 0)
        self.check_count(event, date(2037,1,1), date(2038,1,1), 0)
        self.check_count(event, date(2038,1,1), date(2039,1,1), 0)
        self.check_count(event, date(2039,1,1), date(2040,1,1), 0)
        self.check_count(event, date(2040,1,1), date(2041,1,1), 0)
        self.check_count(event, date(2041,1,1), date(2042,1,1), 0)
        self.check_count(event, date(2042,1,1), date(2043,1,1), 0)
        self.check_count(event, date(2043,1,1), date(2044,1,1), 0)
        self.check_count(event, date(2044,1,1), date(2045,1,1), 0)
        self.check_count_rrule(event, date(2045,1,1), date(2046,1,1), 1)


    def test_yearly_bydayinmonth_leapday(self) -> None:
        # Create repeating event "by last x in month" starting leapday
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2008,2,29,17,43,2),
            rrule = {'FREQ':['YEARLY'], 'INTERVAL':[3], 'BYMONTH':['2'], 'BYDAY':['-1FR']})

        # Test null periods
        self.check_count(event, date(2000,1,1), date(2008,1,1), 0)
        self.check_count(event, date(2007,1,1), date(2008,1,1), 0)
        self.check_count(event, date(2008,1,1), date(2008,2,29), 0)
        self.check_count(event, date(2008,3,1), date(2009,1,1), 0)
        self.check_count(event, date(2009,1,1), date(2010,1,1), 0)
        self.check_count(event, date(2010,1,1), date(2011,1,1), 0)
        self.check_count(event, date(2011,1,1), date(2011,2,25), 0)
        self.check_count(event, date(2011,2,26), date(2012,1,1), 0)
        self.check_count(event, date(2012,1,1), date(2014,1,1), 0)
        self.check_count(event, date(2014,1,1), date(2014,2,28), 0)
        self.check_count(event, date(2014,3,1), date(2015,1,1), 0)
        self.check_count(event, date(2015,1,1), date(2017,1,1), 0)
        self.check_count(event, date(2017,1,1), date(2017,2,24), 0)
        self.check_count(event, date(2017,2,25), date(2018,1,1), 0)
        self.check_count(event, date(2018,1,1), date(2020,1,1), 0)
        self.check_count(event, date(2020,1,1), date(2020,2,28), 0)
        self.check_count(event, date(2020,2,29), date(2021,1,1), 0)
        self.check_count(event, date(2021,1,1), date(2023,1,1), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(2008,1,1), date(2009,1,1), 1)
        self.check_count_rrule(event, date(2008,2,29), date(2008,3,1), 1)
        self.check_count_rrule(event, date(2011,1,1), date(2012,1,1), 1)
        self.check_count_rrule(event, date(2011,2,25), date(2011,2,26), 1)
        self.check_count_rrule(event, date(2014,1,1), date(2015,1,1), 1)
        self.check_count_rrule(event, date(2014,2,28), date(2014,3,1), 1)
        self.check_count_rrule(event, date(2017,1,1), date(2018,1,1), 1)
        self.check_count_rrule(event, date(2017,2,24), date(2017,2,25), 1)
        self.check_count_rrule(event, date(2020,1,1), date(2021,1,1), 1)
        self.check_count_rrule(event, date(2020,2,28), date(2020,2,29), 1)


    def test_yearly_dayinyear_lt5(self) -> None:
        # Yearly repeat by second Saturday in year
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2015,1,10),
            rrule = {'FREQ':['YEARLY'], 'BYDAY':['2SA']})

        # Test null periods
        self.check_count(event, date(2014,1,1), date(2015,1,1), 0)
        self.check_count(event, date(2015,1,1), date(2015,1,10), 0)
        self.check_count(event, date(2015,1,11), date(2016,1,1), 0)
        self.check_count(event, date(2025,2,1), date(2026,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2015,1,1), date(2016,1,1), 1)
        self.check_count_rrule(event, date(2015,1,10), date(2015,1,11), 1)
        self.check_count_rrule(event, date(2016,1,1), date(2017,1,1), 1)
        self.check_count_rrule(event, date(2016,1,9), date(2016,1,10), 1)
        self.check_count_rrule(event, date(2017,1,1), date(2018,1,1), 1)
        self.check_count_rrule(event, date(2017,1,14), date(2017,1,15), 1)
        self.check_count_rrule(event, date(2025,1,1), date(2026,1,1), 1)
        self.check_count_rrule(event, date(2025,1,11), date(2025,1,12), 1)


    def test_yearly_dayinyear_gt5(self) -> None:
        # Yearly repeat by ninth Tuesday in year (to check >5 works)
        # Note: >=10 seems to hit a bug in icalendar module (v4.0.9)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2015,3,3),
            rrule = {'FREQ':['YEARLY'], 'BYDAY':['9TU']})

        # Test null periods
        self.check_count(event, date(2014,1,1), date(2015,1,1), 0)
        self.check_count(event, date(2015,1,1), date(2015,3,3), 0)
        self.check_count(event, date(2015,3,4), date(2016,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2015,1,1), date(2016,1,1), 1)
        self.check_count_rrule(event, date(2015,3,3), date(2015,3,4), 1)
        self.check_count_rrule(event, date(2016,1,1), date(2017,1,1), 1)
        self.check_count_rrule(event, date(2016,3,1), date(2016,3,2), 1)
        self.check_count_rrule(event, date(2017,1,1), date(2018,1,1), 1)
        self.check_count_rrule(event, date(2017,2,28), date(2017,3,1), 1)
        self.check_count_rrule(event, date(2018,1,1), date(2019,1,1), 1)
        self.check_count_rrule(event, date(2018,2,27), date(2018,2,28), 1)
        self.check_count_rrule(event, date(2025,1,1), date(2026,1,1), 1)
        self.check_count_rrule(event, date(2025,3,4), date(2025,3,5), 1)


    def test_yearly_us_presidential_elections(self) -> None:
        # Four-yearly repeat by Tuesday following first Mon in November
        # Example from RFC:
        # https://icalendar.org/iCalendar-RFC-5545/3-8-5-3-recurrence-rule.html
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1996,11,5),
            rrule = {'FREQ':['YEARLY'], 'INTERVAL':[4], 'BYMONTH':['11'], 'BYDAY':['TU'], 'BYMONTHDAY':['2','3','4','5','6','7','8']})

        # Test null periods
        self.check_count(event, date(1995,1,1), date(1996,1,1), 0)
        self.check_count(event, date(1997,1,1), date(2000,1,1), 0)
        self.check_count(event, date(2001,1,1), date(2004,1,1), 0)
        self.check_count(event, date(2005,1,1), date(2008,1,1), 0)
        self.check_count(event, date(2009,1,1), date(2012,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1996,1,1), date(1997,1,1), 1)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 1)
        self.check_count_rrule(event, date(2004,1,1), date(2005,1,1), 1)
        self.check_count_rrule(event, date(2008,1,1), date(2009,1,1), 1)
        self.check_count_rrule(event, date(2012,1,1), date(2013,1,1), 1)


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


    def test_monthly_biginterval(self) -> None:
        # Create monthly repeating event with big interval not divisible by 12
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1999,4,20),
            rrule = {'FREQ':['MONTHLY'],'INTERVAL':[35]})

        # Test null periods
        self.check_count(event, date(1995,1,1), date(1999,1,1), 0)
        self.check_count(event, date(1999,1,1), date(1999,4,20), 0)
        self.check_count(event, date(1999,4,21), date(2000,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1999,4,20), date(1999,4,21), 1)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 1)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 0)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 0)
        self.check_count_rrule(event, date(2002,1,1), date(2003,1,1), 1)
        self.check_count_rrule(event, date(2002,3,20), date(2002,3,21), 1)
        self.check_count_rrule(event, date(2003,1,1), date(2004,1,1), 0)
        self.check_count_rrule(event, date(2004,1,1), date(2005,1,1), 0)
        self.check_count_rrule(event, date(2005,1,1), date(2006,1,1), 1)
        self.check_count_rrule(event, date(2005,2,20), date(2005,2,21), 1)
        self.check_count_rrule(event, date(2006,1,1), date(2007,1,1), 0)
        self.check_count_rrule(event, date(2007,1,1), date(2008,1,1), 0)
        self.check_count_rrule(event, date(2008,1,1), date(2009,1,1), 1)
        self.check_count_rrule(event, date(2008,1,20), date(2008,1,21), 1)
        self.check_count_rrule(event, date(2009,1,1), date(2010,1,1), 0)
        self.check_count_rrule(event, date(2010,1,1), date(2011,1,1), 1)
        self.check_count_rrule(event, date(2010,12,20), date(2010,12,21), 1)


    def test_monthly_biginterval_29th(self) -> None:
        # Create monthly repeating event with big interval falling on 29th
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1999,4,29),
            rrule = {'FREQ':['MONTHLY'],'INTERVAL':[35]})

        # Test null periods
        self.check_count(event, date(1995,1,1), date(1999,1,1), 0)
        self.check_count(event, date(1999,1,1), date(1999,4,29), 0)
        self.check_count(event, date(1999,4,30), date(2000,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1999,4,29), date(1999,4,30), 1)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 1)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 0)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 0)
        self.check_count_rrule(event, date(2002,1,1), date(2003,1,1), 1)
        self.check_count_rrule(event, date(2002,3,29), date(2002,3,30), 1)
        self.check_count_rrule(event, date(2003,1,1), date(2004,1,1), 0)
        self.check_count_rrule(event, date(2004,1,1), date(2005,1,1), 0)
        self.check_count_rrule(event, date(2005,1,1), date(2006,1,1), 0) # Feb
        self.check_count_rrule(event, date(2006,1,1), date(2007,1,1), 0)
        self.check_count_rrule(event, date(2007,1,1), date(2008,1,1), 0)
        self.check_count_rrule(event, date(2008,1,1), date(2009,1,1), 1)
        self.check_count_rrule(event, date(2008,1,29), date(2008,1,30), 1)
        self.check_count_rrule(event, date(2009,1,1), date(2010,1,1), 0)
        self.check_count_rrule(event, date(2010,1,1), date(2011,1,1), 1)
        self.check_count_rrule(event, date(2010,12,29), date(2010,12,30), 1)


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


    def test_monthly_byday(self) -> None:
        # Create monthly repeating event "by 2nd to last Friday"
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1959,2,20),
            rrule = {'FREQ':['MONTHLY'],'BYDAY':['-2FR']})

        # Test null periods
        self.check_count(event, date(1958,1,1), date(1959,1,1), 0)
        self.check_count(event, date(1959,1,1), date(1959,2,1), 0)
        self.check_count(event, date(1959,2,1), date(1959,2,20), 0)
        self.check_count(event, date(1959,2,21), date(1959,3,20), 0)
        self.check_count(event, date(1959,3,21), date(1959,4,17), 0)
        self.check_count(event, date(1959,4,18), date(1959,4,22), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1959,2,1), date(1959,3,1), 1)
        self.check_count_rrule(event, date(1959,2,20), date(1959,2,21), 1)
        self.check_count_rrule(event, date(1959,3,20), date(1959,3,21), 1)
        self.check_count_rrule(event, date(1959,4,17), date(1959,4,18), 1)
        self.check_count_rrule(event, date(1959,5,22), date(1959,5,23), 1)
        self.check_count_rrule(event, date(1959,1,1), date(1960,1,1), 11)
        self.check_count_rrule(event, date(1960,1,1), date(1961,1,1), 12)
        self.check_count_rrule(event, date(2020,1,1), date(2021,1,1), 12)
        self.check_count_rrule(event, date(2080,1,1), date(2081,1,1), 12)


    def test_monthly_byday_nonincludedstart(self) -> None:
        # Create monthly byday repeat where DTSTART is not a repeat date.
        # According to the spec this should not happen & behaviour is undefined.
        # https://icalendar.org/iCalendar-RFC-5545/3-8-5-3-recurrence-rule.html
        # However, we want to make sure it is detected & rrule module is used.
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1959,2,21), # Saturday!
            rrule = {'FREQ':['MONTHLY'],'BYDAY':['-2FR']})

        # Test null periods
        self.check_count(event, date(1958,1,1), date(1959,1,1), 0)
        self.check_count(event, date(1959,1,1), date(1959,3,20), 0)
        self.check_count(event, date(1959,2,20), date(1959,2,21), 0)
        self.check_count(event, date(1959,2,21), date(1959,2,22), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1959,3,20), date(1959,3,21), 1)
        self.check_count_rrule(event, date(1959,4,17), date(1959,4,18), 1)
        self.check_count_rrule(event, date(1959,5,22), date(1959,5,23), 1)
        self.check_count_rrule(event, date(1959,1,1), date(1960,1,1), 10)
        self.check_count_rrule(event, date(1960,1,1), date(1961,1,1), 12)
        self.check_count_rrule(event, date(2023,1,1), date(2024,1,1), 12)


    def test_monthly_byday_multiday(self) -> None:
        # Create monthly repeating event "by last Sunday"
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2029,7,29),
            dt_end = date(2029,8,2), # 4 days extending into next month
            rrule = {'FREQ':['MONTHLY'],'BYDAY':['-1SU']})

        # Test null periods
        self.check_count(event, date(2028,1,1), date(2029,1,1), 0)
        self.check_count(event, date(2029,1,1), date(2029,7,29), 0)
        self.check_count(event, date(2029,7,30), date(2029,8,26), 0)
        self.check_count(event, date(2029,8,27), date(2029,9,30), 0)
        self.check_count(event, date(2029,10,1), date(2029,10,28), 0)
        self.check_count(event, date(2029,12,31), date(2030,1,27), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2029,7,1), date(2029,8,1), 1)
        self.check_count_rrule(event, date(2029,7,29), date(2029,7,30), 1)
        self.check_count_rrule(event, date(2029,8,1), date(2029,9,1), 1)
        self.check_count_rrule(event, date(2029,8,26), date(2029,8,27), 1)
        self.check_count_rrule(event, date(2029,9,1), date(2029,10,1), 1)
        self.check_count_rrule(event, date(2029,9,30), date(2029,10,1), 1)
        self.check_count_rrule(event, date(2029,10,1), date(2029,11,1), 1)
        self.check_count_rrule(event, date(2029,10,28), date(2029,10,29), 1)
        self.check_count_rrule(event, date(2029,1,1), date(2030,1,1), 6)
        self.check_count_rrule(event, date(2030,1,1), date(2031,1,1), 12)
        self.check_count_rrule(event, date(2121,1,1), date(2122,1,1), 12)


    def test_monthly_byday_timed(self) -> None:
        # Create bi-monthly repeating event "by 2nd to last Monday" with time
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2001,3,19,14,28),
            rrule = {'FREQ':['MONTHLY'],'INTERVAL':[2],'BYDAY':['-2MO']})

        # Test null periods
        self.check_count(event, date(2000,1,1), date(2001,1,1), 0)
        self.check_count(event, date(2001,1,1), date(2001,3,19), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(2001,3,19), date(2001,3,20), 1)
        self.check_count(event, date(2001,3,20), date(2001,5,21), 0)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 5)
        self.check_count_rrule(event, date(2002,1,1), date(2003,1,1), 6)
        self.check_count_rrule(event, date(2050,1,1), date(2051,1,1), 6)
        self.check_count_rrule(event, date(2050,7,18), date(2050,7,19), 1)
        self.check_count(event, date(2050,7,19), date(2050,9,19), 0)
        self.check_count_rrule(event, date(2050,9,19), date(2050,9,20), 1)


    def test_monthly_byday_timed_duration(self) -> None:
        # Create monthly repeating event "byday" with time + duration
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2010,6,17,23,30),
            dt_end = datetime(2010,6,18,1,30),
            rrule = {'FREQ':['MONTHLY'],'BYDAY':['3TH']})

        # Test null periods
        self.check_count(event, date(2009,1,1), date(2010,1,1), 0)
        self.check_count(event, date(2010,1,1), date(2010,6,17), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(2010,1,1), date(2011,1,1), 7)
        self.check_count_rrule(event, date(2010,6,17), date(2010,6,18), 1)
        self.check_count(event, date(2010,6,18), date(2010,7,15), 0)
        self.check_count_rrule(event, date(2010,7,15), date(2010,7,16), 1)
        self.check_count(event, date(2010,7,16), date(2010,8,19), 0)
        self.check_count_rrule(event, date(2010,8,19), date(2010,8,20), 1)
        self.check_count_rrule(event, date(2010,9,16), date(2010,9,17), 1)
        self.check_count_rrule(event, date(2010,10,21), date(2010,10,22), 1)
        self.check_count_rrule(event, date(2010,11,18), date(2010,11,19), 1)
        self.check_count_rrule(event, date(2010,12,16), date(2010,12,17), 1)
        self.check_count_rrule(event, date(2011,1,1), date(2012,1,1), 12)
        self.check_count_rrule(event, date(2011,1,20), date(2011,1,21), 1)
        self.check_count_rrule(event, date(2012,1,1), date(2013,1,1), 12)
        self.check_count_rrule(event, date(2013,1,1), date(2014,1,1), 12)
        self.check_count_rrule(event, date(2114,1,1), date(2115,1,1), 12)
        self.check_count_rrule(event, date(2114,1,18), date(2114,1,19), 1)
        self.check_count_rrule(event, date(2114,2,15), date(2114,2,16), 1)
        self.check_count_rrule(event, date(2114,3,15), date(2114,3,16), 1)
        self.check_count_rrule(event, date(2114,4,19), date(2114,4,20), 1)
        self.check_count_rrule(event, date(2114,5,17), date(2114,5,18), 1)
        self.check_count_rrule(event, date(2114,6,21), date(2114,6,22), 1)


    def test_monthly_byday_timed_timezone(self) -> None:
        # Create tri-monthly repeating event "by 2nd Thursday" with time+zone
        tz_AD = tz.gettz('Australia/Adelaide')
        self.assertTrue(tz_AD) # check not None
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1986,12,11,1,28, tzinfo=tz_AD),
            rrule = {'FREQ':['MONTHLY'],'INTERVAL':[3],'BYDAY':['2TH']})

        # Test null periods
        self.check_count(event, date(1986,1,1), date(1986,12,10), 0)
        self.check_count(event, date(1986,12,11), date(1987,1,1), 0)

        # Test periods within the repeat time
        # Note events will seem to fall 1 day ahead of Thursday, because
        # of timezone (unless test is run in Australia/NZ etc...).
        # Not sure of best way to improve this test.
        self.check_count_rrule(event, date(1986,1,1), date(1987,1,1), 1)
        self.check_count_rrule(event, date(1986,12,10), date(1986,12,11), 1)
        self.check_count(event, date(1986,12,11), date(1987,3,11), 0)
        self.check_count_rrule(event, date(1987,1,1), date(1988,1,1), 4)
        self.check_count_rrule(event, date(1987,3,11), date(1987,3,12), 1)
        self.check_count_rrule(event, date(1987,6,10), date(1987,6,11), 1)
        self.check_count_rrule(event, date(1987,9,9), date(1987,9,10), 1)
        self.check_count_rrule(event, date(1987,12,9), date(1987,12,10), 1)
        self.check_count_rrule(event, date(1988,1,1), date(1989,1,1), 4)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 4)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 4)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 4)
        self.check_count_rrule(event, date(2038,1,1), date(2039,1,1), 4)
        self.check_count_rrule(event, date(2038,3,10), date(2038,3,11), 1)
        self.check_count_rrule(event, date(2038,6,9), date(2038,6,10), 1)
        self.check_count_rrule(event, date(2038,9,8), date(2038,9,9), 1)
        self.check_count_rrule(event, date(2038,12,8), date(2038,12,9), 1)


    def test_monthly_byday_count(self) -> None:
        # Create monthly repeating event "by 3rd Thursday" with count
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2020,1,16),
            rrule = {'FREQ':['MONTHLY'],'BYDAY':['3TH'],'COUNT':[5]})

        # Test null periods
        self.check_count(event, date(2019,1,1), date(2020,1,1), 0)
        self.check_count(event, date(2020,1,1), date(2020,1,16), 0)
        self.check_count(event, date(2020,5,22), date(2021,1,1), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(2020,1,16), date(2020,1,17), 1)
        self.check_count(event, date(2020,1,17), date(2020,2,20), 0)
        self.check_count_rrule(event, date(2020,2,20), date(2020,2,21), 1)
        self.check_count(event, date(2020,2,21), date(2020,3,19), 0)
        self.check_count_rrule(event, date(2020,3,19), date(2020,3,20), 1)
        self.check_count(event, date(2020,3,20), date(2020,4,16), 0)
        self.check_count_rrule(event, date(2020,4,16), date(2020,4,17), 1)
        self.check_count(event, date(2020,4,17), date(2020,5,21), 0)
        self.check_count_rrule(event, date(2020,5,21), date(2020,5,22), 1)
        self.check_count_rrule(event, date(2020,1,1), date(2021,1,1), 5)


    def test_monthly_byday_timed_count(self) -> None:
        # Create timed bi-monthly repeating event "by last Sunday" with count
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2027,4,25,23,59), # minute to midnight
            rrule = {'FREQ':['MONTHLY'],'INTERVAL':[2],'BYDAY':['-1SU'],'COUNT':[22]})

        # Test null periods
        self.check_count(event, date(2026,1,1), date(2027,1,1), 0)
        self.check_count(event, date(2027,1,1), date(2027,4,25), 0)
        self.check_count(event, date(2030,10,28), date(2031,1,1), 0)
        self.check_count(event, date(2031,1,1), date(2032,1,1), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(2027,1,1), date(2028,1,1), 5)
        self.check_count_rrule(event, date(2028,1,1), date(2029,1,1), 6)
        self.check_count_rrule(event, date(2029,1,1), date(2030,1,1), 6)
        self.check_count_rrule(event, date(2030,1,1), date(2031,1,1), 5)
        self.check_count_rrule(event, date(2027,4,25), date(2027,4,26), 1)
        self.check_count(event, date(2027,4,26), date(2027,6,27), 0)
        self.check_count_rrule(event, date(2027,6,27), date(2027,6,28), 1)
        self.check_count_rrule(event, date(2028,4,30), date(2028,5,1), 1)
        self.check_count_rrule(event, date(2030,8,25), date(2030,8,26), 1)
        self.check_count(event, date(2030,8,26), date(2030,10,27), 0)
        self.check_count_rrule(event, date(2030,10,27), date(2030,10,28), 1)


    def test_monthly_byday_until(self) -> None:
        # Create 5-monthly repeating event "by 2nd last Monday" with until.
        # Put an exdate in too, to make sure they work with custom iterator.
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1998,4,20),
            rrule = {'FREQ':['MONTHLY'],'INTERVAL':[5],'BYDAY':['-2MO'],'UNTIL':[date(2003,4,21)]},
            exdates = {date(2001,8,20)}
            )

        # Test null periods
        self.check_count(event, date(1997,1,1), date(1998,1,1), 0)
        self.check_count(event, date(1998,1,1), date(1998,4,20), 0)
        self.check_count(event, date(2003,4,22), date(2004,1,1), 0)
        self.check_count(event, date(2004,1,1), date(2005,1,1), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(1998,4,20), date(1998,4,21), 1)
        self.check_count(event, date(1998,4,21), date(1998,9,21), 0)
        self.check_count_rrule(event, date(1998,9,21), date(1998,9,22), 1)
        self.check_count(event, date(1998,9,22), date(1999,2,15), 0)
        self.check_count_rrule(event, date(1999,2,15), date(1999,2,16), 1)
        self.check_count(event, date(1999,2,16), date(1999,7,19), 0)
        self.check_count_rrule(event, date(1999,7,19), date(1999,7,20), 1)
        self.check_count_rrule(event, date(1998,1,1), date(1999,1,1), 2)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 3)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 2)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 1)#Ma,[Au]
        self.check_count_rrule(event, date(2002,1,1), date(2003,1,1), 3)#Ja,Ju,No
        self.check_count_rrule(event, date(2003,1,1), date(2004,1,1), 1)
        self.check_count(event, date(2003,1,1), date(2003,4,21), 0)
        self.check_count_rrule(event, date(2003,4,21), date(2003,4,22), 1)


    def test_monthly_byday_timed_until(self) -> None:
        # Create monthly timed repeating event "by 1st Sunday" with until
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(2013,10,6,10,15),
            rrule = {'FREQ':['MONTHLY'],'BYDAY':['1SU'],'UNTIL':[datetime(2015,10,4,10,15)]})

        # Test null periods
        self.check_count(event, date(2013,1,1), date(2013,10,6), 0)
        self.check_count(event, date(2013,9,29), date(2013,10,6), 0)
        self.check_count(event, date(2013,10,7), date(2013,11,3), 0)
        self.check_count(event, date(2015,10,5), date(2016,1,1), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(2013,1,1), date(2014,1,1), 3)
        self.check_count_rrule(event, date(2014,1,1), date(2015,1,1), 12)
        self.check_count_rrule(event, date(2015,1,1), date(2016,1,1), 10)
        self.check_count_rrule(event, date(2013,10,6), date(2013,10,7), 1)
        self.check_count_rrule(event, date(2013,9,30), date(2013,10,7), 1)
        self.check_count_rrule(event, date(2013,10,1), date(2013,10,8), 1)
        self.check_count_rrule(event, date(2013,10,2), date(2013,10,9), 1)
        self.check_count_rrule(event, date(2013,10,3), date(2013,10,10), 1)
        self.check_count_rrule(event, date(2013,10,4), date(2013,10,11), 1)
        self.check_count_rrule(event, date(2013,10,5), date(2013,10,12), 1)
        self.check_count_rrule(event, date(2013,10,6), date(2013,10,13), 1)
        self.check_count(event, date(2013,10,7), date(2013,10,14), 0)
        self.check_count_rrule(event, date(2013,11,3), date(2013,11,4), 1)
        self.check_count(event, date(2013,10,27), date(2013,11,3), 0)
        self.check_count_rrule(event, date(2013,10,28), date(2013,11,4), 1)
        self.check_count_rrule(event, date(2013,10,29), date(2013,11,5), 1)
        self.check_count_rrule(event, date(2013,10,30), date(2013,11,6), 1)
        self.check_count_rrule(event, date(2013,10,31), date(2013,11,7), 1)
        self.check_count_rrule(event, date(2013,11,1), date(2013,11,8), 1)
        self.check_count_rrule(event, date(2013,11,2), date(2013,11,9), 1)
        self.check_count_rrule(event, date(2013,11,3), date(2013,11,10), 1)
        self.check_count(event, date(2013,11,4), date(2013,11,11), 0)
        self.check_count_rrule(event, date(2013,12,1), date(2013,12,2), 1)
        self.check_count(event, date(2013,11,4), date(2013,12,1), 0)
        self.check_count_rrule(event, date(2013,11,25), date(2013,12,2), 1)
        self.check_count_rrule(event, date(2013,11,26), date(2013,12,3), 1)
        self.check_count_rrule(event, date(2013,11,27), date(2013,12,4), 1)
        self.check_count_rrule(event, date(2013,11,28), date(2013,12,5), 1)
        self.check_count_rrule(event, date(2013,11,29), date(2013,12,6), 1)
        self.check_count_rrule(event, date(2013,11,30), date(2013,12,7), 1)
        self.check_count_rrule(event, date(2013,12,1), date(2013,12,8), 1)
        self.check_count(event, date(2013,12,2), date(2013,12,9), 0)
        self.check_count_rrule(event, date(2015,9,6), date(2015,9,7), 1)
        self.check_count(event, date(2015,8,30), date(2015,9,6), 0)
        self.check_count_rrule(event, date(2015,8,31), date(2015,9,7), 1)
        self.check_count_rrule(event, date(2015,9,1), date(2015,9,8), 1)
        self.check_count_rrule(event, date(2015,9,2), date(2015,9,9), 1)
        self.check_count_rrule(event, date(2015,9,3), date(2015,9,10), 1)
        self.check_count_rrule(event, date(2015,9,4), date(2015,9,11), 1)
        self.check_count_rrule(event, date(2015,9,5), date(2015,9,12), 1)
        self.check_count_rrule(event, date(2015,9,6), date(2015,9,13), 1)
        self.check_count(event, date(2015,9,7), date(2015,9,14), 0)
        self.check_count_rrule(event, date(2015,10,4), date(2015,10,5), 1)
        self.check_count(event, date(2015,9,27), date(2015,10,4), 0)
        self.check_count_rrule(event, date(2015,9,28), date(2015,10,5), 1)
        self.check_count_rrule(event, date(2015,9,29), date(2015,10,6), 1)
        self.check_count_rrule(event, date(2015,9,30), date(2015,10,7), 1)
        self.check_count_rrule(event, date(2015,10,1), date(2015,10,8), 1)
        self.check_count_rrule(event, date(2015,10,2), date(2015,10,9), 1)
        self.check_count_rrule(event, date(2015,10,3), date(2015,10,10), 1)
        self.check_count_rrule(event, date(2015,10,4), date(2015,10,11), 1)
        self.check_count(event, date(2015,10,5), date(2015,10,12), 0)


    def test_monthly_byday_starting_gt28(self) -> None:
        # Create repeating event "by last Friday in month" starting >28th
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2014,5,30),
            rrule = {'FREQ':['MONTHLY'],'BYDAY':['-1FR']})

        # Test null periods
        self.check_count(event, date(2013,1,1), date(2014,1,1), 0)
        self.check_count(event, date(2014,1,1), date(2014,5,30), 0)
        self.check_count(event, date(2014,5,31), date(2014,6,27), 0)
        self.check_count(event, date(2143,1,26), date(2143,2,22), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(2014,5,30), date(2014,5,31), 1)
        self.check_count_rrule(event, date(2014,6,27), date(2014,6,28), 1)
        self.check_count_rrule(event, date(2014,1,1), date(2015,1,1), 8)
        self.check_count_rrule(event, date(2014,1,1), date(2015,1,1), 8)
        self.check_count_rrule(event, date(2014,1,1), date(2015,1,1), 8)
        self.check_count_rrule(event, date(2015,1,1), date(2016,1,1), 12)
        self.check_count_rrule(event, date(2143,1,1), date(2144,1,1), 12)
        self.check_count_rrule(event, date(2143,1,25), date(2143,1,26), 1)
        self.check_count_rrule(event, date(2143,2,22), date(2143,2,23), 1)
        self.check_count_rrule(event, date(2143,3,29), date(2143,3,30), 1)


    def test_monthly_byday_fifth(self) -> None:
        # Create bi-monthly repeating event "by 5th Friday in month".
        # (This will use the dateutil.rrule module internally.)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1998,10,30),
            rrule = {'FREQ':['MONTHLY'],'BYDAY':['5FR'],'INTERVAL':[2]})

        # Test null periods
        self.check_count(event, date(1997,1,1), date(1998,1,1), 0)
        self.check_count(event, date(1998,1,1), date(1998,10,30), 0)
        self.check_count(event, date(1998,10,31), date(1999,1,1), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(1998,10,30), date(1998,10,31), 1)
        self.check_count_rrule(event, date(1998,1,1), date(1999,1,1), 1)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 3)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 2)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 2)
        self.check_count_rrule(event, date(2002,1,1), date(2003,1,1), 1)
        self.check_count_rrule(event, date(2003,1,1), date(2004,1,1), 2)
        self.check_count_rrule(event, date(2004,1,1), date(2005,1,1), 3)
        self.check_count_rrule(event, date(2008,2,1), date(2008,3,1), 1) # Feb


    def test_monthly_byday_fifthlast(self) -> None:
        # Create monthly repeating event "by 5th last Monday in month".
        # (This will use the dateutil.rrule module internally.)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2015,8,3),
            rrule = {'FREQ':['MONTHLY'],'BYDAY':['-5MO']})

        # Test null periods
        self.check_count(event, date(2014,1,1), date(2015,1,1), 0)
        self.check_count(event, date(2015,1,1), date(2015,8,3), 0)
        self.check_count(event, date(2015,8,4), date(2015,11,2), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(2015,8,3), date(2015,8,4), 1)
        self.check_count_rrule(event, date(2015,11,2), date(2015,11,3), 1)
        self.check_count_rrule(event, date(2015,1,1), date(2016,1,1), 2)
        self.check_count_rrule(event, date(2016,1,1), date(2017,1,1), 4)
        self.check_count_rrule(event, date(2017,1,1), date(2018,1,1), 4)
        self.check_count_rrule(event, date(2018,1,1), date(2019,1,1), 5)
        self.check_count_rrule(event, date(2019,1,1), date(2020,1,1), 4)
        self.check_count_rrule(event, date(2020,1,1), date(2021,1,1), 4)
        self.check_count_rrule(event, date(2021,1,1), date(2022,1,1), 4)
        self.check_count_rrule(event, date(2022,1,1), date(2023,1,1), 4)
        self.check_count_rrule(event, date(2023,1,1), date(2024,1,1), 4)
        self.check_count_rrule(event, date(2024,1,1), date(2025,1,1), 5)


    def test_monthly_byday_leapday(self) -> None:
        # Create repeating event "by last x in month" starting leapday
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1992,2,29),
            rrule = {'FREQ':['MONTHLY'], 'INTERVAL':[5], 'BYDAY':['-1SA']})

        # Test null periods
        self.check_count(event, date(1988,1,1), date(1992,1,1), 0)
        self.check_count(event, date(1992,1,1), date(1992,2,29), 0)
        self.check_count(event, date(1992,3,1), date(1992,7,25), 0)
        self.check_count(event, date(1992,7,26), date(1992,12,26), 0)

        # Test periods within the repeat time
        self.check_count_rrule(event, date(1992,1,1), date(1993,1,1), 3)
        self.check_count_rrule(event, date(1992,2,29), date(1992,3,1), 1)
        self.check_count_rrule(event, date(1992,7,25), date(1992,7,26), 1)
        self.check_count_rrule(event, date(1992,12,26), date(1992,12,27), 1)
        self.check_count_rrule(event, date(1993,1,1), date(1994,1,1), 2)
        self.check_count_rrule(event, date(1994,1,1), date(1995,1,1), 2)
        self.check_count_rrule(event, date(1995,1,1), date(1996,1,1), 3)
        self.check_count_rrule(event, date(1996,1,1), date(1997,1,1), 2)
        self.check_count_rrule(event, date(1997,1,1), date(1998,1,1), 3)
        self.check_count_rrule(event, date(1998,1,1), date(1999,1,1), 2)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 2)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 3)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 2)
        self.check_count_rrule(event, date(2002,1,1), date(2003,1,1), 3)
        self.check_count_rrule(event, date(2002,2,23), date(2002,2,24), 1)
        self.check_count_rrule(event, date(2002,7,27), date(2002,7,28), 1)
        self.check_count_rrule(event, date(2002,12,28), date(2002,12,29), 1)
        self.check_count_rrule(event, date(2003,1,1), date(2004,1,1), 2)


    def test_monthly_tuesdaysinmonth(self) -> None:
        # Use monthly/byday to repeat on all Tuesdays every other month
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(1996,11,5),
            rrule = {'FREQ':['MONTHLY'], 'INTERVAL':[2], 'BYDAY':['TU']})

        # Test null periods
        self.check_count(event, date(1995,1,1), date(1996,1,1), 0)
        self.check_count(event, date(1996,1,1), date(1996,11,5), 0)
        self.check_count(event, date(1996,12,1), date(1997,1,1), 0)
        self.check_count(event, date(1997,2,1), date(1997,3,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(1996,1,1), date(1997,1,1), 4)
        self.check_count_rrule(event, date(1996,11,1), date(1996,12,1), 4)
        self.check_count_rrule(event, date(1996,11,1), date(1996,11,8), 1)
        self.check_count_rrule(event, date(1997,1,1), date(1998,1,1), 26)
        self.check_count_rrule(event, date(1998,1,1), date(1999,1,1), 26)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 26)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 25)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 27)
        self.check_count_rrule(event, date(2002,1,1), date(2003,1,1), 26)


    def test_monthly_friday13th(self) -> None:
        # Create monthly/byday to repeat every Friday 13th
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2000,10,13),
            rrule = {'FREQ':['MONTHLY'], 'BYMONTHDAY':['13'], 'BYDAY':['FR']})

        # Test null periods
        self.check_count(event, date(1999,1,1), date(2000,1,1), 0)
        self.check_count(event, date(2000,1,1), date(2000,10,13), 0)
        self.check_count(event, date(2000,10,14), date(2001,1,1), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 1)
        self.check_count_rrule(event, date(2000,10,13), date(2000,10,14), 1)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 2)
        self.check_count_rrule(event, date(2001,4,13), date(2001,4,14), 1)
        self.check_count_rrule(event, date(2001,7,13), date(2001,7,14), 1)
        self.check_count_rrule(event, date(2002,1,1), date(2003,1,1), 2)
        self.check_count_rrule(event, date(2003,1,1), date(2004,1,1), 1)
        self.check_count_rrule(event, date(2004,1,1), date(2005,1,1), 2)
        self.check_count_rrule(event, date(2005,1,1), date(2006,1,1), 1)
        self.check_count_rrule(event, date(2006,1,1), date(2007,1,1), 2)
        self.check_count_rrule(event, date(2007,1,1), date(2008,1,1), 2)
        self.check_count_rrule(event, date(2008,1,1), date(2009,1,1), 1)
        self.check_count_rrule(event, date(2009,1,1), date(2010,1,1), 3)
        self.check_count_rrule(event, date(2010,1,1), date(2011,1,1), 1)
        self.check_count_rrule(event, date(2011,1,1), date(2012,1,1), 1)


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


    def test_weekly_timed(self) -> None:
        # Create weekly repeating event at midnight
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            datetime(1950,4,19,0,0), # Midnight
            rrule = {'FREQ':['WEEKLY']})

        # Test null periods
        self.check_count(event, date(1949,1,1), date(1950,1,1), 0)
        self.check_count(event, date(1950,1,1), date(1950,4,19), 0)
        self.check_count(event, date(1950,4,20), date(1950,4,26), 0)

        # Test some non-null periods
        self.check_count_rrule(event, date(1950,1,1), date(1951,1,1), 37)
        self.check_count_rrule(event, date(1951,1,1), date(1952,1,1), 52)
        self.check_count_rrule(event, date(1999,1,1), date(2000,1,1), 52)
        self.check_count_rrule(event, date(2000,1,1), date(2001,1,1), 52)
        self.check_count_rrule(event, date(2049,1,1), date(2050,1,1), 52)
        self.check_count_rrule(event, date(2050,1,1), date(2051,1,1), 52)
        self.check_count_rrule(event, date(5050,1,1), date(5051,1,1), 52)


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


    def test_weekly_invalid_day(self) -> None:
        # Create weekly repeating event with a bad BYDAY argument
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2023,4,25),
            rrule = {'FREQ':['WEEKLY'], 'BYDAY':['TU','QX']})

        # Test before start
        self.check_count(event, date(2022,1,1), date(2023,1,1), 0)
        self.check_count(event, date(2023,1,1), date(2023,4,25), 0)

        # First occurence of invalid event
        #self.check_count(event, date(2023,4,25), date(2023,4,26), 1)

        # Test in period raises ValueError
        self.assertRaises(ValueError, repeats_in_range, event, date(2023,4,26), date(2023,4,27))


    def test_weekly_thrice_exdate(self) -> None:
        # Create thrice biweekly repeating event with exception dates
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2024,2,15),
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
        self.check_count(event, date(2000,1,1), date(2000,1,1), 0) # null rng
        self.check_count(event, date(2001,1,1), date(2001,1,1), 0) # null rng

        # Test non-null periods
        self.check_count_rrule(event, date(1999,12,28), date(2000,1,4), 3)
        self.check_count_rrule(event, date(2000,1,1), date(2000,1,2), 1)
        self.check_count_rrule(event, date(2000,2,10), date(2000,2,17), 7)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 365)


    def test_daily_byday(self) -> None:
        # Create daily repeating event with a 'byday' rule.
        # (Not even sure what the correct behaviour is here - hoping
        # dateutil.rrule is correct!)
        event = self.create_event(
            'Event {}'.format(sys._getframe().f_code.co_name),
            date(2000,1,1),
            rrule = {'FREQ':['DAILY'],'BYDAY':['SU']})

        # Test null periods
        self.check_count(event, date(1999,1,1), date(2000,1,1), 0)
        self.check_count(event, date(2000,1,1), date(2000,1,2), 0)

        # Test non-null periods
        self.check_count_rrule(event, date(2000,1,2), date(2000,1,3), 1)
        self.check_count_rrule(event, date(1999,12,28), date(2000,1,4), 1)
        self.check_count_rrule(event, date(2000,2,10), date(2000,2,17), 1)
        self.check_count_rrule(event, date(2001,1,1), date(2002,1,1), 52)


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
        self.check_count(event, date(1999,1,1), date(2000,1,1), 0)
        self.check_count(event, date(2000,1,1), date(2000,1,1), 0) # null rng

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
        self.check_count(event, date(1999,12,1), date(2000,1,1), 0)
        self.check_count(event, date(2000,1,1), date(2000,1,1), 0) # null rng

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
        self.check_count(event, date(2022,7,1), date(2022,7,1), 0) # null rng

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
        self.check_count(event, date(2017,10,15), date(2017,10,15), 0)#null rng

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
        self.check_count(event, date(2022,2,22), date(2022,2,22), 0) # null rng
        self.check_count(event, date(2034,1,1), date(2034,1,1), 0) # null rng

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
        self.check_count(event, date(2020,2,28), date(2020,2,28), 0) # null rng
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
        if 'EXDATE' in event:
            if isinstance(event['EXDATE'],list):
                exdtlist = [ d for dlist in event['EXDATE'] for d in dlist.dts ]
            else:
                exdtlist = event['EXDATE'].dts
            if timed_event:
                for exd in exdtlist:
                    if isinstance(exd.dt,datetime):
                        exdt = exd.dt
                    else:
                        exdt = datetime.combine(exd.dt, event_st.time())
                    if exdt.tzinfo is None:
                        exdt = exdt.replace(tzinfo=self.LOCAL_TZ)
                    rr.exdate(exdt)
            else:
                # Untimed, but rr.exdate() requires datetime objects
                for exd in exdtlist:
                    dt = exd.dt
                    if not isinstance(dt,datetime):
                        dt = datetime(dt.year,dt.month,dt.day)
                    rr.exdate(dt)
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
