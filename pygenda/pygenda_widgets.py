# -*- coding: utf-8 -*-
#
# pygenda_widgets.py
# Date, Time and Duration entry widgets for Pygenda.
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

# To-do:
#    Add timezone field to WidgetTime (default "floating"/None).
#    Allow WidgetDuration to take values > 1 day (2d 5h 06m)
#
# !! Possible addition: ctrl+tab in WidgetDate brings up a calendar
#    (a GtkCalendar) to allow choice with touchscreen (maybe also add
#    a button to WidgetDate).
#    Maybe similar in WidgetTime if can find/make a graphical time
#    picker widget.


from gi import require_version as gi_require_version
gi_require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GObject

from datetime import date as dt_date, time as dt_time, timedelta
from calendar import monthrange
from typing import Optional

# for internationalisation/localisation
import locale
_ = locale.gettext

# pygenda components
from .pygenda_config import Config


class _WidgetDateTimeBase(Gtk.Box):
    # Base class for WidgetDate, WidgetTime, WidgetDuration.
    # Not to be used directly.
    ALLOWED_KEYS = (Gdk.KEY_BackSpace, Gdk.KEY_Delete, Gdk.KEY_Right, Gdk.KEY_Left, Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab, Gdk.KEY_Return, Gdk.KEY_Escape)
    ALLOWED_KEYS_WITH_CTRL = (Gdk.KEY_a, Gdk.KEY_c, Gdk.KEY_x)
    SEPARATOR_KEYS = ()
    FOCUS_STYLE = 'focus'
    field_shortcuts = ()

    def __init__(self, *args, **kwds):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=2, *args, **kwds)
        try:
            dummy = _WidgetDateTimeBase.SHORTCUT_KEYS
        except:
            # Need to set this here for it to be localisable
            _WidgetDateTimeBase.SHORTCUT_KEYS = _('ymdhm')
        self._elts = []
        self._elimpad = []
        self.set_halign(Gtk.Align.START) # default to pack from left (if LTR)


    @classmethod
    def _init_field_numeric(cls, mn:int, mx:int, zeropad:bool=True, align:float=0.5) -> Gtk.Entry:
        # Returns a new numeric field widget with the given properties.
        # Called by child classes in their initialisation.
        ln = len(str(mx))
        f = Gtk.Entry()
        f.set_max_length(ln)
        f.set_width_chars(ln)
        f.set_input_purpose(Gtk.InputPurpose.DIGITS)
        f.set_alignment(align) # default 0.5 = center digits
        f.set_activates_default(True)
        pad = ln if zeropad else 0 # Length with zero padding
        f.connect('focus-out-event', cls.validate_entry, mn, mx, pad)
        return f


    def _init_navigation(self) -> None:
        # Use self._elts array to setup navigation between subfields.
        if not Config.get_bool('global', 'tab_elts_datetime'):
            # Make Tab key only go to first elt
            self.set_focus_chain((self._elts[0],))
        self._focus_count = 0 # init counter for focus in/out
        for i in range(len(self._elts)):
            self._elts[i].connect('key-press-event', self._key_event, i)
            self._elts[i].connect('changed', self._changed)
            self._elts[i].connect('focus-out-event', self._focus_out)
            self._elts[i].connect('focus-in-event', self._focus_in)


    def _focus_in(self, entry:Gtk.Widget, ev:Gdk.EventFocus) -> bool:
        # Event callback for when any sub-field gets the focus
        # This and the next function allow us to style whole widget with .focus
        # We update counter to avoid unnecessary remove/add styles
        if self._focus_count==0:
            self.get_style_context().add_class(self.FOCUS_STYLE)
        self._focus_count += 1
        return False # propagate event

    def _focus_out(self, entry:Gtk.Widget, ev:Gdk.EventFocus) -> bool:
        # Event callback for when any sub-field looses the focus
        # Do the work in idle so in leave/enter pairs, leave happens last
        GLib.idle_add(_WidgetDateTimeBase._do_focus_out, self)
        return False # propagate event

    def _do_focus_out(self) -> None:
        # Idle event callback for when any sub-field loses focus
        self._focus_count -= 1
        if self._focus_count==0:
            self.get_style_context().remove_class(self.FOCUS_STYLE)


    def _key_event(self, entry:Gtk.Entry, ev:Gdk.EventKey, idx:int) -> bool:
        # Event callback for keypress events.
        # Return True if this handles keypress, and False to propagate event.
        try:
            txt_len = entry.get_text_length()
            c_pos = entry.get_property('cursor-position')
            sel_bnds = entry.get_selection_bounds()
            at_st = c_pos==0 or (sel_bnds and sel_bnds[0]==0)
            at_end = c_pos==txt_len or (sel_bnds and sel_bnds[1]==txt_len)
            one_from_max = not sel_bnds and c_pos==entry.get_max_length()-1
        except AttributeError:
            # Widget is not a GTkEntry (probably an am/pm combo-box)
            at_st = True
            at_end = True
            sel_bnds = False

        # Move left/right
        if at_st and idx>0 and (ev.keyval==Gdk.KEY_Left or (not sel_bnds and ev.keyval==Gdk.KEY_BackSpace)):
            self._elts[idx-1].grab_focus()
            return True
        if at_end and ev.keyval==Gdk.KEY_Right and idx+1<len(self._elts):
            self._elts[idx+1].grab_focus()
            return True

        # Increase/decrease keypresses
        shiftdown = ev.state&Gdk.ModifierType.SHIFT_MASK
        if ev.keyval in (Gdk.KEY_plus,Gdk.KEY_greater) or (shiftdown and ev.keyval==Gdk.KEY_Up):
            try:
                v = int(entry.get_text())
                v += 1
            except ValueError:
                # field did not contain a number (e.g. empty)
                v = self._elimpad[idx][0]
            lp = self._elimpad[idx][3]
            if v > self._elimpad[idx][1]:
                v = self._elimpad[idx][0 if lp else 1]
            pad = self._elimpad[idx][2]
            entry.set_text('{{:0{:d}d}}'.format(pad).format(v))
            entry.select_region(0,-1)
            return True
        if ev.keyval in (Gdk.KEY_minus,Gdk.KEY_less) or (shiftdown and ev.keyval==Gdk.KEY_Down):
            try:
                v = int(entry.get_text())
                v -= 1
            except ValueError:
                # field did not contain a number (e.g. empty)
                v = self._elimpad[idx][1]
            lp = self._elimpad[idx][3]
            if v < self._elimpad[idx][0]:
                v = self._elimpad[idx][1 if lp else 0]
            pad = self._elimpad[idx][2]
            entry.set_text('{{:0{:d}d}}'.format(pad).format(v))
            entry.select_region(0,-1)
            return True

        # Move to next field from typing separator
        # Small problem here. The '-' key can be a separator and can also mean
        # "decrease value". Since the latter is checked above it has priority.
        if at_end and not sel_bnds and ev.keyval in self.SEPARATOR_KEYS:
            self._elts[idx+1].grab_focus()
            return True

        # Shortcut keys to jump to fields, e.g. 'm' to jump to month field
        try:
            new_id = self.field_shortcuts.index(ev.keyval)# not found -> exceptn
            self._elts[new_id].grab_focus()
            return True
        except ValueError:
            pass

        # Type a digit
        if ev.keyval>=Gdk.KEY_0 and ev.keyval<=Gdk.KEY_9:
            if at_end and one_from_max and idx+1<len(self._elts):
                # In this case, handle insert and move to next field here
                entry.insert_text(str(ev.keyval-Gdk.KEY_0),-1)
                self._elts[idx+1].grab_focus()
                return True
            # Otherwise number keys can safely be handled by standard code
            return False
        # Return False to allow key to be handled if it's in "safe" list
        return ev.keyval not in (self.ALLOWED_KEYS_WITH_CTRL if ev.state==Gdk.ModifierType.CONTROL_MASK else self.ALLOWED_KEYS)


    def _changed(self, entry:Gtk.Widget) -> bool:
        # If one subcomponent changes, cascade 'changed' signal down
        self.emit('changed')
        return False # propagate event


    @staticmethod
    def validate_entry(entry:Gtk.Entry, ev:Gdk.EventFocus, mn:int, mx:int, pad:int) -> bool:
        # Helper function to validate (and correct) date/time fields.
        # Used as callback function when focus leaves the field.
        entry.select_region(0,0) # remove highlight
        try:
            v = int(entry.get_text())
            v = max(mn,v)
            v = min(mx,v)
        except ValueError:
            v = mn
        entry.set_text('{{:0{:d}d}}'.format(pad).format(v))
        return False # propagate event - in case it's used elsewhere


    def grab_focus(self) -> None:
        # Provide implementation of widget class's grab_focus()
        self._elts[0].grab_focus()


# Allow _WidgetDateTimeBase to emit its own 'changed' signals
GObject.signal_new('changed', _WidgetDateTimeBase, GObject.SIGNAL_RUN_LAST, None, ())


class WidgetDate(_WidgetDateTimeBase):
    # Widget for date entry fields, to use (eg) in "New Entry" dialog.
    __gtype_name__ = 'WidgetDate'
    SEPARATOR_KEYS = (Gdk.KEY_slash, Gdk.KEY_minus, Gdk.KEY_period)

    def __init__(self, dt:dt_date=None, *args, **kwds):
        # Constructor. dt=None -> widget defaults to today.
        super().__init__(*args, **kwds)

        self.field_year = self._init_field_numeric(1,9999,zeropad=False)
        self.field_month = self._init_field_numeric(1,12)
        self.field_day = self._init_field_numeric(1,31)

        sep = Config.get('global','date_sep')
        first = True
        self.field_shortcuts = []

        from .pygenda_gui import GUI # Delayed import to avoid circular dep
        for ch in GUI.date_order:
            if not first:
                self.pack_start(Gtk.Label(sep), False, False, 0)
            if ch=='Y':
                f = self.field_year
                lp = (1,9999,0,False) # min,max,pad,loop
                self.field_shortcuts.append(ord(self.SHORTCUT_KEYS[0]))
            elif ch=='M':
                f = self.field_month
                lp = (1,12,2,True)
                self.field_shortcuts.append(ord(self.SHORTCUT_KEYS[1]))
            else: # ch==D
                f = self.field_day
                lp = (1,31,2,True)
                self.field_shortcuts.append(ord(self.SHORTCUT_KEYS[2]))
            self._elts.append(f) # For _init_navigation()
            self._elimpad.append(lp) # For +/- keys etc
            self.pack_start(f, False, False, 0)
            first = False

        self.set_date(dt)
        self._init_navigation() # So we can navigate among elements


    def set_date(self, dt:Optional[dt_date]) -> None:
        # Set widget contents, dt=None -> today
        if dt is None:
            dt = dt_date.today()
        self.field_year.set_text(str(dt.year))
        self.field_month.set_text('{:02d}'.format(dt.month))
        self.field_day.set_text('{:02d}'.format(dt.day))


    def get_date(self) -> dt_date:
        # Get widget contents. Raises ValueError if date invalid.
        y = int(self.field_year.get_text())
        m = int(self.field_month.get_text())
        d = int(self.field_day.get_text())
        dt = dt_date(year=y, month=m, day=d)
        return dt


    def get_date_or_none(self) -> Optional[dt_date]:
        # Get widget contents. Returns None if date invalid.
        try:
            return self.get_date()
        except ValueError:
            return None


    def get_approx_date_or_none(self) -> Optional[dt_date]:
        # Get "approximate" date contents. Approximate here means try to
        # guess invalid dates, e.g. 2022-02-30 -> 2022-02-28.
        # This is for the "goto" dialog, so it doesn't force the user to
        # enter a strictly valid date.
        try:
            return self.get_date()
        except ValueError:
            pass

        # If get_date() gave an error, try harder to get values
        today = dt_date.today() # defaults if fields are empty/meaningless
        try:
            y = int(float(self.field_year.get_text()))
            if y <= 0:
                y = 1
            elif y > 9999:
                y = 9999
        except ValueError:
            y = today.year

        try:
            m = int(float(self.field_month.get_text()))
            if m <= 0:
                m = 1
            elif m > 12:
                m = 12
        except ValueError:
            m = today.month

        try:
            d = int(float(self.field_day.get_text()))
            monthdays = monthrange(y,m)[1]
            if d <= 0:
                d = 1
            elif d > monthdays:
                d = monthdays
        except ValueError:
            d = 1

        try:
            dt = dt_date(year=y, month=m, day=d)
        except ValueError:
            dt = None
        return dt


    def is_valid_date(self) -> bool:
        # Returns True if widget date is valid, False otherwise.
        try:
            self.get_date()
        except ValueError:
            return False
        return True


class WidgetTime(_WidgetDateTimeBase):
    # Widget for time entry fields, to use (eg) in "New Entry" dialog.
    __gtype_name__ = 'WidgetTime'
    SEPARATOR_KEYS = (Gdk.KEY_colon, Gdk.KEY_period)
    am_str = None # Initialise these later when we have locale config
    pm_str = None
    am_keys = None
    pm_keys = None

    def __init__(self, dt, *args, **kwds):
        super().__init__(*args, **kwds)
        self._init_ampm_locale()
        if not WidgetTime.field_shortcuts:
            WidgetTime.field_shortcuts = [ord(c) for c in (_WidgetDateTimeBase.SHORTCUT_KEYS[3:5])]

        self.is24 = Config.get_bool('global','24hr')
        if self.is24:
            self.field_hour = self._init_field_numeric(0,23)
        else:
            self.field_hour = self._init_field_numeric(1,12,zeropad=False,align=1)
            self.field_ampm = self._init_field_ampm()
        self.field_min = self._init_field_numeric(0,59)

        self.pack_start(self.field_hour, False, False, 0)
        self.pack_start(Gtk.Label(Config.get('global','time_sep')), False, False, 0)
        self.pack_start(self.field_min, False, False, 0)

        self._elts.append(self.field_hour) # For _init_navigation()
        self._elts.append(self.field_min)

        if self.is24:
            self._elimpad.append((0,23,2,True)) # For +/- keys etc
        else:
            self.pack_start(self.field_ampm, False, False, 0)
            self._elts.append(self.field_ampm)
            self._elimpad.append((1,12,0,True))
            # Add callbacks to change am/pm:
            self.field_hour.connect('key-press-event', self._remote_ampm_key_event, self.field_ampm)
            self.field_min.connect('key-press-event', self._remote_ampm_key_event, self.field_ampm)
        self._elimpad.append((0,59,2,True))

        self.set_time(dt)
        self._init_navigation() # So we can navigate among elements


    @classmethod
    def _init_ampm_locale(cls) -> None:
        # Initialise localised am/pm strings if they're None
        if cls.am_str is None:
            # Use strftime to get locale-dependent am/pm strings
            cls.am_str = dt_time().strftime('%p')
            if not cls.am_str: # For locales with "" am/pm string (eg fr_FR)
                cls.am_str = 'am' # fallback value
            cls.pm_str = dt_time(12).strftime('%p') # at 12:00
            if not cls.pm_str:
                cls.pm_str = 'pm' # fallback value

            # Now make combobox shortcut keys equal 1st chars of these strings
            # (Edge case where 1st chars of am/pm are the same?)
            ch = cls.am_str[0]
            if ch.lower() == ch.upper():
                cls.am_keys = (ord(ch),)
            else:
                cls.am_keys = (ord(ch.lower()),ord(ch.upper()))

            ch = cls.pm_str[0]
            if ch.lower() == ch.upper():
                cls.pm_keys = (ord(ch),)
            else:
                cls.pm_keys = (ord(ch.lower()),ord(ch.upper()))


    @classmethod
    def _init_field_ampm(cls) -> Gtk.ComboBoxText:
        # Returns a new am/pm field - a ComboBox.
        f = Gtk.ComboBoxText()
        f.append('a', cls.am_str)
        f.append('p', cls.pm_str)
        f.connect('key-press-event', cls._ampm_key_event)
        return f


    @staticmethod
    def _remote_ampm_key_event(entry:Gtk.Widget, ev:Gdk.EventKey, ampmfield:Gtk.ComboBoxText) -> bool:
        # Callback handler so can press a/p in other fields and have
        # it affect the am/pm field.
        if ev.keyval in WidgetTime.am_keys:
            ampmfield.set_active_id('a')
            return True
        if ev.keyval in WidgetTime.pm_keys:
            ampmfield.set_active_id('p')
            return True
        return False


    @staticmethod
    def _ampm_key_event(entry:Gtk.ComboBoxText, ev:Gdk.EventKey) -> bool:
        # Callback handler for keypresses when am/pm field is focussed.
        # Return True if this handles keypress and nothing further to do.
        if ev.keyval==Gdk.KEY_space:
            entry.popup()
            return True
        if ev.keyval in WidgetTime.am_keys:
            entry.set_active_id('a')
            return True
        if ev.keyval in WidgetTime.pm_keys:
            entry.set_active_id('p')
            return True
        shiftdown = ev.state&Gdk.ModifierType.SHIFT_MASK
        if ev.keyval in (Gdk.KEY_plus,Gdk.KEY_minus,Gdk.KEY_greater,Gdk.KEY_less) or (shiftdown and ev.keyval in (Gdk.KEY_Up,Gdk.KEY_Down)):
            entry.set_active_id('p' if entry.get_active_id()=='a' else 'a')
            return True
        if ev.keyval==Gdk.KEY_Up:
            return entry.get_toplevel().child_focus(Gtk.DirectionType.UP)
        if ev.keyval==Gdk.KEY_Down:
            return entry.get_toplevel().child_focus(Gtk.DirectionType.DOWN)
        if ev.keyval==Gdk.KEY_Return:
            dlg = entry.get_toplevel()
            if dlg:
                dlg.response(Gtk.ResponseType.OK)
                return True
        # Return False to allow key to be handled if it's in "safe" list
        return ev.keyval not in _WidgetDateTimeBase.ALLOWED_KEYS


    def set_time(self, tm:dt_time) -> None:
        # Set widget contents.
        if self.is24:
            self.field_hour.set_text('{:02d}'.format(tm.hour))
        else: # 12hr
            h = tm.hour
            self.field_ampm.set_active_id('a' if h<12 else 'p')
            if h==0:
                h = 12
            elif h>12:
                h -= 12
            self.field_hour.set_text(str(h))
        self.field_min.set_text('{:02d}'.format(tm.minute))


    def get_time(self) -> dt_time:
        # Get widget contents. Raises ValueError if time invalid.
        h = int(self.field_hour.get_text())
        if not self.is24:
            if h==12:
                h = 0
            if self.field_ampm.get_active_id()=='p':
                h += 12
        m = int(self.field_min.get_text())
        tm = dt_time(hour=h, minute=m)
        return tm


    def get_time_or_none(self) -> Optional[dt_time]:
        # Get widget contents. Returns None if time invalid.
        try:
            return self.get_time()
        except ValueError:
            return None


    def is_valid_time(self) -> bool:
        # Returns True if widget contents give a valid time; False otherwise.
        try:
            self.get_time()
        except ValueError:
            return False
        return True


class WidgetDuration(_WidgetDateTimeBase):
    # Widget for duration entry fields, to use (eg) in "New Entry" dialog.
    __gtype_name__ = 'WidgetDuration'
    SEPARATOR_KEYS = (Gdk.KEY_colon, Gdk.KEY_period)

    def __init__(self, timed, *args, **kwds):
        super().__init__(*args, **kwds)
        if not WidgetDuration.field_shortcuts:
            WidgetDuration.field_shortcuts = [ord(c) for c in (_WidgetDateTimeBase.SHORTCUT_KEYS[3:5])]

        # !! For now we limit to <24hrs
        self.field_hour = self._init_field_numeric(0,23,zeropad=False,align=1)
        self.field_min = self._init_field_numeric(0,59)

        self.pack_start(self.field_hour, False, False, 0)
        self.pack_start(Gtk.Label(Config.get('global','time_sep')), False, False, 0)
        self.pack_start(self.field_min, False, False, 0)

        self._elts.append(self.field_hour) # For _init_navigation()
        self._elts.append(self.field_min)
        self._elimpad.append((0,23,0,False)) # For +/- keys etc
        self._elimpad.append((0,59,2,True))

        self.set_duration(timed)
        self._init_navigation() # So we can navigate among elements


    def set_duration(self, timed:timedelta) -> None:
        # Set widget contents.
        tot_min = int(timed.total_seconds()//60)
        hr,mn = divmod(tot_min,60)
        self.field_hour.set_text(str(hr))
        self.field_min.set_text('{:02d}'.format(mn))


    def get_duration(self) -> timedelta:
        # Get widget contents. Raises ValueError if duration invalid.
        hr = int(self.field_hour.get_text())
        mn = int(self.field_min.get_text())
        if not (0<=mn<60) or hr<0:
            raise(ValueError)
        td = timedelta(hours=hr, minutes=mn)
        return td


    def get_duration_or_none(self) -> Optional[timedelta]:
        # Get widget contents. Returns None if duration invalid.
        try:
            return self.get_duration()
        except ValueError:
            return None


# CSS names
try:
    # Requires GTK 3.20+
    WidgetDate.set_css_name('date_entry')
    WidgetTime.set_css_name('time_entry')
    WidgetDuration.set_css_name('duration_entry')
except AttributeError:
    pass
