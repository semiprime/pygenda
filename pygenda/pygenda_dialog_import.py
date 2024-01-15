# -*- coding: utf-8 -*-
#
# pygenda_dialog_import.py
# Code for import dialogs
#
# Copyright (C) 2024 Matthew Lewis
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


from gi.repository import Gtk

from icalendar import Calendar as iCalendar, Event as iEvent, Todo as iTodo
from locale import gettext as _ # type:ignore[attr-defined]
from sys import stderr
from typing import Optional, Union

# Pygenda components
from .pygenda_gui import GUI
from .pygenda_calendar import Calendar


# Singleton class to manage importing file
class ImportController:

    @classmethod
    def import_flow(cls) -> None:
        # Called to import a file
        filenm = cls._get_file()
        if filenm:
            cls._import_file(filenm)


    @classmethod
    def _get_file(cls) -> Optional[str]:
        # Opens file chooser, returns filename or None
        chooser = Gtk.FileChooserNative.new(_('Import File'), GUI._window, Gtk.FileChooserAction.OPEN, _('_Import'), None)

        # Add filters
        filt_ical = Gtk.FileFilter()
        filt_ical.set_name(_('iCalendar files'))
        filt_ical.add_mime_type('text/calendar')
        chooser.add_filter(filt_ical)
        filt_none = Gtk.FileFilter()
        filt_none.set_name(_('All files'))
        filt_none.add_pattern('*')
        chooser.add_filter(filt_none)

        # Run dialog and return value depending on result
        res = chooser.run()
        if res==Gtk.ResponseType.ACCEPT:
            return chooser.get_filename() # type:ignore[no-any-return]
        return None


    @classmethod
    def _import_file(cls, filename:str) -> None:
        # Opens file as iCal file and imports each entry
        with open(filename, 'rb') as file:
            try:
                cal = iCalendar.from_ical(file.read())
            except:
                print('Error: Failed to parse ical file '+filename, file=stderr)
                return
        if cal.is_broken:
            print('Error: Non-conformant ical data '+filename, file=stderr)
            return

        entries = cal.walk('VEVENT')
        entries.extend(cal.walk('VTODO'))

        if not entries:
            print('Notice: No event or todo entries found in '+filename, file=stderr)
            return

        jump_to_en = None # Store the first entry imported - to move cursor to
        for en in entries:
            new_en = cls._process_entry(en)
            if jump_to_en is None and new_en is not None:
                jump_to_en = new_en

        if jump_to_en is not None:
            if isinstance(jump_to_en, iEvent):
                GUI.cursor_goto_event(jump_to_en)
            else:  # is a Todo
                GUI.cursor_goto_todo(jump_to_en, 0)# 0 = find first occ of todo
            GUI.view_redraw(en_changes=True)


    @classmethod
    def _process_entry(cls, en:Union[iEvent,iTodo]) -> Union[iEvent,iTodo,None]:
        # Import or skip entry in iCal file, depending on user interaction
        res = cls._import_entry_dialog(en)
        if res==Gtk.ResponseType.ACCEPT:
            new_en = Calendar.new_entry_from_example(en, cal_idx=None, use_ex_uid_created=True, use_ex_rpts=True, use_ex_alarms=False)
            return new_en
        return None


    @classmethod
    def _import_entry_dialog(cls, en:Union[iEvent,iTodo]) -> int:
        # Show/manage dialog to query importing single entry.
        # This will be shown for each entry in an imported iCal file.
        dialog = Gtk.Dialog(title=_('Import entry'), parent=GUI._window,
            flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=(_('Skip'), Gtk.ResponseType.REJECT))
        dialog.set_resizable(False)
        import_button = dialog.add_button(_('Import'), Gtk.ResponseType.ACCEPT)
        can_import = True # Will use this to enable/disable Import button

        grid = Gtk.Grid()
        dialog.get_content_area().add(grid)
        grid.attach(Gtk.Label(_('Import entry?')), 0,0, 1,1)
        if 'SUMMARY' in en:
            desc_txt = en['SUMMARY']
            if len(desc_txt)>60:
                desc_txt = desc_txt[:60]+u'…'
        else:
            desc_txt = _('None')
        cls._add_row(grid, 1, _('Description:'), desc_txt)
        en_is_event = isinstance(en,iEvent) # False => a Todo
        cls._add_row(grid, 2, _('Type:'), _('Event') if en_is_event else _('Todo'))

        # Display extra information rows depending on entry type
        y = 3
        if en_is_event:
            if 'DTSTART' in en:
                cls._add_row(grid, y, _('Date/time:'), str(en['DTSTART'].dt))
            else:
                grid.attach(Gtk.Label(_('Invalid event, no date found')), 1,y, 1,1)
                can_import = False
            y += 1
            if can_import and 'RRULE' in en:
                rr = en['RRULE']
                if 'FREQ' in rr:
                    rep_type = rr['FREQ'][0].capitalize()
                    cls._add_row(grid, y, _('Repeats:'), _(rep_type))
                    y += 1
        else: # en is Todo
            if 'DUE' in en:
                cls._add_row(grid, y, _('Due date:'), str(en['DUE'].dt))
                y += 1

        # Check entry UID. If present, use it to test if entry already exists
        if 'UID' not in en:
            grid.attach(Gtk.Label(_('Invalid entry, no ID found')), 1,y, 1,1)
            can_import = False
        elif Calendar.get_entry_by_uid(en['UID']) is not None: # entry exists?
            grid.attach(Gtk.Label(_('An event with this ID already exists')), 1,y, 1,1)
            can_import = False

        import_button.set_sensitive(can_import)
        dialog.show_all()
        res = dialog.run() # type:int
        dialog.destroy()
        return res


    @staticmethod
    def _add_row(grid:Gtk.Grid, y:int, label:str, cont:str) -> None:
        # Add text to bottom of grid in the form "label cont".
        propnm_lab = Gtk.Label(label)
        propnm_lab.set_halign(Gtk.Align.END)
        propnm_lab.set_yalign(0)
        propnm_lab.get_style_context().add_class(GUI.STYLE_TXTLABEL)
        grid.attach(propnm_lab, 0,y, 1,1)

        cont_lab = Gtk.Label(cont)
        cont_lab.set_halign(Gtk.Align.START)
        cont_lab.set_yalign(0)
        cont_lab.set_xalign(0)
        cont_lab.get_style_context().add_class(GUI.STYLE_TXTPROP)
        grid.attach(cont_lab, 1,y, 1,1)
