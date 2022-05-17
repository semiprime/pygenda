# -*- coding: utf-8 -*-
#
# pygenda_view_todo.py
# Provides the "To-Do View" for Pygenda.
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


from gi import require_version as gi_require_version
gi_require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from gi.repository.Pango import WrapMode as PWrapMode

from icalendar import cal as iCal, Todo as iTodo
from locale import gettext as _
from typing import Optional

# pygenda components
from .pygenda_view import View
from .pygenda_calendar import Calendar
from .pygenda_config import Config
from .pygenda_gui import GUI


# Singleton class for Todo View
class View_Todo(View):
    Config.set_defaults('todo_view',{
        'list0_title': _('To-do'),
    })

    @staticmethod
    def view_name() -> str:
        # Return (localised) string to use in menu
        return _('_Todo View')

    @staticmethod
    def accel_key() -> int:
        # Return (localised) keycode for menu shortcut
        k = _('todo_view_accel')
        return ord(k[0]) if len(k)>0 else 0


    @classmethod
    def init(cls) -> Gtk.Widget:
        # Called on startup.
        # Gets view framework from glade file & tweaks/adds a few elements.
        # Returns widget containing view.
        cls._init_parse_list_config()
        cls._init_todo_widgets()
        return cls._topboxscroll


    @classmethod
    def _init_parse_list_config(cls) -> None:
        # Read & parse config settings
        i = 0
        cls._list_titles = []
        cls._list_filters = []
        while True:
            try:
                title = Config.get('todo_view','list{}_title'.format(i))
            except:
                break
            try:
                filt = Config.get('todo_view','list{}_filter'.format(i))
            except:
                filt = None
            cls._list_titles.append(title)
            cls._list_filters.append(filt)
            i += 1
        cls._list_count = i


    @classmethod
    def _init_todo_widgets(cls) -> None:
        # Initialise widgets - create list labels, entry spaces etc.
        # First make the top-level container
        cls._topboxscroll = Gtk.ScrolledWindow()
        cls._topboxscroll.set_name('view_todo')
        cls._topboxscroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.NEVER)
        cls._topboxscroll.set_overlay_scrolling(False)
        cls._topboxscroll.set_hexpand(True)
        list_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        list_hbox.set_homogeneous(True)
        cls._topboxscroll.add(list_hbox)

        # Now add vertical boxes for each list
        cls._list_container = []
        for i in range(cls._list_count):
            new_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            new_list.get_style_context().add_class('todoview_list')
            new_title = Gtk.Label(cls._list_titles[i])
            new_list.add(new_title)
            new_title.get_style_context().add_class('todoview_title')
            new_list_scroller = Gtk.ScrolledWindow()
            new_list_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            new_list_scroller.set_overlay_scrolling(False)
            new_list_scroller.set_vexpand(True)
            new_list.add(new_list_scroller)
            new_list_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            new_list_scroller.add(new_list_content)
            cls._list_container.append(new_list_scroller)
            list_hbox.add(new_list)


    @classmethod
    def get_cursor_entry(cls) -> iCal.Event:
        # Returns entry at cursor position, or None if cursor not on entry.
        # Called from cursor_edit_entry().
        return None


    @classmethod
    def redraw(cls, ev_changes:bool) -> None:
        # Called when redraw required
        # ev_changes: bool indicating if event display needs updating too
        if not ev_changes:
            return
        for cont in cls._list_container:
            cont.get_child().destroy()
        todos = Calendar.todo_list()
        for i in range(len(cls._list_container)):
            new_list_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            for td in todos:
                if 'SUMMARY' in td:
                    if cls._todo_matches_filter(td, cls._list_filters[i]):
                        row = Gtk.Box()
                        mark_label = Gtk.Label(u'•')
                        mark_label.set_halign(Gtk.Align.END)
                        mark_label.set_valign(Gtk.Align.START)
                        ctx = mark_label.get_style_context()
                        ctx.add_class('todoview_marker')
                        row.add(mark_label)
                        item_text = Gtk.Label(td['SUMMARY'])
                        item_text.set_xalign(0)
                        item_text.set_yalign(0)
                        item_text.set_line_wrap(True)
                        item_text.set_line_wrap_mode(PWrapMode.WORD_CHAR)
                        row.add(item_text)
                        new_list_content.add(row)
            new_list_content.get_style_context().add_class('todoview_items')
            cls._list_container[i].add(new_list_content)
            cls._list_container[i].show_all()


    @staticmethod
    def _todo_matches_filter(td:iTodo, filt:Optional[str]) -> bool:
        # Return True if categories of to-do item match filter
        if filt is None:
            return True
        cats = View_Todo._get_categories(td)
        if not cats:
            return filt=='UNCATEGORIZED'
        return filt in cats


    @staticmethod
    def _get_categories(td:iTodo) -> list:
        # Return list of categories of the given to-do item
        if 'CATEGORIES' not in td:
            cats = []
        elif isinstance(td['CATEGORIES'],list):
            cats = []
            for clist in td['CATEGORIES']:
                if isinstance(clist,str):
                    cats.extend([c for c in clist.split(',') if c])
                else:
                    cats.extend([c for c in clist.cats if c])
        elif isinstance(td['CATEGORIES'],str):
            cats = [c for c in td['CATEGORIES'].split(',') if c]
        else:
            cats = [c for c in td['CATEGORIES'].cats if c]
        return cats
