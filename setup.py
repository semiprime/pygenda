#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# setup.py for Pygenda
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
#

# Example usage:
#   ./setup.py install [--user]
#   ./setup.py develop [--user]
#   ./setup.py sdist
#   ./setup.py bdist_wheel --plat-name=[linux-x86_64|linux-aarch64]


from setuptools import setup
from setuptools.command.bdist_egg import bdist_egg
from sys import platform
import subprocess
from os import path as ospath


# Subclass Egg installer to handle building clipboard library from C source
class PygendaEggInstall(bdist_egg):
    def run(self):
        # Override run() method of parent class
        self.make_clipboard_library()
        super().run() # continue with standard parent run() method

    @staticmethod
    def make_clipboard_library():
        # Only know how to do this on Linux - needs fixing for other platforms
        if platform == 'linux':
            print("Compiling clipboard library...")
            cdir = '{:s}/csrc'.format(ospath.dirname(__file__))
            subprocess.run(['cmake','.'], cwd=cdir)
            subprocess.run(['make','clean'], cwd=cdir)
            subprocess.run(['make'], cwd=cdir)
            print("Copying clipboard library...")
            subprocess.run(['make','cp'], cwd=cdir)
        else:
            print("Don't know how to build clipboard library on this platform.\nSkipping.")


# Grab version number from source code, so it only needs updating
# in one location.
pygenda_version = None
with open('pygenda/pygenda_version.py') as f:
    for line in f:
        if line.startswith('__version__'):
            pygenda_version = line.split('=')[1].replace('\'','').replace('"','').strip()
            break

assert pygenda_version is not None

setup(
    name = "pygenda",
    version = pygenda_version,
    url = "https://github.com/semiprime/pygenda",
    author = "Matthew Lewis",
    author_email = "pygenda@semiprime.com",
    description = "An agenda application inspired by Agenda programs on Psion PDAs.",
    long_description = "Pygenda is a calendar/agenda application written in Python3/GTK3. The UI is inspired by the Agenda programs on the Psion Series 3 and Series 5 range of keyboard PDAs, with the aim of being suitable for devices such as Planet Computers' Gemini (running Linux).\n\nFor more information/latest source, see https://github.com/semiprime/pygenda",
    packages = ["pygenda"],
    cmdclass = {'bdist_egg': PygendaEggInstall}, # use custom install above
    package_data = {'': ['ui/*.ui', 'css/*.css', 'css/*.svg', 'libpygenda_clipboard.so', 'locale/*/LC_MESSAGES/pygenda.mo', 'app/pygenda.desktop']}, # files for bdists
    license = "GPLv3 only",
    python_requires = ">=3.5",
    install_requires = [
        "PyGObject",
        "pycairo",
        "python-dateutil",
        "icalendar",
        "tzlocal!=2.*", # Gemian on GeminiPDA does not work with tzlocal 2.x
        "num2words",
    ],
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Environment :: Handhelds/PDA's",
        "Environment :: X11 Applications :: GTK",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Office/Business :: Scheduling",
    ],
)
