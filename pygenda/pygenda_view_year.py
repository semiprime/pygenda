# -*- coding: utf-8 -*-
#
# pygenda_view_year.py
# Provides the "Year View" for Pygenda.
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

import calendar
from datetime import date as dt_date, datetime as dt_datetime, timedelta
from locale import gettext as _
from icalendar import cal as iCal
from typing import Tuple

# pygenda components
from .pygenda_view import View, View_DayUnit_Base
from .pygenda_gui import GUI
from .pygenda_dialog_event import EventDialogController
from .pygenda_config import Config
from .pygenda_calendar import Calendar
from .pygenda_util import start_end_dts_occ


# Singleton class for Year View
class View_Year(View_DayUnit_Base):
    Config.set_defaults('year_view',{
        'show_event_location': 'always',
        'zoom_levels': 5,
        'default_zoom': 2,
    })

    DAY_CLASS = [ 'yearview_day_{}'.format(s) for s in ['mon','tue','wed','thu','fri','sat','sun'] ]
    GRID_COLUMNS = 37
    GRID_ROWS = 12 # One per month
    GRID_CURSOR_STYLE = 'yearview_cursor'
    ENTRY_CURSOR_STYLE = 'yearview_entry_cursor'
    _target_col = None
    _year_viewed = -1 # Indicates next redraw will draw year
    _last_cursor = None
    _visible_occurrences = None
    _show_datecontent_pending = False
    _date_content_count = 0
    _scroll_to_cursor_required = False
    _target_entry = None

    SHOW_LOC_ALWAYS = 1 # constant 'enum' for _show_location flag

    @staticmethod
    def view_name() -> str:
        # Return (localised) string to use in menu
        return _('_Year View')

    @staticmethod
    def accel_key() -> int:
        # Return (localised) keycode for menu shortcut
        k = _('year_view_accel')
        return ord(k[0]) if len(k)>0 else 0


    @classmethod
    def init(cls) -> Gtk.Widget:
        # Called on startup.
        # Gets view framework from glade file & tweaks/adds a few elements.
        # Returns widget containing view.
        GUI.load_glade_file('view_year.glade')
        cls._topbox = GUI._builder.get_object('view_year')
        cls._grid_cells = GUI._builder.get_object('year_grid_days')
        cls._date_label = GUI._builder.get_object('year_datelabel')
        cls._date_content_scroll = GUI._builder.get_object('year_datecontent_scroll')
        cls._date_content = GUI._builder.get_object('year_datecontent')
        cls._draw_day_month_labels()
        cls._init_keymap()
        cls._init_grid()
        cls._init_config()
        cls.init_zoom('year_view', cls._topbox.get_style_context())

        # Connect signal handlers
        HANDLERS = {
            'year_grid_click': cls.click_grid,
            'year_dtcont_click': cls.click_events,
            'year_dtcont_draw': cls._pre_datecontent_draw,
            }
        GUI._builder.connect_signals(HANDLERS)

        return cls._topbox


    @classmethod
    def _draw_day_month_labels(cls) -> None:
        # Adds text to grid day and month labels.
        # Called only at initialisation.
        mon_names = GUI._builder.get_object('month_names')
        for i in range(cls.GRID_ROWS):
            l = Gtk.Label(calendar.month_abbr[i+1].capitalize())
            ctx = l.get_style_context()
            ctx.add_class('yearview_month_label')
            mon_names.add(l)

        st_wk = Config.get_int('global','start_week_day')
        day_names = GUI._builder.get_object('day_names')
        day_label_txt = [ d[0].capitalize() for d in calendar.day_abbr ]
        for i in range(st_wk,st_wk+cls.GRID_COLUMNS):
            l = Gtk.Label(day_label_txt[i%7])
            ctx = l.get_style_context()
            ctx.add_class('yearview_day_label')
            ctx.add_class(cls.DAY_CLASS[i%7])
            day_names.add(l)


    @classmethod
    def _init_keymap(cls) -> None:
        # Initialises KEYMAP for class. Called from init() since it needs
        # to be called after class construction, so that functions exist.
        cls._KEYMAP = {
            Gdk.KEY_Left: lambda: cls._cursor_move_lr(-1),
            Gdk.KEY_Right: lambda: cls._cursor_move_lr(1),
            Gdk.KEY_Up: lambda: cls._cursor_move_up(),
            Gdk.KEY_Down: lambda: cls._cursor_move_dn(),
            Gdk.KEY_Home: lambda: cls._cursor_move_stmon(),
            Gdk.KEY_End: lambda: cls._cursor_move_endmon(),
            Gdk.KEY_Page_Up: lambda: cls._cursor_move_pgupdn(-1),
            Gdk.KEY_Page_Down: lambda: cls._cursor_move_pgupdn(1),
            Gdk.KEY_space: lambda: cls._cursor_move_today(),
            Gdk.KEY_Return: lambda: cls.cursor_edit_entry(),
        }
        cls._KEYMAP_SHIFT = {
            Gdk.KEY_Up: lambda: cls._idxcursor_move_up(),
            Gdk.KEY_Down: lambda: cls._idxcursor_move_dn(),
            Gdk.KEY_Page_Up: lambda: cls._idxcursor_move_up(), # !! Placeholder
            Gdk.KEY_Page_Down: lambda: cls._idxcursor_move_dn(),#!! Placeholder
        }


    @classmethod
    def _init_grid(cls) -> None:
        # Adds labels to each grid cell
        for m in range(0,cls.GRID_ROWS):
            for d in range(0,cls.GRID_COLUMNS):
                l = Gtk.Label()
                l.set_xalign(0)
                l.set_yalign(0)
                cls._grid_cells.attach(l,d,m,1,1)


    @classmethod
    def _init_config(cls) -> None:
        # Initialisation from config settings.
        # Set _show_location flag from config.
        show_loc = Config.get('year_view','show_event_location')
        map = {'always':cls.SHOW_LOC_ALWAYS, 'never':0}
        cls._show_location = map[show_loc] if show_loc in map else 0


    @classmethod
    def _draw_year(cls) -> None:
        # Draws year - adds formatting classes to cells, labels to some dates.
        # Called on redraw if year has changed.
        # Function a bit disorganised, tidying might be beneficial...
        c_date = View._cursor_date
        yr = c_date.year
        cls._year_viewed = yr
        l = GUI._builder.get_object('year_yearlabel')
        l.set_text(str(yr))

        st_wk = Config.get_int('global','start_week_day')
        mon_labs = GUI._builder.get_object('month_names').get_children()
        day_labs = GUI._builder.get_object('day_names').get_children()
        date = dt_date(year=yr,month=1,day=1)
        oneday = timedelta(days=1)
        today = dt_date.today()

        for m in range(1,cls.GRID_ROWS+1):
            day,daycount = calendar.monthrange(yr,m)
            col = (day-st_wk)%7 # Column for first of the month
            ctx = mon_labs[m-1].get_style_context()
            if col==0:
                ctx.add_class('yearview_leftofdaycell')
            else:
                ctx.remove_class('yearview_leftofdaycell')
            if m!=cls.GRID_ROWS:
                # This is to take account of grid lines above next month
                nday,ndaycount = calendar.monthrange(yr,m+1)
                ncol = (nday-st_wk)%7
                ndayend = ncol+ndaycount
            else:
                ncol = 7
                ndayend = 0
            for c in range(col): # Empty cells before col
                l = cls._grid_cells.get_child_at(c,m-1)
                l.set_text('')
                ctx = l.get_style_context()
                cls.remove_all_classes(ctx)
                ctx.add_class('yearview_emptycell')
                if c==col-1:
                    ctx.add_class('yearview_leftofdaycell')
                if c>=ncol:
                    ctx.add_class('yearview_abovedaycell')
                if m==1:
                    ctx = day_labs[c].get_style_context()
                    ctx.remove_class('yearview_abovedaycell')

            for d in range(daycount):
                # Potential optimisations here? Central columns are always in
                # year, so no need to remove&re-add class yearview_daycell etc.
                # Also if not start of week, will never be start of week,
                # so we know label text is already ''.
                t = ''
                if day==st_wk or d==0 or d==daycount-1:
                    t = str(d+1)
                l = cls._grid_cells.get_child_at(col,m-1)
                l.set_text(t)
                ctx = l.get_style_context()
                cls.remove_all_classes(ctx)
                ctx.add_class('yearview_daycell')
                ctx.add_class(cls.DAY_CLASS[day])
                if date<today:
                    ctx.add_class('yearview_pastday')
                elif date==today:
                    ctx.add_class('yearview_today')
                if m==1:
                    ctx = day_labs[col].get_style_context()
                    ctx.add_class('yearview_abovedaycell')
                day = (day+1)%7
                col += 1
                date += oneday

            for c in range(col,cls.GRID_COLUMNS): # Empty cells after
                l = cls._grid_cells.get_child_at(c,m-1)
                l.set_text('')
                ctx = l.get_style_context()
                cls.remove_all_classes(ctx)
                ctx.add_class('yearview_emptycell')
                if c<ndayend:
                    ctx.add_class('yearview_abovedaycell')
                if m==1:
                    ctx = day_labs[c].get_style_context()
                    ctx.remove_class('yearview_abovedaycell')


    @classmethod
    def renew_display(cls) -> None:
        # Called when we switch to this view to reset state.
        cls._target_col = None


    @classmethod
    def redraw(cls, en_changes:bool) -> None:
        # Called when redraw required.
        # en_changes: bool indicating if displayed entries need updating too
        if cls._year_viewed != View._cursor_date.year:
            cls._draw_year()
            cls._last_cursor = None
            en_changes = True
        cls._show_cursor()
        cls._show_datelabel()
        # Queue delayed redraw of day content
        if not cls._show_datecontent_pending:
            cls._date_content.foreach(Gtk.Widget.destroy)
            cls._show_datecontent_pending = True
            cls._date_content_count = 0
            # Schedule idle to add datecontent
            # Priority below draw, so datelabel will be redrawn while moving
            GLib.idle_add(cls._show_datecontent,priority=GLib.PRIORITY_HIGH_IDLE+40)
        if en_changes:
            GLib.idle_add(cls._show_gridcontent,priority=GLib.PRIORITY_HIGH_IDLE+35)


    @classmethod
    def _show_datelabel(cls) -> None:
        # Show cursor date in label in bottom panel of view.
        # Called on redraw
        st = View._cursor_date.strftime(GUI.date_formatting_text_noyear)+':'
        cls._date_label.set_text(st)


    @classmethod
    def _show_datecontent(cls) -> None:
        # Show events for current cursor date in bottom panel of view.
        # Assumes that no events are currently shown.
        # Can be slow, so called in idle from redraw.
        dt = View._cursor_date
        cls._visible_occurrences = Calendar.occurrence_list(dt, dt+timedelta(days=1))
        r = 0
        for occ in cls._visible_occurrences:
            occ_dt_sta,occ_dt_end = start_end_dts_occ(occ)
            row = Gtk.Box()
            # Create entry mark (bullet or time) & add to row
            mark_label = cls.marker_label(occ[0], occ_dt_sta)
            ctx = mark_label.get_style_context()
            ctx.add_class('yearview_marker') # add style for CSS
            row.add(mark_label)
            # Create entry content label & add to row
            cont_label = cls.entry_text_label(occ[0], occ_dt_sta, occ_dt_end, add_location=cls._show_location)
            cont_label.set_hexpand(True) # Also sets hexpand_set to True
            row.add(cont_label)
            cls._date_content.add(row)
            # See if we've hit the cursor target entry
            if cls._target_entry is not None and cls._target_entry is occ[0]:
                View._cursor_idx_in_date = r
                cls._target_entry = None
            r += 1
        cls._date_content_count = r
        cls._date_content.show_all()
        cls._show_entry_cursor()
        cls._show_datecontent_pending = False
        cls._target_entry = None # just in case - should be done already


    @classmethod
    def _show_entry_cursor(cls) -> None:
        # Set style to display entry cursor (= cursor in lower section of view)
        if cls._date_content_count==0:
            # No entries for day - return
            View._cursor_idx_in_date = 0
            GUI.set_menu_elts(on_event=False) # Disable menu items
            return
        i = View._cursor_idx_in_date
        if i<0 or i>=cls._date_content_count:
            i = cls._date_content_count-1
            View._cursor_idx_in_date = i
        mk = cls._date_content.get_children()[i].get_children()[0]
        ctx = mk.get_style_context()
        ctx.add_class(cls.ENTRY_CURSOR_STYLE)
        cls._last_entry_cursor = i
        cls._scroll_to_cursor_required = True # to be read in draw handler
        GUI.set_menu_elts(on_event=True) # Enable menu items


    @classmethod
    def _pre_datecontent_draw(cls, wid:Gtk.Widget, _) -> bool:
        # Callback called on 'draw' event on date_content.
        # Called before drawing date content.
        # Used to scroll window when cursor has been moved (since we
        # need to have calculated the layout to know where to scoll to).
        if cls._scroll_to_cursor_required:
            cls.scroll_to_row(cls._date_content, View._cursor_idx_in_date, cls._date_content_scroll)
            cls._scroll_to_cursor_required = False
        return False # propagate event


    @classmethod
    def _hide_entry_cursor(cls) -> None:
        # Remove style from entry cursor (= cursor in lower section of view)
        if cls._last_entry_cursor is not None:
            mk = cls._date_content.get_children()[cls._last_entry_cursor].get_children()[0]
            ctx = mk.get_style_context()
            ctx.remove_class(cls.ENTRY_CURSOR_STYLE)
            cls._last_entry_cursor = None


    @classmethod
    def cursor_set_date(cls, dt:dt_date, idx:int=0, reset_target_col:bool=True) -> bool:
        # Set current cursor date & index in date.
        # Override default method so we can update state of target column.
        # Return True to indicate view supports jumping to a date.
        View._cursor_date = dt
        View._cursor_idx_in_date = idx
        if reset_target_col:
            cls._target_col = None
        return True


    @classmethod
    def get_cursor_entry(cls) -> iCal.Event:
        # Returns entry at cursor position, or None if cursor not on entry.
        # Called from cursor_edit_entry() & delete_request().
        if cls._date_content_count == 0:
            return None
        return cls._visible_occurrences[View._cursor_idx_in_date][0]


    @classmethod
    def _show_gridcontent(cls) -> None:
        # Set styles to show events in grid.
        # Can be slow, so called in idle from redraw.
        # Potential optimisations here. Rather than getting occurences and
        # then splitting, we can add a custom calendar function to return
        # just the dates. Particularly for the repeated entries.
        yr = cls._year_viewed
        date = dt_date(year=yr,month=1,day=1)
        oneday = timedelta(days=1)
        occ_dates_single = [o[1].date() if isinstance(o[1],dt_datetime) else o[1] for o in Calendar.occurrence_list(date, dt_date(year=yr+1,month=1,day=1), include_single=True, include_repeated=False)]
        reps_list = Calendar.occurrence_list(date, dt_date(year=yr+1,month=1,day=1), include_single=False, include_repeated=True)
        occ_dates_repeated = [o[1].date() if isinstance(o[1],dt_datetime) else o[1] for o in reps_list]
        occ_dates_repeated_year = [o[1].date() if isinstance(o[1],dt_datetime) else o[1] for o in reps_list if o[0]['RRULE']['FREQ'][0]=='YEARLY']
        occ_dates_repeated_month = [o[1].date() if isinstance(o[1],dt_datetime) else o[1] for o in reps_list if o[0]['RRULE']['FREQ'][0]=='MONTHLY']
        occ_dates_repeated_week = [o[1].date() if isinstance(o[1],dt_datetime) else o[1] for o in reps_list if o[0]['RRULE']['FREQ'][0]=='WEEKLY']
        occ_dates_repeated_day = [o[1].date() if isinstance(o[1],dt_datetime) else o[1] for o in reps_list if o[0]['RRULE']['FREQ'][0]=='DAILY']
        occ_dates_repeated_hour = [o[1].date() if isinstance(o[1],dt_datetime) else o[1] for o in reps_list if o[0]['RRULE']['FREQ'][0]=='HOURLY']
        occ_dates_repeated_minute = [o[1].date() if isinstance(o[1],dt_datetime) else o[1] for o in reps_list if o[0]['RRULE']['FREQ'][0]=='MINUTELY']
        occ_dates_repeated_second = [o[1].date() if isinstance(o[1],dt_datetime) else o[1] for o in reps_list if o[0]['RRULE']['FREQ'][0]=='SECONDLY']

        for m in range(1,13):
            day,daycount = calendar.monthrange(yr,m)
            x,y = cls._date_to_cell(date)
            for d in range(daycount):
                l = cls._grid_cells.get_child_at(x,y)
                ctx = l.get_style_context()
                if date in occ_dates_single:
                    ctx.add_class('yearview_entry_single')
                else:
                    ctx.remove_class('yearview_entry_single')
                ctx.remove_class('yearview_entry_repeated')
                ctx.remove_class('yearview_entry_repeated_year')
                ctx.remove_class('yearview_entry_repeated_month')
                ctx.remove_class('yearview_entry_repeated_week')
                ctx.remove_class('yearview_entry_repeated_day')
                ctx.remove_class('yearview_entry_repeated_hour')
                ctx.remove_class('yearview_entry_repeated_minute')
                ctx.remove_class('yearview_entry_repeated_second')
                if date in occ_dates_repeated:
                    ctx.add_class('yearview_entry_repeated')
                    if date in occ_dates_repeated_year:
                        ctx.add_class('yearview_entry_repeated_year')
                    if date in occ_dates_repeated_month:
                        ctx.add_class('yearview_entry_repeated_month')
                    if date in occ_dates_repeated_week:
                        ctx.add_class('yearview_entry_repeated_week')
                    if date in occ_dates_repeated_day:
                        ctx.add_class('yearview_entry_repeated_day')
                    if date in occ_dates_repeated_hour:
                        ctx.add_class('yearview_entry_repeated_hour')
                    if date in occ_dates_repeated_minute:
                        ctx.add_class('yearview_entry_repeated_minute')
                    if date in occ_dates_repeated_second:
                        ctx.add_class('yearview_entry_repeated_second')
                date += oneday
                x += 1


    @classmethod
    def _show_cursor(cls) -> None:
        # Add style class for grid cursor to the appropriate cell label
        new_coords = cls._date_to_cell(View._cursor_date)
        if cls._last_cursor!=new_coords:
            cls._hide_cursor()
        l = cls._grid_cells.get_child_at(*new_coords)
        ctx = l.get_style_context()
        ctx.add_class(cls.GRID_CURSOR_STYLE)
        cls._last_cursor = new_coords


    @classmethod
    def _hide_cursor(cls) -> None:
        # Remove grid cursor style class so grid cursor is not shown
        if cls._last_cursor is not None:
            l = cls._grid_cells.get_child_at(*cls._last_cursor)
            ctx = l.get_style_context()
            ctx.remove_class(cls.GRID_CURSOR_STYLE)
            cls._last_cursor = None


    @classmethod
    def _cursor_move_lr(cls, d:int) -> None:
        # Callback for user moving grid cursor left (d<0) or right (d>0).
        cls.cursor_inc(timedelta(days=d), 0)
        cls._target_col = None
        View._today_toggle_date = None


    @classmethod
    def _cursor_move_up(cls) -> None:
        # Callback for user moving grid cursor up.
        cur_dt = View._cursor_date
        if cls._target_col is None:
            cls._target_col = cls._date_to_cell(cur_dt)[0]
        new_y = cur_dt.month-2 # months 1..12, cells 0..11
        new_yr = cur_dt.year
        if new_y<0:
            new_y = 11
            new_yr -= 1
        new_dt = cls._cell_to_date_clamped(cls._target_col, new_y, new_yr)
        cls.cursor_set_date(new_dt, reset_target_col=False)
        cls.redraw(en_changes=False)
        View._today_toggle_date = None


    @classmethod
    def _cursor_move_dn(cls) -> None:
        # Callback for user moving grid cursor down.
        cur_dt = View._cursor_date
        if cls._target_col is None:
            cls._target_col = cls._date_to_cell(cur_dt)[0]
        new_y = cur_dt.month # months 1..12, cells 0..11
        new_yr = cur_dt.year
        if new_y>11:
            new_y = 0
            new_yr += 1
        new_dt = cls._cell_to_date_clamped(cls._target_col, new_y, new_yr)
        cls.cursor_set_date(new_dt, reset_target_col=False)
        cls.redraw(en_changes=False)
        View._today_toggle_date = None


    @classmethod
    def _cursor_move_stmon(cls) -> None:
        # Callback for user moving grid cursor to start of month.
        new_dt = View._cursor_date.replace(day=1)
        cls.cursor_set_date(new_dt, reset_target_col=True)
        cls.redraw(en_changes=False)
        View._today_toggle_date = None


    @classmethod
    def _cursor_move_endmon(cls) -> None:
        # Callback for user moving grid cursor to end of month.
        dt = View._cursor_date
        lastday = calendar.monthrange(dt.year,dt.month)[1]
        new_dt = dt.replace(day=lastday)
        cls.cursor_set_date(new_dt, reset_target_col=True)
        cls.redraw(en_changes=False)
        View._today_toggle_date = None


    @classmethod
    def _cursor_move_pgupdn(cls, d:int) -> None:
        # Callback for user moving grid cursor pageup (d<0) or pagedown (d>0).
        cur_dt = View._cursor_date
        if cls._target_col is None:
            cls._target_col = cls._date_to_cell(cur_dt)[0]
        new_yr = cur_dt.year+d
        new_dt = cls._cell_to_date_clamped(cls._target_col, cur_dt.month-1, new_yr)
        cls.cursor_set_date(new_dt, reset_target_col=False)
        cls.redraw(en_changes=False)
        View._today_toggle_date = None


    @classmethod
    def _cursor_move_today(cls) -> None:
        # Callback for user toggling cursors between today & another date
        today = dt_date.today()
        if View._cursor_date != today:
            View._today_toggle_date = View._cursor_date
            View._today_toggle_idx = View._cursor_idx_in_date
            cls.cursor_set_date(today, reset_target_col=True)
            cls.redraw(en_changes=False)
        elif View._today_toggle_date is not None:
            cls.cursor_set_date(View._today_toggle_date, idx=View._today_toggle_idx, reset_target_col=True)
            cls.redraw(en_changes=False)


    @classmethod
    def _idxcursor_move_up(cls) -> None:
        # Callback to move entry/index cursor (=cursor in bottom section) up
        if View._cursor_idx_in_date>0:
            View._cursor_idx_in_date -= 1
            cls._hide_entry_cursor()
            cls._show_entry_cursor()


    @classmethod
    def _idxcursor_move_dn(cls) -> None:
        # Callback to move entry/index cursor (=cursor in bottom section) down
        if View._cursor_idx_in_date<cls._date_content_count-1:
            View._cursor_idx_in_date += 1
            cls._hide_entry_cursor()
            cls._show_entry_cursor()


    @classmethod
    def keypress(cls, wid:Gtk.Widget, ev:Gdk.EventKey) -> None:
        # Handle key press event in Year view.
        # Called (from GUI.keypress()) on keypress (or repeat) event
        if ev.state & Gdk.ModifierType.SHIFT_MASK:
            # Shift key is being pressed
            try:
                f = cls._KEYMAP_SHIFT[ev.keyval]
                GLib.idle_add(f, priority=GLib.PRIORITY_HIGH_IDLE+30)
                return # If it gets here without errors, we're done
            except KeyError:
                pass
        try:
            f = cls._KEYMAP[ev.keyval]
            GLib.idle_add(f, priority=GLib.PRIORITY_HIGH_IDLE+30)
            return # If it gets here without errors, we're done
        except KeyError:
            pass
        if ev.state & (Gdk.ModifierType.CONTROL_MASK|Gdk.ModifierType.MOD1_MASK)==0 and Gdk.KEY_exclam <= ev.keyval <= Gdk.KEY_asciitilde:
            date = cls.cursor_date()
            GLib.idle_add(EventDialogController.new_event, chr(ev.keyval), date, priority=GLib.PRIORITY_HIGH_IDLE+30)


    @classmethod
    def click_grid(cls, wid:Gtk.Widget, ev:Gdk.EventButton) -> bool:
        # Callback. Called whenever day grid is clicked/tapped.
        # Move grid (main) cursor to cell that was clicked.
        x = int(cls.GRID_COLUMNS*ev.x/wid.get_allocated_width())
        y = int(cls.GRID_ROWS*ev.y/wid.get_allocated_height())
        dt = cls._cell_to_date_clamped(x, y, cls._year_viewed)
        GLib.idle_add(cls._jump_to_date, dt, priority=GLib.PRIORITY_HIGH_IDLE+30)
        return True # event handled - don't propagate


    @classmethod
    def click_events(cls, wid:Gtk.Widget, ev:Gdk.EventButton) -> bool:
        # Callback. Called whenever events area at bottom is clicked/tapped.
        # Move entry cursor to entry that was clicked
        new_idx = cls.y_to_day_row(cls._date_content, ev.y, cls._date_content_count, cls._date_content_scroll)
        if View._cursor_idx_in_date != new_idx:
            View._cursor_idx_in_date = new_idx
            cls._hide_entry_cursor()
            cls._show_entry_cursor()
        return True # event handled - don't propagate


    @classmethod
    def _jump_to_date(cls, dt:dt_date) -> None:
        # Idle callback to move grid cursor to given date, e.g. on click
        cls.cursor_set_date(dt, reset_target_col=True)
        cls.redraw(en_changes=False)


    @staticmethod
    def _date_to_cell(dt:dt_date) -> Tuple[int,int]:
        # Helper function to return cell coordinates of given date.
        stday = calendar.monthrange(dt.year,dt.month)[0] # start day of month
        x = dt.day-1+(stday-Config.get_int('global','start_week_day'))%7
        y = dt.month-1
        return x,y


    @staticmethod
    def _cell_to_date_clamped(x:int, y:int, yr:int) -> dt_date:
        # Helper function to return date given cell coordinates.
        # "Clamps" date, so if the cell is before the start or after the end
        # of the month then it returns the closest date in the month.
        m = y+1
        st_wk = Config.get_int('global','start_week_day')
        st_day,monthdays = calendar.monthrange(yr,m)
        d = x+1-(st_day-st_wk)%7
        if d<1:
            d = 1
        else:
            d = min(d,monthdays)
        return dt_date(year=yr, month=m, day=d)
