# -*- coding: utf-8 -*-
#
# pygenda_dialog_find.py
# Code for find dialog
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


from gi import require_version as gi_require_version
gi_require_version('Gtk', '3.0')
from gi.repository import Gtk

from icalendar import Todo as iTodo
from locale import gettext as _

# pygenda components
from .pygenda_gui import GUI
from .pygenda_calendar import Calendar


# Singleton class to manage Find dialog
class FindDialogController:
    dialog = None # type: Gtk.Dialog
    find_text = None # type: Gtk.Entry

    @classmethod
    def init(cls) -> None:
        # Initialiser for FindController singleton class.
        # Called from GUI init_stage2().

        # Load glade file
        GUI.load_glade_file('dialog_find.glade')

        # Get some references to dialog elements in glade
        cls.dialog = GUI._builder.get_object('dialog_find')
        cls.find_text = GUI._builder.get_object('dialog_find_text')
        if (not cls.dialog or not cls.find_text): # Sanity check
            raise NameError('Dialog Find not found')

    @classmethod
    def find(cls) -> None:
        # Opens Find dialog and passes search query to _find_results()
        cls.find_text.grab_focus()
        response = cls.dialog.run()
        cls.dialog.hide()
        if response==Gtk.ResponseType.OK and cls.find_text.get_text():
            cls._find_results()


    @classmethod
    def _find_results(cls) -> None:
        # Passes search query to Calendar and displays results in a dialog.
        r_dialog = Gtk.Dialog(title=_('Find results'), parent=GUI._window,
            flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        r_dialog.set_icon_name('edit-find')
        txt = cls.find_text.get_text()
        res = Calendar.search(txt)
        if not res:
            r_dialog.get_content_area().add(Gtk.Label(_('No results found')))
        else:
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.set_overlay_scrolling(False)
            r_grid = Gtk.Grid()
            scroller.get_style_context().add_class('find_results')
            scroller.add(r_grid)
            r_dialog.get_content_area().add(scroller)
            i = 0
            for en in res:
                if isinstance(en, iTodo):
                    l_left = Gtk.Label(u'Ⓣ')
                    l_left.set_halign(Gtk.Align.END)
                else:
                    dt = en['DTSTART'].dt
                    l_left = Gtk.Label(dt.strftime(GUI.date_formatting_numeric))
                r_grid.attach(l_left, 0, i, 1, 1)
                l_sum = Gtk.Label(en['SUMMARY'])
                l_sum.set_halign(Gtk.Align.START)
                r_grid.attach(l_sum, 1, i, 1, 1)
                i += 1
        r_dialog.show_all()
        r_dialog.run()
        r_dialog.destroy()
