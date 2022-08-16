# -*- coding: utf-8 -*-
#
# pygenda_view.py
# "View" class definition - base class for Week View, Year View.
# Provides default implementations of functions.
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

from icalendar import cal as iCal, Event as iEvent, Todo as iTodo
from datetime import date as dt_date, timedelta
from typing import Optional, Union

from .pygenda_gui import GUI, EventDialogController
from .pygenda_util import datetime_to_time, datetime_to_date, date_to_datetime, format_time, format_compact_date, format_compact_time, format_compact_datetime, dt_lte
from .pygenda_calendar import Calendar
from .pygenda_entryinfo import EntryInfo


# Base class for pygenda Views (Week View, Year View, etc.)
class View:
    # Provide default implementations of required methods.

    @staticmethod
    def view_name() -> str:
        # Return name string to use in menu, should be localised.
        # This default should never be called, so provide dummy name.
        return 'Null View'


    @staticmethod
    def accel_key() -> int:
        # Return keycode for menu shortcut, should be localised.
        return 0


    @classmethod
    def init(cls) -> Gtk.Widget:
        # Initialise view and return Gtk widget for that view.
        # Called from GUI._init_views() on startup.
        return None


    @classmethod
    def renew_display(cls) -> None:
        # Called when we switch to this view.
        # Used to reset local state; default null implementation may be enough.
        pass


    @classmethod
    def redraw(cls, en_changes:bool) -> None:
        # Called when redraw required
        # en_changes: bool indicating if displayed entries need updating too
        pass


    @classmethod
    def keypress(cls, wid:Gtk.Widget, ev:Gdk.Event) -> None:
        # Called (from GUI.keypress()) on keypress (or repeat) event
        # Default does nothing. Derived views will override.
        pass


    @classmethod
    def new_entry_from_example(cls, en:Union[iEvent,iTodo]) -> None:
        # Creates new entry based on entry en. Used for pasting entries.
        # Type of entry should depend on View (e.g. Todo View -> to-do item).
        # Default implementation does nothing.
        pass


    @classmethod
    def paste_text(cls, txt:str) -> None:
        # Handle pasting of text.
        # Default implementation does nothing.
        pass


    @classmethod
    def cursor_date(cls) -> Optional[dt_date]:
        # Returns date (maybe datetime in the future) with cursor.
        # Default implementation: cursor not on date.
        return None


    @classmethod
    def cursor_todo_list(cls) -> Optional[int]:
        # returns index of todo list with cursor
        # Default implementation: cursor not on todo list.
        return None


    @staticmethod
    def entry_text_label(ev:iCal.Event, dt_st:dt_date, dt_end:dt_date) -> Gtk.Label:
        # Returns a GtkLabel with entry summary + icons as content.
        # Used by Week & Year views to display entries.
        lab = Gtk.Label()
        lab.set_line_wrap(True)
        lab.set_line_wrap_mode(PWrapMode.WORD_CHAR)
        lab.set_xalign(0)
        lab.set_yalign(0)
        endtm = View.entry_endtime(dt_st,dt_end,True)
        icons = View.entry_icons(ev,True)
        d_txt = ev['SUMMARY'] if 'SUMMARY' in ev else ''
        lab.set_text(u'{:s}{:s}{:s}'.format(d_txt,endtm,icons))
        View.add_event_styles(lab, ev)
        return lab


    @staticmethod
    def entry_icons(ev:iCal.Event, prefix_space:bool) -> str:
        # Returns string of icons for entry (repeat, alarm...)
        alarm = u'♫' # alternatives: alarm clock ⏰ (U+23F0), bell 🔔 (U+1F514)
        repeat = u'⟳'
        icons = ''
        if ev.walk('VALARM'):
            icons += alarm
        if 'RRULE' in ev:
            icons += repeat
        if prefix_space and icons:
            icons = ' {:s}'.format(icons)
        return icons


    @staticmethod
    def entry_endtime(dt_st:dt_date, dt_end:dt_date, frame_text:bool) -> str:
        # Returns end time in format suitable for displaying in entry.
        if not dt_end or dt_lte(dt_end, dt_st):
            return ''
        if type(dt_st) is dt_date and type(dt_end) is dt_date:
            end_date = dt_end-timedelta(1)
            if dt_st>=end_date:
                return ''
            t_str = format_compact_date(end_date, dt_st.year!=end_date.year, True)
        else:
            # At least one of dt_st,st_end is a datetime
            # => consider them *both* as datetimes
            st_date = datetime_to_date(dt_st)
            dt_end = date_to_datetime(dt_end)
            end_date = datetime_to_date(dt_end-timedelta(milliseconds=1))
            if st_date == end_date:
                t_str = format_compact_time(dt_end, True)
            else:
                t_str = format_compact_datetime(dt_end, st_date.year!=end_date.year, True)
        if frame_text and t_str:
            t_str = u' (→{:s})'.format(t_str)
        return t_str


    @staticmethod
    def add_event_styles(wid:Gtk.Label, ev:iCal.Event) -> None:
        # Adds formatting class to label corresponding to event status.
        # Allows entry to be formatted appropriately by CSS.
        if 'STATUS' in ev and ev['STATUS'] in ('TENTATIVE','CONFIRMED','CANCELLED'):
            ctx = wid.get_style_context()
            ctx.add_class(ev['STATUS'].lower())


    @staticmethod
    def scroll_to_row(rowbox:Gtk.Box, row:int, scroller:Gtk.ScrolledWindow) -> bool:
        # Given a box displaying entries in a scroller (such as those
        # in Week & Year views), scroll to reveal row number 'row'.
        # Note: this may need to be called after rows are rendered,
        #   so that the allocated_heights are correct
        top = rowbox.get_spacing()*row # to hold max value to show top of cell
        rows = rowbox.get_children()
        for i in range(row):
            top += rows[i].get_allocated_height()
        bot = top + rows[row].get_allocated_height()
        bot -= scroller.get_allocated_height()
        # Account for padding, margin, border
        # First get the widths from the style context
        ctx = rowbox.get_style_context()
        pad = ctx.get_padding(Gtk.StateFlags.NORMAL)
        bord = ctx.get_border(Gtk.StateFlags.NORMAL)
        marg = ctx.get_margin(Gtk.StateFlags.NORMAL)
        # Looks a bit odd to be exactly on edge, so go halfway into padding
        top += bord.top + marg.top + (pad.top+1)//2
        bot += pad.top + bord.top + marg.top + (pad.bottom+1)//2
        if bot>top: # need this if row height bigger than scroll area
            bot = top # to favour showing top, rather than bottom, of cell
        adj = scroller.get_vadjustment()
        v = adj.get_value()
        if top < v:
            adj.set_value(top)
        elif v < bot:
            adj.set_value(bot)
        # According to:
        # https://developer.gnome.org/glib/stable/glib-The-Main-Event-Loop.html#g-idle-add
        # returning False is the right thing to do for one-shot calls.
        # Not sure if this is required, but let's do it anyway.
        return False


    @staticmethod
    def y_to_day_row(rowbox:Gtk.Box, y:float, maxrow:int, scroller:Gtk.ScrolledWindow=None) -> int:
        # Helper function to convert y-coord to row index in day.
        # Used to calculate entry to jump to when entry list is clicked,
        # for example in Week or Year View.
        if maxrow <= 1:
            return 0
        rs = rowbox.get_spacing()
        # Take account of padding/border/margins/row-spacing/scroller...
        ctx = rowbox.get_style_context()
        yc = ctx.get_padding(Gtk.StateFlags.NORMAL).top
        yc += ctx.get_border(Gtk.StateFlags.NORMAL).top
        yc += ctx.get_margin(Gtk.StateFlags.NORMAL).top
        yc -= rs/2
        if scroller is not None:
            yc -= scroller.get_vadjustment().get_value()

        row = -1 # return value
        rows = rowbox.get_children()
        # accumulate height of rows until it's greater than target y
        for i in range(maxrow):
            row += 1
            yc += rows[i].get_allocated_height()
            yc += rs
            if yc > y:
                break
        return row


    @staticmethod
    def remove_all_classes(ctx:Gtk.StyleContext) -> None:
        # Helper function to remove all classes from a view context.
        # Used when redrawing Year view, might be used for other views.
        for c in ctx.list_classes():
            ctx.remove_class(c)


class View_DayUnit_Base(View):
    # Used as base class for Day & Year views
    @classmethod
    def new_entry_from_example(cls, en:Union[iEvent,iTodo]) -> None:
        # Creates new entry based on entry en. Used for pasting entries.
        # Implementation for Week and Year Views - makes an event.
        Calendar.new_entry_from_example(en, e_type=EntryInfo.TYPE_EVENT, dt_start=GUI.cursor_date)


    @classmethod
    def paste_text(cls, txt:str) -> None:
        # Handle pasting of text in Week/Year views.
        # Open a New Entry dialog with description initialised as txt
        date = cls.cursor_date()
        GLib.idle_add(EventDialogController.newevent, txt, date)


    @classmethod
    def cursor_date(cls) -> Optional[dt_date]:
        # Returns date(time) with cursor.
        # Default implementation: cursor not on date.
        return GUI.cursor_date


    @classmethod
    def cursor_edit_entry(cls) -> None:
        # Opens an entry edit dialog for the entry at the cursor,
        # or to create a new entry if the cursor is not on entry.
        # Assigned to the 'Enter' key in Week and Year views.
        en = cls.get_cursor_entry()
        if en is None:
            date = cls.cursor_date()
            EventDialogController.newevent(date=date)
        else:
            EventDialogController.editevent(en)


    @classmethod
    def get_cursor_entry(cls) -> Optional[iCal.Event]:
        # Returns entry at cursor position, or None if cursor not on entry.
        # Default: None. Derived classes will provided their implementations.
        return None


    # Bullets to use as markers in Week/Year views
    _BULLET = u'•'
    _BULLET_ALLDAY = u'‣' # alternatives:❖⍟✪⦿❂
    _BULLET_TODO = u'🅣' # alternative:Ⓣ

    @classmethod
    def marker_label(cls, ev:iCal.Event, dt_st:dt_date) -> Gtk.Label:
        # Returns bullet or entry time suitable for marking entries.
        # Used to display entries in Week and Year views.
        lab = Gtk.Label()
        lab.set_halign(Gtk.Align.END)
        lab.set_valign(Gtk.Align.START)
        if datetime_to_time(dt_st)!=False:
            mark = format_time(dt_st, True)
        elif type(ev) is iCal.Todo:
            mark = cls._BULLET_TODO
        elif 'DTEND' in ev:
            mark = cls._BULLET_ALLDAY
        else:
            mark = cls._BULLET
        lab.set_text(mark)

        return lab
