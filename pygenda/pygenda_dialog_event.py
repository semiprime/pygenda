# -*- coding: utf-8 -*-
#
# pygenda_dialog_event.py
# Code for Event dialog (used to create/update events)
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

from datetime import date as dt_date, time as dt_time, datetime as dt_datetime, timedelta
from dateutil import rrule as du_rrule
from dateutil.relativedelta import relativedelta
from icalendar import Event as iEvent, vRecur
from sys import stderr
from typing import Optional, Union, Tuple, List

# for internationalisation/localisation
from locale import gettext as _, getlocale
from calendar import day_name, month_name, monthrange
from num2words import num2words

# pygenda components
from .pygenda_config import Config
from .pygenda_gui import GUI
from .pygenda_widgets import WidgetDate, WidgetTime, WidgetDuration
from .pygenda_calendar import Calendar, RepeatInfo
from .pygenda_entryinfo import EntryInfo, AlarmInfo
from .pygenda_util import datetime_to_date, parse_timedelta


# Exception used to indicate dialog can't display event properties.
# In these cases there is a danger of the user accidentally changing
# the event property. For example, if the dialog can't show monthly
# repeats that happen on two days of the month, (BYMONTHDAY has two
# values) it could try to "approximate" it, by just showing one day;
# however, the user might not notice, and change some other property,
# save the entry, and thus erase half of the repeats (i.e. data loss).
class EventPropertyBeyondEditDialog(Exception):
    pass


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
    revs_repeaton = None
    wid_rep_interval = None # type: Gtk.SpinButton
    wid_rep_forever = None # type: Gtk.CheckButton
    wid_repeaton_year = None # type: Gtk.ComboBox
    wid_repeaton_month = None # type: Gtk.ComboBox
    wid_rep_occs = None # type: Gtk.SpinButton
    wid_rep_enddt = None # type: WidgetDate
    revs_rep_ends = None
    rep_occs_determines_end = True
    _rep_handler_date = 0
    _rep_handler_date_repon = 0
    _rep_handler_time = 0
    _rep_handler_type = 0
    _rep_handler_repon_year = 0
    _rep_handler_repon_month = 0
    _rep_handler_inter = 0
    _rep_handler_occs = 0
    _rep_handler_enddt = 0
    _lab_rep_exceptions = None # type: Gtk.Label
    dur_determines_end = False
    exception_list = [] # type: List[dt_date]

    show_alarm_warning = True
    wid_alarmstack = None # type: Gtk.Stack
    wid_alarmset = None # type: Gtk.Switch
    _revealer_alarmlist = None # type: Gtk.Revealer
    wid_alarmlist = None # type: Gtk.TreeView
    alarmlist_model = None # type: Gtk.ListStore
    _default_alarm_before = None # type: timedelta

    wid_status = None # type: Gtk.ComboBox
    wid_location = None # type: Gtk.Entry

    # Set defaults for config
    Config.set_defaults('new_event',{
        'show_alarm_warning': True,
        'timed_default_alarm_before': '15m',
        'default_alarm_emailaddr': None,
        })

    @classmethod
    def init(cls) -> None:
        # Initialiser for singleton class.
        # Called from GUI init_stage2().

        # Load glade file
        GUI.load_glade_file('dialog_event.glade')

        # Connect signal handlers
        HANDLERS = {
            'timed_toggled': cls._do_timed_toggle,
            'allday_toggled': cls._do_allday_toggle,
            'reptype_changed': cls._reptype_changed,
            'repforever_toggled': cls._do_repeatforever_toggle,
            'exceptions_modify': cls.dialog_repeat_exceptions,
            'alarms_understood': cls.alarms_understood,
            'alarmset_changed': cls._do_alarmset_toggle,
            'alarmlist_focusout': cls._alarmlist_focusloss,
            'alarmlist_keypress': cls._alarmlist_keypress,
            }
        GUI._builder.connect_signals(HANDLERS)

        # Get some references to dialog elements in glade
        cls.dialog = GUI._builder.get_object('dialog_event')
        if (not cls.dialog): # Sanity check
            raise NameError('Dialog Event not found')

        cls.wid_desc = GUI._builder.get_object('entry_dialogevent_desc')
        cls._wid_desc_changed_handler = cls.wid_desc.connect('changed', cls._desc_changed)
        wid_grid = GUI._builder.get_object('dialogevent_grid')
        cls.wid_tabs = GUI._builder.get_object('dialogevent_tabs')

        # Create & add event date widget
        cls.wid_date = WidgetDate()
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
        cls.revs_repeaton = cls._revealers_from_ids('revealer_repeaton_l','revealer_repeaton_opts')

        cls.wid_rep_interval = GUI._builder.get_object('repeat_interval')
        cls.wid_rep_forever = GUI._builder.get_object('repeat_forever')
        cls.wid_repeaton_year = GUI._builder.get_object('combo_repeaton_year')
        cls.wid_repeaton_month = GUI._builder.get_object('combo_repeaton_month')

        cls.wid_rep_occs = GUI._builder.get_object('repeat_occurrences')
        cls.wid_rep_enddt = WidgetDate()
        rbox = GUI._builder.get_object('revealer_repeat_until_e').get_child() # Should be a GtkBox
        rbox.add(cls.wid_rep_enddt)
        rbox.show_all()
        cls.revs_rep_ends = cls._revealers_from_ids('revealer_repeat_until_l', 'revealer_repeat_until_e')

        cls._rep_handler_date = cls.wid_date.connect('changed', cls._repend_changed,0)
        cls._rep_handler_date_repon = cls.wid_date.connect('changed', cls._repon_changed)
        cls._rep_handler_time = cls.wid_time.connect('changed', cls._repend_changed,0)
        cls._rep_handler_type = cls.wid_rep_type.connect('changed', cls._repend_changed,0)
        cls._rep_handler_repon_year = cls.wid_repeaton_year.connect('changed', cls._repend_changed,0)
        cls._rep_handler_repon_month = cls.wid_repeaton_month.connect('changed', cls._repend_changed,0)
        cls._rep_handler_inter = cls.wid_rep_interval.connect('changed', cls._repend_changed,0)
        cls._rep_handler_occs = cls.wid_rep_occs.connect('changed', cls._repend_changed,1)
        cls._rep_handler_enddt = cls.wid_rep_enddt.connect('changed', cls._repend_changed,2)

        # Get label used to display exception dates
        cls._lab_rep_exceptions = GUI._builder.get_object('lab_rep_exceptions')

        # We want default to be signal *blocked* - unblock when dialog active
        cls._block_rep_occend_signals()


    @classmethod
    def _init_alarmfields(cls) -> None:
        # Initialise widgets etc in the Event dialog under the "Alarm" tab.
        # Called on app startup.
        cls.show_alarm_warning = Config.get_bool('new_event','show_alarm_warning')
        cls.wid_alarmstack = GUI._builder.get_object('alarm-stack')
        cls.wid_alarmset = GUI._builder.get_object('alarm-set')
        cls._revealer_alarmlist = GUI._builder.get_object('revealer_alarmlist')

        cls.wid_alarmlist = GUI._builder.get_object('alarm-list')
        cls.alarmlist_model = Gtk.ListStore(object, str, str) # AlarmInfo + cols
        cls.wid_alarmlist.set_model(cls.alarmlist_model)
        cls.wid_alarmlist.append_column(Gtk.TreeViewColumn(_('Time before event'),Gtk.CellRendererText(), text=1))
        cls.wid_alarmlist.append_column(Gtk.TreeViewColumn(_('Action'), Gtk.CellRendererText(), text=2))

        # Read config settings
        td_str = Config.get('new_event','timed_default_alarm_before')
        cls._default_alarm_before = parse_timedelta(td_str)


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
            cls.wid_timed_buttons[i].connect('key-press-event', cls._radiobutton_keypress)


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
    def _do_timed_toggle(cls, wid:Gtk.RadioButton) -> bool:
        # Callback. Called when "timed" radio button changes state.
        # Reveals/hides appropriate sub-obtions.
        ti = cls.wid_timed_buttons[1].get_active()
        cls._do_multireveal(cls.revs_timedur, ti)
        return False # propagate event


    @classmethod
    def _do_allday_toggle(cls, wid:Gtk.RadioButton) -> bool:
        # Callback. Called when "all day" radio button changes state.
        # Reveals/hides appropriate sub-obtions.
        ad = cls.wid_timed_buttons[2].get_active()
        cls._do_multireveal(cls.revs_allday, ad)
        return False # propagate event


    @classmethod
    def _desc_changed(cls, wid:Gtk.Entry) -> bool:
        # Callback. Called when event description is changed by user.
        # Removes error state styling if it is no longer needed.
        cls._is_valid_event(set_style=False) # remove error styles if present
        return False # propagate event


    @classmethod
    def _reptype_changed(cls, wid:Gtk.ComboBox) -> bool:
        # Callback. Called when event repeat type is changed by user.
        # Reveals/hides relevant sub-options.
        # wid should be the repeat-type combobox
        st = wid.get_active()>0
        cls._do_multireveal(cls.revs_repeat, st)
        r_yearly = (wid.get_active_id()=='YEARLY') # Boolean
        r_monthly = (not r_yearly and wid.get_active_id()=='MONTHLY')
        # We assume that repeat-on comboboxes are set up, just make visible
        cls._do_multireveal(cls.revs_repeaton, r_monthly or r_yearly)
        cls.wid_repeaton_year.set_visible(r_yearly)
        cls.wid_repeaton_month.set_visible(r_monthly)
        return False # propagate event


    @classmethod
    def _do_repeatforever_toggle(cls, wid:Gtk.Button) -> bool:
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

        return False # propagate event


    @classmethod
    def _do_alarmset_toggle(cls, wid:Gtk.Widget, state:bool) -> bool:
        # Callback. Called when alarm set state is changed.
        # Reveals/hides alarm list.
        if state and len(cls.alarmlist_model)==0:
            # User just enabled alarms, so if no alarms, create default ones
            cls._add_alarm(AlarmInfo(-cls._default_alarm_before,action='AUDIO'))
            cls._add_alarm(AlarmInfo(-cls._default_alarm_before,action='DISPLAY',desc=cls.wid_desc.get_text()))
        cls._revealer_alarmlist.set_reveal_child(state)
        return False # must propagate event for active CSS selector to apply


    @classmethod
    def _add_alarm(cls, a_info:AlarmInfo) -> None:
        # Adds an alarm to alarm list
        itr = cls.alarmlist_model.append(None)
        cls._set_alarm_row(itr, a_info)


    @classmethod
    def _set_alarm_row(cls, itr:Gtk.TreeIter, a_info:AlarmInfo) -> None:
        # Sets alarm in alarm list for row given by itr
        act = a_info.action.capitalize()
        desc = _(act)
        if act=='Email':
            desc += ' (' + a_info.attendee + ')'
        elif act=='Display' and a_info.desc is not None:
            desc += ' '
            desc += _(u'“{:s}”').format(a_info.desc)
        cls.alarmlist_model.set(itr, 0,a_info, 1,str(-a_info.tdelta), 2,desc)


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
        cls.wid_date.handler_block(cls._rep_handler_date_repon)
        cls.wid_time.handler_block(cls._rep_handler_time)
        cls.wid_rep_type.handler_block(cls._rep_handler_type)
        cls.wid_repeaton_year.handler_block(cls._rep_handler_repon_year)
        cls.wid_repeaton_month.handler_block(cls._rep_handler_repon_month)
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
        cls.wid_date.handler_unblock(cls._rep_handler_date_repon)
        cls.wid_time.handler_unblock(cls._rep_handler_time)
        cls.wid_rep_type.handler_unblock(cls._rep_handler_type)
        cls.wid_repeaton_year.handler_unblock(cls._rep_handler_repon_year)
        cls.wid_repeaton_month.handler_unblock(cls._rep_handler_repon_month)
        cls.wid_rep_interval.handler_unblock(cls._rep_handler_inter)
        cls.wid_rep_occs.handler_unblock(cls._rep_handler_occs)
        cls.wid_rep_enddt.handler_unblock(cls._rep_handler_enddt)


    @classmethod
    def _tmdur_changed(cls, wid:Gtk.Widget, el:int) -> bool:
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
        cls._is_valid_event(set_style=False) # remove error styles if present
        return False # propagate event


    @classmethod
    def _repend_changed(cls, wid:Gtk.Widget, el:int) -> bool:
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
        cls._is_valid_event(set_style=False) # remove error styles if present
        return False # propagate event


    @classmethod
    def _set_occs_min(cls, mn:int) -> None:
        # quick method to set minimum of the occurrences spinbutton
        mx = cls.wid_rep_occs.get_range().max
        cls.wid_rep_occs.set_range(mn,mx)


    # Maps used to calculate repeats using dateutil.rrule class
    MAP_RTYPE_TO_RRULE = {
        'YEARLY': du_rrule.YEARLY,
        'MONTHLY': du_rrule.MONTHLY,
        'WEEKLY': du_rrule.WEEKLY,
        'DAILY': du_rrule.DAILY,
        'HOURLY': du_rrule.HOURLY,
        'MINUTELY': du_rrule.MINUTELY,
        'SECONDLY': du_rrule.SECONDLY
        }

    MAP_RDAY_TO_RRULEDAY = (
        du_rrule.MO,
        du_rrule.TU,
        du_rrule.WE,
        du_rrule.TH,
        du_rrule.FR,
        du_rrule.SA,
        du_rrule.SU
        )

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
            cls._sync_rep_ends_from_occs(rtype)
        else:
            cls._sync_occs_from_rep_ends(rtype)


    @classmethod
    def _sync_rep_ends_from_occs(cls, rtype:str) -> None:
        # Function to recalculate & update repeat End Date
        # from Occurences count.
        stdt = cls.get_date_start()
        if stdt is not None:
            span = (cls.get_repeat_occurrences()-1) * cls.get_repeat_interval()
            if rtype=='YEARLY':
                # Special case for leap day & repeat on e.g. 2nd Monday of May
                if (stdt.day==29 and stdt.month==2) or cls.wid_repeaton_year.get_active()>0:
                    cls._sync_rep_end_from_occ_rrule(rtype)
                    return
                delta = relativedelta(years=span) # type:Union[relativedelta,timedelta]
            elif rtype=='MONTHLY':
                if stdt.day>=29 or cls.wid_repeaton_month.get_active()>0:
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
            else:
                # !! Don't know how to sync
                print('Warning: Sync for {} not implemented'.format(rtype), file=stderr)
                return
            edt = stdt+delta
            cls.wid_rep_enddt.set_date(edt)


    @classmethod
    def _sync_occs_from_rep_ends(cls, rtype:str) -> None:
        # Function to recalculate & update repeat Occurences count
        # from End Date.
        # Uses dateutil:rrule to do calculation.
        rend = cls.wid_rep_enddt.get_date_or_none()
        if rend is None:
            # End date is invalid (e.g. 31st Feb), exit
            return
        rr = cls._get_rrule_for_sync(rtype, rend=rend)
        if rr is not None:
            c = rr.count()
            if c>=0:
                cls._set_occs_min(0 if c==0 else 1) # possibly allow "0"
                cls.wid_rep_occs.set_value(c)


    @classmethod
    def _sync_rep_end_from_occ_rrule(cls, rtype:str) -> None:
        # Function to synchronise End Date repeat field from Occurrences in
        # complex situations, e.g. leapday (29 Feb) or monthly late in month.
        # Use rrule class for these.
        occs = cls.get_repeat_occurrences()
        rr = cls._get_rrule_for_sync(rtype, occs=occs)
        if rr is not None:
            edt = list(rr)[-1]
            cls.wid_rep_enddt.set_date(edt)


    @classmethod
    def _get_rrule_for_sync(cls, rtype:str, occs:int=None, rend:dt_date=None) -> Optional[du_rrule.rrule]:
        # Return an rrule object suitable for calculating end date/no of occs.
        # Only one of occs/rend must be None. Otherwise get infinite repeats.
        dtst = cls.get_date_start() # Without time - time breaks occs calc
        if dtst is None:
            # Start date is invalid (e.g. 31st Feb), exit
            return None
        try:
            fr = cls.MAP_RTYPE_TO_RRULE[rtype]
        except KeyError:
            # !! Don't know how to sync
            print('Warning: Sync for {} not implemented'.format(rtype), file=stderr)
            return None
        if rtype=='YEARLY':
            bymt,bywkdy = cls._get_yearly_bymonth_byweekday()
            bymtdy = None
        elif rtype=='MONTHLY':
            bymtdy,bywkdy = cls._get_monthly_bymonthday_byweekday()
            bymt = None
        else:
            bymt = None
            bymtdy = None
            bywkdy = None
        interv = cls.get_repeat_interval()
        rr = du_rrule.rrule(fr, dtstart=dtst, interval=interv, count=occs, until=rend, bymonth=bymt, bymonthday=bymtdy, byweekday=bywkdy)
        return rr


    @classmethod
    def _get_yearly_bymonth_byweekday(cls) -> Tuple:
        # Return bymonth & byweekday for yearly repeats to pass to rrule
        repon = cls.wid_repeaton_year.get_active_id()
        dtst = cls.get_date_start()
        bymt = None
        bywkdy = None
        if dtst is not None:
            bymt = dtst.month
            if repon=='WEEKDAY':
                dayocc = cls._weekday_count_in_month(dtst)
                bywkdy = cls.MAP_RDAY_TO_RRULEDAY[dtst.weekday()](dayocc)
            elif repon=='WEEKDAY_FROMEND':
                dayocc = cls._weekday_fromend_in_month(dtst)
                bywkdy = cls.MAP_RDAY_TO_RRULEDAY[dtst.weekday()](dayocc)
        return bymt,bywkdy


    @classmethod
    def _get_monthly_bymonthday_byweekday(cls) -> Tuple:
        # Return bymonthday & byweekday for monthday repeats to pass to rrule
        repon = cls.wid_repeaton_month.get_active_id()
        dtst = cls.get_date_start()
        bymtdy = None
        bywkdy = None
        if dtst is not None:
            if repon=='FROMEND':
                bymtdy = dtst.day - monthrange(dtst.year,dtst.month)[1] - 1
            elif repon=='WEEKDAY':
                dayocc = cls._weekday_count_in_month(dtst)
                bywkdy = cls.MAP_RDAY_TO_RRULEDAY[dtst.weekday()](dayocc)
            elif repon=='WEEKDAY_FROMEND':
                dayocc = cls._weekday_fromend_in_month(dtst)
                bywkdy = cls.MAP_RDAY_TO_RRULEDAY[dtst.weekday()](dayocc)
        return bymtdy,bywkdy


    @staticmethod
    def _weekday_count_in_month(dt:dt_date) -> int:
        # Convenience function, returns "rrule-style" count of weekday in month.
        # E.g. if dt is 3rd Monday in month, return 3.
        return (dt.day+6)//7


    @staticmethod
    def _weekday_fromend_in_month(dt:dt_date) -> int:
        # Convenience function, returns "from end" count of weekday in month.
        # E.g. if dt is 2nd to last Monday in month, return -2.
        return (dt.day-monthrange(dt.year,dt.month)[1]-1)//7


    @staticmethod
    def _weekday_abbr(dt:dt_date) -> str:
        # Convenience function, returns rrule weekday abbreviation
        return RepeatInfo.DAY_ABBR[dt.weekday()]


    @classmethod
    def _repon_changed(cls, wid:Gtk.Widget) -> bool:
        # Handler for signals from any widget that might result in the
        # text of the repeat on field to change. Rewrites text.
        cls._block_rep_occend_signals()
        cls._repon_wid_datesync_yearly()
        cls._repon_wid_datesync_monthly()
        cls._unblock_rep_occend_signals()
        return False # propagate event


    @classmethod
    def _repon_wid_datesync_yearly(cls) -> None:
        # Rewrites text of repeat-on yearly widget to reflect start date.
        # Note: Should be called with signals blocked, o/w get side-effects.
        dt = cls.wid_date.get_date_or_none()
        if dt is None:
            return # invalid date (eg 31st Feb)
        active = cls.wid_repeaton_year.get_active() # save current value
        fromend = monthrange(dt.year,dt.month)[1] - dt.day
        daynm = day_name[dt.weekday()]
        monthnm = month_name[dt.month]
        lang = getlocale()[0]
        cls.wid_repeaton_year.remove_all()
        if dt.day==1:
            cls.wid_repeaton_year.append('STD',_('1st {month:s}').format(month=monthnm))
        else:
            cls.wid_repeaton_year.append('STD',_('{ord:s} {month:s}').format(ord=num2words(dt.day,to='ordinal_num',lang=lang), card=dt.day, month=monthnm))
        m_str = 'April' if dt.month==4 else 'August' if dt.month==8 else 'October' if dt.month==10 else '{month:s}'
        cls.wid_repeaton_year.append('WEEKDAY',_('{ord:s} {day:s} of '+m_str).format(ord=num2words((dt.day+6)//7,to='ordinal_num',lang=lang),day=daynm,month=monthnm))
        if fromend < 7:
            cls.wid_repeaton_year.append('WEEKDAY_FROMEND',_('Last {day:s} of '+m_str).format(day=daynm,month=monthnm))
        else:
            cls.wid_repeaton_year.append('WEEKDAY_FROMEND',_('{ord:s} to last {day:s} of '+m_str).format(ord=num2words(fromend//7+1,to='ordinal_num',lang=lang),day=daynm,month=monthnm))
        cls.wid_repeaton_year.set_active(active) # restore saved value


    @classmethod
    def _repon_wid_datesync_monthly(cls) -> None:
        # Rewrites text of repeat-on monthly widget to reflect start date.
        # Note: Should be called with signals blocked, o/w get side-effects.
        dt = cls.wid_date.get_date_or_none()
        if dt is None:
            return # invalid date (eg 31st Feb)
        active = cls.wid_repeaton_month.get_active() # save current value
        fromend = monthrange(dt.year,dt.month)[1] - dt.day
        daynm = day_name[dt.weekday()]
        lang = getlocale()[0]
        cls.wid_repeaton_month.remove_all()
        if dt.day==1:
            cls.wid_repeaton_month.append('STD',_('1st day of month'))
        else:
            cls.wid_repeaton_month.append('STD',_('{ord:s} day of month').format(ord=num2words(dt.day,to='ordinal_num',lang=lang),card=dt.day))
        if fromend == 0:
            cls.wid_repeaton_month.append('FROMEND',_('Last day of month'))
        else:
            cls.wid_repeaton_month.append('FROMEND',_('{:s} to last day of month').format(num2words(fromend+1,to='ordinal_num',lang=lang)))
        cls.wid_repeaton_month.append('WEEKDAY',_('{ord:s} {day:s} of month').format(ord=num2words((dt.day+6)//7,to='ordinal_num',lang=lang),day=daynm))
        if fromend < 7:
            cls.wid_repeaton_month.append('WEEKDAY_FROMEND',_('Last {day:s} of month').format(day=daynm))
        else:
            cls.wid_repeaton_month.append('WEEKDAY_FROMEND',_('{ord:s} to last {day:s} of month').format(ord=num2words(fromend//7+1,to='ordinal_num',lang=lang),day=daynm))
        cls.wid_repeaton_month.set_active(active) # restore saved value


    @classmethod
    def new_event(cls, txt:str=None, date:dt_date=None) -> None:
        # Called to implement "new event" from GUI, e.g. menu
        cls.dialog.set_title(_('New Event'))
        response,ei = cls._do_event_dialog(txt=txt, date=date)
        if response==Gtk.ResponseType.OK and ei.desc:
            ev = Calendar.new_entry(ei)
            GUI.cursor_goto_event(ev)
            GUI.view_redraw(en_changes=True)


    @classmethod
    def edit_event(cls, event:iEvent, subtab:int=None) -> None:
        # Called to implement "edit event" from GUI
        cls.dialog.set_title(_('Edit Event'))
        response,ei = cls._do_event_dialog(event=event, subtab=subtab)
        if response==Gtk.ResponseType.OK:
            if ei.desc:
                Calendar.update_entry(event, ei)
                GUI.cursor_goto_event(event)
                GUI.view_redraw(en_changes=True)
            else: # Description text has been deleted in dialog
                # This should now be impossible since the removal of
                # _empty_desc_allowed flag. Leaving in as a "just in case".
                print('Warning: Dialog with empty description accepted as valid. Fall back to offering delete option.', file=stderr)
                GUI.dialog_deleteentry(event)


    @classmethod
    def _do_event_dialog(cls, event:iEvent=None, txt:str=None, date:dt_date=None, subtab:int=None) -> Tuple[int,EntryInfo]:
        # Do the core work displaying event dialog and extracting result.
        # Called from both new_event() and edit_event().
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
        discard_on_empty = (event is None) # True if creating a new event
        try:
            while True:
                response = cls.dialog.run()
                if response!=Gtk.ResponseType.OK:
                    break
                if discard_on_empty and cls._fields_are_defaults():
                    # New event & nothing entered, so discard as a null entry
                    response = Gtk.ResponseType.CANCEL
                    break
                if cls._is_valid_event(set_style=True):
                    break
                discard_on_empty = False # only allow discard first time
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

        # First, set to default values (possibly overwritten later)
        cls._set_fields_to_defaults(date)

        # Two cases: new event or edit existing event
        if event is None:
            # Initialise decscription field
            cls._seed_text_only(txt)
        else: # existing entry - take values
            cls._seed_from_event(event)
        cls._repon_wid_datesync_yearly() # Done at end, so date used is correct
        cls._repon_wid_datesync_monthly()

        cls._seed_rep_exception_list(event) # If event==None this clears exlist


    @classmethod
    def _set_fields_to_defaults(cls, date:Optional[dt_date]) -> None:
        # Set dialog fields to default values.
        # 'date' is an optional argument, usually the cursor date.
        # If you change this, also change _fields_are_defaults()
        # and maybe _is_valid_event() & _reset_err_style() below.

        # Desc. This is not a user interaction, so block signal
        cls.wid_desc.handler_block(cls._wid_desc_changed_handler)
        cls.wid_desc.set_text('')
        cls.wid_desc.handler_unblock(cls._wid_desc_changed_handler) # unblock
        cls.wid_date.set_date(dt_date.today() if date is None else date)

        # Time tab
        cls.wid_timed_buttons[0].set_active(True) # Sends signal to hide fields
        tm9 = dt_time(hour=9)
        cls.wid_time.set_time(tm9)
        cls.wid_dur.set_duration(timedelta(0))
        cls.wid_endtime.set_time(tm9)
        cls.dur_determines_end = True
        cls.wid_allday_count.set_value(1)

        # Repeats tab
        cls.wid_rep_type.set_active(0) # Sends signal to hide fields
        cls.wid_repeaton_year.set_active(0)
        cls.wid_repeaton_month.set_active(0)
        cls.wid_rep_interval.set_value(1)
        cls.wid_rep_forever.set_active(True)
        cls.rep_occs_determines_end = True
        cls.wid_rep_occs.set_value(1)
        cls._set_occs_min(1)
        # No need to set wid_rep_enddt because it will be synced when revealed

        # Alarm tab
        if cls.show_alarm_warning:
            cls.wid_alarmstack.set_visible_child_name('warning')
        cls.wid_alarmset.set_active(False)
        cls.alarmlist_model.clear()

        # Details tab
        cls.wid_status.set_active(0)
        cls.wid_location.set_text('')


    @classmethod
    def _seed_text_only(cls, txt:Optional[str]) -> None:
        # Called when dialog is opened for a new event
        # Text possibly typed, or pasted from clipboard
        if txt is not None:
            # Not a user interaction, so block signal
            cls.wid_desc.handler_block(cls._wid_desc_changed_handler)
            cls.wid_desc.set_text(txt)
            cls.wid_desc.set_position(len(txt))
            cls.wid_desc.handler_unblock(cls._wid_desc_changed_handler)
        cls.wid_desc.grab_focus_without_selecting()


    @classmethod
    def _seed_from_event(cls, event:iEvent) -> None:
        # Called when dialog is opened for an existing event.
        # Assume defaults already set before this is called.

        if 'SUMMARY' in event:
            cls.wid_desc.set_text(event['SUMMARY'])
        cls.wid_desc.grab_focus() # also selects text in field

        # Date & Time tab
        cls._seed_date_timetab(event)

        # Repeats tab
        if 'RRULE' in event:
            cls._seed_repeatstab(event['RRULE'])

        # Alarm tab
        valarms = event.walk('VALARM')
        if valarms:
            cls._seed_alarmstab(valarms)

        # Details tab
        if 'STATUS' in event and event['STATUS'] in Calendar.STATUS_LIST_EVENT:
            cls.wid_status.set_active_id(event['STATUS'])
        if 'LOCATION' in event:
            cls.wid_location.set_text(event['LOCATION'])

        cls._sync_rep_occs_end()


    @classmethod
    def _seed_date_timetab(cls, event:iEvent) -> None:
        # Called when dialog is opened for an existing event.
        # Seeds the date field and the time tab (inc. all-day events).
        dt = event['DTSTART'].dt
        dttm = None
        tm = None
        dur = None
        end_dttm = None
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
            if 'DTEND' in event and isinstance(event['DTEND'].dt, dt_date):
                end_dttm = event['DTEND'].dt
        else: # dt is neither a date nor a datetime
            raise TypeError('Event date of unexpected type')
        cls.wid_date.set_date(dt)

        # Setting radio buttons etc. for Untimed/Timed/Allday.
        # This also reveals appropriate UI elements via signal connections.
        if tm is not None:
            # Timed entry
            cls.wid_timed_buttons[1].set_active(True)
            cls.wid_time.set_time(tm)
        elif end_dttm is not None:
            # All day entry
            cls.wid_timed_buttons[2].set_active(True)
            d = end_dttm - dt
            cls.wid_allday_count.set_value(d.days)

        if dur is not None:
            end_dttm = dttm + dur
            cls.dur_determines_end = True
        elif end_dttm is not None and dttm is not None:
            dur = end_dttm - dttm
            cls.dur_determines_end = False

        if dur is None:
            if tm is not None:
                # No duration or endtime in event.
                # Set dialog endtime equal to starttime.
                cls.wid_endtime.set_time(tm)
        else:
            # One of duration or endtime in event.
            # Set both fields in dialog. Values have been made to match above.
            cls.wid_dur.set_duration(dur)
            cls.wid_endtime.set_time(end_dttm.time())


    @classmethod
    def _seed_repeatstab(cls, rrule:vRecur) -> None:
        # Called when dialog is opened for an existing event.
        # Assumes that start date has already been set from event.
        rrfreq = rrule['FREQ'][0]
        if rrfreq in ('YEARLY','MONTHLY','WEEKLY','DAILY'):
            cls.wid_rep_type.set_active_id(rrfreq)
        else:
            raise EventPropertyBeyondEditDialog('Editing repeat freq \'{}\' not (yet) supported'.format(rrfreq))

        if rrfreq == 'YEARLY':
            cls._seed_reptab_yearly(rrule)
        elif rrfreq == 'MONTHLY':
            cls._seed_reptab_monthly(rrule)

        if rrfreq == 'WEEKLY' and 'BYDAY' in rrule:
            rr_byday = rrule['BYDAY']
            if isinstance(rr_byday, list) and len(rr_byday)>1:
                raise EventPropertyBeyondEditDialog('Editing WEEKLY repeat with multiple \'BYDAY\' not (yet) supported')

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
            dt_st = cls.get_date_start() # Won't be none, because seeded
            cls.wid_rep_enddt.set_date(u if u>dt_st else dt_st)
            cls.rep_occs_determines_end = False


    @classmethod
    def _seed_reptab_yearly(cls, rrule:vRecur) -> None:
        # Called when dialog is opened for a yearly repeating event
        if 'BYYEARDAY' in rrule:
            raise EventPropertyBeyondEditDialog('BYYEARDAY in YEARLY repeat not supported')
        if 'BYWEEKNO' in rrule:
            raise EventPropertyBeyondEditDialog('BYWEEKNO in YEARLY repeat not supported')

        has_bymonth = ('BYMONTH' in rrule)
        has_byday = ('BYDAY' in rrule)
        if has_bymonth and not has_byday:
            raise EventPropertyBeyondEditDialog('BYMONTH in YEARLY repeat only supported with BYDAY')
        if has_byday and not has_bymonth:
            raise EventPropertyBeyondEditDialog('BYDAY in YEARLY repeat only supported with BYMONTH')

        if has_byday: # will also have bymonth
            byday = rrule['BYDAY']
            if len(byday) > 1:
                raise EventPropertyBeyondEditDialog('Editing YEARLY repeat with multiple BYDAY not supported')
            byday = byday[0]
            bymonth = rrule['BYMONTH']
            if len(bymonth) > 1:
                raise EventPropertyBeyondEditDialog('Editing YEARLY repeat with multiple BYMONTH not supported')
            bymonth = bymonth[0]
            dt_st = cls.get_date_start() # Won't be none, because seeded
            if int(bymonth) != dt_st.month:
                raise EventPropertyBeyondEditDialog('YEARLY repeat with mismatching BYMONTH')
            byday_day = byday[-2:]
            if cls._weekday_abbr(dt_st) != byday_day:
                raise EventPropertyBeyondEditDialog('Repeat BYDAY does not match start date')
            try:
                byday_int = int(byday[0:-2])
            except ValueError:
                raise EventPropertyBeyondEditDialog('Non-integer value for BYDAY')
            if byday_int == cls._weekday_count_in_month(dt_st):
                cls.wid_repeaton_year.set_active_id('WEEKDAY')
            elif byday_int == cls._weekday_fromend_in_month(dt_st):
                cls.wid_repeaton_year.set_active_id('WEEKDAY_FROMEND')
            else:
                raise EventPropertyBeyondEditDialog('Repeat BYDAY does not match start date')


    @classmethod
    def _seed_reptab_monthly(cls, rrule:vRecur) -> None:
        # Called when dialog is opened for a monthly repeating event
        has_byday = 'BYDAY' in rrule
        has_bymonthday = 'BYMONTHDAY' in rrule
        if has_byday and has_bymonthday:
            raise EventPropertyBeyondEditDialog('MONTHLY repeat has both BYDAY and BYMONTHDAY')
        if has_byday:
            byday = rrule['BYDAY']
            if len(byday) > 1:
                raise EventPropertyBeyondEditDialog('Editing MONTHLY repeat with multiple \'BYDAY\' not (yet) supported')
            byday = byday[0]
            byday_day = byday[-2:]
            dt_st = cls.get_date_start() # Won't be none, because seeded
            if cls._weekday_abbr(dt_st) != byday_day:
                raise EventPropertyBeyondEditDialog('Repeat BYDAY does not match start date')
            try:
                byday_int = int(byday[0:-2])
            except ValueError:
                raise EventPropertyBeyondEditDialog('Non-integer value for BYDAY')
            if byday_int == cls._weekday_count_in_month(dt_st):
                cls.wid_repeaton_month.set_active_id('WEEKDAY')
            elif byday_int == cls._weekday_fromend_in_month(dt_st):
                cls.wid_repeaton_month.set_active_id('WEEKDAY_FROMEND')
            else:
                raise EventPropertyBeyondEditDialog('Repeat BYDAY does not match start date')
        elif has_bymonthday:
            bymday = rrule['BYMONTHDAY']
            if len(bymday)!=1:
                raise EventPropertyBeyondEditDialog('Editing MONTHLY repeat with multiple \'BYMONTHDAY\' not (yet) supported')
            try:
                bymday = int(bymday[0])
            except ValueError:
                raise EventPropertyBeyondEditDialog('Non-integer value for BYMONTHDAY')
            dt_st = cls.get_date_start() # Won't be none, because seeded
            if bymday>=0:
                if dt_st.day != bymday:
                    raise EventPropertyBeyondEditDialog('Repeat BYMONTHDAY does not match start date')
                # No need to set repeaton value - default works
            else: # bymday < 0
                dt_st_fromend = dt_st.day - monthrange(dt_st.year,dt_st.month)[1] - 1
                if dt_st_fromend != bymday:
                    raise EventPropertyBeyondEditDialog('Repeat BYMONTHDAY does not match start date')
                cls.wid_repeaton_month.set_active_id('FROMEND')


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
    def _seed_alarmstab(cls, valarms:list) -> None:
        # Initialise Alarms tab.
        # Called from _seed_from_event(). Assumes list cleared.
        for valarm in valarms:
            if 'TRIGGER' in valarm and 'ACTION' in valarm:
                pretime = valarm['TRIGGER'].dt
                act = str(valarm['ACTION'])
                desc = valarm['DESCRIPTION'] if 'DESCRIPTION' in valarm else None
                summ = valarm['SUMMARY'] if 'SUMMARY' in valarm else None
                attee = valarm['ATTENDEE'] if 'ATTENDEE' in valarm else None
                if isinstance(attee, list):
                    raise EventPropertyBeyondEditDialog('Can\'t edit alarm with >1 email addresses')
                a_info = AlarmInfo(pretime, action=act, desc=desc, summary=summ, attendee=attee)
                cls._add_alarm(a_info)
        if len(cls.alarmlist_model):
            cls.wid_alarmset.set_active(True)


    @classmethod
    def _fields_are_defaults(cls) -> bool:
        # Return True if all fields are defaults, False if any non-default
        if cls.wid_desc.get_text():
            return False
        if cls.get_date_start() is None: # Date has been edited & is invalid
            return False
        if not cls.wid_timed_buttons[0].get_active():
            return False
        if cls.wid_rep_type.get_active() != 0:
            return False
        if cls.show_alarm_warning and cls.wid_alarmstack.get_visible_child_name() != 'warning':
            return False
        if cls.wid_alarmset.get_active():
            return False
        if cls.wid_location.get_text():
            return False
        if cls.wid_status.get_active() != 0:
            return False
        return True


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

        # Repeat information
        cls._fillin_repeatinfo(ei)

        # Alarm info
        if cls.wid_alarmset.get_active():
            for al in cls.alarmlist_model:
                ei.add_alarm(al[0])

        return ei


    @classmethod
    def _fillin_repeatinfo(cls, ei:EntryInfo) -> None:
        # Add repeat info from dialog to ei
        reptype = cls.wid_rep_type.get_active_id()
        if reptype is not None:
            inter = cls.get_repeat_interval()
            # Repeat type details, e.g. monthly, 2nd Monday of month
            byday = None
            bymonth = None
            bymonthday = None # type: Optional[str]
            if reptype=='YEARLY':
                repon = cls.wid_repeaton_year.get_active_id()
                dt = cls.get_date_start()
                if dt is not None:
                    if repon=='WEEKDAY':
                        bymonth = str(dt.month)
                        dayocc = cls._weekday_count_in_month(dt)
                        dayabbr = cls._weekday_abbr(dt)
                        byday = str(dayocc)+dayabbr # e.g. '2SU' - 2nd Sunday
                    elif repon=='WEEKDAY_FROMEND':
                        bymonth = str(dt.month)
                        dayocc = cls._weekday_fromend_in_month(dt)
                        dayabbr = cls._weekday_abbr(dt)
                        byday = str(dayocc)+dayabbr # e.g. '-2MO', 2nd last Mon
            elif reptype=='MONTHLY':
                repon = cls.wid_repeaton_month.get_active_id()
                dt = cls.get_date_start()
                if dt is not None:
                    if repon=='FROMEND':
                        bymonthday = dt.day - monthrange(dt.year,dt.month)[1] - 1 # type: ignore
                        bymonthday = str(bymonthday)
                    elif repon=='WEEKDAY':
                        dayocc = cls._weekday_count_in_month(dt)
                        dayabbr = cls._weekday_abbr(dt)
                        byday = str(dayocc)+dayabbr # e.g. '2SU' - 2nd Sunday
                    elif repon=='WEEKDAY_FROMEND':
                        dayocc = cls._weekday_fromend_in_month(dt)
                        dayabbr = cls._weekday_abbr(dt)
                        byday = str(dayocc)+dayabbr # e.g. '-2MO', 2nd last Mon
            # If not "repeat forever", when repeats stop
            count = None
            until = None
            if not cls.wid_rep_forever.get_active():
                if cls.rep_occs_determines_end:
                    count = cls.get_repeat_occurrences()
                else:
                    until = cls.wid_rep_enddt.get_date_or_none()
            ei.set_repeat_info(reptype, interval=inter, count=count, until=until, byday=byday, bymonth=bymonth, bymonthday=bymonthday, except_list=cls._get_exceptions_list_for_type())


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
        # Note: If you change this, also update _reset_err_style() below.

        ret = True
        # Check description is good (optional)
        ctx = cls.wid_desc.get_style_context()
        if not cls.wid_desc.get_text(): # is empty string
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
    def dialog_repeat_exceptions(cls, *args) -> bool:
        # Callback for +/- button to open sub-dialog for "repeat exceptions"
        edc = ExceptionsDialogController(cls.exception_list, parent=cls.dialog)
        result = edc.run()
        if result==Gtk.ResponseType.OK:
            dates = sorted(edc.get_dates())
            cls.exception_list = dates
            cls._set_label_rep_list()
        edc.destroy()
        return False # propagate event


    @classmethod
    def alarms_understood(cls, *args) -> bool:
        # Handler for Alarms Understood button - show content
        cls.wid_alarmstack.set_visible_child_name('content')
        return False # propagate event


    @classmethod
    def _alarmlist_keypress(cls, wid:Gtk.Widget, ev:Gdk.EventKey) -> bool:
        # Handler for key-press/repeat when alarmlist is focused
        if ev.keyval in (Gdk.KEY_BackSpace, Gdk.KEY_Delete):
            store,row = wid.get_selection().get_selected()
            if store and row:
                store.remove(row)
            return True # Event handled; don't propagate
        elif ev.keyval == Gdk.KEY_Up:
            # If cursor at top of list, need to handle navigation
            sel = wid.get_cursor()[0]
            if sel is not None:
                rows = sel.get_indices()
            if sel is None or (len(rows)>0 and rows[0]==0):
                cls.wid_alarmset.grab_focus()
                return True # Don't propagate
        # !! We should handle other navigation too (KEY_Down). However,
        # !! UI is still in a state of flux, so leaving that out for now.
        elif ev.keyval in GUI.SPINBUTTON_INC_KEY:
            cls._alarmlist_add_to_current_row(timedelta(minutes=1))
            return True # Don't propagate event
        elif ev.keyval in GUI.SPINBUTTON_DEC_KEY:
            cls._alarmlist_add_to_current_row(timedelta(minutes=-1))
            return True # Don't propagate event
        elif ev.keyval in (Gdk.KEY_a, Gdk.KEY_d, Gdk.KEY_e):
            # Change selected alarm to Audio/Display/Email
            store,row = wid.get_selection().get_selected()
            if store and row:
                a_info = cls.alarmlist_model.get_value(row,0)
                a_info.desc = None
                a_info.summary = None
                a_info.attendee = None
                if ev.keyval==Gdk.KEY_a:
                    a_info.action = 'AUDIO'
                elif ev.keyval==Gdk.KEY_d:
                    a_info.action = 'DISPLAY'
                    a_info.desc = cls.wid_desc.get_text()
                elif ev.keyval==Gdk.KEY_e:
                    a_info.action = 'EMAIL'
                    a_info.attendee = Config.get('new_event','default_alarm_emailaddr')
                    a_info.summary = cls.wid_desc.get_text() # email subject
                    a_info.desc = a_info.summary # email body
                    loc = cls.wid_location.get_text()
                    if loc:
                        a_info.desc += '\n' + loc
                    if not a_info.attendee:
                        # If no default address, for now can't set email alarms
                        print('Error: No email address available', file=stderr)
                        return True
                cls._set_alarm_row(row, a_info)
            return True # Don't propagate event
        elif ev.keyval==Gdk.KEY_n:
            # Add new alarm to list, Audio since it's the most basic type
            cls._add_alarm(AlarmInfo(-cls._default_alarm_before,action='AUDIO'))
            wid.set_cursor(len(cls.alarmlist_model)-1) # Move cursor to new row
            return True # Don't propagate event
        elif ev.keyval==Gdk.KEY_Return:
            # Manually trigger default event on dialog box
            dlg = wid.get_toplevel()
            if dlg:
                dlg.response(Gtk.ResponseType.OK)
            return True # Don't propagate event

        return False # Propagate event


    @classmethod
    def _alarmlist_add_to_current_row(cls, d:timedelta) -> None:
        # Add timedelta d to time in currently selected alarmlist row
        store,row = cls.wid_alarmlist.get_selection().get_selected()
        if store and row:
            a_info = cls.alarmlist_model.get_value(row, 0)
            a_info.tdelta = min(a_info.tdelta+d, timedelta()) # don't go above 0
            cls._set_alarm_row(row, a_info)


    @classmethod
    def _alarmlist_focusloss(cls, wid:Gtk.Widget, ev:Gdk.EventKey) -> bool:
        # Handler for alarmlist losing focus.
        # Removes highlight/selection.
        # !! Maybe I'm overlooking something obvious, but I can't find
        # !! a simple way to remove the highlight from a TreeView.
        # !! I tried set_cursor() with various aguments, as well as
        # !! row_activated(), but nothing worked.
        # !! Hence this function works by temporarily changing the view's
        # !! model to an empty one and then back to the proper model.
        wid.set_model(Gtk.ListStore())
        wid.set_model(cls.alarmlist_model)
        return False


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
        self.wdate = WidgetDate()
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
