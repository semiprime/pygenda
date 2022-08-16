# -*- coding: utf-8 -*-
#
# pygenda_view_todo.py
# Provides the "To-Do View" for Pygenda.
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
from locale import gettext as _
from typing import Optional, List, Union

# pygenda components
from .pygenda_view import View
from .pygenda_calendar import Calendar
from .pygenda_config import Config
from .pygenda_gui import GUI, TodoDialogController
from .pygenda_entryinfo import EntryInfo


# Singleton class for Todo View
class View_Todo(View):
    Config.set_defaults('todo_view',{
        'list0_title': _('To-do'),
    })

    _cursor_list = 0
    _cursor_idx_in_list = 0
    _last_cursor_list = None
    _last_cursor_idx_in_list = None
    _list_items = None # type: list
    CURSOR_STYLE = 'todoview_cursor'

    @staticmethod
    def view_name() -> str:
        # Return (localised) string to use in menu
        return _('_Todo View')

    @staticmethod
    def accel_key() -> int:
        # Return (localised) keycode for menu shortcut
        k = _('todo_view_accel')
        return ord(k[0]) if len(k)>0 else 0


    @classmethod
    def init(cls) -> Gtk.Widget:
        # Called on startup.
        # Gets view framework from glade file & tweaks/adds a few elements.
        # Returns widget containing view.
        cls._init_parse_list_config()
        cls._init_todo_widgets()
        cls._init_keymap()
        return cls._topboxscroll


    @classmethod
    def _init_parse_list_config(cls) -> None:
        # Read & parse config settings
        i = 0
        cls._list_titles = []
        cls._list_filters = []
        cls._list_default_cats = []
        while True:
            try:
                title = Config.get('todo_view','list{}_title'.format(i))
            except:
                break
            try:
                filt = Config.get('todo_view','list{}_filter'.format(i))
            except:
                filt = None
            cls._list_titles.append(title)
            cls._list_filters.append(filt)
            cls._list_default_cats.append(cls._default_cats_from_filter(filt))
            i += 1
        cls._list_count = i
        cls._item_counts = [0]*cls._list_count


    @staticmethod
    def _default_cats_from_filter(filt:Optional[str]) -> Optional[list]:
        # Return list of categories that will match given filter string.
        # For now this is quite simple, but in the future it may support
        # more complex filters (e.g. project1 AND this_week).
        if not filt or filt=='UNCATEGORIZED':
            return None
        return [filt]


    @classmethod
    def _init_todo_widgets(cls) -> None:
        # Initialise widgets - create list labels, entry spaces etc.
        # First make the top-level container
        cls._topboxscroll = Gtk.ScrolledWindow()
        cls._topboxscroll.set_name('view_todo')
        cls._topboxscroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.NEVER)
        cls._topboxscroll.set_overlay_scrolling(False)
        cls._topboxscroll.set_hexpand(True)
        list_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        list_hbox.set_homogeneous(True)
        cls._topboxscroll.add(list_hbox)

        # Now add vertical boxes for each list
        cls._list_container = []
        for i in range(cls._list_count):
            new_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            new_list.get_style_context().add_class('todoview_list')
            new_title = Gtk.Label(cls._list_titles[i])
            new_list.add(new_title)
            new_title.get_style_context().add_class('todoview_title')
            new_list_scroller = Gtk.ScrolledWindow()
            new_list_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            new_list_scroller.set_overlay_scrolling(False)
            new_list_scroller.set_vexpand(True)
            new_list.add(new_list_scroller)
            new_list_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            new_list_scroller.add(new_list_content)
            cls._list_container.append(new_list_scroller)
            list_hbox.add(new_list)


    @classmethod
    def _init_keymap(cls) -> None:
        # Initialises KEYMAP for class. Called from init() since it needs
        # to be called after class construction, so that functions exist.
        cls._KEYMAP = {
            Gdk.KEY_Up: lambda: cls._cursor_move_up(),
            Gdk.KEY_Down: lambda: cls._cursor_move_dn(),
            Gdk.KEY_Right: lambda: cls._cursor_move_rt(),
            Gdk.KEY_Left: lambda: cls._cursor_move_lt(),
            Gdk.KEY_Home: lambda: cls._cursor_move_list(0),
            Gdk.KEY_End: lambda: cls._cursor_move_list(-1),
            Gdk.KEY_Page_Up: lambda: cls._cursor_move_index(0),
            Gdk.KEY_Page_Down: lambda: cls._cursor_move_index(-1),
            Gdk.KEY_Return: lambda: cls.cursor_edit_entry(),
        }


    @classmethod
    def get_cursor_entry(cls) -> Optional[iTodo]:
        # Returns entry at cursor position, or None if cursor not on entry.
        # Called from cursor_edit_entry() & delete_request().
        if len(cls._list_items[cls._cursor_list]) == 0:
            return None
        return cls._list_items[cls._cursor_list][cls._cursor_idx_in_list]


    @classmethod
    def new_entry_from_example(cls, en:Union[iEvent,iTodo]) -> None:
        # Creates new entry based on entry en. Used for pasting entries.
        # Type of entry depends on View (e.g. Todo View -> to-do item).
        cats = cls._list_default_cats[cls._cursor_list]
        Calendar.new_entry_from_example(en, e_type=EntryInfo.TYPE_TODO, e_cats=cats)


    @classmethod
    def paste_text(cls, txt:str) -> None:
        # Handle pasting of text in Todo view.
        # Open a New Todo dialog with description initialised as txt,
        # and to-do list set from current cursor position.
        GLib.idle_add(lambda x: TodoDialogController.newtodo(txt=x, list_idx=cls.cursor_todo_list()), txt)


    @classmethod
    def cursor_todo_list(cls) -> int:
        # Returns index of todo list with cursor.
        # Used by "new todo" etc to initialise dialog with focused todo list.
        return cls._cursor_list


    @classmethod
    def redraw(cls, en_changes:bool) -> None:
        # Called when redraw required
        # en_changes: bool indicating if displayed entries need updating too
        if not en_changes:
            return
        cls._last_cursor_list = None
        cls._last_cursor_idx_in_list = None
        for cont in cls._list_container:
            cont.get_child().destroy()
        todos = Calendar.todo_list()
        cls._list_items = []
        for i in range(len(cls._list_container)):
            new_list_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            count = 0
            cls._list_items.append([])
            for td in todos:
                if cls._todo_matches_filter(td, cls._list_filters[i]):
                    row = Gtk.Box()
                    # Potential markers: ①-0x245f ➀-0x277f ❶-0x2775 ➊-0x2789
                    mark_label = Gtk.Label(chr(0x2789+td['PRIORITY']) if 'PRIORITY' in td else u'•')
                    mark_label.set_halign(Gtk.Align.END)
                    mark_label.set_valign(Gtk.Align.START)
                    ctx = mark_label.get_style_context()
                    ctx.add_class('todoview_marker')
                    row.add(mark_label)
                    item_text = Gtk.Label(td['SUMMARY'] if 'SUMMARY' in td else '')
                    item_text.set_xalign(0)
                    item_text.set_yalign(0)
                    item_text.set_line_wrap(True)
                    item_text.set_line_wrap_mode(PWrapMode.WORD_CHAR)
                    row.add(item_text)
                    new_list_content.add(row)
                    cls._list_items[-1].append(td)
                    count += 1
            cls._item_counts[i] = count
            if count==0:
                # an empty list, need something for cursor
                mark_label = Gtk.Label()
                mark_label.set_halign(Gtk.Align.START) # else cursor fills line
                ctx = mark_label.get_style_context()
                ctx.add_class('todoview_marker')
                new_list_content.add(mark_label)
            new_list_content.get_style_context().add_class('todoview_items')
            cls._list_container[i].add(new_list_content)
            cls._list_container[i].show_all()
        cls._show_cursor()


    @staticmethod
    def _todo_matches_filter(td:iTodo, filt:Optional[str]) -> bool:
        # Return True if categories of to-do item match filter
        if filt is None:
            return True
        cats = View_Todo._get_categories(td)
        if not cats:
            return filt=='UNCATEGORIZED'
        return filt in cats


    @staticmethod
    def _get_categories(td:iTodo) -> list:
        # Return list of categories of the given to-do item
        if 'CATEGORIES' not in td:
            cats = [] # type: List[str]
        elif isinstance(td['CATEGORIES'],list):
            cats = []
            for clist in td['CATEGORIES']:
                if isinstance(clist,str):
                    cats.extend([c for c in clist.split(',') if c])
                else:
                    cats.extend([c for c in clist.cats if c])
        elif isinstance(td['CATEGORIES'],str):
            cats = [c for c in td['CATEGORIES'].split(',') if c]
        else:
            cats = [c for c in td['CATEGORIES'].cats if c]
        return cats


    @classmethod
    def _show_cursor(cls) -> None:
        # Locates bullet corresponding to the current cursor and adds
        # 'todoview_cursor' class to it, so cursor is visible via CSS styling.

        # First correct cursor if required (e.g. item was deleted)
        if not (0 <= cls._cursor_list < cls._list_count):
            cls._cursor_list = max(0, cls._list_count-1)
        icount = cls._item_counts[cls._cursor_list]
        if not (0 <= cls._cursor_idx_in_list < icount):
            cls._cursor_idx_in_list = max(0, icount-1)

        cls._hide_cursor()

        ctx = cls._get_cursor_ctx(cls._cursor_list, cls._cursor_idx_in_list)
        if ctx is not None:
            ctx.add_class(cls.CURSOR_STYLE)
        cls._last_cursor_list = cls._cursor_list
        cls._last_cursor_idx_in_list = cls._cursor_idx_in_list
        cls._scroll_to_cursor()


    @classmethod
    def _hide_cursor(cls) -> None:
        # Clears 'todoview_cursor' style class from cursor position,
        # so cursor is no longer visible.
        if cls._last_cursor_list is not None:
            ctx = cls._get_cursor_ctx(cls._last_cursor_list, cls._last_cursor_idx_in_list)
            if ctx is not None:
                ctx.remove_class(cls.CURSOR_STYLE)
            cls._last_cursor_list = None
            cls._last_cursor_idx_in_list = None


    @classmethod
    def _get_cursor_ctx(cls, c_list:int, c_i_in_list:int) -> Gtk.StyleContext:
        # Returns a StyleContext object for to-do cursor coordinates
        # c_list & c_i_in_list
        lst = cls._list_container[c_list].get_child().get_child()
        item = lst.get_children()[c_i_in_list]
        if cls._item_counts[c_list]==0:
            ci = item
        else:
            ci = item.get_children()[0]
        return ci.get_style_context()


    @classmethod
    def _scroll_to_cursor(cls) -> None:
        # If required, scroll view elements so that cursor is visible.
        # Note: On first call view is not yet drawn, so calculation is not
        # correct. However, since don't need to scroll, behaviour is right.
        list_width = cls._list_container[0].get_allocated_width() # homogeneous
        view_width = cls._topboxscroll.get_allocated_width()
        maxv = cls._cursor_list*list_width # left edge of list at left of view
        minv = (cls._cursor_list+1)*list_width-view_width # rt edge @ rt of view
        adj = cls._topboxscroll.get_hadjustment()
        cur = adj.get_value()
        if minv > maxv:
            minv = maxv # If list is wider than view, then show left edge
        if cur > maxv:
            adj.set_value(maxv)
        elif cur < minv:
            adj.set_value(minv)

        # Now the vertical scrolling...
        list_scroller = cls._list_container[cls._cursor_list]
        list_box = list_scroller.get_child().get_child()
        list_item_wids = list_box.get_children()
        maxv = list_box.get_spacing()*cls._cursor_idx_in_list
        for i in range(cls._cursor_idx_in_list):
            maxv += list_item_wids[i].get_allocated_height()
        minv = maxv + list_item_wids[cls._cursor_idx_in_list].get_allocated_height()
        minv -= list_scroller.get_allocated_height()
        # Take into account padding/margin etc.
        ctx = list_box.get_style_context()
        pad = ctx.get_padding(Gtk.StateFlags.NORMAL)
        bord = ctx.get_border(Gtk.StateFlags.NORMAL)
        marg = ctx.get_margin(Gtk.StateFlags.NORMAL)
        minv += pad.top + bord.top + marg.top + pad.bottom
        if minv > maxv:
            minv = maxv # If item is taller than view, then show top
        adj = list_scroller.get_vadjustment()
        cur = adj.get_value()
        if cur > maxv:
            adj.set_value(maxv)
        elif cur < minv:
            adj.set_value(minv)


    @classmethod
    def keypress(cls, wid:Gtk.Widget, ev:Gdk.EventKey) -> None:
        # Handle key press event in Week view.
        # Called (from GUI.keypress()) on keypress (or repeat) event
        try:
            f = cls._KEYMAP[ev.keyval]
            GLib.idle_add(f)
        except KeyError:
            # If it's a character key, take as first of new todo
            # !! Bug: only works for ASCII characters
            if ev.state & (Gdk.ModifierType.CONTROL_MASK|Gdk.ModifierType.MOD1_MASK)==0 and Gdk.KEY_exclam <= ev.keyval <= Gdk.KEY_asciitilde:
                GLib.idle_add(lambda x: TodoDialogController.newtodo(txt=x, list_idx=cls.cursor_todo_list()), chr(ev.keyval))


    @classmethod
    def _cursor_move_up(cls) -> None:
        # Callback for user moving cursor up
        cls._cursor_idx_in_list -= 1 # Cursor correction will fix if <0
        cls._show_cursor()

    @classmethod
    def _cursor_move_dn(cls) -> None:
        # Callback for user moving cursor down
        if cls._item_counts[cls._cursor_list] > 0:
            cls._cursor_idx_in_list = (cls._cursor_idx_in_list+1)%cls._item_counts[cls._cursor_list]
            cls._show_cursor()

    @classmethod
    def _cursor_move_rt(cls) -> None:
        # Callback for user moving cursor right
        cls._cursor_list = (cls._cursor_list+1)%cls._list_count
        cls._show_cursor()

    @classmethod
    def _cursor_move_lt(cls) -> None:
        # Callback for user moving cursor left
        cls._cursor_list -= 1 # Cursor correction will fix if <0
        cls._show_cursor()

    @classmethod
    def _cursor_move_list(cls, lst:int) -> None:
        # Callback for user moving cursor to list
        cls._cursor_list = lst
        cls._show_cursor()

    @classmethod
    def _cursor_move_index(cls, idx:int) -> None:
        # Callback for user moving cursor to idx in current list
        cls._cursor_idx_in_list = idx
        cls._show_cursor()

    @classmethod
    def cursor_edit_entry(cls) -> None:
        # Opens a todo edit dialog for the entry at the cursor,
        # or to create a new todo if the cursor is not on entry.
        # Assigned to the 'Enter' key.
        en = cls.get_cursor_entry()
        if en is None:
            TodoDialogController.newtodo(list_idx=cls.cursor_todo_list())
        else:
            TodoDialogController.edittodo(en, list_idx=cls.cursor_todo_list())
