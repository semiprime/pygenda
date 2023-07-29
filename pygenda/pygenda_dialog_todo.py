# -*- coding: utf-8 -*-
#
# pygenda_dialog_todo.py
# Code for Todo dialog (used to create/update to-do items)
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
from gi.repository import Gtk, Gdk

from icalendar import Todo as iTodo
from locale import gettext as _
from typing import Optional, Tuple

# pygenda components
from .pygenda_gui import GUI
from .pygenda_calendar import Calendar
from .pygenda_entryinfo import EntryInfo


# Exception used to indicate dialog can't display todo properties.
# In these cases there is a danger of the user accidentally changing
# the todo property.
class TodoPropertyBeyondEditDialog(Exception):
    pass


# Singleton class to manage Todo dialog
class TodoDialogController:
    dialog = None # type: Gtk.Dialog
    wid_desc = None # type: Gtk.Entry
    wid_todolist = None # type: Gtk.ComboBoxText
    wid_priority = None # type: Gtk.ComboBoxText
    wid_status = None # type: Gtk.ComboBoxText
    list_default_cats = None # type: list

    @classmethod
    def init(cls) -> None:
        # Initialiser for TodoDialogController singleton class.
        # Called from GUI init_stage2().

        # Load glade file
        GUI.load_glade_file('dialog_todo.glade')

        # Get some references to dialog elements in glade
        cls.dialog = GUI._builder.get_object('dialog_todo')
        if (not cls.dialog): # Sanity check
            raise NameError('Dialog Todo not found')

        cls.wid_desc = GUI._builder.get_object('entry_dialogtodo_desc')
        cls._init_todolists()
        cls.wid_priority = GUI._builder.get_object('combo_todo_priority')
        cls.wid_status = GUI._builder.get_object('combo_todo_status')


    @classmethod
    def _init_todolists(cls) -> None:
        # Get reference to todo-list combobox & initialise its entries
        cls.wid_todolist = GUI._builder.get_object('combo_todo_list')
        todo_titles, cls.list_default_cats = GUI.todo_titles_default_cats()
        for t in todo_titles:
            cls.wid_todolist.append_text(t)


    @classmethod
    def new_todo(cls, txt:str=None, list_idx:int=None) -> None:
        # Called to implement "new todo" from GUI, e.g. menu
        cls.dialog.set_title(_('New To-do'))
        response,ei,list_idx = cls._do_todo_dialog(txt=txt, list_idx=list_idx)
        if response==Gtk.ResponseType.OK and ei.desc:
            td = Calendar.new_entry(ei)
            GUI.cursor_goto_todo(td, list_idx)
            GUI.view_redraw(en_changes=True)


    @classmethod
    def edit_todo(cls, todo:iTodo, list_idx:int=None) -> None:
        # Called to implement "edit todo" from GUI
        cls.dialog.set_title(_('Edit To-do'))
        response,ei,list_idx = cls._do_todo_dialog(todo=todo, list_idx=list_idx)
        if response==Gtk.ResponseType.OK:
            if ei.desc:
                Calendar.update_entry(todo, ei)
                GUI.cursor_goto_todo(todo, list_idx)
                GUI.view_redraw(en_changes=True)
            else: # Description text has been deleted in dialog
                GUI.dialog_deleteentry(todo)


    @classmethod
    def _do_todo_dialog(cls, todo:iTodo=None, txt:str=None, list_idx:Optional[int]=0) -> Tuple[int,EntryInfo,int]:
        # Do the core work displaying todo dialog and extracting result.
        cls._seed_fields(todo=todo, txt=txt, list_idx=list_idx)
        try:
            while True:
                response = cls.dialog.run()
                break
        finally:
            cls.dialog.hide()
        return response,cls._get_entryinfo(),cls.wid_todolist.get_active()


    @classmethod
    def _seed_fields(cls, todo:Optional[iTodo], txt:Optional[str], list_idx:Optional[int]=0) -> None:
        # Initialise fields when dialog is opened.
        # Data optionally from an existing todo, or text used as summary.

        # First, set to default values (possibly overwritten later)
        cls._set_fields_to_defaults()

        if todo is not None:
            # existing entry - take values
            if 'SUMMARY' in todo:
                cls.wid_desc.set_text(todo['SUMMARY'])
            cls.wid_desc.grab_focus() # also selects contents
            if 'PRIORITY' in todo:
                p = int(todo['PRIORITY'])
                if 1<=p<=9:
                    cls.wid_priority.set_active(p)
            if 'DTSTART' in todo or 'DTEND' in todo or 'DUE' in todo or 'COMPETED' in todo:
                raise TodoPropertyBeyondEditDialog('Editing todo with date not supported')
            if 'STATUS' in todo:
                s = todo['STATUS']
                if s in Calendar.STATUS_LIST_TODO:
                    cls.wid_status.set_active_id(s)
        elif txt is not None:
            cls.wid_desc.set_text(txt)
            cls.wid_desc.set_position(len(txt))

        if list_idx is not None:
            cls.wid_todolist.set_active(list_idx)


    @classmethod
    def _set_fields_to_defaults(cls) -> None:
        # Set dialog fields to default values
        cls.wid_desc.set_text('')
        cls.wid_desc.grab_focus_without_selecting()
        cls.wid_todolist.set_active(0)
        cls.wid_priority.set_active(0)
        cls.wid_status.set_active(0)


    @classmethod
    def _get_entryinfo(cls) -> EntryInfo:
        # Decipher entry fields and return info as an EntryInfo object.
        desc = cls.wid_desc.get_text()
        stat = cls.wid_status.get_active_id()
        ei = EntryInfo(type=EntryInfo.TYPE_TODO, desc=desc, status=stat)
        list_idx = cls.wid_todolist.get_active()
        ei.set_categories(cls.list_default_cats[list_idx])
        ei.set_priority(cls.wid_priority.get_active())
        return ei
