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
from datetime import datetime as dt_datetime
from typing import Optional, Tuple

# pygenda components
from .pygenda_gui import GUI
from .pygenda_calendar import Calendar
from .pygenda_entryinfo import EntryInfo
from .pygenda_widgets import WidgetDate


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
    wid_duedate_switch = None # type: Gtk.Switch
    revealer_duedate = None # type:Gtk.Revealer
    wid_duedate = None # type:WidgetDate
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
        cls.wid_desc.connect('changed', cls._validated_field_changed)
        cls._init_todolists()
        cls.wid_priority = GUI._builder.get_object('combo_todo_priority')
        cls.wid_status = GUI._builder.get_object('combo_todo_status')
        cls._init_duedate()


    @classmethod
    def _init_todolists(cls) -> None:
        # Get reference to todo-list combobox & initialise its entries
        cls.wid_todolist = GUI._builder.get_object('combo_todo_list')
        todo_titles, cls.list_default_cats = GUI.todo_titles_default_cats()
        for t in todo_titles:
            cls.wid_todolist.append_text(t)


    @classmethod
    def _init_duedate(cls) -> None:
        # Get references to due date element and set up revealer
        cls.wid_duedate_switch = GUI._builder.get_object('switch_todo_duedate')
        cls.revealer_duedate = GUI._builder.get_object('revealer_duedate')
        cls.wid_duedate = WidgetDate()
        cls.revealer_duedate.add(cls.wid_duedate)
        cls.wid_duedate.show_all()
        cls.wid_duedate.connect('changed', cls._validated_field_changed)
        cls.wid_duedate_switch.connect('state-set', cls._toggle_duedate)
        cls.wid_duedate.get_style_context().add_class('hidden') # Remove -ve width warnings


    @classmethod
    def _toggle_duedate(cls, wid:Gtk.ComboBox, val:bool) -> bool:
        # Callback for "Due date" switch. Shows or hides date field.
        cls.revealer_duedate.set_reveal_child(val)
        ctx = cls.wid_duedate.get_style_context()
        if val:
            ctx.remove_class('hidden')
        else:
            ctx.add_class('hidden')
        return False # must propagate event for active CSS selector to apply


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
        cls._reset_err_style() # clear error highlights
        discard_on_empty = (todo is None) # True if creating a new todo entry
        try:
            while True:
                response = cls.dialog.run()
                if response!=Gtk.ResponseType.OK:
                    break
                if discard_on_empty and cls._fields_are_defaults():
                    # New todo & nothing entered, so discard as a null entry
                    response = Gtk.ResponseType.CANCEL
                    break
                if cls._is_valid_todo(set_style=True):
                    break
                discard_on_empty = False # only allow discard first time
        finally:
            cls.dialog.hide()
        return response, cls._get_entryinfo(), cls.wid_todolist.get_active()


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
            if 'DUE' in todo:
                due = todo['DUE'].dt
                if isinstance(due,dt_datetime):
                    raise TodoPropertyBeyondEditDialog('Editing todo with date+time DUE not supported')
                cls.wid_duedate_switch.set_active(True)
                cls.wid_duedate.set_date(due)
            if 'DTSTART' in todo or 'DTEND' in todo or 'COMPETED' in todo:
                raise TodoPropertyBeyondEditDialog('Editing todo with unsupported date property')
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
        # Set dialog fields to default values.
        # If you change this, also change _fields_are_defaults()
        # and maybe _is_valid_todo() & _reset_err_style() below.
        cls.wid_desc.set_text('')
        cls.wid_desc.grab_focus_without_selecting()
        cls.wid_todolist.set_active(0)
        cls.wid_priority.set_active(0)
        cls.wid_duedate_switch.set_active(False)
        cls.wid_duedate.set_date(None) # today
        cls.wid_status.set_active(0)


    @classmethod
    def _fields_are_defaults(cls) -> bool:
        # Return True if all fields are defaults, False if any non-default
        # Ignores To-do List field. No particular justification for this,
        # but if someone just changes that, then it's not really the
        # to-do item that they changed, just where they want to store it.
        if cls.wid_desc.get_text():
            return False
        if cls.wid_priority.get_active()!=0:
            return False
        if cls.wid_duedate_switch.get_active():
            return False
        if cls.wid_status.get_active()!=0:
            return False
        return True


    @classmethod
    def _is_valid_todo(cls, set_style:bool=False) -> bool:
        # Function checks if todo dialog fields are valid.
        # Used when "OK" clicked in the dialog.
        # Returns True if all fields valid; False if *any* field is invalid.
        # If a field is invalid and set_style==True it also adds a
        # CSS class to the widget, so the error is visibly indicated.
        # If the event is valid then it removes the error style, so
        # the error indication will disappear (regardless of set_style).
        # Note: If you change this, also update _reset_err_style() below.

        ret = True

        # Check description is non-empty
        ctx = cls.wid_desc.get_style_context()
        if not cls.wid_desc.get_text():
            ret = False
            if set_style:
                ctx.add_class(GUI.STYLE_ERR)
        else:
            ctx.remove_class(GUI.STYLE_ERR)

        # If due date is on, check given date is valid
        ctx = cls.wid_duedate.get_style_context()
        if cls.wid_duedate_switch.get_active() and not cls.wid_duedate.is_valid_date():
            ret = False
            if set_style:
                ctx.add_class(GUI.STYLE_ERR)
        else:
            ctx.remove_class(GUI.STYLE_ERR)

        return ret


    @classmethod
    def _reset_err_style(cls) -> None:
        # Remove 'dialog_error' style class from todo dialog widgets where
        # it might be set, so any visible indications of errors are removed.
        # Used, for example, when the dialog is reinitialised.
        for w in (cls.wid_desc, cls.wid_duedate):
            w.get_style_context().remove_class(GUI.STYLE_ERR)


    @classmethod
    def _validated_field_changed(cls, wid:Gtk.Entry) -> bool:
        # Callback. Called when a "validated field" changes.
        # A "validated field" is one that is checked with _is_valid_todo().
        # Function removes any error state styling that is no longer needed.
        # It does *not* add any new error styling.
        cls._is_valid_todo(set_style=False)
        return False # propagate event


    @classmethod
    def _get_entryinfo(cls) -> EntryInfo:
        # Decipher entry fields and return info as an EntryInfo object.
        desc = cls.wid_desc.get_text()
        stat = cls.wid_status.get_active_id()
        ei = EntryInfo(type=EntryInfo.TYPE_TODO, desc=desc, status=stat)
        list_idx = cls.wid_todolist.get_active()
        ei.set_categories(cls.list_default_cats[list_idx])
        if cls.wid_duedate_switch.get_active():
            ei.set_duedate(cls.wid_duedate.get_date_or_none())
        ei.set_priority(cls.wid_priority.get_active())
        return ei
