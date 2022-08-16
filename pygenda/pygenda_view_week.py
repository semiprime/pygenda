# -*- coding: utf-8 -*-
#
# pygenda_view_week.py
# Provides the "Week View" for Pygenda.
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

from calendar import day_abbr,month_name
from datetime import time as dt_time, date as dt_date, timedelta
from icalendar import cal as iCal
from locale import gettext as _
from typing import Optional

# pygenda components
from .pygenda_view import View_DayUnit_Base
from .pygenda_calendar import Calendar
from .pygenda_config import Config
from .pygenda_util import start_of_week, day_in_week, month_abbr, start_end_dts_occ, dt_lte
from .pygenda_gui import GUI, EventDialogController


# Singleton class for Week View
class View_Week(View_DayUnit_Base):
    Config.set_defaults('week_view',{
        'pageleft_datepos': 'left',
        'pageright_datepos': 'right',
    })

    _day_ent_count = [0]*7 # entry count for each day
    _visible_occurrences = []
    _week_viewed = None # So view will be fully redrawn when needed
    _last_cursor = None
    _scroll_callback_id = None
    CURSOR_STYLE = 'weekview_cursor'

    @staticmethod
    def view_name() -> str:
        # Return (localised) string to use in menu
        return _('_Week View')

    @staticmethod
    def accel_key() -> int:
        # Return (localised) keycode for menu shortcut
        k = _('week_view_accel')
        return ord(k[0]) if len(k)>0 else 0


    @classmethod
    def init(cls) -> Gtk.Widget:
        # Called on startup.
        # Gets view framework from glade file & tweaks/adds a few elements.
        # Returns widget containing view.
        cls._topbox = GUI._builder.get_object('view_week')
        cls._month_label = GUI._builder.get_object('week_label_month')
        cls._weekno_label = GUI._builder.get_object('week_label_weekno')
        cls._init_week_widgets()
        cls._init_keymap()
        return cls._topbox


    @classmethod
    def _init_week_widgets(cls) -> None:
        # Initialise widgets - create day labels, entry spaces etc.
        # Do this here so it take account of start_week_day setting,
        # page*_datepos settings, and set CSS styles for each day.

        # Create widgets for day labels & text spaces
        cls._day_eventbox = []
        cls._day_label = []
        cls._day_rows = []
        cls._day_scroll = []
        st_wk = Config.get_int('global','start_week_day')
        dpos_r = Config.get('week_view','pageleft_datepos')=='right'
        day_ab = ('mon','tue','wed','thu','fri','sat','sun')#don't trans
        for i in range(7):
            # create event box & contained box
            cls._day_eventbox.append(Gtk.EventBox())
            day_box = Gtk.Box()
            ctx = day_box.get_style_context()
            # Add classes for css flexibility
            ctx.add_class('weekview_day')
            ctx.add_class('weekview_day{:d}'.format(i))
            ctx.add_class('weekview_{:s}'.format(day_ab[(i+st_wk)%7]))
            cls._day_eventbox[i].add(day_box)
            cls._day_eventbox[i].connect("button_press_event", cls.click_date)
            # labels
            cls._day_label.append(Gtk.Label())
            cls._day_label[i].set_justify(Gtk.Justification.CENTER)
            cls._day_label[i].set_xalign(0.5)
            cls._day_label[i].set_yalign(0.5)
            ctx = cls._day_label[i].get_style_context()
            ctx.add_class('weekview_labelday')
            if i==3: # starting rightpage
                dpos_r = Config.get('week_view','pageright_datepos')=='right'
            if dpos_r:
                day_box.pack_end(cls._day_label[i], False, False, 0)
            else:
                day_box.pack_start(cls._day_label[i], False, False, 0)
            # scroller & textview
            day_scroller = Gtk.ScrolledWindow()
            cls._day_scroll.append(day_scroller)
            day_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            day_scroller.set_overlay_scrolling(False)
            day_scroller.set_hexpand(True)
            cls._day_rows.append(Gtk.Box(orientation=Gtk.Orientation.VERTICAL))
            day_scroller.add(cls._day_rows[i])
            ctx = cls._day_rows[i].get_style_context()
            ctx.add_class('weekview_daytext')
            day_box.pack_start(day_scroller, True, True, 0)

        # Attach elements to pages
        page_l = GUI._builder.get_object('week_page_l')
        page_r = GUI._builder.get_object('week_page_r')
        for i in range(3): # Left
            page_l.pack_start(cls._day_eventbox[i], True, True, 0)
        for i in range(3,7): # ... and right
            page_r.pack_start(cls._day_eventbox[i], True, True, 0)


    @classmethod
    def _set_label_text(cls) -> None:
        # Sets date and month label text and style classes.
        # Called on view redraw.
        cls._last_cursor = None
        dt = start_of_week(GUI.cursor_date)
        cls._week_viewed = dt
        dt_end = dt + timedelta(days=6)
        # Month label
        if dt.month == dt_end.month:
            mn = month_name[dt.month].capitalize()
            ml = u'{mon:s} {yr:d}'.format(mon=mn, yr=dt.year)
        elif dt.year == dt_end.year:
            msn = month_abbr[dt.month].capitalize()
            ml = u'{mon_st:s} – {mon_end:s} {yr:d}'.format(mon_st=msn, mon_end=month_abbr[dt_end.month], yr=dt.year)
        else: # month & year different
            msn = month_abbr[dt.month].capitalize()
            ml = u'{mon_st:s} {yr_st:d} – {mon_end:s} {yr_end:d}'.format(mon_st=msn, mon_end=month_abbr[dt_end.month], yr_st=dt.year, yr_end=dt_end.year)
        cls._month_label.set_text(ml)

        # Week number label
        # Week 1 is the first to include 4+ days of year.
        # E.g. if week starts Monday then Wk1 is first to include a Thursday.
        wkno = (dt.timetuple().tm_yday+9)//7
        if wkno==53 and dt.day>=29:
            wkno_txt = _('Week 53/Week 1')
        else:
            wkno_txt = _('Week {}').format(wkno)
        cls._weekno_label.set_text(wkno_txt)

        # Day labels
        today = dt_date.today()
        for i in range(7):
            ctx = cls._day_eventbox[i].get_style_context()
            if dt<today:
                ctx.add_class('weekview_pastday')
            else:
                ctx.remove_class('weekview_pastday')
            if dt==today:
                ctx.add_class('weekview_today')
            else:
                ctx.remove_class('weekview_today')

            dn = day_abbr[dt.weekday()]
            if dn[-1]=='.':
                dn = dn[:-1] # remove dot
            cls._day_label[i].set_text(u'{day:s}\n{date:d}'.format(day=dn,date=dt.day))
            dt += timedelta(days=1)


    @classmethod
    def _set_entry_text(cls) -> None:
        # Sets label text and style classes for event-displaying labels.
        # Called on view redraw.
        cls._last_cursor = None
        dt = start_of_week(GUI.cursor_date)
        cls._visible_occurrences = Calendar.occurrence_list(dt, dt+timedelta(days=7))
        itr = iter(cls._visible_occurrences)
        try:
            occ = next(itr)
        except StopIteration:
            occ = None
        cls._day_ent_count = [0]*7 # we'll fill this in as we display
        for i in range(7):
            dt_nxt = dt + timedelta(days=1)
            # Delete anything previously written to day v-box
            cls._day_rows[i].foreach(Gtk.Widget.destroy)
            while True:
                if occ is None:
                    break
                occ_dt_sta,occ_dt_end = start_end_dts_occ(occ)
                if dt_lte(dt_nxt, occ_dt_sta):
                    # into next day so break this loop
                    break
                row = Gtk.Box()
                # Create entry mark (bullet or time) & add to row
                mark_label = cls.marker_label(occ[0], occ_dt_sta)
                ctx = mark_label.get_style_context()
                ctx.add_class('weekview_marker') # add style for CSS
                row.add(mark_label)

                # Create entry content label & add to row
                cont_label = cls.entry_text_label(occ[0],occ_dt_sta,occ_dt_end)
                cont_label.set_hexpand(True) # Also sets hexpand_set to True
                row.add(cont_label)
                cls._day_rows[i].add(row)
                cls._day_ent_count[i] += 1
                try:
                    occ = next(itr)
                except StopIteration:
                    occ = None
            if cls._day_ent_count[i]==0:
                # an empty day, need something for cursor
                mark_label = Gtk.Label()
                ctx = mark_label.get_style_context()
                ctx.add_class('weekview_marker')
                mark_label.set_halign(Gtk.Align.START) # else cursor fills line
                cls._day_rows[i].add(mark_label)
            dt = dt_nxt
            cls._day_rows[i].show_all()


    @classmethod
    def _show_cursor(cls) -> None:
        # Locates bullet/date corresponding to the current cursor and adds
        # 'weekview_cursor' class to it so cursor is visible via CSS styling.
        dy = day_in_week(GUI.cursor_date)
        ecount = cls._day_ent_count[dy]
        i = GUI.cursor_idx_in_date
        if i < 0 or i >= ecount:
            i = max(0,ecount-1)
            GUI.cursor_idx_in_date = i
        cls._hide_cursor()
        row = cls._day_rows[dy].get_children()[i]
        if ecount==0:
            mk = row
        else:
            mk = row.get_children()[0]
        ctx = mk.get_style_context()
        ctx.add_class(cls.CURSOR_STYLE)
        cls._last_cursor = int(dy+8*i)
        if cls._scroll_callback_id is not None:
            # Cancel existing callback to prevent inconsistent scroll requests.
            GLib.source_remove(cls._scroll_callback_id)
            cls._scroll_callback_id = None
        if cls._day_ent_count[dy] > 0:
            # We may need to scroll content to show entry at cursor.
            # Want this to happen after redraw, otherwise, can't access
            # dimensions of elements needed to calculate scroll size (because
            # they haven't been calculated). So delay scroll to after redraw.
            # We save the returned id so the callback can be cancelled.
            cls._scroll_callback_id = GLib.idle_add(cls._scroll_to_row, cls._day_rows[dy], i, cls._day_scroll[dy], priority=GLib.PRIORITY_HIGH_IDLE+30)


    @classmethod
    def _scroll_to_row(cls, rowbox:Gtk.Box, row:int, scroller:Gtk.ScrolledWindow) -> bool:
        # Local version of scroll_to_row() that clears the id, then
        # calls the parent class scroll_to_row() to do the work.
        cls._scroll_callback_id = None
        return cls.scroll_to_row(rowbox, row, scroller)


    @classmethod
    def _hide_cursor(cls) -> None:
        # Clears 'weekview_cursor' style class from cursor position,
        # so cursor is no longer visible.
        if cls._last_cursor is not None:
            # _last_cursor is an int split into two parts:
            # Lower 3 bits give day, other higher bits give entry within day
            dy = cls._last_cursor%8
            row = cls._day_rows[dy].get_children()[cls._last_cursor//8]
            if cls._day_ent_count[dy]==0:
                mk = row
            else:
                mk = row.get_children()[0]
            ctx = mk.get_style_context()
            ctx.remove_class(cls.CURSOR_STYLE)
            cls._last_cursor = None


    @classmethod
    def get_cursor_entry(cls) -> iCal.Event:
        # Returns entry at cursor position, or None if cursor not on entry.
        # Called from cursor_edit_entry() & delete_request().
        dy = day_in_week(GUI.cursor_date)
        if cls._day_ent_count[dy]==0:
            return None
        i = sum(cls._day_ent_count[:dy])
        i += GUI.cursor_idx_in_date
        return cls._visible_occurrences[i][0]


    @classmethod
    def renew_display(cls) -> None:
        # Called when we switch to this view to reset state.
        cls._week_viewed = None


    @classmethod
    def redraw(cls, en_changes:bool) -> None:
        # Called when redraw required.
        # en_changes: bool indicating if displayed entries need updating too
        if cls._week_viewed != start_of_week(GUI.cursor_date):
            cls._set_label_text()
            en_changes = True
        if en_changes:
            cls._set_entry_text()
        cls._show_cursor()


    @classmethod
    def _cursor_move_up(cls) -> None:
        # Callback for user moving cursor up.
        GUI.cursor_idx_in_date -= 1
        if GUI.cursor_idx_in_date < 0:
            GUI.cursor_inc(timedelta(days=-1))
            # Leave idx_in_date as -1 since that signals last entry
            GUI.today_toggle_date = None
        else:
            cls._show_cursor()


    @classmethod
    def _cursor_move_dn(cls) -> None:
        # Callback for user moving cursor down.
        GUI.cursor_idx_in_date += 1
        dy = day_in_week(GUI.cursor_date)
        if GUI.cursor_idx_in_date >= cls._day_ent_count[dy]:
            GUI.cursor_inc(timedelta(days=1), 0)
            GUI.today_toggle_date = None
        else:
            cls._show_cursor()


    @classmethod
    def _cursor_move_lt(cls) -> None:
        # Callback for user moving cursor left.
        i = day_in_week(GUI.cursor_date)
        d = -7 if i<3 else (-3 if i==3 else -4)
        GUI.cursor_inc(timedelta(days=d), 0)
        GUI.today_toggle_date = None


    @classmethod
    def _cursor_move_rt(cls) -> None:
        # Callback for user moving cursor right.
        i = day_in_week(GUI.cursor_date)
        d = 4 if i<3 else 7
        GUI.cursor_inc(timedelta(days=d), 0)
        GUI.today_toggle_date = None


    @classmethod
    def _cursor_move_today(cls) -> None:
        # Callback for user toggling cursor between today & another date
        today = dt_date.today()
        if GUI.cursor_date != today:
            GUI.today_toggle_date = GUI.cursor_date
            GUI.today_toggle_idx = GUI.cursor_idx_in_date
            GUI.cursor_set(today,0)
        elif GUI.today_toggle_date is not None:
            GUI.cursor_set(GUI.today_toggle_date,GUI.today_toggle_idx)


    @classmethod
    def _init_keymap(cls) -> None:
        # Initialises KEYMAP for class. Called from init() since it needs
        # to be called after class construction, so that functions exist.
        cls._KEYMAP = {
            Gdk.KEY_Up: lambda: cls._cursor_move_up(),
            Gdk.KEY_Down: lambda: cls._cursor_move_dn(),
            Gdk.KEY_Right: lambda: cls._cursor_move_rt(),
            Gdk.KEY_Left: lambda: cls._cursor_move_lt(),
            Gdk.KEY_space: lambda: cls._cursor_move_today(),
            Gdk.KEY_Return: lambda: cls.cursor_edit_entry(),
        }


    @classmethod
    def keypress(cls, wid:Gtk.Widget, ev:Gdk.EventKey) -> None:
        # Handle key press event in Week view.
        # Called (from GUI.keypress()) on keypress (or repeat) event
        try:
            f = cls._KEYMAP[ev.keyval]
            GLib.idle_add(f)
        except KeyError:
            # If it's a character key, take as first of new entry
            # !! Bug: only works for ASCII characters
            if ev.state & (Gdk.ModifierType.CONTROL_MASK|Gdk.ModifierType.MOD1_MASK)==0 and Gdk.KEY_exclam <= ev.keyval <= Gdk.KEY_asciitilde:
                date = cls.cursor_date()
                GLib.idle_add(EventDialogController.newevent, chr(ev.keyval), date)


    @classmethod
    def click_date(cls, wid:Gtk.Widget, ev:Gdk.EventButton) -> None:
        # Callback. Called whenever a date is clicked/tapped.
        # Moves cursor to date/item clicked
        try:
            new_day = cls._day_eventbox.index(wid)
        except ValueError:
            return

        new_idx = 0 # default index if not going to specific entry

        # Has user clicked on a specific entry within day?
        # If so, move the cursor to that entry.
        if cls._day_ent_count[new_day] > 1: # Only check if >1 entry in the day
            # Check if clicked in day's label area
            d_wids = wid.get_child().get_children()
            ll = isinstance(d_wids[0],Gtk.Label) # True if left label
            if ll != (ev.x < d_wids[0].get_allocated_width()): # Clicked entries
                # We're not clicking in date label area, use y to calc entry
                new_idx = cls.y_to_day_row(cls._day_rows[new_day], ev.y, cls._day_ent_count[new_day], cls._day_scroll[new_day])

        GLib.idle_add(GUI.cursor_set, cls._day_index_to_date(new_day), new_idx)


    @classmethod
    def _day_index_to_date(cls, idx:int) -> Optional[dt_date]:
        # Given an day index idx=0...6 of day cell in the visible Week View,
        # return the corresponding date
        if cls._week_viewed is None:
            return None
        return cls._week_viewed+timedelta(days=idx)
