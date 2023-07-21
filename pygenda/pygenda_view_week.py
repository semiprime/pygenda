# -*- coding: utf-8 -*-
#
# pygenda_view_week.py
# Provides the "Week View" for Pygenda.
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
from gi.repository import Gtk, Gdk, GLib

from calendar import day_abbr,month_name
from datetime import time as dt_time, date as dt_date, datetime as dt_datetime, timedelta
from icalendar import cal as iCal
from locale import gettext as _
from typing import Optional

# pygenda components
from .pygenda_view import View, View_DayUnit_Base
from .pygenda_calendar import Calendar
from .pygenda_config import Config
from .pygenda_util import start_of_week, day_in_week, month_abbr, start_end_dts_occ, dt_lt, dt_lte
from .pygenda_gui import GUI
from .pygenda_dialog_event import EventDialogController


# Singleton class for Week View
class View_Week(View_DayUnit_Base):
    Config.set_defaults('week_view',{
        'pageleft_datepos': 'left',
        'pageright_datepos': 'right',
        'show_ongoing_event': 'first_day',
        'show_event_location': 'always',
        'zoom_levels': 5,
        'default_zoom': 1,
    })

    _day_ent_count = [0]*7 # entry count for each day
    _day_entries = [[], [], [], [], [], [], []]
    _week_viewed = None # So view will be fully redrawn when needed
    _last_cursor = None
    _scroll_to_cursor_in_day = None
    _target_entry = None
    _is_repeat_key = False
    CURSOR_STYLE = 'weekview_cursor'

    SHOW_LOC_ALWAYS = 1 # constant 'enum' for _show_location flag

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
        GUI.load_glade_file('view_week.glade')
        cls._topbox = GUI._builder.get_object('view_week')
        cls._month_label = GUI._builder.get_object('week_label_month')
        cls._weekno_label = GUI._builder.get_object('week_label_weekno')
        cls._init_week_widgets()
        cls._init_keymap()
        cls._init_config()
        cls.init_zoom('week_view', cls._topbox.get_style_context())
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
            cls._day_eventbox[i].connect('button_press_event', cls.click_date)
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
            cls._day_rows[i].connect('draw', cls._pre_datecontent_draw, i)
            day_box.pack_start(day_scroller, True, True, 0)

        # Attach elements to pages
        page_l = GUI._builder.get_object('week_page_l')
        page_r = GUI._builder.get_object('week_page_r')
        for i in range(3): # Left
            page_l.pack_start(cls._day_eventbox[i], True, True, 0)
        for i in range(3,7): # ... and right
            page_r.pack_start(cls._day_eventbox[i], True, True, 0)


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
    def _init_config(cls) -> None:
        # Initialisation from config settings.
        # Set _show_ongoing flag from config.
        show_ongoing = Config.get('week_view','show_ongoing_event')
        map = {'every_day':1, 'first_day':0}
        cls._show_ongoing = map[show_ongoing] if show_ongoing in map else 0

        # Set _show_location flag from config.
        show_loc = Config.get('week_view','show_event_location')
        map = {'always':cls.SHOW_LOC_ALWAYS, 'never':0}
        cls._show_location = map[show_loc] if show_loc in map else 0


    @classmethod
    def _set_label_text(cls) -> None:
        # Sets date and month label text and style classes.
        # Called on view redraw.
        cls._last_cursor = None
        dt = start_of_week(View._cursor_date)
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
        dt = start_of_week(View._cursor_date)
        cls._day_entries = [[], [], [], [], [], [], []] # reset stored events
        cls._day_ent_count = [0]*7
        sorted_occurrences = Calendar.occurrence_list(dt, dt+timedelta(days=7))
        itr = iter(sorted_occurrences)
        try:
            occ = next(itr)
        except StopIteration:
            occ = None
        if cls._show_ongoing:
            ongoing = [] # !! Replace with call to calendar
            rollover_dt = dt # Might want this to be 2am or something
        oneday = timedelta(days=1)
        for i in range(7):
            dt_nxt = dt + oneday
            # Delete anything previously written to day v-box
            cls._day_rows[i].foreach(Gtk.Widget.destroy)
            if cls._show_ongoing:
                # Add rows for the ongoing events
                rollover_dt += oneday
                j = 0
                while j < len(ongoing):
                    occo = ongoing[j]
                    occ_dt_sta,occ_dt_end = start_end_dts_occ(occo)
                    cls._add_day_entry_row(occo[0], occ_dt_sta, occ_dt_end, i, show_loc=False, is_ongoing=True)
                    # If this occurrence ends here, remove it from 'ongoing'
                    if dt_lte(occ_dt_end, rollover_dt):
                        ongoing.pop(j)
                    else:
                        j += 1
            # Now we add events that start on this day
            while True:
                if occ is None:
                    break
                occ_dt_sta,occ_dt_end = start_end_dts_occ(occ)
                if dt_lte(dt_nxt, occ_dt_sta):
                    # into next day so break this loop
                    break
                # First, see if we've hit the cursor target entry
                if cls._target_entry is not None and cls._target_entry is occ[0] and dt==View._cursor_date:
                    View._cursor_idx_in_date = cls._day_ent_count[i]
                    cls._target_entry = None
                cls._add_day_entry_row(occ[0], occ_dt_sta, occ_dt_end, i, cls._show_location)
                if cls._show_ongoing:
                    # Add to 'ongoing' list if occurrence goes into next day
                    if occ_dt_end and dt_lt(rollover_dt, occ_dt_end):
                        ongoing.append(occ)
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
        cls._target_entry = None # just in case - should be done already


    @classmethod
    def _add_day_entry_row(cls, ev:iCal.Event, dt_st:dt_date, dt_end:dt_date, dayidx:int, show_loc:bool, is_ongoing:bool=False) -> None:
        # Add Gtk labels for event 'ev', occurrence at time/date from 'dt_st'
        # to 'dt_end', in day 'dayidx' (e.g. 0=Monday if week starts Monday).
        # Used when displaying week contents.
        row = Gtk.Box()
        # Create entry mark (bullet or time) & add to row
        mark_label = cls.marker_label(ev, dt_st, is_ongoing)
        ctx = mark_label.get_style_context()
        ctx.add_class('weekview_marker') # add style for CSS
        row.add(mark_label)
        # Create entry content label & add to row
        cont_label = cls.entry_text_label(ev, dt_st, dt_end, add_location=show_loc)
        cont_label.set_hexpand(True) # Also sets hexpand_set to True
        row.add(cont_label)
        cls._day_rows[dayidx].add(row)
        cls._day_entries[dayidx].append(ev)
        cls._day_ent_count[dayidx] += 1


    @classmethod
    def _show_cursor(cls) -> None:
        # Locates bullet/date corresponding to the current cursor and adds
        # 'weekview_cursor' class to it so cursor is visible via CSS styling.
        dy = day_in_week(View._cursor_date)
        ecount = cls._day_ent_count[dy]
        i = View._cursor_idx_in_date
        if i < 0 or i >= ecount:
            i = max(0,ecount-1)
            View._cursor_idx_in_date = i
        cls._hide_cursor()
        row = cls._day_rows[dy].get_children()[i]
        if ecount==0:
            mk = row
        else:
            mk = row.get_children()[0]
        ctx = mk.get_style_context()
        ctx.add_class(cls.CURSOR_STYLE)
        cls._last_cursor = int(dy+8*i)
        if cls._day_ent_count[dy] > 0:
            # We may need to scroll content to show entry at cursor.
            cls._day_rows[dy].queue_draw()
            cls._scroll_to_cursor_in_day = dy # to be read in draw handler
        else:
            cls._scroll_to_cursor_in_day = None
        GUI.set_menu_elts(on_event=(ecount!=0)) # Enable/disable hide menu items


    @classmethod
    def _pre_datecontent_draw(cls, wid:Gtk.Widget, cairo_ctx, day:int) -> bool:
        # Callback called on 'draw' event on date_content.
        # Called before drawing date content.
        # Used to scroll window when cursor has been moved (since we
        # need to have calculated the layout to know where to scoll to).
        if cls._scroll_to_cursor_in_day == day:
            cls.scroll_to_row(cls._day_rows[day], View._cursor_idx_in_date, cls._day_scroll[day])
            cls._scroll_to_cursor_in_day = None
        return False # propagate event


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
    def cursor_set_date(cls, dt:dt_date, idx:int=0) -> bool:
        # Set current cursor date & index in date.
        # Override default method & return True to indicate success.
        View._cursor_date = dt
        View._cursor_idx_in_date = idx
        return True


    @classmethod
    def get_cursor_entry(cls) -> iCal.Event:
        # Returns entry at cursor position, or None if cursor not on entry.
        # Called from cursor_edit_entry() & delete_request().
        dy = day_in_week(View._cursor_date)
        if cls._day_ent_count[dy]==0:
            return None
        return cls._day_entries[dy][View._cursor_idx_in_date]


    @classmethod
    def renew_display(cls) -> None:
        # Called when we switch to this view to reset state.
        cls._week_viewed = None


    @classmethod
    def redraw(cls, en_changes:bool) -> None:
        # Called when redraw required.
        # en_changes: bool indicating if displayed entries need updating too
        if cls._week_viewed != start_of_week(View._cursor_date):
            cls._set_label_text()
            cls._reset_scrollers()
            en_changes = True
        if en_changes:
            cls._set_entry_text()
        cls._show_cursor()


    @classmethod
    def _reset_scrollers(cls) -> None:
        # Resets all day vertical scrollbars to top
        for s in cls._day_scroll:
            s.get_vadjustment().set_value(0)


    @classmethod
    def _cursor_move_up(cls) -> None:
        # Callback for user moving cursor up.
        View._cursor_idx_in_date -= 1
        if View._cursor_idx_in_date < 0:
            cls.cursor_inc(timedelta(days=-1))
            # Leave idx_in_date as -1 since that signals last entry
            View._today_toggle_date = None
        else:
            cls._show_cursor()


    @classmethod
    def _cursor_move_dn(cls) -> None:
        # Callback for user moving cursor down.
        View._cursor_idx_in_date += 1
        dy = day_in_week(View._cursor_date)
        if View._cursor_idx_in_date >= cls._day_ent_count[dy]:
            cls.cursor_inc(timedelta(days=1), 0)
            View._today_toggle_date = None
        else:
            cls._show_cursor()


    @classmethod
    def _cursor_move_lt(cls) -> None:
        # Callback for user moving cursor left.
        i = day_in_week(View._cursor_date)
        d = -4 if i>3 else -3 if (not cls._is_repeat_key or i==3) else -7
        cls.cursor_inc(timedelta(days=d), 0)
        View._today_toggle_date = None
        cls._is_repeat_key = True # for next time, unless cancelled by release


    @classmethod
    def _cursor_move_rt(cls) -> None:
        # Callback for user moving cursor right.
        i = day_in_week(View._cursor_date)
        d = (4 if i<3 else 7) if cls._is_repeat_key else 4 if i<4 else 3
        cls.cursor_inc(timedelta(days=d), 0)
        View._today_toggle_date = None
        cls._is_repeat_key = True # for next time, unless cancelled by release


    @classmethod
    def _cursor_move_today(cls) -> None:
        # Callback for user toggling cursor between today & another date
        today = dt_date.today()
        if View._cursor_date != today:
            View._today_toggle_date = View._cursor_date
            View._today_toggle_idx = View._cursor_idx_in_date
            cls.cursor_set_date(today)
            cls.redraw(en_changes=False)
        elif View._today_toggle_date is not None:
            cls.cursor_set_date(View._today_toggle_date, idx=View._today_toggle_idx)
            cls.redraw(en_changes=False)


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
                GLib.idle_add(EventDialogController.new_event, chr(ev.keyval), date)


    @classmethod
    def keyrelease(cls, wid:Gtk.Widget, ev:Gdk.EventKey) -> None:
        # Handle key release event.
        # Cancels flag to indicate keypress is, in fact, a key repeat.
        cls._is_repeat_key = False


    @classmethod
    def click_date(cls, wid:Gtk.Widget, ev:Gdk.EventButton) -> bool:
        # Callback. Called whenever a date is clicked/tapped.
        # Moves cursor to date/item clicked
        try:
            new_day = cls._day_eventbox.index(wid)
        except ValueError:
            return False # propagate event

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

        GLib.idle_add(cls._jump_to_date, cls._day_index_to_date(new_day), new_idx)
        return True # event handled - don't propagate


    @classmethod
    def _jump_to_date(cls, dt:dt_date, idx:int) -> None:
        # Idle callback to move cursor to given date, e.g. on click
        cls.cursor_set_date(dt, idx=idx)
        cls.redraw(en_changes=False)


    @classmethod
    def _day_index_to_date(cls, idx:int) -> Optional[dt_date]:
        # Given an day index idx=0...6 of day cell in the visible Week View,
        # return the corresponding date
        if cls._week_viewed is None:
            return None
        return cls._week_viewed+timedelta(days=idx)
