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

print('BEGIN:VCALENDAR', end='\r\n')
print('VERSION:2.0', end='\r\n')
print('PRODID:-//Semiprime//PygendaTest//EN', end='\r\n')

for x in range(50000):
    print('BEGIN:VEVENT', end='\r\n')
    print('UID:Pygenda-{:08d}'.format(x), end='\r\n')
    print('DTSTAMP:20220101T000000Z', end='\r\n')
    print('SUMMARY:Test event {:d}'.format(x), end='\r\n')
    print('DTSTART:{:04d}{:02d}{:02d}'.format(2025-x//100, 11-(x//10)%10, 20-x%10), end='\r\n')
    #print('DURATION:PT30M', end='\r\n')
    print('END:VEVENT', end='\r\n')
print('END:VCALENDAR', end='\r\n')
