#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# pygenda/__main__.py
# Main entry point for Pygenda.
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


# Import pygenda components
from .pygenda_gui import GUI
from .pygenda_calendar import Calendar


if __name__=="__main__":
    GUI.init()
    GUI.main()
