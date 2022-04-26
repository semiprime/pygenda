# -*- coding: utf-8 -*-
#
# pygenda_config.py
# Provides the Config class, to access configuration settings.
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


import argparse
from gi.repository import GLib
from pathlib import Path
import configparser
from sys import stderr
from datetime import datetime
from typing import Optional


# Singleton class to handle config from .ini file & command line
class Config:
    _cparser = configparser.RawConfigParser()
    CONFIG_DIR = GLib.get_user_config_dir() + '/pygenda'
    DEFAULT_CONFIG_FILE = CONFIG_DIR + '/pygenda.ini'
    DEFAULT_ICS_FILENAME = 'pygenda.ics' # Put this here to avoid cyclic dep.


    @classmethod
    def init(cls) -> None:
        # Initialise config - read command line, config file etc.
        # This called when file is first included (see bottom of file).
        cl_args = cls._read_arguments()
        config_file = cl_args.config
        cls.date = datetime.strptime(cl_args.date, '%Y-%m-%d').date() if cl_args.date else None
        # Now read the config file
        default_config = not config_file
        if default_config:
            config_file = cls.DEFAULT_CONFIG_FILE
            # If using default, create directory if it doesn't exist
            Path(config_file).parent.mkdir(parents=True, exist_ok=True)
        if not cls._cparser.read(config_file):
            if not default_config:
                print("Configuration file {:s} not found".format(config_file), file=stderr)
                exit(-1)
        # Store the dirname so it can be used by other components
        cls.conf_dirname = Path(config_file).parent.as_posix()

        # Read 'file' from command line, write to config store as ics_file
        if cl_args.file:
            cls.set('calendar', 'ics_file', cl_args.file)
            cls.set('calendar', 'caldav_server', None)
        if cl_args.view is not None:
            cls.set('startup','view',cl_args.view.lower())


    @classmethod
    def set_defaults(cls, sect:str, value_list:dict) -> None:
        # Called by pygena components to set defaults for config parameters.
        # This way, individual views etc control their own parameters.
        if not cls._cparser.has_section(sect):
            cls._cparser.add_section(sect)
        for key in value_list:
            if not cls._cparser.has_option(sect, key):
                cls._cparser.set(sect,key,value_list[key])


    @staticmethod
    def _read_arguments() -> argparse.Namespace:
        # Helper function to parse & return command-line arguments.
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('-c', '--config', metavar='FILE', type=str, default=None, help='Config file. Default: {:s}'.format(Config.DEFAULT_CONFIG_FILE))
        parser.add_argument('-d', '--date', metavar='DATE', type=str, default=None, help='Cursor startup date (YYYY-MM-DD)')
        parser.add_argument('-f', '--file', metavar='FILE', type=str, default=None, help='Calendar file. Default: {:s} in config directory'.format(Config.DEFAULT_ICS_FILENAME))
        parser.add_argument('-v', '--view', metavar='VIEW', type=str, default=None, help='Opening view')
        return parser.parse_args()


    @classmethod
    def get(cls, section:str, option:str):
        # Generic method to get a config option.
        # Return type can be Any(?) - often str, also bool, None.
        return cls._cparser.get(section,option)


    @classmethod
    def set(cls, section:str, option:str, value) -> None:
        # Generic method to set a config option.
        # 'value' parameter can be Any type.
        if not cls._cparser.has_section(section):
            cls._cparser.add_section(section)
        cls._cparser.set(section, option, value)


    @classmethod
    def get_float(cls, section:str, option:str) -> Optional[float]:
        # Get a config option as a float.
        # Return None if the value can't be interpreted as a float.
        v = cls._cparser.get(section,option)
        if v is None or v=='':
            return None
        return cls._cparser.getfloat(section,option)


    @classmethod
    def get_int(cls, section:str, option:str) -> Optional[int]:
        # Get a config option as an int.
        # Return None if the value can't be interpreted as an int.
        v = cls._cparser.get(section,option)
        if v is None or v=='':
            return None
        return cls._cparser.getint(section,option)


    @classmethod
    def get_bool(cls, section:str, option:str) -> Optional[bool]:
        # Get a config option as a bool.
        # Return None if the value can't be interpreted as a bool.
        v = cls._cparser.get(section,option)
        if v is None or v=='':
            return None
        if isinstance(v, bool):
            return v
        return cls._cparser.getboolean(section,option)


# Setup when imported
Config.init()
