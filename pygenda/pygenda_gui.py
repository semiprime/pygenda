# -*- coding: utf-8 -*-
#
# pygenda_gui.py
# Top-level GUI code and shared elements (e.g. menu, soft buttons)
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
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio

from datetime import date as dt_date, time as dt_time, datetime as dt_datetime, timedelta
from icalendar import Calendar as iCalendar, Event as iEvent, Todo as iTodo
from importlib import import_module
from os import path as ospath
from sys import stderr
import signal
import ctypes
from typing import Optional, Tuple, List, Union, Any, Type

# for internationalisation/localisation
import locale
_ = locale.gettext

# pygenda components
from .pygenda_config import Config
from .pygenda_calendar import Calendar
from .pygenda_widgets import WidgetDate
from .pygenda_util import guess_date_ord_from_locale,guess_date_sep_from_locale,guess_time_sep_from_locale, guess_date_fmt_text_from_locale, datetime_to_date
from .pygenda_version import __version__

# Dialog classes - imported in _init_dialogs()
EventDialogController = None # type:Any
TodoDialogController = None # type:Any
FindDialogController = None # type:Any
EntryPropertiesDialog = None # type:Any
EventPropertyBeyondEditDialog = None # type:Any
TodoPropertyBeyondEditDialog = None # type:Any


# Singleton class for top-level GUI control
class GUI:
    _CSS_FILE_APP = '{:s}/css/pygenda.css'.format(ospath.dirname(__file__))
    _CSS_FILE_USER = GLib.get_user_config_dir() + '/pygenda/pygenda.css'
    _LOCALE_DIR = '{:s}/locale/'.format(ospath.dirname(__file__))
    _VIEWS = ('Week','Year','Todo') # Order gives order in menus
    SPINBUTTON_INC_KEY = (Gdk.KEY_plus,Gdk.KEY_greater)
    SPINBUTTON_DEC_KEY = (Gdk.KEY_minus,Gdk.KEY_less)
    STYLE_TXTLABEL = 'tlabel'
    STYLE_TXTPROP = 'plabel'
    STYLE_ERR = 'dialog_error'

    views = [] # type: List[Type]
    view_widgets = [] # type: List[Gtk.Widget]
    _view_idx = 0 # take first view as default
    _toggle_view_idx = -1 # used to toggle between views (Esc key)

    _lib_clip = None

    _builder = Gtk.Builder()
    _window = None # type: Gtk.Window
    _is_fullscreen = False
    _box_view_cont = None # type: Gtk.Box
    _eventbox = Gtk.EventBox()

    _menu_elt_fullscreen = None # type: Gtk.Widget
    _menu_elts_entry = None # type: Tuple[Gtk.Widget,...]
    _menu_elts_event = None # type: Tuple[Gtk.Widget,...]
    _menu_elts_stat_event = None # type: Tuple[Gtk.Widget,...]
    _menu_elts_stat_todo = None # type: Tuple[Gtk.Widget,...]

    _image_leave_fs = Gtk.Image.new_from_icon_name('gtk-leave-fullscreen',Gtk.IconSize.MENU)
    _image_enter_fs = None # type: Gtk.Widget

    date_order = ''
    date_formatting_numeric = ''
    date_formatting_text = ''
    date_formatting_text_noyear = ''
    date_formatting_textabb = ''
    date_formatting_textabb_noyear = ''

    _plus_minus_zoom = False

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
        'plus_minus_zoom': True,
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
        cls.load_glade_file('main.glade')

        cls._window = cls._builder.get_object('window_main')
        if (not cls._window): # Sanity check
            raise NameError('Main window not found')
        cls._window.set_default_icon_name('x-office-calendar')

        cls._window.set_hide_titlebar_when_maximized(Config.get_bool('global','hide_titlebar_when_maximized'))
        if Config.get_bool('startup','maximize'):
            cls._window.maximize()
        cls._menu_elt_fullscreen = cls._builder.get_object('menuelt-fullscreen')
        cls._image_enter_fs = cls._menu_elt_fullscreen.get_image()
        if Config.get_bool('startup','fullscreen'):
            cls.toggle_fullscreen()

        # Get handles to menu items to enable/disable when on/not on an entry
        cls._menu_elts_entry = cls._get_objs_by_id(('menuelt-cut','menuelt-copy','menuelt-delete','menuelt-show-entry-props','menuelt-set-status'))
        cls._menu_elts_event = cls._get_objs_by_id(('menuelt-edit-time','menuelt-edit-reps','menuelt-edit-alarm','menuelt-edit-details'))
        cls._menu_elts_stat_event = cls._get_objs_by_id(('menuelt-status-confirmed','menuelt-status-tentative'))
        cls._menu_elts_stat_todo = cls._get_objs_by_id(('menuelt-status-needsaction','menuelt-status-inprocess','menuelt-status-completed'))

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
            'menuitem_deleteentry': cls.delete_request,
            'menuitem_newevent': cls.handler_newevent,
            'menuitem_newtodo': cls.handler_newtodo,
            'menuitem_show_entry_props': cls.handler_showentryprops,
            'menuitem_edittime': cls.handler_edittime,
            'menuitem_editrepeats': cls.handler_editrepeats,
            'menuitem_editalarm': cls.handler_editalarm,
            'menuitem_editdetails': cls.handler_editdetails,
            'menuitem_stat_none': lambda a: cls.handler_stat_toggle(None),
            'menuitem_stat_confirmed': lambda a: cls.handler_stat_toggle('CONFIRMED'),
            'menuitem_stat_canceled': lambda a: cls.handler_stat_toggle('CANCELLED'),
            'menuitem_stat_tentative': lambda a: cls.handler_stat_toggle('TENTATIVE'),
            'menuitem_stat_needsaction': lambda a: cls.handler_stat_toggle('NEEDS-ACTION'),
            'menuitem_stat_inprocess': lambda a: cls.handler_stat_toggle('IN-PROCESS'),
            'menuitem_stat_completed': lambda a: cls.handler_stat_toggle('COMPLETED'),
            'menuitem_switchview': cls.switch_view,
            'menuitem_zoomin': lambda a: cls.zoom(+1),
            'menuitem_zoomout': lambda a: cls.zoom(-1),
            'menuitem_fullscreen': cls.toggle_fullscreen,
            'menuitem_goto': cls.dialog_goto,
            'menuitem_find': cls.handler_find,
            'menuitem_about': cls.dialog_about,
            'button0_clicked': cls.handler_newevent,
            'button1_clicked': cls.switch_view,
            'button2_clicked': cls.dialog_goto,
            'button3_clicked': cls.zoom_button,
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


    @classmethod
    def _get_objs_by_id(cls, id_list:Tuple[str,...]) -> Tuple[Gtk.Widget,...]:
        # Helper function to get a tuple of widgets by id
        return tuple((cls._builder.get_object(id) for id in id_list))


    @classmethod
    def load_glade_file(cls, gfile:str) -> None:
        # Load GUI elements from GTK Builder XML glade file in glade directory
        fullname = ospath.dirname(__file__) + '/glade/' + gfile
        r = cls._builder.add_from_file(fullname)
        if not r:
            print('Error loading glade file '+gfile, file=stderr)
            Gtk.main_quit()


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
        # !! Should probably move these as GIL means they aren't async
        cls._init_clipboard()
        cls._init_date_format()

        # Wait for calendar to finish initialising before doing views
        while cls._starting_cal:
            if Gtk.main_iteration_do(False):
                # True => main_quit() has been called
                ci_cancel.cancel()
                return
            GLib.usleep(8000) # microsecs; low->smooth spin, high->fast start
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

        # If view set in config, set index
        vw = Config.get('startup','view')
        if vw:
            for ii in range(len(GUI._VIEWS)):
                if GUI._VIEWS[ii].lower() == vw:
                    cls._view_idx = ii
                    break

        # If date set from command line, jump there now
        if Config.date:
            for i in range(cls._view_idx, cls._view_idx+len(cls.views)):
                if cls.views[i%len(cls.views)].cursor_set_date(Config.date):
                    break

        cls._box_view_cont.pack_start(cls._eventbox, True, True, 0)
        cls._box_view_cont.reorder_child(cls._eventbox, view_pos)
        cls._eventbox.add(cls.view_widgets[cls._view_idx])
        cls._eventbox.connect('key-press-event', cls.keypress)
        cls._eventbox.connect('key-release-event', cls.keyrelease)
        cls.view_widgets[cls._view_idx].grab_focus() # so it gets keypresses
        del(cls._box_view_cont) # don't need this anymore

        cls._init_config()
        cls._init_dialogs()

        # Add functionality to spinbuttons not provided by GTK
        cls._init_spinbuttons()
        cls._init_comboboxes()
        cls._init_entryboxes()

        # Menu bar & softbutton bar made insensitive in .glade for startup.
        # We make them sensitive here before activating view.
        cls._builder.get_object('menu_bar').set_sensitive(True)
        cls._builder.get_object('box_buttons').set_sensitive(True)

        cls.view_redraw(True) # Draw active view, including entries
        cls._eventbox.show_all()


    @classmethod
    def _init_config(cls) -> None:
        # Read config settings at startup
        cls._plus_minus_zoom = Config.get_bool('global','plus_minus_zoom')


    @staticmethod
    def _init_dialogs() -> None:
        # Import and initialise dialog classes.
        # Doing imports here avoids circular dependencies.
        global EventDialogController, EventPropertyBeyondEditDialog, TodoDialogController, TodoPropertyBeyondEditDialog, EntryPropertiesDialog, FindDialogController

        from .pygenda_dialog_event import EventDialogController, EventPropertyBeyondEditDialog
        EventDialogController.init()

        from .pygenda_dialog_todo import TodoDialogController, TodoPropertyBeyondEditDialog
        TodoDialogController.init() # Need to do this after Todo View init

        from .pygenda_dialog_find import FindDialogController
        FindDialogController.init()

        from .pygenda_dialog_entryprops import EntryPropertiesDialog


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
        # Get Gtk Widgets for views; add view switching options to menu
        for v in GUI._VIEWS:
            m = import_module('.pygenda_view_{:s}'.format(v.lower()),package='pygenda')
            cls.views.append(getattr(m, 'View_{:s}'.format(v)))
            cls.view_widgets.append(cls.views[-1].init())
            cls.view_widgets[-1].get_style_context().add_class('view')

        # Add views to menu, so the user can switch to them
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
        for cb_id in ('combo_repeat_type','combo_repeaton_year','combo_repeaton_month','combo_status','combo_todo_list','combo_todo_priority','combo_todo_status'):
            cb = cls._builder.get_object(cb_id)
            cb.connect('key-press-event', cls._combobox_keypress)


    @classmethod
    def _init_entryboxes(cls) -> None:
        # Connect Entry textbox events to handlers for extra features.
        for eb_id in ('entry_dialogevent_desc','entry_dialogevent_location','entry_dialogtodo_desc'):
            eb = cls._builder.get_object(eb_id)
            eb.connect('focus-out-event', cls._focusout_unhighlight)


    @classmethod
    def set_menu_elts(cls, on_event:bool=False, on_todo:bool=False) -> None:
        # Called from Views as the cursor is moved. Enables/disables/hides
        # menu items appropriate for the current cursor item.
        for id in cls._menu_elts_entry:
            id.set_sensitive(on_event or on_todo)
        for id in cls._menu_elts_event:
            id.set_sensitive(on_event)
        if on_event:
            for id in cls._menu_elts_stat_event:
                id.show()
            for id in cls._menu_elts_stat_todo:
                id.hide()
        elif on_todo:
            for id in cls._menu_elts_stat_event:
                id.hide()
            for id in cls._menu_elts_stat_todo:
                id.show()


    @classmethod
    def keypress(cls, wid:Gtk.Widget, ev:Gdk.EventKey) -> bool:
        # Called whenever a key is pressed/repeated when View in focus
        if cls._plus_minus_zoom:
            if ev.keyval==Gdk.KEY_plus:
                cls.zoom(+1)
                return True # handled
            elif ev.keyval==Gdk.KEY_minus:
                cls.zoom(-1)
                return True # handled
        if ev.keyval==Gdk.KEY_Escape:
            if cls._toggle_view_idx >= 0:
                cls.switch_view(None, cls._toggle_view_idx)
        else:
            cls.views[cls._view_idx].keypress(wid,ev)
        return True # event handled - don't propagate


    @classmethod
    def keyrelease(cls, wid:Gtk.Widget, ev:Gdk.EventKey) -> bool:
        # Called whenever a key is released
        cls.views[cls._view_idx].keyrelease(wid,ev)
        return True # event handled - don't propagate


    @staticmethod
    def _spinbutton_keypress(wid:Gtk.SpinButton, ev:Gdk.EventKey) -> bool:
        # Called to handle extra spinbutton keyboard controls
        shiftdown = ev.state&Gdk.ModifierType.SHIFT_MASK
        if ev.keyval in GUI.SPINBUTTON_INC_KEY or (shiftdown and ev.keyval==Gdk.KEY_Up):
            wid.update() # So if user types "5" then "+" value changes to "6"
            wid.spin(Gtk.SpinType.STEP_FORWARD, 1)
            return True # done, don't propagate
        if ev.keyval in GUI.SPINBUTTON_DEC_KEY or (shiftdown and ev.keyval==Gdk.KEY_Down):
            wid.update()
            wid.spin(Gtk.SpinType.STEP_BACKWARD, 1)
            return True # done
        if ev.keyval==Gdk.KEY_Up:
            return wid.get_toplevel().child_focus(Gtk.DirectionType.UP)
        if ev.keyval==Gdk.KEY_Down:
            return wid.get_toplevel().child_focus(Gtk.DirectionType.DOWN)
        return False # unhandled, so propagate event


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
            return True # done, don't propagate

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
            return True # done, don't propagate

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
        cls.views[cls._view_idx].redraw(en_changes=en_changes)


    @classmethod
    def switch_view(cls, wid:Gtk.Widget, idx:int=None, redraw:bool=True) -> bool:
        # Callback from UI widget (e.g. menu, softbutton) to change view.
        # idx = index of new view (otherwise goes to next view in list)
        if idx is None:
            # Go to next view in list
            cls._toggle_view_idx = cls._view_idx
            cls._view_idx = (cls._view_idx+1)%len(cls.views)
        elif cls._view_idx == idx:
            return True # No change, so skip redraw & don't propagate event
        else:
            cls._toggle_view_idx = cls._view_idx
            cls._view_idx = idx
        cls._eventbox.remove(cls._eventbox.get_child())
        new_view = cls.views[cls._view_idx]
        new_view.renew_display()
        if redraw:
            new_view.redraw(en_changes=True)
        new_wid = cls.view_widgets[cls._view_idx]
        cls._eventbox.add(new_wid)
        new_wid.grab_focus()
        new_wid.show_all()
        return True # don't propagate event


    @classmethod
    def cursor_goto_date(cls, dt:dt_date) -> None:
        # Call view to set current cursor date.
        # If current view does not support setting date (e.g. Todo View)
        # try next view etc., and make successful view active.
        # (N.B.: Does not call redraw - caller needs to handle that.)
        for i in range(cls._view_idx, cls._view_idx+len(cls.views)):
            v = i%len(cls.views)
            if cls.views[v].cursor_set_date(dt): # True if view can show date
                if v != cls._view_idx:
                    cls.switch_view(None, v, redraw=False)
                break


    @classmethod
    def cursor_goto_event(cls, ev:iEvent) -> None:
        # Call view to move cursor to given event.
        # If current view does not support showing event (e.g. Todo View),
        # try next view etc., and make successful view active.
        # (N.B.: Does not call redraw - caller needs to handle that.)
        for i in range(cls._view_idx, cls._view_idx+len(cls.views)):
            v = i%len(cls.views)
            if cls.views[v].cursor_goto_event(ev): # True if view can show event
                if v != cls._view_idx:
                    cls.switch_view(None, v, redraw=False)
                break


    @classmethod
    def cursor_goto_todo(cls, todo:iTodo, list_idx:int) -> None:
        # Call view to move cursor to given todo in given todo list.
        # If current view does not support displaying todo, try
        # the next view etc., and make successful view active.
        # (N.B.: Does not call redraw - caller needs to handle that.)
        for i in range(cls._view_idx, cls._view_idx+len(cls.views)):
            v = i%len(cls.views)
            if cls.views[v].cursor_goto_todo(todo, list_idx): # True if view can show todo
                if v != cls._view_idx:
                    cls.switch_view(None, v, redraw=False)
                break


    # Main
    @classmethod
    def main(cls) -> None:
        # Run the man Gtk loop
        Gtk.main()


    # Signal handling functions
    @classmethod
    def exit(cls, *args) -> bool:
        # Callback for various types of exit signal (command line, menus...)
        Gtk.main_quit()
        return True # don't propagate event

    @classmethod
    def handler_newevent(cls, *args) -> bool:
        # Callback for "Create new event" signal (menu, softbutton)
        date = cls.views[cls._view_idx].cursor_date()
        EventDialogController.new_event(date=date)
        return True # don't propagate event

    @classmethod
    def handler_newtodo(cls, *args) -> bool:
        # Callback for "Create new todo" signal (menu)
        lst = cls.views[cls._view_idx].cursor_todo_list()
        TodoDialogController.new_todo(list_idx=lst)
        return True # don't propagate event

    @classmethod
    def handler_find(cls, *args) -> bool:
        # Callback for find signal (menu)
        FindDialogController.find()
        return True # don't propagate event

    @classmethod
    def handler_showentryprops(cls, *args) -> bool:
        # Callback for "show entry properties" signal (menu item)
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en:
            cls.dialog_showentryprops(en)
        return True # don't propagate event

    @classmethod
    def handler_edittime(cls, *args) -> bool:
        # Callback for "edit entry time" signal (menu item)
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en:
            cls.edit_or_display_event(en, EventDialogController.TAB_TIME)
        return True # don't propagate event

    @classmethod
    def handler_editrepeats(cls, *args) -> bool:
        # Callback for "edit entry repeats" signal (menu item)
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en:
            cls.edit_or_display_event(en, EventDialogController.TAB_REPEATS)
        return True # don't propagate event

    @classmethod
    def handler_editalarm(cls, *args) -> bool:
        # Callback for "edit entry alarms" signal (menu item)
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en:
            cls.edit_or_display_event(en, EventDialogController.TAB_ALARM)
        return True # don't propagate event

    @classmethod
    def handler_editdetails(cls, *args) -> bool:
        # Callback for "edit entry details" signal (menu item)
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en:
            cls.edit_or_display_event(en, EventDialogController.TAB_DETAILS)
        return True # don't propagate event


    @classmethod
    def edit_or_display_event(cls, en:iEvent, subtab:int=None) -> None:
        # Bring up dialog to edit event, or show details if not editable
        try:
            EventDialogController.edit_event(en, subtab)
        except EventPropertyBeyondEditDialog as exc:
            print('Warning: {:s} - showing entry properties'.format(str(exc)), file=stderr)
            cls.dialog_showentryprops(en)


    @classmethod
    def edit_or_display_todo(cls, todo:iTodo, list_idx:int=None) -> None:
        # Bring up dialog to edit todo item, or show details if not editable
        try:
            TodoDialogController.edit_todo(todo, list_idx)
        except TodoPropertyBeyondEditDialog as exc:
            print('Warning: {:s} - showing todo properties'.format(str(exc)), file=stderr)
            cls.dialog_showentryprops(todo)


    @classmethod
    def handler_stat_toggle(cls, stat:Optional[str]) -> bool:
        # Handle signals from menu to change current entry's status.
        # Paramenter stat is None or text string for status (eg 'CONFIRMED').
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en:
            Calendar.set_toggle_status_entry(en, stat)
            cls.view_redraw(en_changes=True)
        return True # don't propagate event


    @classmethod
    def delete_request(cls, *args) -> bool:
        # Callback to implement "delete" from GUI, e.g. backspace key pressed
        en = cls.views[cls._view_idx].get_cursor_entry()
        if en is not None:
            cls.dialog_deleteentry(en)
        return True # don't propagate event


    @classmethod
    def cut_request(cls, *args) -> bool:
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
                cls.view_redraw(en_changes=True)
        return True # don't propagate event


    @classmethod
    def copy_request(cls, *args) -> bool:
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
        return True # don't propagate event


    @classmethod
    def paste_request(cls, *args) -> bool:
        # Handler to implement "paste" from GUI, e.g. paste clicked in menu
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        # First, we try requesting a 'text/calendar' type from the clipboard
        sdat = cb.wait_for_contents(Gdk.Atom.intern('text/calendar', False))
        try:
            ical = iCalendar.from_ical(sdat.get_data())
            en = ical.walk()[0]
            cls.views[cls._view_idx].new_entry_from_example(en)
            cls.view_redraw(en_changes=True)
        except:
            # Fallback: request plain text from clipboard
            txt = cb.wait_for_text()
            if txt: # might be None
                txt = cls._sanitise_pasted_text(txt)
                # Type of entry created depends on View, so call View paste fn
                if txt:
                    cls.views[cls._view_idx].paste_text(txt)
        return True # don't propagate event


    @staticmethod
    def _sanitise_pasted_text(txt:str) -> str:
        # Clean up text from clipboard so it's suitable as an entry summary
        txt = txt.strip()
        txt = txt.replace('\n',' ')
        txt = txt.replace('\t',' ')
        return txt


    @classmethod
    def dialog_deleteentry(cls, en:iEvent) -> None:
        # Dialog to implement "delete" from GUI, e.g. backspace key
        dialog = Gtk.Dialog(title=_('Delete Entry'), parent=cls._window,
            flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CLOSE, Gtk.STOCK_DELETE, Gtk.ResponseType.APPLY))
        if 'RRULE' in en:
            # repeating entry - clarify what is being deleted
            # !! We should really ask if user wants to delete all/single etc.
            l_template = _(u'Delete all repeats:\n“{:s}”?')
        else:
            l_template = _(u'Delete entry:\n“{:s}”?')
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
            cls.view_redraw(en_changes=True)


    @classmethod
    def dialog_showentryprops(cls, entry:Union[iEvent,iTodo]) -> None:
        # Shows dialog with entry details.
        # Used if requested from menu or, e.g., for read-only entries.
        dialog = EntryPropertiesDialog(entry, parent=cls._window)
        response = dialog.run()
        dialog.destroy()


    @classmethod
    def dialog_goto(cls, *args) -> bool:
        # Called to implement "go to" from GUI, e.g. button
        dialog = Gtk.Dialog(title=_('Go To'), parent=cls._window,
            flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CLOSE))
        wdate = WidgetDate(cls.views[cls._view_idx].cursor_date())
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
            cls.cursor_goto_date(dt)
            cls.view_redraw(en_changes=False)
        dialog.destroy()
        return True # don't propagate event


    @staticmethod
    def check_date_fixed(wid:WidgetDate) -> bool:
        # Removes error highlight if date is valid (e.g. not 30th Feb)
        # Would be nice to make this a method of WidgetDate class.
        # Can be used as a callback, e.g. attached to 'changed' signal
        if wid.get_date_or_none() is not None:
            wid.get_style_context().remove_class(GUI.STYLE_ERR)
        return False # propagate event


    @classmethod
    def dialog_about(cls, *args) -> bool:
        # Display the "About Pygenda" dialog
        dialog = Gtk.AboutDialog(parent=cls._window)
        dialog.set_program_name('Pygenda')
        dialog.set_copyright(u'Copyright © 2022,2023 Matthew Lewis')
        dialog.set_license_type(Gtk.License.GPL_3_0_ONLY)
        github_url = 'https://github.com/semiprime/pygenda'
        dialog.set_website(github_url)
        dialog.set_website_label(_('Source code & documentation: ')+github_url)
        logo = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 1, 1)
        dialog.set_logo(logo)
        dialog.set_authors(('Matthew Lewis',))
        dialog.set_version('version {:s}'.format(__version__))
        dialog.set_comments(_(u'A calendar/agenda application written in Python/GTK3. The UI is inspired by the Agenda apps on the Psion Series 3 and Series 5 PDAs.\nWARNING: This is in-development code, released for testing and feedback. There will be bugs; please report them to: pygenda@semiprime.com.'))
        dialog.add_credit_section(_('Thanks for testing &amp; feedback'),('Edward Hasbrouck', 'Neil Sands'))
        dialog.show_all()
        dialog.run()
        dialog.destroy()
        return True # don't propagate event


    @classmethod
    def toggle_fullscreen(cls, *args) -> bool:
        # Callback to toggle fullscreen mode on/off (e.g. from menu)
        cls._is_fullscreen = not cls._is_fullscreen
        if cls._is_fullscreen:
            cls._window.fullscreen()
            cls._menu_elt_fullscreen.set_label('gtk-leave-fullscreen')
            cls._menu_elt_fullscreen.set_image(cls._image_leave_fs)
        else:
            cls._window.unfullscreen()
            cls._menu_elt_fullscreen.set_label('gtk-fullscreen')
            cls._menu_elt_fullscreen.set_image(cls._image_enter_fs)
        return True # don't propagate event


    @classmethod
    def zoom_button(cls, wid:Gtk.Widget, ev:Gdk.EventKey) -> bool:
        # Zoom handler for Zoom soft-button
        cls.zoom(-1 if ev.state&(Gdk.ModifierType.SHIFT_MASK|Gdk.ModifierType.CONTROL_MASK) else +1)
        return True # don't propagate event


    @classmethod
    def zoom(cls, inc:int) -> bool:
        # Callback for zoom-in/out menu items
        # Zoom by inc, so zoom-in if inc==+1; zoom-out if inc==-1
        # Call current view to do the work
        cls.views[cls._view_idx].zoom(inc)
        return True # don't propagate event


    @classmethod
    def todo_titles_default_cats(cls) -> Tuple[list,list]:
        # Return titles and default categories of todo lists
        try:
            todo_idx = cls._VIEWS.index('Todo')
        except ValueError:
            return [], []
        tdv = cls.views[todo_idx]
        return tdv._list_titles, tdv._list_default_cats
