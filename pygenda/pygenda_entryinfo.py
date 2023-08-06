# -*- coding: utf-8 -*-
#
# pygenda_entryinfo.py
# Class to encapsulate entry details passed from dialog to calendar.
#
# Copyright (C) 2022,2023 Matthew Lewis
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


from datetime import date as dt_date, time as dt_time, datetime as dt_datetime, timedelta
from copy import deepcopy
from typing import Optional, List


class EntryInfo:
    # Simple class to store entry info to be sent to Calendar
    end_dt = None
    duration = None
    rep_type = None
    rep_inter = 1
    rep_count = None
    rep_until = None
    rep_byday = None
    rep_bymonth = None
    rep_bymonthday = None
    rep_exceptions = None
    categories = None
    priority = None
    duedate = None

    TYPE_EVENT=0
    TYPE_TODO=1

    def __init__(self, type:int=TYPE_EVENT, desc:str=None, start_dt:dt_date=None, end_dt:dt_date=None, duration:timedelta=None, status:str=None, location:str=None):
        self.type = type
        self.desc = '' if desc is None else desc
        self.start_dt = start_dt # date or datetime
        self.set_end_dt(end_dt)
        self.set_duration(duration) # also checks only one of dur/enddt is set
        self.status = status # string, e.g. 'CONFIRMED'
        self.location = location if location else None
        self.alarms = [] # type:List['AlarmInfo']


    def get_start_date(self) -> Optional[dt_date]:
        # Return the start date of the entry, without any time
        if isinstance(self.start_dt, dt_datetime):
            return self.start_dt.date()
        return self.start_dt

    def get_start_time(self) -> Optional[dt_time]:
        # Return the start time of the entry, or None if there's no time
        if isinstance(self.start_dt, dt_datetime):
            return self.start_dt.time()
        return None

    def set_end_dt(self, end_dt:Optional[dt_date]) -> None:
        # Set entry end date/time, checking no duration has been set
        assert end_dt is None or self.duration is None
        self.end_dt = end_dt

    def set_duration(self, dur:Optional[timedelta]) -> None:
        # Set entry duration, checking no end date/time has been set
        assert dur is None or self.end_dt is None
        self.duration = dur

    def set_repeat_info(self, reptype:str, interval:int=None, count:int=None, until:dt_date=None, byday:str=None, bymonth:str=None, bymonthday:str=None, except_list=None) -> None:
        # Set repeat details for this Entry
        assert until is None or count is None
        self.rep_type = reptype
        self.rep_inter = 1 if interval is None else interval
        self.rep_count = count
        self.rep_until = until
        self.rep_byday = byday # e.g. '-1MO' = last Monday
        self.rep_bymonth = bymonth # e.g. '2' = February
        self.rep_bymonthday = bymonthday # e.g. '-2' = second to last day
        self.rep_exceptions = except_list


    def set_categories(self, catlist:list) -> None:
        # Set categories for this entry (make it a set, so no repeats)
        if catlist:
            self.categories = set(catlist)
        else:
            self.categories = None


    def set_priority(self, pri:Optional[int]) -> None:
        # Set priority for this entry
        self.priority = pri if pri and 0<pri<=9 else None


    def set_duedate(self, dt:Optional[dt_datetime]) -> None:
        # Set duetime for this entry (should be a todo)
        self.duedate = dt


    def add_alarm(self, alarm_info:'AlarmInfo') -> None:
        # Add alarm for this entry
        self.alarms.append(deepcopy(alarm_info))


class AlarmInfo:
    def __init__(self, tdelta:timedelta, action:str, desc:str=None, summary:str=None, attendee:str=None):
        self.tdelta = tdelta # Note: -ve -> before entry; +ve -> after entry
        self.action = action
        self.desc = desc
        self.summary = summary
        self.attendee = attendee
