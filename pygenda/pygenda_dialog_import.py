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
from typing import Optional, Union, Tuple

# Pygenda components
from .pygenda_gui import GUI
from .pygenda_calendar import Calendar


# Singleton class to manage importing file
class ImportController:

    _dialog_grid = None # type:Gtk.Grid
    _dialog_y = 0

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
            if new_en is False:
                # False indicates import has been cancelled, so stop here
                break
            if jump_to_en is None and new_en is not None:
                jump_to_en = new_en

        if jump_to_en is not None:
            if isinstance(jump_to_en, iEvent):
                GUI.cursor_goto_event(jump_to_en)
            else:  # is a Todo
                GUI.cursor_goto_todo(jump_to_en, 0)# 0 = find first occ of todo
            GUI.view_redraw(en_changes=True)


    @classmethod
    def _get_calendar_combobox(cls, is_event:bool) -> Optional[Gtk.ComboBox]:
        # Return a combobox for selecting calendar for events.
        # Combobox = None -> None required
        if is_event:
            cal_list = Calendar.calendar_displaynames_event_rw()
        else: # is a todo
            cal_list = Calendar.calendar_displaynames_todo_rw()
        if len(cal_list) <= 1:
            # No need for a combobox when there's no choice to make
            return None
        combobox = Gtk.ComboBoxText()
        for id,dn in cal_list:
            combobox.append(str(id), dn)
        combobox.connect('key-press-event', GUI._combobox_keypress, Gtk.ResponseType.ACCEPT)
        return combobox


    @classmethod
    def _process_entry(cls, en:Union[iEvent,iTodo]) -> Union[iEvent,iTodo,bool,None]:
        # Import or skip entry in iCal file, depending on user interaction.
        # Return entry if entry imported, None if skipped, False if cancelled.
        res,cal = cls._import_entry_dialog(en)
        if res==Gtk.ResponseType.DELETE_EVENT:
            return False
        if res==Gtk.ResponseType.ACCEPT:
            new_en = Calendar.import_entry(en, cal_idx=cal)
            return new_en
        return None


    @classmethod
    def _import_entry_dialog(cls, en:Union[iEvent,iTodo]) -> Tuple[int,Optional[int]]:
        # Show/manage dialog to query importing single entry.
        # This will be shown for each entry in an imported iCal file.
        dialog = Gtk.Dialog(title=_('Import entry'), parent=GUI._window,
            flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=(_('Skip'), Gtk.ResponseType.REJECT))
        dialog.set_resizable(False)
        import_button = dialog.add_button(_('Import'), Gtk.ResponseType.ACCEPT)
        can_import = True # Will use this to enable/disable Import button

        cls._dialog_grid = Gtk.Grid()
        dialog.get_content_area().add(cls._dialog_grid)
        cls._dialog_y = 0

        cls._add_row(_('Found entry:'), style=GUI.STYLE_SECTLABEL, halign=Gtk.Align.START)

        if 'SUMMARY' in en:
            desc_txt = en['SUMMARY']
            if len(desc_txt)>60:
                desc_txt = desc_txt[:60]+u'…'
        else:
            desc_txt = _('None')
        cls._add_row_prop(_('Description:'), desc_txt)
        en_is_event = isinstance(en,iEvent) # False => a Todo
        cls._add_row_prop(_('Type:'), _('Event') if en_is_event else _('Todo'))

        # Display extra information rows depending on entry type
        if en_is_event:
            if 'DTSTART' in en:
                cls._add_row_prop(_('Date/time:'), str(en['DTSTART'].dt))
            else:
                cls._add_row(_('Invalid event, no date found'))
                can_import = False
            if can_import and 'RRULE' in en:
                rr = en['RRULE']
                if 'FREQ' in rr:
                    rep_type = rr['FREQ'][0].capitalize()
                    cls._add_row_prop(_('Repeats:'), _(rep_type))
        else: # en is Todo
            if 'DUE' in en:
                cls._add_row_prop(_('Due date:'), str(en['DUE'].dt))

        # Check entry UID. If present, use it to test if entry already exists
        if 'UID' not in en:
            cls._add_row(_('Invalid entry, no ID found'), style=GUI.STYLE_ALERTLABEL, halign=Gtk.Align.CENTER)
            can_import = False
        elif Calendar.get_entry_by_uid(en['UID']) is not None: # entry exists?
            cls._add_row(_('An entry with this ID already exists'), style=GUI.STYLE_ALERTLABEL, halign=Gtk.Align.CENTER)
            can_import = False

        # If necessary, add dropdown box to select calendar to import into
        cb_cal = None
        if can_import:
            cb_cal = cls._get_calendar_combobox(en_is_event)
            if cb_cal is not None:
                cb_cal.set_active(0)
                cls._add_row_widget(_('Import to calendar:'), cb_cal)

        # If can_import, sensitise the "Import" button
        import_button.set_sensitive(can_import)

        dialog.show_all()
        res = dialog.run() # type:int
        dest_cal = None if cb_cal is None else int(cb_cal.get_active_id())
        dialog.destroy()
        cls._dialog_grid = None # so grid & contents are cleaned up
        return res, dest_cal


    @classmethod
    def _add_row(cls, txt:str, style:str=None, halign:Gtk.Align=None) -> None:
        # Add text to next row of grid in the form "`txt`"
        lab = Gtk.Label(txt)
        if style:
            lab.get_style_context().add_class(style)
        if halign:
            lab.set_halign(halign)
        lab.set_yalign(0.5)
        cls._dialog_grid.attach(lab, 0,cls._dialog_y, 2,1) # spans 2 columns
        cls._dialog_y += 1


    @classmethod
    def _add_row_prop(cls, label:str, cont:str) -> None:
        # Add text to next row of grid in the form "`label` `cont`"
        propnm_lab = Gtk.Label(label)
        propnm_lab.set_halign(Gtk.Align.END)
        propnm_lab.set_yalign(0.5)
        propnm_lab.get_style_context().add_class(GUI.STYLE_TXTLABEL)
        cls._dialog_grid.attach(propnm_lab, 0,cls._dialog_y, 1,1)

        cont_lab = Gtk.Label(cont)
        cont_lab.set_halign(Gtk.Align.START)
        cont_lab.set_yalign(0.5)
        cont_lab.set_xalign(0)
        cont_lab.get_style_context().add_class(GUI.STYLE_TXTPROP)
        cls._dialog_grid.attach(cont_lab, 1,cls._dialog_y, 1,1)

        cls._dialog_y += 1


    @classmethod
    def _add_row_widget(cls, label:str, wid:Gtk.Widget) -> None:
        # Add label + widget to next row of grid
        propnm_lab = Gtk.Label(label)
        propnm_lab.set_halign(Gtk.Align.END)
        propnm_lab.set_yalign(0.5)
        propnm_lab.get_style_context().add_class(GUI.STYLE_TXTLABEL)
        cls._dialog_grid.attach(propnm_lab, 0,cls._dialog_y, 1,1)

        cls._dialog_grid.attach(wid, 1,cls._dialog_y, 1,1)
        cls._dialog_y += 1
