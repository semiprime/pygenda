# -*- coding: utf-8 -*-
#
# pygenda_gui.py
# Top-level GUI code and shared elements (e.g. soft buttons, dialogs)
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
from gi.repository import Gtk, Gdk, GLib, Gio

from datetime import date as dt_date, time as dt_time, datetime as dt_datetime, timedelta
from dateutil import rrule as du_rrule
from dateutil.relativedelta import relativedelta
from icalendar import Calendar as iCalendar, Event as iEvent, Todo as iTodo
from importlib import import_module
from os import path as ospath
from sys import stderr
import signal
import ctypes
from typing import Optional, Tuple, List

# for internationalisation/localisation
import locale
_ = locale.gettext
from calendar import day_name, monthrange

# pygenda components
from .pygenda_config import Config
from .pygenda_calendar import Calendar, RepeatInfo
from .pygenda_widgets import WidgetDate, WidgetTime, WidgetDuration
from .pygenda_entryinfo import EntryInfo
from .pygenda_util import guess_date_ord_from_locale,guess_date_sep_from_locale,guess_time_sep_from_locale, guess_date_fmt_text_from_locale, datetime_to_date
from .pygenda_version import __version__


# Singleton class for top-level GUI control
class GUI:
    _GLADE_FILE = '{:s}/pygenda.glade'.format(ospath.dirname(__file__))
    _CSS_FILE_APP = '{:s}/css/pygenda.css'.format(ospath.dirname(__file__))
    _CSS_FILE_USER = GLib.get_user_config_dir() + '/pygenda/pygenda.css'
    _LOCALE_DIR = '{:s}/locale/'.format(ospath.dirname(__file__))
    _VIEWS = ('Week','Year','Todo') # Order gives order in menus
    SPINBUTTON_INC_KEY = (Gdk.KEY_plus,Gdk.KEY_greater)
    SPINBUTTON_DEC_KEY = (Gdk.KEY_minus,Gdk.KEY_less)
    STYLE_ERR = 'dialog_error'

    cursor_date = dt_date.today()
    cursor_idx_in_date = 0 # cursor index within date
    today_toggle_date = None
    today_toggle_idx = 0

    views = []
    view_widgets = [] # type: List[Gtk.Widget]
    _view_idx = 0 # take first view as default

    _lib_clip = None

    _builder = Gtk.Builder()
    _window = None # type: Gtk.Window
    _is_fullscreen = False
    _box_view_cont = None # type: Gtk.Box
    _eventbox = Gtk.EventBox()

    date_order = ''
    date_formatting_numeric = ''
    date_formatting_text = ''
    date_formatting_text_noyear = ''
    date_formatting_textabb = ''
    date_formatting_textabb_noyear = ''

    # For startup
    _starting_cal = True
    _loading_indicator = None

    Config.set_defaults('global',{
        'language': '', # use OS language
        'hide_titlebar_when_maximized': False,
        'date_ord': guess_date_ord_from_locale(),
        'date_sep': guess_date_sep_from_locale(),
        'time_sep': guess_time_sep_from_locale(),
        'date_fmt_text': guess_date_fmt_text_from_locale(),
        'date_fmt_text_noyear': '', # construct from date_fmt_text
        'date_fmt_textabb': '', # construct from date_fmt_text
        'date_fmt_textabb_noyear': '', # construct from date_fmtabb_text
        '24hr': False,
        'start_week_day': 0, # 0 = Monday, 6 = Sunday
        'tab_elts_datetime': False,
        })
    Config.set_defaults('startup',{
        'maximize': False,
        'fullscreen': False,
        'view': False,
        'softbutton_display': '',
        })

    # Constructor
    @classmethod
    def init(cls) -> None:
        # First stage initialisation to bring up the UI.
        # See init_stage2() below for init done after gtk_main loop started.

        # First set the locale, so UI language (e.g. in menu) is correct
        cls._init_locale()

        # Construct GUI from GTK Builder XML glade file
        cls._builder.add_from_file(cls._GLADE_FILE)

        cls._window = cls._builder.get_object('window_main')
        if (not cls._window): # Sanity check
            raise NameError('Main window not found')
        cls._window.set_default_icon_name('x-office-calendar')

        cls._window.set_hide_titlebar_when_maximized(Config.get_bool('global','hide_titlebar_when_maximized'))
        if Config.get_bool('startup','maximize'):
            cls._window.maximize()
        cls._is_fullscreen = Config.get_bool('startup','fullscreen')
        if cls._is_fullscreen:
            cls._window.fullscreen()

        # Handle SIGINT (e.g. from ctrl+C) etc.
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT_IDLE, signal.SIGINT, cls.exit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT_IDLE, signal.SIGTERM, cls.exit)

        # Connect signals now, so clicking on [X] in window exits application
        HANDLERS = {
            'window_main delete': cls.exit,
            'menuitem_quit': cls.exit,
            'menuitem_cut': cls.cut_request,
            'menuitem_copy': cls.copy_request,
            'menuitem_paste': cls.paste_request,
            'menuitem_newevent': cls.handler_newevent,
            'menuitem_newtodo': cls.handler_newtodo,
            'menuitem_edittime': cls.handler_edittime,
            'menuitem_editrepeats': cls.handler_editrepeats,
            'menuitem_editalarm': cls.handler_editalarm,
            'menuitem_editdetails': cls.handler_editdetails,
            'menuitem_stat_none': lambda a: cls.handler_stat_toggle(None),
            'menuitem_stat_confirmed': lambda a: cls.handler_stat_toggle('CONFIRMED'),
            'menuitem_stat_canceled': lambda a: cls.handler_stat_toggle('CANCELLED'),
            'menuitem_stat_tentative': lambda a: cls.handler_stat_toggle('TENTATIVE'),
            'menuitem_deleteentry': cls.delete_request,
            'menuitem_switchview': cls.switch_view,
            'menuitem_goto': cls.dialog_goto,
            'menuitem_fullscreen': cls.toggle_fullscreen,
            'menuitem_about': cls.dialog_about,
            'button0_clicked': cls.handler_newevent,
            'button1_clicked': cls.switch_view,
            'button2_clicked': cls.dialog_goto,
            'button3_clicked': cls.debug, # zoom, to be decided/implemented
            'exceptions_modify': EventDialogController.dialog_repeat_exceptions
            }
        cls._builder.connect_signals(HANDLERS)

        cls._box_view_cont = cls._builder.get_object('box_view_cont')
        if (not cls._box_view_cont): # Sanity check
            raise NameError('View container not found')

        # Add a spinner while the view is still loading
        cls._loading_indicator = Gtk.Box()
        cls._loading_indicator.set_name('view_loading')
        spinner = Gtk.Spinner.new()
        cls._loading_indicator.set_center_widget(spinner)
        cls._box_view_cont.pack_start(cls._loading_indicator, True, True, 0)
        spinner.start()
        cls._loading_indicator.show_all()

        # Setup CSS provider(s) now so "loading" notice is styled
        css_prov = Gtk.CssProvider()
        css_prov.load_from_path(cls._CSS_FILE_APP)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css_prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        try:
            css_prov_u = Gtk.CssProvider()
            css_prov_u.load_from_path(cls._CSS_FILE_USER)
            Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css_prov_u, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        except:
            pass

        # Set position/display of softbuttons before showing loading indicator
        cfig_sbut = Config.get('startup','softbutton_display').lower()
        bbut = cls._builder.get_object('box_buttons')
        if cfig_sbut == 'hide':
            bbut.hide()
        elif cfig_sbut == 'left':
            cls._box_view_cont.reorder_child(bbut,0)
        else:
            cls._box_view_cont.reorder_child(bbut,1)

        # Delay further initialisation so we can display GUI/window early
        cls._window.show()
        GLib.idle_add(cls.init_stage2)


    @staticmethod
    def init_cal(task:Gio.Task, src_obj, t_data, cancel:Gio.Cancellable)->None:
        # Wrapper around Calendar.init(), so we can call it in a GTask thread.
        Calendar.init()
        task.return_int(0)

    @classmethod
    def init_cal_callback(cls, data, task:Gio.Task) -> None:
        # Callback called to signal that init_cal() has finished.
        cls._starting_cal = False

    @staticmethod
    def init_cal_iosc(job:Gio.IOSchedulerJob, cancel:Gio.Cancellable, u_data) -> bool:
        # Wrapper around Calendar.init, so we can call it in an IOScheduler.
        # Fallback for Gio version < 2.36 (hence needed for Gemini).
        try:
            Calendar.init()
        finally:
            GUI._starting_cal = False
        return False # indicates task complete


    @classmethod
    def init_stage2(cls) -> None:
        # Second-stage initialisation.
        # This is run in the gtk_main thread after basic UI is displayed.

        # First, initialise calendar connector.
        # Do this outside main thread, so UI remains active/responsive.
        ci_cancel = Gio.Cancellable.new()
        if 'run_in_thread' in dir(Gio.Task):
            # Preferred way to run in separate thread.
            task = Gio.Task.new(cancellable=ci_cancel, callback=cls.init_cal_callback)
            task.run_in_thread(cls.init_cal)
        else:
            # Deprecated, but needed to run on Gemini.
            Gio.io_scheduler_push_job(cls.init_cal_iosc, None, GLib.PRIORITY_DEFAULT, ci_cancel)

        # Initialise some things in main thread while calendar loading
        cls._init_clipboard()
        cls._init_date_format()
        EventDialogController.init()

        # If date set from command line, jump there now
        if Config.date:
            GUI.cursor_date = Config.date

        # Wait for calendar to finish initialising before doing views
        while cls._starting_cal:
            if Gtk.main_iteration_do(False):
                # True => main_quit() has been called
                ci_cancel.cancel()
                return
            GLib.usleep(1000) # microsecs
        del(cls._starting_cal) # Flag no longer needed

        # Get rid of loading indicator, but store position for view placement
        view_pos = cls._box_view_cont.child_get_property(cls._loading_indicator, 'position')
        cls._box_view_cont.remove(cls._loading_indicator)
        del(cls._loading_indicator) # should be only remaining reference

        # Check that calendar initialised/connected properly
        if not hasattr(Calendar, 'calConnector') or not Calendar.calConnector:
            print('Error: Calendar could not be initialized', file=stderr)
            Gtk.main_quit()
            return

        cls._init_views()
        TodoDialogController.init() # Need to do this after Todo View init

        vw = Config.get('startup','view')
        if vw:
            for ii in range(len(GUI._VIEWS)):
                if GUI._VIEWS[ii].lower() == vw:
                    cls._view_idx = ii
                    break
        cls._box_view_cont.pack_start(cls._eventbox, True, True, 0)
        cls._box_view_cont.reorder_child(cls._eventbox, view_pos)
        cls._eventbox.add(cls.view_widgets[cls._view_idx])
        cls._eventbox.connect('key_press_event', cls.keypress)
        cls.view_widgets[cls._view_idx].grab_focus() # so it gets keypresses
        del(cls._box_view_cont) # don't need this anymore

        # Add functionality to spinbuttons not provided by GTK
        cls._init_spinbuttons()
        cls._init_comboboxes()
        cls._init_entryboxes()

        # Menu bar & softbutton bar made insensitive in .glade for startup.
        # We make them sensitive here before activating view.
        cls._builder.get_object('menu_bar').set_sensitive(True)
        cls._builder.get_object('box_buttons').set_sensitive(True)

        cls.view_redraw() # Draw active view
        cls._eventbox.show_all()


    @classmethod
    def _init_locale(cls) -> None:
        # Initialise language from config or OS settings
        lang = Config.get('global', 'language')
        if not lang:
            lang = locale.getlocale()
        if isinstance(lang,str) and '.' not in lang:
            # Need to include encoding
            lang = (lang,'UTF-8')
        locale.setlocale(locale.LC_ALL, lang)
        locale.bindtextdomain('pygenda', cls._LOCALE_DIR)
        locale.textdomain('pygenda')


    @classmethod
    def _init_clipboard(cls) -> None:
        # Load clipboard helper library if available, or set to None
        try:
            libclip_file = '{:s}/libpygenda_clipboard.so'.format(ospath.dirname(__file__))
            cls._lib_clip = ctypes.CDLL(libclip_file)
        except:
            print('Warning: Failed to load clipboard library', file=stderr)


    @classmethod
    def _init_date_format(cls) -> None:
        # Initialise date formatting strings from config
        cls.date_order = cls._date_order_from_config()

        # Make date_formatting_numeric - a format string like '%Y-$m-$d'
        dto_tmp = cls.date_order.replace('M','m').replace('D','d')
        cls.date_formatting_numeric = '%{0:s}{sep:s}%{1:s}{sep:s}%{2:s}'.format(dto_tmp[0],dto_tmp[1],dto_tmp[2],sep=Config.get('global','date_sep'))

        # Make format strings for longer formats, e.g. "Mon Dec 31, 2001"
        cls.date_formatting_text = Config.get('global','date_fmt_text')

        # Other format strings might be constructed if not set in config file
        # date_formatting_text_noyear
        cst = Config.get('global','date_fmt_text_noyear')
        cls.date_formatting_text_noyear = ' '.join(cls.date_formatting_text.replace('%y','%Y').replace('%Y,',' ').replace(', %Y',' ').replace('%Y','').split()) if not cst else cst

        # date_formatting_textabb
        cst = Config.get('global','date_fmt_textabb')
        cls.date_formatting_textabb = cls.date_formatting_text.replace('%A','%a').replace('%B','%b') if not cst else cst

        # date_formatting_textabb_noyear
        cst = Config.get('global','date_fmt_textabb_noyear')
        cls.date_formatting_textabb_noyear = ' '.join(cls.date_formatting_textabb.replace('%y','%Y').replace('%Y,',' ').replace(', %Y',' ').replace('%Y','').split()) if not cst else cst


    @staticmethod
    def _date_order_from_config() -> str:
        # Process date order string from config.
        # Converts, e.g. 'YYYY-MM-DD' -> 'YMD' & checks output is valid.
        raw = Config.get('global','date_ord').upper()
        ret = ''
        for ch in raw:
            if ch in 'YMD' and ch not in ret:
                ret += ch
        assert(len(ret)==3)
        return ret


    @classmethod
    def _init_views(cls) -> None:
        # Get new Gtk Widgets for views.
        # Add view switching options to menu.
        for v in GUI._VIEWS:
            m = import_module('.pygenda_view_{:s}'.format(v.lower()),package='pygenda')
            cls.views.append(getattr(m, 'View_{:s}'.format(v)))
            cls.view_widgets.append(cls.views[-1].init())
            cls.view_widgets[-1].get_style_context().add_class('view')

        menu_views_list = cls._builder.get_object('menu_views_list')
        accel_gp = Gtk.AccelGroup()
        cls._window.add_accel_group(accel_gp)
        for i in range(len(cls.views)):
            m = Gtk.MenuItem(cls.views[i].view_name())
            m.set_use_underline(True)
            akey = cls.views[i].accel_key()
            if akey:
                m.add_accelerator('activate', accel_gp, akey, Gdk.ModifierType.SHIFT_MASK|Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
            m.connect('activate',cls.switch_view,i)
            m.show()
            menu_views_list.add(m)


    @classmethod
    def _init_spinbuttons(cls) -> None:
        # Connect spinbutton keypress event to handler for extra features.
        # All spinbuttons are part of the Event dialog, so this could go
        # in the EventDialogController class. However, in theory spinbuttons
        # can be anywhere, so putting this in the general GUI class.
        for sb_id in ('allday_count','repeat_interval','repeat_occurrences'):
            sb = cls._builder.get_object(sb_id)
            sb.connect('key-press-event', cls._spinbutton_keypress)
            sb.connect('focus-out-event', cls._focusout_unhighlight)


    @classmethod
    def _init_comboboxes(cls) -> None:
        # Connect ComboBox events to handlers for extra features.
        for cb_id in ('combo_repeat_type','combo_bydaymonth','combo_byday_ord','combo_byday_day','combo_status','combo_todo_list','combo_todo_priority'):
            cb = cls._builder.get_object(cb_id)
            cb.connect('key-press-event', cls._combobox_keypress)


    @classmethod
    def _init_entryboxes(cls) -> None:
        # Connect Entry textbox events to handlers for extra features.
        for eb_id in ('entry_dialogevent_desc','entry_dialogevent_location','entry_dialogtodo_desc'):
            eb = cls._builder.get_object(eb_id)
            eb.connect('focus-out-event', cls._focusout_unhighlight)


    @classmethod
    def keypress(cls, wid:Gtk.Widget, ev:Gdk.EventKey) -> None:
        # Called whenever a key is pressed/repeated when View in focus
        cls.views[cls._view_idx].keypress(wid,ev)


    @staticmethod
    def _spinbutton_keypress(wid:Gtk.SpinButton, ev:Gdk.EventKey) -> bool:
        # Called to handle extra spinbutton keyboard controls
        shiftdown = ev.state&Gdk.ModifierType.SHIFT_MASK
        if ev.keyval in GUI.SPINBUTTON_INC_KEY or (shiftdown and ev.keyval==Gdk.KEY_Up):
            wid.update() # So if user types "5" then "+" value changes to "6"
            wid.spin(Gtk.SpinType.STEP_FORWARD, 1)
            return True # done
        if ev.keyval in GUI.SPINBUTTON_DEC_KEY or (shiftdown and ev.keyval==Gdk.KEY_Down):
            wid.update()
            wid.spin(Gtk.SpinType.STEP_BACKWARD, 1)
            return True # done
        if ev.keyval==Gdk.KEY_Up:
            return wid.get_toplevel().child_focus(Gtk.DirectionType.UP)
        if ev.keyval==Gdk.KEY_Down:
            return wid.get_toplevel().child_focus(Gtk.DirectionType.DOWN)
        return False # propagate event


    @staticmethod
    def _combobox_keypress(wid:Gtk.ComboBox, ev:Gdk.EventKey) -> bool:
        # Called to handle extra combobox keyboard controls
        # BUG!! This is not called when the combobox is in "popout" state
        if ev.keyval==Gdk.KEY_Return:
            # Manually trigger default event on dialog box
            dlg = wid.get_toplevel()
            if dlg:
                dlg.response(Gtk.ResponseType.OK)
            return True # done

        mdl = wid.get_model()
        count = mdl.iter_n_children()
        a = wid.get_active()
        shiftdown = ev.state&Gdk.ModifierType.SHIFT_MASK
        if ev.keyval in GUI.SPINBUTTON_INC_KEY or (shiftdown and ev.keyval==Gdk.KEY_Down):
            a = (a+1)%count
            wid.set_active(a)
            return True # done
        if ev.keyval in GUI.SPINBUTTON_DEC_KEY or (shiftdown and ev.keyval==Gdk.KEY_Up):
            if a<0:
                a = 0
            a = (a-1)%count
            wid.set_active(a)
            return True # done

        if ev.keyval==Gdk.KEY_Up:
            return wid.get_toplevel().child_focus(Gtk.DirectionType.UP)
        if ev.keyval==Gdk.KEY_Down:
            return wid.get_toplevel().child_focus(Gtk.DirectionType.DOWN)
        if ev.keyval in (Gdk.KEY_Left,Gdk.KEY_Right):
            # Return - otherwise detected as alphabetic (not sure why!)
            return False

        ch = chr(ev.keyval)
        if ch.isalpha() or ch.isdigit():
            ch = ch.lower()
            # Search for ch in first characters of combobox values
            it = mdl.iter_nth_child(None,a)
            for i in range(1,count):
                it = mdl.iter_next(it)
                if it is None: # at end of list, loop to top!
                    it = mdl.get_iter_first()
                ch1 = mdl.get(it,0)[0][0].lower()
                if ch==ch1:
                    wid.set_active((a+i)%count)
                    break
            return True # done

        return False # propagate event


    @staticmethod
    def _focusout_unhighlight(wid:Gtk.Widget, ev:Gdk.EventKey) -> bool:
        # Called to handle remove highlight from entry box/spinbutton
        # when focus moves to another widget
        dlg = wid.get_toplevel()
        if dlg.get_focus() != wid:
            wid.select_region(0,0) # remove highlight
        return False # propagate event


    @classmethod
    def view_redraw(cls, en_changes:bool=False) -> None:
        # Redraw the currently active view.
        # en_changes: bool, True if displayed entries need updating too
        cls.views[cls._view_idx].redraw(en_changes)


    @classmethod
    def switch_view(cls, wid:Gtk.Widget, idx:int=None) -> None:
        # Callback from UI widget (e.g. menu, softbutton) to change view.
        # idx = index of new view (otherwise goes to next view in list)
        if idx is None:
            # Go to next view in list
            cls._view_idx = (cls._view_idx+1)%len(cls.views)
        elif cls._view_idx == idx:
            return # No change, so skip redraw
        else:
            cls._view_idx = idx
        cls._eventbox.remove(cls._eventbox.get_child())
        new_view = cls.views[cls._view_idx]
        new_view.renew_display()
        new_view.redraw(True)
        new_wid = cls.view_widgets[cls._view_idx]
        cls._eventbox.add(new_wid)
        new_wid.grab_focus()
        new_wid.show_all()


    @classmethod
    def cursor_set(cls, dt:dt_date, idx:int=None) -> None:
        # Set current cursor date, and optionally the index within the date.
        # Call redraw on view if required.
        if dt != cls.cursor_date or (idx is not None and idx != cls.cursor_idx_in_date):
            cls.cursor_date = dt
            if idx is not None:
                cls.cursor_idx_in_date = idx
            cls.view_redraw(False)


    @classmethod
    def cursor_inc(cls, delta:timedelta, idx:int=None) -> None:
        # Add delta to current cursor date; optionally set index in date.
        # Call redraw on view.
        cls.cursor_date += delta
        if idx is not None:
            cls.cursor_idx_in_date = idx
        cls.view_redraw(False)


    # Main
    @classmethod
    def main(cls) -> None:
        # Run the man Gtk loop
        Gtk.main()


    # Signal handling functions
    @classmethod
    def exit(cls, *args) -> None:
        # Callback for various types of exit signal (command line, menus...)
        Gtk.main_quit()

    @classmethod
    def handler_newevent(cls, *args) -> None:
        # Callback for new event signal (menu, softbutton)
        date = cls.views[cls._view_idx].cursor_date()
        EventDialogController.newevent(date=date)

    @classmethod
    def handler_newtodo(cls, *args) -> None:
        # Callback for new todo signal (menu)
        lst = cls.views[cls._view_idx].cursor_todo_list()
        TodoDialogController.newtodo(list_idx=lst)

    @classmethod
    def handler_edittime(cls, *args) -> None:
        # Callback for change-entry-time signal (menu item)
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en:
            EventDialogController.editevent(en, EventDialogController.TAB_TIME)

    @classmethod
    def handler_editrepeats(cls, *args) -> None:
        # Callback for change-entry-repeats signal (menu item)
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en:
            EventDialogController.editevent(en, EventDialogController.TAB_REPEATS)

    @classmethod
    def handler_editalarm(cls, *args) -> None:
        # Callback for change-entry-alarm signal (menu item)
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en:
            EventDialogController.editevent(en, EventDialogController.TAB_ALARM)

    @classmethod
    def handler_editdetails(cls, *args) -> None:
        # Callback for change-entry-details signal (menu item)
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en:
            EventDialogController.editevent(en, EventDialogController.TAB_DETAILS)


    @classmethod
    def handler_stat_toggle(cls, stat:Optional[str]) -> None:
        # Handle signals from menu to change current entry's status.
        # Paramenter stat is None or text string for status (eg 'CONFIRMED').
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en:
            Calendar.set_toggle_status_entry(en, stat)
            cls.view_redraw(True)


    @classmethod
    def delete_request(cls, *args) -> None:
        # Callback to implement "delete" from GUI, e.g. backspace key pressed
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en is not None:
            cls.dialog_deleteentry(en)


    @classmethod
    def cut_request(cls, *args) -> None:
        # Handler to implement "cut" from GUI, e.g. cut clicked in menu
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en and 'SUMMARY' in en:
            if cls._lib_clip is None:
                # Don't do fallback - might lead to unexpected data loss
                print('Warning: No clipboard library, cut not available', file=stderr)
            elif 'RRULE' in en: # repeating entry
                # Need to think about how to implement this from UI side.
                # Problem: Does user expect single occurrence to be cut, or all?
                # Maybe bring up dialog "Cut single occurrence, or all repeats?"
                # Then, do we do the came for Copying repeating entries?
                # How do we adapt repeats when moved to a different date?
                print('Warning: Cutting repeating entries not implemented', file=stderr)
            else:
                txtbuf = bytes(en['SUMMARY'], 'utf-8')
                calbuf = en.to_ical()
                cls._lib_clip.set_cb(ctypes.create_string_buffer(txtbuf),ctypes.create_string_buffer(calbuf))
                Calendar.delete_entry(en)
                cls.view_redraw(True)


    @classmethod
    def copy_request(cls, *args) -> None:
        # Handler to implement "copy" from GUI, e.g. copy clicked in menu
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en and 'SUMMARY' in en:
            if cls._lib_clip is None:
                print('Warning: No clipboard library, fallback to text copy', file=stderr)
                cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                txt = en['SUMMARY']
                cb.set_text(txt, -1)
            else:
                txtbuf = bytes(en['SUMMARY'], 'utf-8')
                calbuf = en.to_ical()
                cls._lib_clip.set_cb(ctypes.create_string_buffer(txtbuf),ctypes.create_string_buffer(calbuf))


    @classmethod
    def paste_request(cls, *args) -> None:
        # Handler to implement "paste" from GUI, e.g. paste clicked in menu
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        # First, we try requesting a 'text/calendar' type from the clipboard
        sdat = cb.wait_for_contents(Gdk.Atom.intern('text/calendar', False))
        try:
            ical = iCalendar.from_ical(sdat.get_data())
            en = ical.walk()[0]
            cls.views[cls._view_idx].new_entry_from_example(en)
            cls.view_redraw(True)
            return
        except:
            None

        # Fallback: request plain text from clipboard
        txt = cb.wait_for_text()
        if txt is not None:
            txt = txt.strip()
            txt = txt.replace('\n',' ')
            txt = txt.replace('\t',' ')
            # What type of entry is created will depend on view, so call current view paste fn
            cls.views[cls._view_idx].paste_text(txt)


    @classmethod
    def dialog_deleteentry(cls, en:iEvent) -> None:
        # Dialog to implement "delete" from GUI, e.g. backspace key
        dialog = Gtk.Dialog(title=_('Delete Entry'), parent=cls._window,
            flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CLOSE, Gtk.STOCK_DELETE, Gtk.ResponseType.APPLY))
        if 'RRULE' in en:
            # repeating entry - clarify what is being deleted
            # !! We should really ask if user wants to delete all/single etc.
            l_template = _('Delete all repeats:\n"{:s}"?')
        else:
            l_template = _('Delete entry:\n"{:s}"?')
        lab = Gtk.Label(l_template.format(en['SUMMARY'] if 'SUMMARY' in en else u' ')) # narrow space
        if (not dialog or not lab): # Sanity check
            raise NameError('Dialog Delete creation failure')
        dialog.set_resizable(False)
        lab.set_justify(Gtk.Justification.CENTER)
        dialog.get_content_area().add(lab)
        dialog.set_default_response(Gtk.ResponseType.APPLY)#Enter action
        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.APPLY:
            Calendar.delete_entry(en)
            cls.view_redraw(True)


    @classmethod
    def dialog_goto(cls, *args) -> None:
        # Called to implement "go to" from GUI, e.g. button
        dialog = Gtk.Dialog(title=_('Go To'), parent=cls._window,
            flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CLOSE))
        wdate = WidgetDate(cls.cursor_date)
        if (not dialog or not wdate): # Allocation check
            raise NameError('Dialog Goto creation failure')
        wdate.connect('changed', GUI.check_date_fixed)
        dialog.set_resizable(False)
        dialog.get_content_area().add(wdate)
        wdate.set_halign(Gtk.Align.CENTER)
        icon = Gtk.Image()
        icon.set_from_stock(Gtk.STOCK_JUMP_TO, Gtk.IconSize.BUTTON)
        go_but = Gtk.Button(label=_('Go'), image=icon)
        go_but.set_can_default(True)
        dialog.add_action_widget(go_but, Gtk.ResponseType.APPLY)
        go_but.grab_default() # So "Enter" activates go_but
        dialog.show_all()
        while True:
            response = dialog.run()
            dt = wdate.get_approx_date_or_none() # So Feb 30th -> end of Feb
            if response!=Gtk.ResponseType.APPLY or dt is not None:
                break
            # Date is invalid, add error styling
            wdate.get_style_context().add_class(GUI.STYLE_ERR)
        if response == Gtk.ResponseType.APPLY:
            cls.cursor_set(dt)
        dialog.destroy()


    @staticmethod
    def check_date_fixed(wid:WidgetDate) -> None:
        # Removes error highlight if date is valid (e.g. not 30th Feb)
        # Would be nice to make this a method of WidgetDate class.
        # Can be used as a callback, e.g. attached to 'changed' signal
        if wid.get_date_or_none() is not None:
            wid.get_style_context().remove_class(GUI.STYLE_ERR)


    @classmethod
    def dialog_about(cls, *args) -> None:
        # Display the "About" dialog
        dialog = Gtk.AboutDialog(parent=cls._window)
        dialog.set_program_name('Pygenda')
        dialog.set_copyright(u'Copyright © 2022 Matthew Lewis')
        dialog.set_license_type(Gtk.License.GPL_3_0_ONLY)
        dialog.set_logo_icon_name('x-office-calendar')
        dialog.set_authors(('Matthew Lewis',))
        dialog.set_version('version {:s}'.format(__version__))
        dialog.set_comments(_(u'A calendar/agenda application written in Python/GTK3. The UI is inspired by the Agenda apps on the Psion Series 3 and Series 5 PDAs.\nWARNING: This is in-development code, released as a preview for developers. There will be bugs; please report them to: pygenda@semiprime.com.'))
        dialog.show_all()
        dialog.run()
        dialog.destroy()


    @classmethod
    def toggle_fullscreen(cls, *args) -> None:
        # Callback to toggle fullscreen mode on/off (e.g. from menu)
        # !! to-do: update menu text to reflect state
        cls._is_fullscreen = not cls._is_fullscreen
        if cls._is_fullscreen:
            cls._window.fullscreen()
        else:
            cls._window.unfullscreen()


    @classmethod
    def debug(cls, *args):
        # Temporary callback - delete me !!!!
        # Placeholder until we decide what fourth button does
        print('Button clicked {}'.format(args[0]))


    @classmethod
    def todo_titles_default_cats(cls) -> Tuple[list,list]:
        # Return titles and default categories of todo lists
        try:
            todo_idx = cls._VIEWS.index('Todo')
        except ValueError:
            return [], []
        tdv = cls.views[todo_idx]
        return tdv._list_titles, tdv._list_default_cats


# Singleton class to manage Event dialog (to create/edit Events)
class EventDialogController:
    TAB_TIME = 0
    TAB_REPEATS = 1
    TAB_ALARM = 2
    TAB_DETAILS = 3
    TAB_COUNT = 4

    dialog = None  # type: Gtk.Dialog
    wid_desc = None # type: Gtk.Entry
    _wid_desc_changed_handler = 0
    wid_date = None # type: WidgetDate
    wid_tabs = None # type: Gtk.Notebook

    # _empty_desc_allowed has three possible values:
    #   None - empty desc allowed in dialog (signals delete event)
    #   True - empty desc allowed, but can turn False!
    #   False - empty desc not allowed in dialog (e.g. new event)
    _empty_desc_allowed = None # type: Optional[bool]

    wid_timed_buttons = None # type: Gtk.Box
    # Create widgets for time & duration fields
    wid_time = WidgetTime(dt_time(hour=9))
    wid_dur = WidgetDuration(timedelta())
    wid_endtime = WidgetTime(dt_time(hour=9))
    revs_timedur = None
    revs_allday = None
    wid_allday_count = None # type: Gtk.SpinButton
    _tmdur_handler_time = 0
    _tmdur_handler_dur = 0
    _tmdur_handler_endtime = 0

    wid_rep_type = None # type: Gtk.ComboBox
    revs_repeat = None
    revs_rep_monthdays = None
    revs_rep_weekdays = None
    revs_rep_monthweekdays = None
    wid_rep_interval = None # type: Gtk.SpinButton
    wid_rep_forever = None # type: Gtk.CheckButton
    wid_repbymonthday = None # type: Gtk.ComboBox
    wid_repbyweekday_day = None # type: Gtk.ComboBox
    wid_repbyweekday_ord = None # type: Gtk.ComboBox
    wid_rep_occs = None # type: Gtk.SpinButton
    wid_rep_enddt = None # type: WidgetDate
    revs_rep_ends = None
    rep_occs_determines_end = True
    _rep_handler_date = 0
    _rep_handler_time = 0
    _rep_handler_type = 0
    _rep_handler_mday = 0
    _rep_handler_wdayday = 0
    _rep_handler_wdayord = 0
    _rep_handler_inter = 0
    _rep_handler_occs = 0
    _rep_handler_enddt = 0
    _lab_rep_exceptions = None # type: Gtk.Label
    repbymonthday_initialized = False
    repbyweekday_initialized = False
    dur_determines_end = False
    exception_list = [] # type: List[dt_date]

    wid_alarmset = None # type: Gtk.Switch

    wid_status = None # type: Gtk.ComboBox
    wid_location = None # type: Gtk.Entry


    @classmethod
    def init(cls) -> None:
        # Initialiser for singleton class.
        # Called from GUI init_stage2().

        # Get some references to dialog elements in glade
        cls.dialog = GUI._builder.get_object('dialog_event')
        if (not cls.dialog): # Sanity check
            raise NameError('Dialog Event not found')

        cls.wid_desc = GUI._builder.get_object('entry_dialogevent_desc')
        cls._wid_desc_changed_handler = cls.wid_desc.connect('changed', cls._desc_changed)
        wid_grid = GUI._builder.get_object('dialogevent_grid')
        cls.wid_tabs = GUI._builder.get_object('dialogevent_tabs')

        # Create & add event date widget
        cls.wid_date = WidgetDate(GUI.cursor_date)
        wid_grid.attach(cls.wid_date, 1,1, 1,1)# Can we locate this another way?
        cls.wid_date.show_all()

        # Init other groups of widgets
        cls._init_timefields()
        cls._init_repeatfields()
        cls._init_alarmfields()
        cls._init_detailfields()
        cls._init_navigation()


    @classmethod
    def _init_timefields(cls) -> None:
        # Initialise widgets etc in the Event dialog under the "Time" tab.
        # Called on app startup.
        cls.wid_timed_buttons = GUI._builder.get_object('radiobuttons_istimed').get_children()

        # Add time & duration widgets to dialog
        wid_reveal_tm_e = GUI._builder.get_object('revealer_time_e')
        tbox = wid_reveal_tm_e.get_child() # should be a GtkBox
        tbox.add(cls.wid_time)
        tbox.add(cls.wid_dur)
        tbox.add(cls.wid_endtime)
        tbox.show_all()

        # Make lists of revealers, so they can be hidden/revealed
        cls.revs_timedur = cls._revealers_from_ids('revealer_time_l', 'revealer_time_e')
        cls.revs_allday = cls._revealers_from_ids('revealer_allday_l', 'revealer_allday_e')
        cls.wid_allday_count = GUI._builder.get_object('allday_count')

        cls.wid_timed_buttons[1].connect('toggled', cls._do_timed_toggle)
        cls.wid_timed_buttons[2].connect('toggled', cls._do_allday_toggle)

        # We keep references to these connections, so then can be (un)blocked.
        cls._tmdur_handler_time = cls.wid_time.connect('changed', cls._tmdur_changed, 0)
        cls._tmdur_handler_dur = cls.wid_dur.connect('changed', cls._tmdur_changed, 1)
        cls._tmdur_handler_endtime = cls.wid_endtime.connect('changed', cls._tmdur_changed, 2)

        # By default the signal is *blocked* - unblock when dialog active
        cls._block_tmdur_signals()


    @classmethod
    def _init_repeatfields(cls) -> None:
        # Initialise widgets etc in the Event dialog under the "Repeats" tab.
        # Called on app startup.
        cls.wid_rep_type = GUI._builder.get_object('combo_repeat_type')
        cls.revs_repeat = cls._revealers_from_ids('revealer_repeat_l','revealer_repeat_e')
        cls.revs_rep_monthdays = cls._revealers_from_ids('revealer_repeat_monthday_e')
        cls.revs_rep_weekdays = cls._revealers_from_ids('revealer_repeat_weekday_e')
        cls.revs_rep_monthweekdays = cls._revealers_from_ids('revealer_repeat_day_l')
        cls.wid_rep_type.connect('changed', cls._reptype_changed)

        cls.wid_rep_interval = GUI._builder.get_object('repeat_interval')
        cls.wid_rep_forever = GUI._builder.get_object('repeat_forever')
        cls.wid_repbymonthday = GUI._builder.get_object('combo_bydaymonth')
        cls.wid_repbyweekday_day = GUI._builder.get_object('combo_byday_day')
        cls.wid_repbyweekday_ord = GUI._builder.get_object('combo_byday_ord')
        cls.wid_rep_forever.connect('toggled', cls._do_repeatforever_toggle)

        cls.wid_rep_occs = GUI._builder.get_object('repeat_occurrences')
        cls.wid_rep_enddt = WidgetDate(GUI.cursor_date)
        rbox = GUI._builder.get_object('revealer_repeat_until_e').get_child() # Should be a GtkBox
        rbox.add(cls.wid_rep_enddt)
        rbox.show_all()
        cls.revs_rep_ends = cls._revealers_from_ids('revealer_repeat_until_l', 'revealer_repeat_until_e')

        cls._rep_handler_date = cls.wid_date.connect('changed', cls._repend_changed,0)
        cls._rep_handler_time = cls.wid_time.connect('changed', cls._repend_changed,0)
        cls._rep_handler_type = cls.wid_rep_type.connect('changed', cls._repend_changed,0)
        cls._rep_handler_mday = cls.wid_repbymonthday.connect('changed', cls._repend_changed,0)
        cls._rep_handler_wdayday = cls.wid_repbyweekday_day.connect('changed', cls._repend_changed,0)
        cls._rep_handler_wdayord = cls.wid_repbyweekday_ord.connect('changed', cls._repend_changed,0)
        cls._rep_handler_inter = cls.wid_rep_interval.connect('changed', cls._repend_changed,0)
        cls._rep_handler_occs = cls.wid_rep_occs.connect('changed', cls._repend_changed,1)
        cls._rep_handler_enddt = cls.wid_rep_enddt.connect('changed', cls._repend_changed,2)

        # For repeat on "1st Sat." etc, we fill ComboBox with local day names
        day = Config.get_int('global','start_week_day')
        for i in range(7):
            cls.wid_repbyweekday_day.append(RepeatInfo.DAY_ABBR[day],day_name[day])
            day = (day+1)%7

        # Get label used to display exception dates
        cls._lab_rep_exceptions = GUI._builder.get_object('lab_rep_exceptions')

        # We want default to be signal *blocked* - unblock when dialog active
        cls._block_rep_occend_signals()


    @classmethod
    def _init_alarmfields(cls) -> None:
        # Initialise widgets etc in the Event dialog under the "Alarm" tab.
        # Called on app startup.
        cls.wid_alarmset = GUI._builder.get_object('alarm-set')


    @classmethod
    def _init_detailfields(cls) -> None:
        # Initialise widgets etc in the Event dialog under the "Details" tab.
        # Called on app startup.
        cls.wid_status = GUI._builder.get_object('combo_status')
        cls.wid_location = GUI._builder.get_object('entry_dialogevent_location')


    @classmethod
    def _init_navigation(cls) -> None:
        # For some reason, cannot generally navigate up/down from
        # radio buttons. This sets up a custom handler.
        for i in range(3):
            cls.wid_timed_buttons[i].connect('key_press_event', cls._radiobutton_keypress)


    @classmethod
    def _revealers_from_ids(cls, *idlist) -> list:
        # Given a list of id strings, in glade file, make a list of revealers
        revs = []
        for id in idlist:
            obj = GUI._builder.get_object(id)
            if obj is not None:
                revs.append(obj)
                # Reduce transition time, o/w devices like Gemini feel sluggish.
                # Tried to do this with CSS, so could be set per device,
                # but couldn't get it to work. So this is a workaround.
                # Alternative: in ~/.config/gtk-3.0/settings.ini, try one of
                #   gtk-enable-animations=0
                #   gtk-revealer-transition-duration=10
                obj.set_transition_duration(20) # millisecs; default 250
            else:
                print('Warning: Object with id "{:s}" not found'.format(id), file=stderr)
        return revs


    @staticmethod
    def _do_multireveal(revlist, reveal:bool) -> None:
        # Given a list of ids, reveal (or hide) children
        for r in revlist:
            r.set_reveal_child(reveal)


    @staticmethod
    def _radiobutton_keypress(wid:Gtk.RadioButton, ev:Gdk.EventKey) -> bool:
        # Custom hander for up/down keys on radiobuttons.
        # Note: Assumes there's nothing to left/right so can use TAB_FWD/BKWD
        if ev.keyval==Gdk.KEY_Up:
            return wid.get_toplevel().child_focus(Gtk.DirectionType.TAB_BACKWARD)
        if ev.keyval==Gdk.KEY_Down:
            return wid.get_toplevel().child_focus(Gtk.DirectionType.TAB_FORWARD)
        return False # Indicates event still needs handling - propagate it


    @classmethod
    def _cancel_empty_desc_allowed(cls) -> None:
        # Change _empty_desc_allowed True->False
        # Leave unchanged if is None
        if cls._empty_desc_allowed:
            cls._empty_desc_allowed = False


    @classmethod
    def _do_timed_toggle(cls, wid:Gtk.RadioButton) -> None:
        # Callback. Called when "timed" radio button changes state.
        # Reveals/hides appropriate sub-obtions, and flags that
        # dialog state had been changed.
        ti = cls.wid_timed_buttons[1].get_active()
        cls._do_multireveal(cls.revs_timedur, ti)
        cls._cancel_empty_desc_allowed()


    @classmethod
    def _do_allday_toggle(cls, wid:Gtk.RadioButton) -> None:
        # Callback. Called when "all day" radio button changes state.
        # Reveals/hides appropriate sub-obtions, and flags that
        # dialog state had been changed.
        ad = cls.wid_timed_buttons[2].get_active()
        cls._do_multireveal(cls.revs_allday, ad)
        cls._cancel_empty_desc_allowed()


    @classmethod
    def _desc_changed(cls, wid:Gtk.Entry) -> None:
        # Callback. Called when event description is changed by user.
        # Flags that dialog state had been changed.
        # Removes error state styling if it is no longer needed.
        if cls.wid_desc.get_text(): # if desc field is non-empty
            cls._cancel_empty_desc_allowed()
        cls._is_valid_event(set_style=False) # remove error styles if present


    @classmethod
    def _reptype_changed(cls, wid:Gtk.ComboBox) -> None:
        # Callback. Called when event repeat type is changed by user.
        # Reveals/hides relevant sub-options.
        # wid should be the repeat-type combobox
        st = wid.get_active()>0
        cls._do_multireveal(cls.revs_repeat, st)
        monthday = (wid.get_active_id()=='MONTHLY-MONTHDAY')
        weekday = (wid.get_active_id()=='MONTHLY-WEEKDAY') # Booleans
        cls._do_multireveal(cls.revs_rep_monthdays, monthday)
        cls._do_multireveal(cls.revs_rep_weekdays, weekday)
        cls._do_multireveal(cls.revs_rep_monthweekdays, monthday or weekday)
        if monthday and not cls.repbymonthday_initialized:
            # First time shown showing monthday-repeats, so initialise based on start date
            cls.repbymonthday_initialized = True
            sdt = cls.get_date_start()
            if sdt is None: # Fallback in case date is invalid
                cls.wid_repbymonthday.set_active(0)
            else:
                idx = sdt.day - monthrange(sdt.year,sdt.month)[1] - 1
                if -7 <= idx <= -2:
                    cls.wid_repbymonthday.set_active_id(str(idx))
                else:
                    cls.wid_repbymonthday.set_active(0)
        elif weekday and not cls.repbyweekday_initialized:
            # First time shown showing weekday-repeats, so initialise based on start date
            cls.repbyweekday_initialized = True
            sdt = cls.get_date_start()
            if sdt is None: # Fallback in case date is invalid
                cls.wid_repbyweekday_ord.set_active(0)
                cls.wid_repbyweekday_day.set_active(0)
            else:
                wkst = Config.get_int('global','start_week_day')
                cls.wid_repbyweekday_day.set_active((sdt.weekday()-wkst)%7)
                if sdt.day<=21:
                    # Value will be, e.g. "1st", "2nd" (Tues of month)
                    cls.wid_repbyweekday_ord.set_active_id(str(1+(sdt.day-1)//7))
                else:
                    # Want, e.g. "last" (Friday of month)
                    rem = monthrange(sdt.year,sdt.month)[1]-sdt.day
                    cls.wid_repbyweekday_ord.set_active_id(str(-1-(rem//7)))
        cls._cancel_empty_desc_allowed()


    @classmethod
    def _do_repeatforever_toggle(cls, wid:Gtk.Button) -> None:
        # Callback. Called when repeat-forever state is changed by user.
        # Reveals/hides relevant sub-options.
        st = not wid.get_active() #If *not* forever, we show repeat-til options
        cls._do_multireveal(cls.revs_rep_ends, st)
        if st:
            # Want to make sure revealed elements are synced
            if cls.rep_occs_determines_end:
                cls._sync_rep_occs_end()
            else:
                # if enddate determines occs, need to check enddate>=startdate
                sdt = cls.get_date_start()
                edt = cls.wid_rep_enddt.get_date_or_none()
                if sdt is not None and (edt is None or edt < sdt):
                    cls.wid_rep_enddt.set_date(sdt)
                    cls.wid_rep_occs.set_value(1)

        cls._cancel_empty_desc_allowed()


    @classmethod
    def _block_tmdur_signals(cls) -> None:
        # Block update signals from start time, duration & endtime
        # fields, so they can be updated programmatically without
        # getting "update signal feedback loops".
        cls.wid_time.handler_block(cls._tmdur_handler_time)
        cls.wid_dur.handler_block(cls._tmdur_handler_dur)
        cls.wid_endtime.handler_block(cls._tmdur_handler_endtime)


    @classmethod
    def _unblock_tmdur_signals(cls) -> None:
        # Unblock update signals from start time, duration & endtime
        # fields, so if user changes one then other fields update.
        cls.wid_time.handler_unblock(cls._tmdur_handler_time)
        cls.wid_dur.handler_unblock(cls._tmdur_handler_dur)
        cls.wid_endtime.handler_unblock(cls._tmdur_handler_endtime)


    @classmethod
    def _block_rep_occend_signals(cls) -> None:
        # Function to disable "changed" signals from various widgets that
        # lead to either the end-date or repeat count being re-calculated
        # based on the new values. Generally, keep signals blocked except
        # when the dialog is being shown to the user.
        cls.wid_date.handler_block(cls._rep_handler_date)
        cls.wid_time.handler_block(cls._rep_handler_time)
        cls.wid_rep_type.handler_block(cls._rep_handler_type)
        cls.wid_repbymonthday.handler_block(cls._rep_handler_mday)
        cls.wid_repbyweekday_day.handler_block(cls._rep_handler_wdayday)
        cls.wid_repbyweekday_ord.handler_block(cls._rep_handler_wdayord)
        cls.wid_rep_interval.handler_block(cls._rep_handler_inter)
        cls.wid_rep_occs.handler_block(cls._rep_handler_occs)
        cls.wid_rep_enddt.handler_block(cls._rep_handler_enddt)


    @classmethod
    def _unblock_rep_occend_signals(cls) -> None:
        # Function to re-enable "changed" signals from various widgets that
        # lead to either the end-date or repeat count being re-calculated
        # based on the new values. Generally, unblock when the dialog is
        # being used and user can change these values.
        cls.wid_date.handler_unblock(cls._rep_handler_date)
        cls.wid_time.handler_unblock(cls._rep_handler_time)
        cls.wid_rep_type.handler_unblock(cls._rep_handler_type)
        cls.wid_repbymonthday.handler_unblock(cls._rep_handler_mday)
        cls.wid_repbyweekday_day.handler_unblock(cls._rep_handler_wdayday)
        cls.wid_repbyweekday_ord.handler_unblock(cls._rep_handler_wdayord)
        cls.wid_rep_interval.handler_unblock(cls._rep_handler_inter)
        cls.wid_rep_occs.handler_unblock(cls._rep_handler_occs)
        cls.wid_rep_enddt.handler_unblock(cls._rep_handler_enddt)


    @classmethod
    def _tmdur_changed(cls, wid:Gtk.Widget, el:int) -> None:
        # Callback. Called when starttime/endtime/duration changed.
        # 'el' paramenter indicates which one changed (but could use wid).
        sdt = cls.get_date_start()
        stm = cls.wid_time.get_time_or_none()
        d = cls.wid_dur.get_duration_or_none()
        etm = cls.wid_endtime.get_time_or_none()
        if sdt is not None and stm is not None and d is not None and etm is not None:
            # First, update which of dur & end-time determines the other
            if el==1:
                cls.dur_determines_end = True
            elif el==2:
                cls.dur_determines_end = False

            # Second, do the required update
            cls._block_tmdur_signals() # prevent accidental recursion
            try:
                st_dttm = dt_datetime.combine(sdt,stm)
                if cls.dur_determines_end:
                    cls.wid_endtime.set_time(st_dttm+d)
                else: # need to update dur
                    end_dttm = dt_datetime.combine(sdt,etm)
                    if end_dttm<st_dttm:
                        end_dttm += timedelta(days=1)
                    cls.wid_dur.set_duration(end_dttm - st_dttm)
            finally:
                cls._unblock_tmdur_signals()
        cls._cancel_empty_desc_allowed()
        cls._is_valid_event(set_style=False) # remove error styles if present


    @classmethod
    def _repend_changed(cls, wid:Gtk.Widget, el:int) -> None:
        # Handler for signals from any widget that might result in either the
        # repeat end-date or occurence count changing. Prompts recalculation
        # and possibly also updates which of end-date/occurences is the leader.
        # Variable el indicates if either possible leader was updated.
        if el == 1: # Occurrences edited, make it "leader"
            cls.rep_occs_determines_end = True
            cls._set_occs_min(1)
        elif el == 2: # Repeat until edited, make it "leader"
            cls.rep_occs_determines_end = False

        cls._block_rep_occend_signals() # prevent accidental recursion
        try:
            cls._sync_rep_occs_end()
        finally:
            cls._unblock_rep_occend_signals()
        cls._cancel_empty_desc_allowed()
        cls._is_valid_event(set_style=False) # remove error styles if present


    @classmethod
    def _set_occs_min(cls, mn:int) -> None:
        # quick method to set minimum of the occurrences spinbutton
        mx = cls.wid_rep_occs.get_range().max
        cls.wid_rep_occs.set_range(mn,mx)


    # Maps used to calculate repeats using dateutil.rrule class
    MAP_RTYPE_TO_RRULE = {
        'YEARLY': du_rrule.YEARLY,
        'MONTHLY': du_rrule.MONTHLY,
        'MONTHLY-MONTHDAY': du_rrule.MONTHLY,
        'MONTHLY-WEEKDAY': du_rrule.MONTHLY,
        'WEEKLY': du_rrule.WEEKLY,
        'DAILY': du_rrule.DAILY,
        'HOURLY': du_rrule.HOURLY,
        'MINUTELY': du_rrule.MINUTELY,
        'SECONDLY': du_rrule.SECONDLY
        }

    MAP_RDAY_TO_RRULEDAY = {
        'MO': du_rrule.MO,
        'TU': du_rrule.TU,
        'WE': du_rrule.WE,
        'TH': du_rrule.TH,
        'FR': du_rrule.FR,
        'SA': du_rrule.SA,
        'SU': du_rrule.SU
        }

    @classmethod
    def _sync_rep_occs_end(cls) -> None:
        # Function to recalculate repeat end-date or occurences count.
        # Called when widgets that might affect repeat counts are updated.
        if cls.wid_rep_forever.get_active():
            return
        rtype = cls.wid_rep_type.get_active_id()
        if rtype is None:
            return
        if cls.rep_occs_determines_end:
            stdt = cls.get_date_start()
            if stdt is not None:
                span = (cls.get_repeat_occurrences()-1) * cls.get_repeat_interval()
                if rtype=='YEARLY':
                    if stdt.day==29 and stdt.month==2: # 29th Feb - leap day!
                        cls._sync_rep_end_from_occ_rrule(rtype)
                        return
                    delta = relativedelta(years=span)
                elif rtype=='MONTHLY':
                    if cls.get_datetime_start().day>=29:
                        cls._sync_rep_end_from_occ_rrule(rtype)
                        return
                    else:
                        delta = relativedelta(months=span)
                elif rtype=='WEEKLY':
                    delta = timedelta(days=span*7)
                elif rtype=='DAILY':
                    delta = timedelta(days=span)
                elif rtype=='HOURLY':
                    delta = timedelta(hours=span)
                elif rtype=='MINUTELY':
                    delta = timedelta(minutes=span)
                elif rtype=='SECONDLY':
                    delta = timedelta(seconds=span)
                elif rtype in ('MONTHLY-MONTHDAY','MONTHLY-WEEKDAY'):
                    cls._sync_rep_end_from_occ_rrule(rtype)
                    return
                else:
                    # !! Don't know how to sync
                    print('Warning: Sync for {} not implemented'.format(rtype), file=stderr)
                    return
                edt = stdt+delta
                cls.wid_rep_enddt.set_date(edt)
        else: # occurrences determined by end date - use dateutil:rrule to calc
            try:
                fr = cls.MAP_RTYPE_TO_RRULE[rtype]
            except KeyError:
                # !! Don't know how to sync
                print('Warning: Sync for {} not implemented'.format(rtype), file=stderr)
                return
            bymtdy = None
            bywkdy = None
            if rtype=='MONTHLY-MONTHDAY':
                bymtdy = cls._get_cal_monthday_rep()
            elif rtype=='MONTHLY-WEEKDAY':
                bywkdy = cls._get_cal_weekday_rep()
            dtst = cls.get_date_start() # Without time, because time breaks calc
            interv = cls.get_repeat_interval()
            rend = cls.wid_rep_enddt.get_date_or_none()
            if dtst is not None and rend is not None:
                rr = du_rrule.rrule(fr, dtstart=dtst, interval=interv, until=rend, byweekday=bywkdy, bymonthday=bymtdy)
                c = rr.count()
                if c>=0:
                    cls._set_occs_min(0 if c==0 else 1) # possibly allow "0"
                    cls.wid_rep_occs.set_value(c)


    @classmethod
    def _sync_rep_end_from_occ_rrule(cls, rtype:str) -> None:
        # Function to synchronise End Date repeat field from Occurrences in
        # complex situations, e.g. leapday (29 Feb) or monthly late in month.
        # Use rrule class for these.
        try:
            fr = cls.MAP_RTYPE_TO_RRULE[rtype]
        except KeyError:
            # !! Don't know how to sync
            print('Warning: Sync for {} not implemented'.format(rtype), file=stderr)
            return
        dtst = cls.get_datetime_start()
        if dtst is None:
            return
        interv = cls.get_repeat_interval()
        occs = cls.get_repeat_occurrences()
        bymtdy = None
        bywkdy = None
        if rtype=='MONTHLY-MONTHDAY':
            bymtdy = cls._get_cal_monthday_rep()
        elif rtype=='MONTHLY-WEEKDAY':
            bywkdy = cls._get_cal_weekday_rep()
        rr = du_rrule.rrule(fr, dtstart=dtst, interval=interv, count=occs, byweekday=bywkdy, bymonthday=bymtdy)
        edt = list(rr)[-1]
        cls.wid_rep_enddt.set_date(edt)


    @classmethod
    def _get_cal_monthday_rep(cls) -> int:
        # Return value for monthday repeats to pass to rrule
        retd = int(cls.wid_repbymonthday.get_active_id())
        return retd


    @classmethod
    def _get_cal_weekday_rep(cls) -> du_rrule.weekday:
        # Return rrule structure for weekday repeats.
        # E.g. MO(-2) = "2nd last Monday"
        rrwd = cls.MAP_RDAY_TO_RRULEDAY[cls.wid_repbyweekday_day.get_active_id()](int(cls.wid_repbyweekday_ord.get_active_id()))
        return rrwd


    @classmethod
    def newevent(cls, txt:str=None, date:dt_date=None) -> None:
        # Called to implement "new event" from GUI, e.g. menu
        cls.dialog.set_title(_('New Event'))
        cls._empty_desc_allowed = True # initially allowed, can switch to False
        response,ei = cls._do_event_dialog(txt=txt, date=date)
        if response==Gtk.ResponseType.OK and ei.desc:
            Calendar.new_entry(ei)
            if ei.rep_type is None:
                # Jump to event date (not repeating, so well-defined)
                # !! This is a quick fix most common case. Need to fix:
                #    - Multiple entries on one day - jump to correct
                #    - Repeating entries (jump to visible/closest)
                GUI.cursor_date = ei.get_start_date()
            GUI.view_redraw(True)


    @classmethod
    def editevent(cls, event:iEvent, subtab:int=None) -> None:
        # Called to implement "edit event" from GUI
        cls.dialog.set_title(_('Edit Event'))
        cls._empty_desc_allowed = None # empty desc always allowed (for delete)
        response,ei = cls._do_event_dialog(event=event, subtab=subtab)
        if response==Gtk.ResponseType.OK:
            if ei.desc:
                Calendar.update_entry(event, ei)
                if ei.rep_type is None:
                    # Jump to event date
                    GUI.cursor_date = ei.get_start_date()
                GUI.view_redraw(True)
            else: # Description text has been deleted in dialog
                GUI.dialog_deleteentry(event)


    @classmethod
    def _do_event_dialog(cls, event:iEvent=None, txt:str=None, date:dt_date=None, subtab:int=None) -> Tuple[int,EntryInfo]:
        # Do the core work displaying event dialog and extracting result.
        # Called from both newevent() and editevent().
        cls._seed_fields(event, txt, date)

        # Select visible subtab: time, repeats, alarms...
        cls.wid_tabs.set_current_page(0) # default
        if subtab is not None: # jump to tab requested
            cls.wid_tabs.set_current_page(subtab)
            cls.wid_tabs.grab_focus()
            cls.wid_desc.select_region(0,0) # remove highlight

        cls._reset_err_style() # clear old error highlights

        # Unblock signals when dialog is active (user interaction -> updates)
        cls._unblock_tmdur_signals()
        cls._unblock_rep_occend_signals()
        try:
            while True:
                response = cls.dialog.run()
                if response!=Gtk.ResponseType.OK or cls._is_valid_event(set_style=True):
                    break
                cls._cancel_empty_desc_allowed() # after OK, desc required
        finally:
            # re-block signals
            cls._block_tmdur_signals()
            cls._block_rep_occend_signals()
            cls.dialog.hide()

        return response,cls._get_entryinfo()


    @classmethod
    def _seed_fields(cls, event:iEvent, txt:Optional[str], date:Optional[dt_date]) -> None:
        # Initialise fields when dialog is opened.
        # Data optionally from an existing event, or text used as summary.
        # !! This function is a horrible mess. Needs rationalising !!

        # Set defaults
        dur = None
        end_dttm = None
        cls.dur_determines_end = True
        cls.wid_allday_count.set_value(1)
        cls.wid_rep_type.set_active(0)
        cls.repbymonthday_initialized = False # Init these later when we can
        cls.repbyweekday_initialized = False  # choose appropriate values.
        cls.wid_rep_interval.set_value(1)
        cls.wid_rep_forever.set_active(True)
        cls.rep_occs_determines_end = True
        cls._set_occs_min(1)
        cls.wid_rep_occs.set_value(1)
        # No need to set wid_rep_enddt because it will be synced when revealed
        cls.wid_status.set_active(0)
        cls.wid_location.set_text('')
        cls.wid_alarmset.set_active(False)

        # Two cases: new event or edit existing event
        if event is None:
            # Initialise decscription field
            # We don't want this to count as user interaction, so block signal
            cls.wid_desc.handler_block(cls._wid_desc_changed_handler)
            if txt is None:
                cls.wid_desc.set_text('') # clear text
            else:
                cls.wid_desc.set_text(txt)
                cls.wid_desc.set_position(len(txt))
            cls.wid_desc.handler_unblock(cls._wid_desc_changed_handler)#unblock
            cls.wid_desc.grab_focus_without_selecting()
            dt = dt_date.today() if date is None else date
            tm = None
        else: # existing entry - take values
            cls.wid_desc.set_text(event['SUMMARY'] if 'SUMMARY' in event else '')
            cls.wid_desc.grab_focus()
            dt = event['DTSTART'].dt
            dttm = None
            if isinstance(dt,dt_datetime):
                dttm = dt
                dt = dttm.date()
                tm = dttm.time()
                if 'DTEND' in event:
                    end_dttm = event['DTEND'].dt
                    if isinstance(end_dttm, dt_time):
                        end_dttm = dt_datetime.combine(dt,end_dttm)
                        if end_dttm<dttm:
                            end_dttm += timedelta(days=1)
                elif 'DURATION' in event:
                    dur = event['DURATION'].dt
            elif isinstance(dt,dt_date):
                tm = None
                if 'DTEND' in event and isinstance(event['DTEND'].dt, dt_date):
                    end_dttm = event['DTEND'].dt
            else: # dt is neither a date nor a datetime
                raise TypeError("Event date of unexpected type")
            if 'RRULE' in event:
                rrule = event['RRULE']
                rrfreq = rrule['FREQ'][0]
                if rrfreq == 'MONTHLY' and 'BYDAY' in rrule:
                    cls.wid_rep_type.set_active_id('MONTHLY-WEEKDAY')
                    byday = rrule['BYDAY'][0]
                    cls.repbyweekday_initialized = True
                    cls.wid_repbyweekday_ord.set_active_id(byday[1 if byday[0]=='+' else 0:-2])
                    cls.wid_repbyweekday_day.set_active_id(byday[-2:])
                elif rrfreq == 'MONTHLY' and 'BYMONTHDAY' in rrule:
                    if len(rrule['BYMONTHDAY'])!=1:
                        raise TypeError('Editing repeat with multiple \'BYMONTHDAY\' not (yet) supported')
                    cls.wid_rep_type.set_active_id('MONTHLY-MONTHDAY')
                    bymday = rrule['BYMONTHDAY'][0]
                    if not(-7 <= int(bymday) <= -1):
                        raise TypeError('Editing repeat with BYMONTHDAY={} not (yet) supported'.format(bymday))
                    cls.wid_repbymonthday.set_active_id(str(bymday))
                    cls.repbymonthday_initialized = True
                elif rrfreq in ('YEARLY','MONTHLY','WEEKLY','DAILY'):
                    cls.wid_rep_type.set_active_id(rrfreq)
                else:
                    raise TypeError('Editing repeat freq \'{}\' not (yet) supported'.format(rrfreq))
                cls.wid_rep_interval.set_value(int(rrule['INTERVAL'][0]) if 'INTERVAL' in rrule else 1)
                if 'COUNT' in rrule:
                    cls.wid_rep_forever.set_active(False)
                    c = rrule['COUNT'][0]
                    cls.wid_rep_occs.set_value(c if c>=1 else 1)
                    cls.rep_occs_determines_end = True
                elif 'UNTIL' in rrule:
                    cls.wid_rep_forever.set_active(False)
                    u = rrule['UNTIL'][0]
                    if isinstance(u,dt_datetime):
                        u = u.date()
                    cls.wid_rep_enddt.set_date(u if u>dt else dt)
                    cls.rep_occs_determines_end = False
            if 'STATUS' in event and event['STATUS'] in ('TENTATIVE','CONFIRMED','CANCELLED'):
                cls.wid_status.set_active_id(event['STATUS'])
            if 'LOCATION' in event:
                cls.wid_location.set_text(event['LOCATION'])
            if event.walk('VALARM'):
                cls.wid_alarmset.set_active(True)

        cls.wid_date.set_date(dt)
        cls._sync_rep_occs_end()

        if tm is None:
            # Setting radio buttons for Untimed/Timed/Allday.
            # This also reveals appropriate UI elements via signal connections.
            if end_dttm is None:
                cls.wid_timed_buttons[0].set_active(True)
            else:
                cls.wid_timed_buttons[2].set_active(True)
                d = end_dttm - dt
                cls.wid_allday_count.set_value(d.days)
            tm = dt_time(hour=9)
        else:
            cls.wid_timed_buttons[1].set_active(True)
        cls.wid_time.set_time(tm)

        if dur is not None:
            end_dttm = dttm + dur
            cls.dur_determines_end = True
        elif end_dttm is not None and dttm is not None:
            dur = end_dttm - dttm
            cls.dur_determines_end = False

        if dur is None:
            cls.wid_dur.set_duration(timedelta(0))
            cls.wid_endtime.set_time(tm)
        else:
            cls.wid_dur.set_duration(dur)
            cls.wid_endtime.set_time(end_dttm.time())

        cls._seed_rep_exception_list(event)


    @classmethod
    def _seed_rep_exception_list(cls, event:iEvent) -> None:
        # Sets & displays repeat exception list from event parameter.
        # Called from _seed_fields() when dialog is opened.
        cls._set_rep_exception_list(event)
        cls._set_label_rep_list()


    @classmethod
    def _set_rep_exception_list(cls, event:iEvent) -> None:
        # Set cls.exception_list to list of exception dates for event
        cls.exception_list = []
        if event is None or 'RRULE' not in event or 'EXDATE' not in event:
            return
        exdate = event['EXDATE']
        if isinstance(exdate,list):
            # Create set => elements unique
            dtlist = set([datetime_to_date(t.dts[i].dt) for t in exdate for i in range(len(t.dts))])
        else:
            dtlist = set([datetime_to_date(t.dt) for t in exdate.dts])
        cls.exception_list = sorted(dtlist)


    @classmethod
    def _set_label_rep_list(cls) -> None:
        # Construct string and set text for label widget displaying
        # exception dates. Takes dates from cls.exception_list.
        list_txt = ''
        first = True
        for dt in cls.exception_list:
            if not first:
                list_txt += ', '
            list_txt += dt.strftime(GUI.date_formatting_numeric)
            first = False
        if not list_txt:
            list_txt = _('None')
        cls._lab_rep_exceptions.set_text(list_txt)


    @classmethod
    def _get_entryinfo(cls) -> EntryInfo:
        # Decipher dialog fields and return info as an EntryInfo object.
        desc = cls.wid_desc.get_text()
        dt = cls.get_datetime_start()
        stat = cls.wid_status.get_active_id()
        loc = cls.wid_location.get_text()
        ei = EntryInfo(desc=desc, start_dt=dt, status=stat, location=loc)
        if cls.wid_timed_buttons[2].get_active():
            # "Day entry" selected, read number of days from widget
            d = max(1,int(cls.wid_allday_count.get_value()))
            ei.set_end_dt(dt+timedelta(days=d))
        elif cls.dur_determines_end:
            ei.set_duration(cls.wid_dur.get_duration_or_none())
        else:
            ei.set_end_dt(cls.wid_endtime.get_time_or_none())

        # repeat information
        reptype = cls.wid_rep_type.get_active_id()
        if reptype is not None:
            inter = cls.get_repeat_interval()
            count = None
            until = None
            byday = None
            bymonthday = None
            if reptype=='MONTHLY-WEEKDAY':
                reptype = 'MONTHLY'
                byday = cls.wid_repbyweekday_ord.get_active_id() + cls.wid_repbyweekday_day.get_active_id()
            elif reptype=='MONTHLY-MONTHDAY':
                reptype = 'MONTHLY'
                bymonthday = cls.wid_repbymonthday.get_active_id()
            if not cls.wid_rep_forever.get_active():
                if cls.rep_occs_determines_end:
                    count = cls.get_repeat_occurrences()
                else:
                    until = cls.wid_rep_enddt.get_date_or_none()
            ei.set_repeat_info(reptype, interval=inter, count=count, until=until, bymonthday=bymonthday, byday=byday, except_list=cls._get_exceptions_list_for_type())
        return ei


    @classmethod
    def _get_exceptions_list_for_type(cls) -> Optional[list]:
        # Return exceptions list transformed to match event.
        # E.g. if a timed event, return timed exceptions.
        if len(cls.exception_list)==0:
            return None
        if cls.wid_timed_buttons[1].get_active():
            # Include the time in exclusions for timed entries.
            # This seems to be the most correct interpretation of
            # RFC-5545, Sec 3.8.5.1. (However, when reading exdates
            # we'll try to be more generous for wider compatibility.)
            tm = cls.wid_time.get_time_or_none()
            if tm is not None:
                return [ dt_datetime.combine(dt,tm) for dt in cls.exception_list]
        return cls.exception_list


    @classmethod
    def _is_valid_event(cls, set_style:bool=False) -> bool:
        # Function checks if event dialog fields are valid.
        # Used when "OK" clicked in the dialog (so important!).
        # Returns True if all fields valid; False if *any* field is invalid.
        # If an event is invalid and set_style==True it also adds a
        # CSS class to the widget, so the error is visibly indicated.
        # If the event is valid then it removes the error style, so
        # the error indication will disappear (regardless of set_style).

        ret = True
        # Check description is good (optional)
        ctx = cls.wid_desc.get_style_context()
        if cls._empty_desc_allowed==False and not cls.wid_desc.get_text(): # is empty string
            ret = False
            if set_style:
                ctx.add_class(GUI.STYLE_ERR)
        else:
            ctx.remove_class(GUI.STYLE_ERR)

        # Check date is good (e.g. not February 30th)
        ctx = cls.wid_date.get_style_context()
        st_dt = cls.get_date_start()
        if st_dt is None:
            ret = False
            if set_style:
                ctx.add_class(GUI.STYLE_ERR)
        else: # always try to remove style, so corrections visible
            ctx.remove_class(GUI.STYLE_ERR)

        # Track tabs were errors found so they can be selected if needed
        err_tabs = [False]*cls.TAB_COUNT

        # Check start time is good (e.g. not 10:70)
        ctx = cls.wid_time.get_style_context()
        if cls.wid_time.get_time_or_none() is None:
            ret = False
            if set_style:
                ctx.add_class(GUI.STYLE_ERR)
                err_tabs[cls.TAB_TIME] = True
        else:
            ctx.remove_class(GUI.STYLE_ERR)

        # Check duration is good
        # Don't want to do an if/else here because need to reset conterpart
        ctx = cls.wid_dur.get_style_context()
        if cls.dur_determines_end and cls.wid_dur.get_duration_or_none() is None:
            ret = False
            if set_style:
                ctx.add_class(GUI.STYLE_ERR)
                err_tabs[cls.TAB_TIME] = True
        else:
            ctx.remove_class(GUI.STYLE_ERR)

        # Check end time is good
        ctx = cls.wid_endtime.get_style_context()
        if not cls.dur_determines_end and cls.wid_endtime.get_time_or_none() is None:
            ret = False
            if set_style:
                ctx.add_class(GUI.STYLE_ERR)
                err_tabs[cls.TAB_TIME] = True
        else:
            ctx.remove_class(GUI.STYLE_ERR)

        # Shared Boolean used in checking repeat enddate & occs
        reps_active = cls.wid_rep_type.get_active()>0 and not cls.wid_rep_forever.get_active()

        # Check end repeat date is good
        ctx = cls.wid_rep_enddt.get_style_context()
        end_dt = cls.wid_rep_enddt.get_date_or_none()
        if reps_active and (end_dt is None or (st_dt is not None and end_dt<st_dt)):
            ret = False
            if set_style:
                ctx.add_class(GUI.STYLE_ERR)
                err_tabs[cls.TAB_REPEATS] = True
        else:
            ctx.remove_class(GUI.STYLE_ERR)

        # Check repeat occurrences is good
        ctx = cls.wid_rep_occs.get_style_context()
        if reps_active and cls.wid_rep_occs.get_value()<1:
            ret = False
            if set_style:
                ctx.add_class(GUI.STYLE_ERR)
                err_tabs[cls.TAB_REPEATS] = True
        else:
            ctx.remove_class(GUI.STYLE_ERR)

        # Move to a tab with highlighted errors if not already on one
        if set_style and not err_tabs[cls.wid_tabs.get_current_page()]:
            for i in range(cls.TAB_COUNT):
                if err_tabs[i]:
                    cls.wid_tabs.set_current_page(i)
                    break

        return ret


    @classmethod
    def _reset_err_style(cls) -> None:
        # Remove 'dialog_error' style class from event dialog widgets where
        # it might be set, so any visible indications of errors are removed.
        # Used, for example, when the dialog is reinitialised.
        for w in (cls.wid_desc, cls.wid_date, cls.wid_time, cls.wid_dur, cls.wid_endtime, cls.wid_rep_enddt, cls.wid_rep_occs):
            w.get_style_context().remove_class(GUI.STYLE_ERR)


    @classmethod
    def get_date_start(cls) -> dt_date:
        # Convenience function to get start date from dialog (None if invalid)
        return cls.wid_date.get_date_or_none()


    @classmethod
    def get_datetime_start(cls) -> dt_date:
        # Returns start date & time from dialog if time set; o/w just the date
        dt = cls.wid_date.get_date_or_none()
        if dt is not None and cls.wid_timed_buttons[1].get_active():
            # timed event
            tm = cls.wid_time.get_time_or_none()
            if tm is not None:
                dt = dt_datetime.combine(dt,tm)
        return dt


    @classmethod
    def get_repeat_interval(cls) -> int:
        # Use get_text() rather than get_value() since there can be
        # delays in value being updated. This can lead to outdated
        # values being reported. This happens almost all the time
        # on the Gemini device.
        try:
            r = int(cls.wid_rep_interval.get_text())
            if r<1:
                r = 1
        except ValueError:
            r = 1
        return r


    @classmethod
    def get_repeat_occurrences(cls) -> int:
        # Use get_text() rather than get_value() - see above.
        try:
            r = int(cls.wid_rep_occs.get_text())
            if r<1:
                r = 1
        except ValueError:
            r = 1
        return r


    @classmethod
    def dialog_repeat_exceptions(cls, *args) -> None:
        # Callback for +/- button to open sub-dialog for "repeat exceptions"
        edc = ExceptionsDialogController(cls.exception_list, parent=cls.dialog)
        result = edc.run()
        if result==Gtk.ResponseType.OK:
            dates = sorted(edc.get_dates())
            cls.exception_list = dates
            cls._set_label_rep_list()
        edc.destroy()


class DateLabel(Gtk.Label):
    # Label Widget displaying a date.
    # Used for rows in listbox of Exception dates dialog.

    def __init__(self, date:dt_date):
        # !! date argument assumed a dt_date here; may be dt_datetime in future
        self.date = date
        st = self.date.strftime(GUI.date_formatting_textabb)
        super().__init__(st)


    def compare(self, dl2:Gtk.Label) -> int:
        # Compare two DateLabels.
        # Return <0 if self<dl2; 0 if equal; >0 otherwise.
        # Used to sort ListBox.
        # !! If using datetime, then this won't distinguish within day
        o1 = self.date.toordinal()
        o2 = dl2.date.toordinal()
        return o1-o2


class ExceptionsDialogController:
    # Dialog box to add/remove a repeating event's "Exception dates".
    # Called when +/- button is clicked in Event Repeats tab.

    def __init__(self, ex_date_list:list, parent:Gtk.Window=None):
        self.dialog = Gtk.Dialog(title=_('Exception dates'), parent=parent,
            flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CLOSE, Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.dialog.set_resizable(False)
        content = Gtk.Box()
        add_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        list_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.add(add_content)
        content.add(list_content)
        self.dialog.get_content_area().add(content)

        # Date widget
        self.wdate = WidgetDate(GUI.cursor_date)
        self.wdate.connect('changed', GUI.check_date_fixed)
        add_content.add(self.wdate)

        # Add date button
        button_add = Gtk.Button(_('Add date'))
        button_add.get_style_context().add_class('dialogbutton')
        button_add.connect('clicked', self._add_date, self)
        add_content.add(button_add)

        # Date listbox (scrollable)
        list_scroller = Gtk.ScrolledWindow()
        list_scroller.set_size_request(-1,70) # temporary magic number !!
        list_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        list_scroller.set_overlay_scrolling(False)
        self.list_listbox = Gtk.ListBox()
        self.list_listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.list_listbox.set_activate_on_single_click(False)
        self.list_listbox.set_sort_func(self._sort_func)
        for dt in set(ex_date_list): # set() to uniquify
            lab = DateLabel(dt)
            self.list_listbox.add(lab)
        list_scroller.add(self.list_listbox)
        list_content.add(list_scroller)

        # Remove date(s) button
        button_remove = Gtk.Button(_('Remove date(s)'))
        button_remove.get_style_context().add_class('dialogbutton')
        button_remove.connect('clicked', self._remove_dates, self)
        list_content.add(button_remove)

        # !! Add WIP notice, so status is clear to user !!
        wip_label = Gtk.Label('Note: this dialog needs refining!')
        self.dialog.get_content_area().add(wip_label)

        self.dialog.show_all()


    def run(self) -> Gtk.ResponseType:
        # run the dialog
        return self.dialog.run()


    def destroy(self) -> None:
        # destroy the dialog
        self.dialog.destroy()


    def get_dates(self) -> set:
        # Return list of dates.
        # Returned as a set, so guaranteed no repeats, but not sorted.
        dl = {row.get_child().date for row in self.list_listbox.get_children()}
        return dl


    @staticmethod
    def _add_date(button:Gtk.Button, ctrl:'ExceptionsDialogController') -> None:
        # Callback when "Add date" button is clicked
        dt = ctrl.wdate.get_date_or_none()
        if dt is None:
            # Date is invalid, add error styling
            ctrl.wdate.get_style_context().add_class(GUI.STYLE_ERR)
        else:
            ctrl.list_listbox.unselect_all() # so new row can be highlighted
            for row in ctrl.list_listbox.get_children():
                if dt == row.get_child().date:
                    # date already in list - highlight & stop
                    ctrl.list_listbox.select_row(row)
                    return
            lab = DateLabel(dt)
            lab.show_all()
            ctrl.list_listbox.add(lab)
            # Now select the new row - helps to see where new entry is,
            # and also means it can be quickly deleted if added in error.
            ctrl.list_listbox.select_row(lab.get_parent())


    @staticmethod
    def _remove_dates(button:Gtk.Button, ctrl:'ExceptionsDialogController') -> None:
        # Callback when "Remove dates" button is clicked
        selected = ctrl.list_listbox.get_selected_rows()
        for row in selected:
            ctrl.list_listbox.remove(row)


    @staticmethod
    def _sort_func(row1:Gtk.ListBoxRow, row2:Gtk.ListBoxRow) -> int:
        # Used as sort function for listbox.
        return row1.get_child().compare(row2.get_child())


# Singleton class to manage Todo dialog
class TodoDialogController:
    dialog = None # type: Gtk.Dialog
    wid_desc = None # type: Gtk.Entry
    wid_todolist = None # type: Gtk.ComboBoxText
    wid_priority = None # type: Gtk.ComboBoxText
    list_default_cats = None # type: list

    @classmethod
    def init(cls) -> None:
        # Initialiser for TodoDialogController singleton class.
        # Called from GUI init_stage2().

        # Get some references to dialog elements in glade
        cls.dialog = GUI._builder.get_object('dialog_todo')
        if (not cls.dialog): # Sanity check
            raise NameError('Dialog Todo not found')

        cls.wid_desc = GUI._builder.get_object('entry_dialogtodo_desc')
        cls._init_todolists()
        cls.wid_priority = GUI._builder.get_object('combo_todo_priority')


    @classmethod
    def _init_todolists(cls) -> None:
        # Get reference to todo-list combobox & initialise its entries
        cls.wid_todolist = GUI._builder.get_object('combo_todo_list')
        todo_titles, cls.list_default_cats = GUI.todo_titles_default_cats()
        for t in todo_titles:
            cls.wid_todolist.append_text(t)


    @classmethod
    def newtodo(cls, txt:str=None, list_idx:int=None) -> None:
        # Called to implement "new todo" from GUI, e.g. menu
        cls.dialog.set_title(_('New To-do'))
        response,ei = cls._do_todo_dialog(txt=txt, list_idx=list_idx)
        if response==Gtk.ResponseType.OK and ei.desc:
            Calendar.new_entry(ei)
            GUI.view_redraw(True)


    @classmethod
    def edittodo(cls, todo:iTodo, list_idx:int=None) -> None:
        # Called to implement "edit todo" from GUI
        cls.dialog.set_title(_('Edit To-do'))
        response,ei = cls._do_todo_dialog(todo=todo, list_idx=list_idx)
        if response==Gtk.ResponseType.OK:
            if ei.desc:
                Calendar.update_entry(todo, ei)
                GUI.view_redraw(True)
            else: # Description text has been deleted in dialog
                GUI.dialog_deleteentry(todo)


    @classmethod
    def _do_todo_dialog(cls, txt:str=None, todo:iTodo=None, list_idx:Optional[int]=0) -> Tuple[int,EntryInfo]:
        # Do the core work displaying todo dialog and extracting result.
        if list_idx==None: # View has not specified a default todo list
            list_idx = 0
        cls.wid_priority.set_active(0)
        if todo is not None:
            # existing entry - take values
            cls.wid_desc.set_text(todo['SUMMARY'] if 'SUMMARY' in todo else'')
            cls.wid_desc.grab_focus()
            if 'PRIORITY' in todo:
                p = int(todo['PRIORITY'])
                cls.wid_priority.set_active(p if 1<=p<=9 else 0)
        elif txt is None:
            cls.wid_desc.set_text('') # clear text
        else:
            cls.wid_desc.set_text(txt)
            cls.wid_desc.set_position(len(txt))
        cls.wid_todolist.set_active(list_idx)
        cls.wid_desc.grab_focus_without_selecting()

        try:
            while True:
                response = cls.dialog.run()
                break
        finally:
            cls.dialog.hide()

        return response,cls._get_entryinfo()


    @classmethod
    def _get_entryinfo(cls) -> EntryInfo:
        # Decipher entry fields and return info as an EntryInfo object.
        desc = cls.wid_desc.get_text()
        ei = EntryInfo(type=EntryInfo.TYPE_TODO, desc=desc)
        list_idx = cls.wid_todolist.get_active()
        ei.set_categories(cls.list_default_cats[list_idx])
        ei.set_priority(cls.wid_priority.get_active())
        return ei
