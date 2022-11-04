#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Generate test file for Pygenda
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

from datetime import datetime,timedelta, date as dt_date

YEAR = datetime.now().year
STAMPDATE = '{}0101T000000'.format(YEAR)
uid = 1234567

def print_stamp_uid():
    global uid
    print('DTSTAMP;VALUE=DATE-TIME:{}Z'.format(STAMPDATE), end='\r\n')
    print('UID:Pygenda-{:08d}'.format(uid), end='\r\n')
    uid += 1


def print_vevent(desc, date, time=None, endtime=None, daycount=None, repeat=None, interval=1, repeat_count=None, bymonthday=None, status=None):
    if isinstance(date, str):
        date = datetime.strptime(date,'%Y-%m-%d').date()
    print('BEGIN:VEVENT', end='\r\n')
    print('SUMMARY:{:s}'.format(desc), end='\r\n')
    if time is not None:
        if isinstance(time, str):
            time = datetime.strptime(time,'%H:%M').time()
        print('DTSTART;VALUE=DATE-TIME:{:04d}{:02d}{:02d}T{:02d}{:02d}{:02d}'.format(date.year, date.month, date.day, time.hour, time.minute, time.second), end='\r\n')
        if endtime is not None:
            if isinstance(endtime, str):
                endtime = datetime.strptime(endtime,'%H:%M').time()
            print('DTEND;VALUE=DATE-TIME:{:04d}{:02d}{:02d}T{:02d}{:02d}{:02d}'.format(date.year, date.month, date.day, endtime.hour, endtime.minute, endtime.second), end='\r\n')
    else:
        print('DTSTART;VALUE=DATE:{:04d}{:02d}{:02d}'.format(date.year, date.month, date.day), end='\r\n')
        if daycount is not None:
            enddate = date+timedelta(days=daycount)
            print('DTEND;VALUE=DATE:{:04d}{:02d}{:02d}'.format(enddate.year, enddate.month, enddate.day), end='\r\n')
    print_stamp_uid()
    if repeat=='YEARLY':
        print('RRULE:FREQ=YEARLY{:s}{:s}{:s}'.format(
            '' if interval==1 else ';INTERVAL={:d}'.format(interval),
            '' if bymonthday is None else ';BYMONTH={:d};BYDAY={:s}'.format(bymonthday[0],bymonthday[1]),
            '' if repeat_count is None else ';COUNT={:d}'.format(repeat_count)
            ), end='\r\n')
    elif repeat=='WEEKLY':
        print('RRULE:FREQ=WEEKLY{:s}{:s}'.format(
            '' if interval==1 else ';INTERVAL={:d}'.format(interval),
            '' if repeat_count is None else ';COUNT={:d}'.format(repeat_count)
            ), end='\r\n')
    elif repeat=='MONTHLY':
        print('RRULE:FREQ=MONTHLY{:s}{:s}{:s}'.format(
            '' if interval==1 else ';INTERVAL={:d}'.format(interval),
            '' if bymonthday is None else ';BYDAY={:s}'.format(bymonthday),
            '' if repeat_count is None else ';COUNT={:d}'.format(repeat_count)
            ), end='\r\n')
    if status is not None:
        print('STATUS:{:s}'.format(status.upper()), end='\r\n')
    print('END:VEVENT', end='\r\n')


def print_vtodo(desc, cat=None, priority=None, status=None, date=None):
    print('BEGIN:VTODO', end='\r\n')
    print('SUMMARY:{:s}'.format(desc), end='\r\n')
    if cat is not None:
        print('CATEGORIES:{:s}'.format(cat), end='\r\n')
    if priority is not None:
        print('PRIORITY:{:d}'.format(priority), end='\r\n')
    if status is not None:
        print('STATUS:{:s}'.format(status), end='\r\n')
    if date is not None:
        if isinstance(date, str):
            date = date.strptime(date,'%Y-%m-%d').date()
        print('DTSTART;VALUE=DATE:{:04d}{:02d}{:02d}'.format(date.year, date.month, date.day), end='\r\n')
    print_stamp_uid()
    print('END:VTODO', end='\r\n')


def print_daylight_saving_changes():
    print_vevent('Clocks go forward (Europe)', '2000-03-26', time='1:00', repeat='YEARLY', bymonthday=[3,'-1SU'])
    print_vevent('Clocks go back (Europe)', '2000-10-29', time='1:00', repeat='YEARLY', bymonthday=[10,'-1SU'])
    print_vevent('Clocks go forward (US)', '2000-03-12', time='2:00', repeat='YEARLY', bymonthday=[3,'2SU'])
    print_vevent('Clocks go back (US)', '2000-11-05', time='2:00', repeat='YEARLY', bymonthday=[11,'1SU'])


def print_thanksgiving():
    print('BEGIN:VEVENT', end='\r\n')
    print('SUMMARY:Thanksgiving (US)', end='\r\n')
    print('DTSTART;VALUE=DATE:19421126', end='\r\n')
    print_stamp_uid()
    print('RRULE:FREQ=YEARLY;BYDAY=4TH;BYMONTH=11', end='\r\n')
    print('END:VEVENT', end='\r\n')
    print('BEGIN:VEVENT', end='\r\n')
    print('SUMMARY:Thanksgiving (Canada)', end='\r\n')
    print('DTSTART;VALUE=DATE:19571014', end='\r\n')
    print_stamp_uid()
    print('RRULE:FREQ=YEARLY;BYDAY=2MO;BYMONTH=10', end='\r\n')
    print('END:VEVENT', end='\r\n')


print('BEGIN:VCALENDAR', end='\r\n')
print('VERSION:2.0', end='\r\n')
print('PRODID:-//Semiprime//PygendaTest//EN', end='\r\n')

Jan01 = dt_date(YEAR, 1, 1)
day_offset = Jan01.weekday() # 0=Mon, 1=Tue...
Mar01 = dt_date(YEAR, 3, 1)
day_offset2 = Mar01.weekday() # 0=Mon, 1=Tue...

#
# Anniversaries and yearly events
#
print_vevent('New Year', '0001-01-01', repeat='YEARLY', daycount=1)
print_vevent('Christmas!', '0001-12-25', repeat='YEARLY', daycount=1)
print_vevent('Christmas Eve', '0001-12-24', repeat='YEARLY', daycount=1)
print_vevent('Boxing Day', '0001-12-26', repeat='YEARLY', daycount=1)
print_vevent('Bonfire Night', '2000-11-05', repeat='YEARLY', daycount=1)
print_vevent('Halloween', '2000-10-31', repeat='YEARLY', daycount=1)
print_vevent('Valentine\'s Day', '2000-02-14', repeat='YEARLY', daycount=1)
print_vevent('Armistice Day', '1918-11-11', repeat='YEARLY', daycount=1)
print_vevent('VE Day', '1945-05-08', repeat='YEARLY', daycount=1)
print_vevent('VJ Day', '1945-08-15', repeat='YEARLY', daycount=1)
print_vevent('May Day', '2000-05-01', repeat='YEARLY', daycount=1)
print_vevent('May Day bank holiday (UK)', '2000-05-01', repeat='YEARLY', bymonthday=[5,'1MO'], daycount=1)
print_vevent('Spring bank holiday (UK)', '2000-05-29', repeat='YEARLY', bymonthday=[5,'-1MO'], daycount=1)
print_vevent('Summer bank holiday (UK)', '2000-08-28', repeat='YEARLY', bymonthday=[8,'-1MO'], daycount=1)
print_vevent('April Fools\' Day', '2000-04-01', repeat='YEARLY', daycount=1)
print_vevent('Burns\' Night', '1759-01-25', repeat='YEARLY', daycount=1)
print_vevent('St Patrick\'s Day', '2000-03-17', repeat='YEARLY', daycount=1)
print_vevent('Mother\'s Day (US)', '2000-05-14', repeat='YEARLY', bymonthday=[5,'2SU'], daycount=1)
print_vevent('Father\'s Day', '2000-06-18', repeat='YEARLY', bymonthday=[6,'3SU'], daycount=1)
print_vevent('Winter Solstice', '0001-12-21', repeat='YEARLY', daycount=1)
print_vevent('Summer Solstice', '0001-06-21', repeat='YEARLY', daycount=1)
print_vevent('New Year\'s Eve', '0001-12-31', repeat='YEARLY', daycount=1)
print_vevent('Holocaust Memorial Day', '1945-01-27', repeat='YEARLY', daycount=1)
print_vevent('International Women\'s Day', '1977-03-08', repeat='YEARLY', daycount=1)
print_vevent('International Men\'s Day', '1999-11-19', repeat='YEARLY', daycount=1)
print_vevent('International Talk Like a Pirate Day', '1995-09-19', repeat='YEARLY', daycount=1)
print_vevent('Pi Day', '2000-03-14', repeat='YEARLY', daycount=1)
print_vevent('Perseids meteor shower', '2000-08-12', repeat='YEARLY')
print_vevent('Leonids meteor shower', '2000-11-17', repeat='YEARLY')
print_vevent('Beethoven\'s birthday', '1770-12-16', repeat='YEARLY', daycount=1)

print_daylight_saving_changes()
print_thanksgiving()

# Work events
day_back = 11-(day_offset+3)%7 # first Mon after 4th Jan
print_vevent('Back to work', '{:04d}-01-{:02d}'.format(YEAR,day_back))
print_vevent('Team meeting', '{:04d}-01-{:02d}'.format(YEAR,1+(7-day_offset)%7), time='10:30', repeat='MONTHLY', bymonthday='1MO')
print_vevent('Farrier', '{:04d}-01-{:02d}'.format(YEAR,day_back+3), time='19:00')
print_vevent('Presentation to Sophie & team', '{:04d}-02-{:02d}'.format(YEAR,day_back+7), time='14:00')
print_vevent('Meeting with Steve (Marketing)', '{:04d}-02-{:02d}'.format(YEAR,1 if day_offset not in (2,3) else 5-day_offset), time='14:30')
print_vevent('Funding deadline', '{:04d}-03-{:02d}'.format(YEAR, 2 if day_offset2 not in (2,3) else 9-day_offset2))
print_vevent('Last day (half day)', '{:04d}-12-{:02}'.format(YEAR,23 if day_offset2 not in (2,3) else 24-day_offset2)) # last weekday before 24th
print_vevent('Visit from Imran (Manufacturing)', '{:04d}-03-{:02d}'.format(YEAR,1 if day_offset not in (2,3) else 5-day_offset), time='10:00', status='cancelled')

# Birthdays (fictional!)
print_vevent('Dad\'s birthday', '1953-04-02', repeat='YEARLY', daycount=1)
print_vevent('Mum\'s birthday', '1955-07-12', repeat='YEARLY', daycount=1)
print_vevent('Grandma\'s birthday', '1930-11-29', repeat='YEARLY', daycount=1)
print_vevent('J\'s birthday', '1980-09-17', repeat='YEARLY', daycount=1)
print_vevent('Mo\'s birthday', '1979-02-16', repeat='YEARLY', daycount=1)
print_vevent('Matt P\'s birthday', '1980-03-22', repeat='YEARLY', daycount=1)
print_vevent('Matt B\'s birthday', '1982-10-29', repeat='YEARLY', daycount=1)
print_vevent('Nila\'s birthday', '1983-01-25', repeat='YEARLY', daycount=1)
print_vevent('Antoine\'s birthday', '1983-05-04', repeat='YEARLY', daycount=1)
print_vevent('The twins\' birthday', '2012-06-01', repeat='YEARLY', daycount=1)

# Easter etc
EASTER_DATES = ('1990-04-15','1991-03-31','1992-04-19','1993-04-11','1994-04-03','1995-04-16','1996-04-07','1997-03-30','1998-04-12','1999-04-04','2000-04-23','2001-04-15','2002-03-31','2003-04-20','2004-04-11','2005-03-27','2006-04-16','2007-04-08','2008-03-23','2009-04-12','2010-04-04','2011-04-24','2012-04-08','2013-03-31','2014-04-20','2015-04-05','2016-03-27','2017-04-16','2018-04-01','2019-04-21','2020-04-12','2021-04-04','2022-04-17','2023-04-09','2024-03-31','2025-04-20','2026-04-05','2027-03-28','2028-04-16','2029-04-01','2030-04-21','2031-04-13','2032-03-28','2033-04-17','2034-04-09','2035-03-25','2036-04-13','2037-04-05','2038-04-25','2039-04-10','2040-04-01','2041-04-21','2042-04-06','2043-03-29','2044-04-17','2045-04-09','2046-03-25','2047-04-14','2048-04-05','2049-04-18','2050-04-10')
for easter_date in EASTER_DATES:
    edt = datetime.strptime(easter_date,'%Y-%m-%d').date()
    print_vevent('Good Friday', edt-timedelta(days=2), daycount=1)
    print_vevent('Easter', edt, daycount=1)
    print_vevent('Easter Monday', edt+timedelta(days=1), daycount=1)
    print_vevent('Shrove Tuesday', edt-timedelta(days=47), daycount=1)
    print_vevent('Mothering Sunday (UK)', edt-timedelta(days=21), daycount=1)

# Full moon (note dates given here are for UTC, so don't use outside of testing)
FULLMOON_DATES =(
        '2020-01-10','2020-02-09','2020-03-09','2020-04-08','2020-05-07','2020-06-05','2020-07-05','2020-08-03','2020-09-02','2020-10-01','2020-10-31','2020-11-30','2020-12-30',
        '2021-01-28','2021-02-27','2021-03-28','2021-04-27','2021-05-26','2021-06-24','2021-07-24','2021-08-22','2021-09-20','2021-10-20','2021-11-19','2021-12-19',
        '2022-01-17','2022-02-16','2022-03-18','2022-04-16','2022-05-16','2022-06-14','2022-07-13','2022-08-12','2022-09-10','2022-10-09','2022-11-08','2022-12-08',
        '2023-01-06','2023-02-05','2023-03-07','2023-04-06','2023-05-05','2023-06-04','2023-07-03','2023-08-01','2023-08-31','2023-09-29','2023-10-28','2023-11-27','2023-12-27',
        '2024-01-25','2024-02-24','2024-03-25','2024-04-23','2024-05-23','2024-06-22','2024-07-21','2024-08-19','2024-09-18','2024-10-17','2024-11-15','2024-12-15',
        '2025-01-13','2025-02-12','2025-03-14','2025-04-13','2025-05-12','2025-06-11','2025-07-10','2025-08-09','2025-09-07','2025-10-07','2025-11-05','2025-12-04',
)
for fm_date in FULLMOON_DATES:
    print_vevent('Full moon', fm_date)

# Social & personal events
first_wed = 12-(day_offset+1)%7 # first Wed after 2nd Jan
print_vevent('Guitar lesson', '{:04d}-01-{:02d}'.format(YEAR, first_wed), time='19:00', repeat='WEEKLY', interval=2)
print_vevent('Dentist', '{:04d}-03-{:02d}'.format(YEAR, 1 if day_offset2<5 else 8-day_offset2), time='9:00')
print_vevent('Merseyside Derby', '{:04d}-02-{:02d}'.format(YEAR, 7-day_offset2), time='14:00')
print_vevent('Party at Mo+Soph\'s', '{:04d}-02-{:02d}'.format(YEAR, 20-day_offset2 if day_offset2<5 else 27-day_offset2), time='20:00')
print_vevent('Mum+Dad visit', '{:04d}-{:02d}-{:02d}'.format(YEAR, 3 if day_offset2==6 else 2, 27-day_offset2 if day_offset2<5 else (28 if day_offset2==6 else 1)))
print_vevent('Romeo & Juliet', '{:04d}-03-11'.format(YEAR), time='19:00')
print_vevent('Take car for MOT', '{:04d}-03-17'.format(YEAR), time='10:00')
print_vevent('New bed delivered', '{:04d}-02-01'.format(YEAR), time='9:00',endtime='12:00')
print_vevent('Thai with Jay+Rich?', '{:04d}-{:02d}-{:02d}'.format(YEAR, 3, 14),status='tentative')

# Some to-dos
# config assumed:
#list0_filter = UNCATEGORIZED
#list1_title = Exercises
#list1_filter = exercise
#list2_title = Spanish vocab
#list2_filter = spanish
#list3_title = Holiday
#list3_filter = holiday

print_vtodo('Book flu vaccinations')
print_vtodo('Renew domain names')
print_vtodo('Phone bank')

# Exercises
print_vtodo('Bike - 5m warmup + 25min alternate 2m & 30s sprints', 'exercise')
print_vtodo('Planks (side) planks - 1min, 3(2) reps', 'exercise')
print_vtodo('Squats - 20, 3 reps', 'exercise')

# Fictional holiday
print_vevent('Fly to Barcelona', '{:04d}-07-{:02d}'.format(YEAR, 24-day_offset2))
print_vevent('Off work', '{:04d}-07-{:02d}'.format(YEAR, 23-day_offset2), daycount=15)
print_vevent('Back to UK', '{:04d}-{:02d}-{:02d}'.format(YEAR, 8 if day_offset2<5 else 7, (5 if day_offset2<5 else 36)-day_offset2))
print_vevent('Spanish class', '{:04d}-05-{:02d}'.format(YEAR, 12-day_offset2), time='19:30', repeat='WEEKLY', repeat_count=11)
print_vtodo('Take Luna (& food etc.) to Antoine & Nila\'s', cat='holiday')
print_vtodo('Order Euros', cat='holiday', priority=1, status='NEEDS-ACTION')
print_vtodo('Buy: suncream, mosquito repellant', cat='holiday')
print_vtodo('Buy: hats & sunglasses for the kids', cat='holiday')
print_vtodo('Find power adaptors', cat='holiday')

# Spanish vocab
print_vtodo(u'el museo - museum', cat='spanish')
print_vtodo(u'el billete de ida y vuelta - return ticket', cat='spanish')
print_vtodo(u'el horario - timetable', cat='spanish')
print_vtodo(u'el mapa - map', cat='spanish')
print_vtodo(u'la heladería - ice cream shop', cat='spanish')
print_vtodo(u'la tumbona - sunbed', cat='spanish')
print_vtodo(u'el secador de pelo - hair dryer', cat='spanish')

print('END:VCALENDAR', end='\r\n')
