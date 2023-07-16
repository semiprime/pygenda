# -*- coding: utf-8 -*-
#
# pygenda_dialog_entryprops.py
# Code for dialog to show entry properties
#
# Copyright (C) 2023 Matthew Lewis
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
from gi.repository import Gtk
from gi.repository.Pango import WrapMode as PWrapMode

from datetime import datetime as dt_datetime, timedelta
from icalendar import Event as iEvent, Todo as iTodo, vDDDTypes
from locale import gettext as _
from typing import Union

# pygenda components
from .pygenda_gui import GUI
from .pygenda_calendar import Calendar


class EntryPropertiesDialog:
    # Dialog to display properties of 'entry' (an Event or Todo item)

    # Constants
    ENTRY_TYPES = ('Event','Todo','Journal')
    RRULE_RPTPROPLIST = {
        'BYMONTH': 'By month:',
        'BYWEEKNO': 'By week number:',
        'BYYEARDAY': 'By year day:',
        'BYMONTHDAY': 'By month day:',
        'BYDAY': 'By day:',
        'BYHOUR': 'By hour:',
        'BYMINUTE': 'By minute:',
        'BYSECOND': 'By second:',
        'BYSETPOS': 'By set position:',
        'WKST': 'Week starts:',
        'UNTIL': 'Until:',
        'COUNT': 'Count:'
        }
    STATUS_MAP = {
        'IN-PROCESS': 'In progress',
        'NEEDS-ACTION': 'Action required'
        }


    def __init__(self, entry:Union[iEvent,iTodo], parent:Gtk.Window=None):
        self.entry = entry
        self.dialog = Gtk.Dialog(title=_('Entry properties'), parent=parent,
            flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        self.dialog.set_resizable(False)
        self.grid = Gtk.Grid()
        self.grid_y = 0
        self.dialog.get_content_area().add(self.grid)


    def _write_dialog_content(self) -> None:
        # Fill the dialog with properties of self.entry
        self._add_property_row('SUMMARY')
        self._add_type_row()
        self._add_datetime_rows()
        self._add_rrule_row()
        self._add_property_row('PRIORITY')
        self._add_status_row()
        self._add_property_row('LOCATION')
        self._add_alarm_rows()
        self._add_description_rows()


    def _add_row(self, label:str, cont:str, wrap:bool=False) -> None:
        # Add text to bottom of grid in the form "label cont"
        propnm_lab = Gtk.Label(label)
        propnm_lab.set_halign(Gtk.Align.END)
        propnm_lab.set_yalign(0)
        propnm_lab.get_style_context().add_class(GUI.STYLE_TXTLABEL)
        cont_lab = Gtk.Label(cont)
        cont_lab.set_halign(Gtk.Align.START)
        cont_lab.set_yalign(0)
        cont_lab.set_xalign(0)
        propnm_lab.get_style_context().add_class(GUI.STYLE_TXTPROP)
        if wrap:
            cont_lab.set_line_wrap(True)
            cont_lab.set_line_wrap_mode(PWrapMode.WORD_CHAR)
            cont_lab.set_max_width_chars(50) # otherwise it fills screen
        self.grid.attach(propnm_lab, 0,self.grid_y, 1,1)
        self.grid.attach(cont_lab, 1,self.grid_y, 1,1)
        self.grid_y += 1


    def _add_property_row(self, propnm:str) -> None:
        # Add simple property in a single row to bottom of grid
        if propnm in self.entry:
            self._add_row(_(propnm.capitalize()+':'), self.entry[propnm])


    def _add_type_row(self) -> None:
        # Add entry type property to bottom of grid
        typestr = str(type(self.entry))
        afterdot = typestr.rfind('.')+1
        endquote = typestr.rfind("'")
        if afterdot>0 and endquote>afterdot:
            typestr = typestr[afterdot:endquote]
            if typestr in self.ENTRY_TYPES:
                self._add_row(_('Type:'), _(typestr))


    def _add_datetime_rows(self) -> None:
        # Add datetime start/end/duration properties to bottom of grid
        self._add_datetime_row_if_exists('DTSTART', _('Start date:'), _('Start date/time:'))
        self._add_datetime_row_if_exists('DTEND', _('End date:'), _('End date/time:'))
        if 'DURATION' in self.entry:
            dur = self.entry['DURATION'].dt
            self._add_row(_('Duration:'), str(dur))
        self._add_datetime_row_if_exists('DUE', _('Due date:'), _('Due date/time:'))
        self._add_datetime_row_if_exists('COMPLETED', _('Completed date (noncompliant):'), _('Completed date/time:'))


    def _add_datetime_row_if_exists(self, ical_lab:str, ui_date_lab:str, ui_dt_lab:str) -> None:
        # If ical_lab date/time property exists, add it to bottom of grid
        if ical_lab in self.entry:
            dt = self.entry[ical_lab]
            dt_dt = dt.dt
            if isinstance(dt_dt, dt_datetime):
                self._add_row(ui_dt_lab, str(dt_dt)+self._tz_str(dt))
            else:
                self._add_row(ui_date_lab, str(dt_dt))


    @staticmethod
    def _tz_str(dt_st:vDDDTypes) -> str:
        # Returns string indicating timezone, to be appended to times
        params = dt_st.params
        if 'TZID' in params:
            return _(' (timezone: {:s})').format(params['TZID']) # type:ignore
        return ''


    def _add_rrule_row(self) -> None:
        # Add rrule properties to bottom of grid
        rep_info = ''
        if 'RRULE' in self.entry:
            rr = self.entry['RRULE']
            if 'FREQ' in rr:
                rep_info = rr['FREQ'][0].capitalize()
                if 'INTERVAL' in rr:
                    rep_info += ' ({} {})'.format(_('interval:'), rr['INTERVAL'][0])
            for by in self.RRULE_RPTPROPLIST:
                if by in rr:
                    if rep_info:
                        rep_info +='\n'
                    val = rr[by]
                    if len(val) == 1:
                        val = val[0]
                    rep_info += '{} {}'.format(_(self.RRULE_RPTPROPLIST[by]), str(val))
        if 'EXDATE' in self.entry:
            exdts = Calendar.caldatetime_tree_to_dt_list(self.entry['EXDATE'])
            if rep_info:
                rep_info +='\n'
            rep_info += _('Exception dates:')
            exdt_str = ''
            for dt in exdts:
                if exdt_str:
                    exdt_str += _(';')
                exdt_str += ' ' + str(dt)
            rep_info += exdt_str

        # Finally, display the info string
        if rep_info:
            self._add_row(_('Repeats:'), rep_info)


    def _add_status_row(self) -> None:
        # Add status property to bottom of grid
        if 'STATUS' in self.entry:
            stat = self.entry['STATUS']
            if stat in self.STATUS_MAP:
                stat = self.STATUS_MAP[stat]
            else:
                stat = stat.capitalize()
            self._add_row(_('Status:'), _(stat))


    def _add_alarm_rows(self) -> None:
        # Add alarm properties to bottom of grid
        alarms = self.entry.walk('VALARM')
        if alarms:
            a_info = ''
            for a in alarms:
                if a_info:
                    a_info += '\n'
                if 'TRIGGER' in a:
                    trig = a['TRIGGER'].dt
                    if isinstance(trig,timedelta) and trig<timedelta(0):
                        # More intuitive way to show negative deltas
                        a_info += u'−'
                        trig = -trig
                    a_info += str(trig)
                    if 'ACTION' in a:
                        act = a['ACTION'].capitalize()
                        a_info += ' ' + _(act)
                        if act=='Email':
                            if 'ATTENDEE' in a:
                                # May be more than one attendee
                                a_info += '\n('
                                attee = a['ATTENDEE']
                                if isinstance(attee, list):
                                    a_info += ', '.join(attee)
                                else:
                                    a_info += attee
                                a_info += ')'
                        if act in ('Display','Email'):
                            if 'DESCRIPTION' in a:
                                # Spec says only one description
                                a_info += '\n'
                                a_info += _(u'“{:s}”').format(a['DESCRIPTION'])
                else:
                    # No Trigger (so breaks specs)
                    a_info += 'Unspecified'
            self._add_row(_('Alarms:'), a_info)


    def _add_description_rows(self) -> None:
        # Add description(s) to bottom of grid.
        # (I notice that in RFC 5545, descriptions must not occur more
        # than once for events/todos. However, I wrote code to handle
        # more than one, so I'm leaving it that way.)
        if 'DESCRIPTION' in self.entry:
            edesc = self.entry['DESCRIPTION']
            if isinstance(edesc, list):
                for d in edesc:
                    if 'LANGUAGE' in d.params:
                        self._add_row(_('Description ({}):').format(d.params['LANGUAGE']), d, wrap=True)
                    else:
                        self._add_row(_('Description:'), d, wrap=True)
            else:
                # !! Not sure how to access LANGUAGE parameter for single desc
                self._add_row(_('Description:'), edesc, wrap=True)


    def run(self) -> Gtk.ResponseType:
        # run the dialog
        self._write_dialog_content()
        self.dialog.show_all()
        return self.dialog.run()


    def destroy(self) -> None:
        # destroy the dialog
        self.dialog.destroy()
