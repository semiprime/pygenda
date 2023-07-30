# -*- coding: utf-8 -*-
#
# pygenda_view_todo.py
# Provides the "To-Do View" for Pygenda.
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
from gi.repository.Pango import WrapMode as PWrapMode

from icalendar import cal as iCal, Event as iEvent, Todo as iTodo
from locale import gettext as _
from typing import Optional, List, Tuple, Union

# pygenda components
from .pygenda_view import View
from .pygenda_calendar import Calendar
from .pygenda_config import Config
from .pygenda_gui import GUI
from .pygenda_dialog_todo import TodoDialogController
from .pygenda_entryinfo import EntryInfo


# Singleton class for Todo View
class View_Todo(View):
    Config.set_defaults('todo_view',{
        'list0_title': _('To-do'),
        'zoom_levels': 5,
        'default_zoom': 2,
    })

    _cursor_list = 0
    _cursor_idx_in_list = 0
    _last_cursor_list = None
    _last_cursor_idx_in_list = None
    _list_items = None # type: list
    _target_listidx = None
    _target_todo = None
    _target_cursor_y = None # type: Optional[float]
    _scroll_to_cursor_required = False
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
        cls.init_zoom('todo_view', cls._topboxscroll.get_style_context())
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
        list_hbox.connect('draw', cls._pre_draw)

        # Now add vertical boxes for each list
        cls._list_box = []
        cls._list_scroller = []
        for i in range(cls._list_count):
            new_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            new_list.get_style_context().add_class('todoview_list')
            new_title = Gtk.Label(cls._list_titles[i])
            new_title.set_line_wrap(True)
            new_title.set_line_wrap_mode(PWrapMode.WORD_CHAR)
            new_title.get_style_context().add_class('todoview_title')
            new_eventbox_title = Gtk.EventBox()
            new_eventbox_title.connect('button_press_event', cls.click_title, i)
            new_eventbox_title.add(new_title)
            new_list.add(new_eventbox_title)
            new_list_scroller = Gtk.ScrolledWindow()
            new_list_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            new_list_scroller.set_overlay_scrolling(False)
            new_list_scroller.set_vexpand(True)
            new_list_scroller.get_style_context().add_class('todoview_listcontent')
            new_list_scroller.get_vadjustment().connect('value-changed', cls._list_scrolled)
            new_eventbox_list = Gtk.EventBox()
            new_eventbox_list.connect('button_press_event', cls.click_list, i)
            new_eventbox_list.add(new_list_scroller)
            new_list.add(new_eventbox_list)
            new_list_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            new_list_scroller.add(new_list_content)
            cls._list_box.append(new_list)
            cls._list_scroller.append(new_list_scroller)
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
        new_en = Calendar.new_entry_from_example(en, e_type=EntryInfo.TYPE_TODO, e_cats=cats)
        cls.cursor_goto_todo(new_en, cls._cursor_list)


    @classmethod
    def paste_text(cls, txt:str) -> None:
        # Handle pasting of text in Todo view.
        # Open a New Todo dialog with description initialised as txt,
        # and to-do list set from current cursor position.
        GLib.idle_add(lambda x: TodoDialogController.new_todo(txt=x, list_idx=cls.cursor_todo_list()), txt)


    @classmethod
    def cursor_todo_list(cls) -> int:
        # Returns index of todo list with cursor.
        # Used by "new todo" etc to initialise dialog with focused todo list.
        return cls._cursor_list


    @classmethod
    def cursor_goto_todo(cls, todo:iTodo, list_idx:int) -> bool:
        # Move cursor to given todo in given list.
        # Return True to indicate this is possible in this view.
        # Set targets, but don't move yet, since we want to redraw view
        # & to use recalculated todo order to determine cursor position.
        cls._target_listidx = list_idx
        cls._target_todo = todo
        return True


    @classmethod
    def redraw(cls, en_changes:bool) -> None:
        # Called when redraw required
        # en_changes: bool indicating if displayed entries need updating too
        cls._target_cursor_y = None # reset navigation y-coord
        if not en_changes:
            return
        cls._last_cursor_list = None
        cls._last_cursor_idx_in_list = None
        for cont in cls._list_scroller:
            cont.get_child().destroy()
        todos = Calendar.todo_list()
        cls._list_items = []
        for i in range(len(cls._list_scroller)):
            new_list_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            count = 0
            cls._list_items.append([])
            for td in todos:
                if cls._todo_matches_filter(td, cls._list_filters[i]):
                    if cls._target_todo is not None and cls._target_todo is td:
                        cls._cursor_list = i
                        cls._cursor_idx_in_list = count
                        if i>=cls._target_listidx:
                            # We've reached the target list, so go no further
                            cls._target_listidx = None
                            cls._target_todo = None
                    row = Gtk.Box()
                    ctx = row.get_style_context()
                    ctx.add_class('todoview_item')
                    # Potential markers: ①-0x245f ➀-0x277f ❶-0x2775 ➊-0x2789
                    mark_label = Gtk.Label(chr(0x2789+td['PRIORITY']) if 'PRIORITY' in td else u'•')
                    mark_label.set_halign(Gtk.Align.END)
                    mark_label.set_valign(Gtk.Align.START)
                    mark_label.get_style_context().add_class('todoview_marker')
                    row.add(mark_label)
                    txt = ''
                    if 'DUE' in td:
                        due_dt = td['DUE'].dt
                        due_dt_st = due_dt.strftime(GUI.date_formatting_numeric)
                        txt += '({:s} {:s}) '.format(_('Due:'), due_dt_st)
                    txt += td['SUMMARY'] if 'SUMMARY' in td else ''
                    item_text = Gtk.Label(txt)
                    item_text.get_style_context().add_class('todoview_itemtext')
                    item_text.set_xalign(0)
                    item_text.set_yalign(0)
                    item_text.set_line_wrap(True)
                    item_text.set_line_wrap_mode(PWrapMode.WORD_CHAR)
                    if 'STATUS' in td and td['STATUS'] in Calendar.STATUS_LIST_TODO:
                        ctx.add_class(td['STATUS'].lower())
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
            cls._list_scroller[i].add(new_list_content)
            cls._list_scroller[i].show_all()
        # Reset target (though in theory this should already be done)
        cls._target_listidx = None
        cls._target_todo = None
        cls._show_cursor()


    @classmethod
    def zoom(cls, inc:int) -> None:
        # Override zoom() in parent class so we can reset y-coord target
        super().zoom(inc) # call version of zoom() in parent class
        cls._target_cursor_y = None


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
    def click_title(cls, wid:Gtk.Widget, ev:Gdk.EventButton, list_idx:int) -> bool:
        # Callback. Called whenever a list title is clicked/tapped.
        # Moves cursor to top of list/item clicked
        cls._cursor_move_list(list_idx)
        cls._cursor_move_index(0)
        cls._target_cursor_y = None
        cls._scroll_to_cursor_required = True
        return True # event handled - don't propagate


    @classmethod
    def click_list(cls, wid:Gtk.Widget, ev:Gdk.EventButton, list_idx:int) -> bool:
        # Callback. Called whenever list content is clicked/tapped.
        # Moves cursor to list/item clicked
        cls._cursor_move_list(list_idx)
        scroller = cls._list_scroller[list_idx]
        vwport = scroller.get_children()[0]
        row_vbox = vwport.get_children()[0]
        # Pixels above the first row:
        ycount = cls._top_spacing(scroller)
        ycount += cls._top_spacing(vwport)
        ycount += cls._top_spacing(row_vbox)
        # Take account of list's vertical scrollbar:
        ycount -= cls._list_scroller[list_idx].get_vadjustment().get_value()
        # Look through rows until cumulative height exceeds click ycoord
        row_spacing = row_vbox.get_spacing()
        rows = row_vbox.get_children()
        ycount -= row_spacing//2 # adjust for no spacing above first row
        i = 0
        for r in rows:
            ycount += r.get_allocated_height()
            ycount += row_spacing
            if ycount > ev.y:
                break
            i += 1
        cls._cursor_move_index(i)
        cls._target_cursor_y = None
        cls._scroll_to_cursor_required = True
        return True # event handled - don't propagate


    @classmethod
    def _list_scrolled(cls, wid:Gtk.Widget) -> bool:
        # Callback. Called whenever a list is scrolled
        cls._target_cursor_y = None # reset navigation y-coord target
        return True # don't propagate event


    @staticmethod
    def _top_spacing(wid:Gtk.Widget) -> float:
        # Return total size of top padding+border+margin of widget
        ctx = wid.get_style_context()
        pad = ctx.get_padding(Gtk.StateFlags.NORMAL)
        bord = ctx.get_border(Gtk.StateFlags.NORMAL)
        marg = ctx.get_margin(Gtk.StateFlags.NORMAL)
        return pad.top + bord.top + marg.top # type:ignore


    @staticmethod
    def _vert_spacing(wid:Gtk.Widget) -> float:
        # Return total size of top+bottom padding+border+margin of widget
        ctx = wid.get_style_context()
        pad = ctx.get_padding(Gtk.StateFlags.NORMAL)
        bord = ctx.get_border(Gtk.StateFlags.NORMAL)
        marg = ctx.get_margin(Gtk.StateFlags.NORMAL)
        return pad.top+pad.bottom + bord.top+bord.bottom + marg.top+marg.bottom # type:ignore


    @staticmethod
    def _left_spacing(wid:Gtk.Widget) -> float:
        # Return total size of left padding+border+margin of widget
        ctx = wid.get_style_context()
        pad = ctx.get_padding(Gtk.StateFlags.NORMAL)
        bord = ctx.get_border(Gtk.StateFlags.NORMAL)
        marg = ctx.get_margin(Gtk.StateFlags.NORMAL)
        return pad.left + bord.left + marg.left # type:ignore


    @staticmethod
    def _side_spacing(wid:Gtk.Widget) -> float:
        # Return total size of left+right padding+border+margin of widget
        ctx = wid.get_style_context()
        pad = ctx.get_padding(Gtk.StateFlags.NORMAL)
        bord = ctx.get_border(Gtk.StateFlags.NORMAL)
        marg = ctx.get_margin(Gtk.StateFlags.NORMAL)
        return pad.left+pad.right + bord.left+bord.right + marg.left+marg.right # type:ignore


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
        # Add scroll call to idle, in case column widths not yet determined
        cls._scroll_to_cursor_required = True
        GUI.set_menu_elts(on_todo=(icount!=0)) # Enable/disable hide menu items

        # If cursor is offscreen, need signal that a redraw is needed
        cls._topboxscroll.get_child().queue_draw()


    @classmethod
    def _pre_draw(cls, wid:Gtk.Widget, _) -> bool:
        # Callback called on 'draw' event on date_content.
        # Called before drawing date content.
        # Used to scroll window when cursor has been moved (since we
        # need to have calculated the layout to know where to scoll to).
        if cls._scroll_to_cursor_required:
            cls._scroll_to_cursor()
            cls._scroll_to_cursor_required = False
        return False # propagate event


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
        lst = cls._list_scroller[c_list].get_child().get_child()
        item = lst.get_children()[c_i_in_list]
        if cls._item_counts[c_list]==0:
            ci = item
        else:
            ci = item.get_children()[0]
        return ci.get_style_context()


    @classmethod
    def _scroll_to_cursor(cls) -> None:
        # If required, scroll view elements so that cursor is visible.
        # Note: If view is not yet laid-out, calculation not correct.
        # Hence this will be called in 'draw' event handler, so layout is done.

        # First: horizontal scrolling...
        # (We know spacing for hbox is zero, since we control it, so ignore)
        list_width = cls._list_box[0].get_allocated_width() # homogeneous
        viewport = cls._topboxscroll.get_child()
        view_width = viewport.get_allocated_width()
        maxv = cls._cursor_list*list_width # left edge of list at left of view
        maxv += cls._left_spacing(viewport.get_child())
        minv = maxv + list_width - view_width # rt edge @ rt of view
        minv += cls._side_spacing(viewport)
        adj = cls._topboxscroll.get_hadjustment()
        cur = adj.get_value()
        if minv > maxv:
            minv = maxv # If list is wider than view, then show left edge
        if cur > maxv:
            adj.set_value(maxv)
        elif cur < minv:
            adj.set_value(minv)

        # Now the vertical scrolling...
        list_scroller, listitems_box = cls._current_scroller_itemsbox()
        viewport = list_scroller.get_child()
        # Take into account padding/margin etc of todoview_items:
        maxv = cls._top_spacing(listitems_box)
        maxv += listitems_box.get_spacing() * cls._cursor_idx_in_list
        list_item_wids = listitems_box.get_children()
        for i in range(cls._cursor_idx_in_list):
            maxv += list_item_wids[i].get_allocated_height()
        minv = maxv + list_item_wids[cls._cursor_idx_in_list].get_allocated_height()
        # For min, subtract visible content height (child in case of padding):
        minv -= viewport.get_allocated_height()
        minv += cls._vert_spacing(viewport)
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
        # Handle key press event in Todo view.
        # Called (from GUI.keypress()) on keypress (or repeat) event
        try:
            f = cls._KEYMAP[ev.keyval]
            GLib.idle_add(f)
        except KeyError:
            # If it's a character key, take as first of new todo
            # !! Bug: only works for ASCII characters
            if ev.state & (Gdk.ModifierType.CONTROL_MASK|Gdk.ModifierType.MOD1_MASK)==0 and Gdk.KEY_exclam <= ev.keyval <= Gdk.KEY_asciitilde:
                GLib.idle_add(lambda x: TodoDialogController.new_todo(txt=x, list_idx=cls.cursor_todo_list()), chr(ev.keyval))


    @classmethod
    def _cursor_move_up(cls) -> None:
        # Callback for user moving cursor up
        cls._cursor_idx_in_list -= 1 # Cursor correction will fix if <0
        cls._target_cursor_y = None
        cls._show_cursor()

    @classmethod
    def _cursor_move_dn(cls) -> None:
        # Callback for user moving cursor down
        cls._target_cursor_y = None
        if cls._item_counts[cls._cursor_list] > 0:
            cls._cursor_idx_in_list = (cls._cursor_idx_in_list+1)%cls._item_counts[cls._cursor_list]
            cls._show_cursor()

    @classmethod
    def _cursor_move_rt(cls) -> None:
        # Callback for user moving cursor right
        if cls._target_cursor_y is None:
            cls._target_cursor_y = cls._get_cursor_y()
        cls._cursor_list = (cls._cursor_list+1)%cls._list_count
        cls._cursor_idx_in_list = cls._y_to_todo_index(cls._target_cursor_y)
        cls._show_cursor()

    @classmethod
    def _cursor_move_lt(cls) -> None:
        # Callback for user moving cursor left
        if cls._target_cursor_y is None:
            cls._target_cursor_y = cls._get_cursor_y()
        cls._cursor_list -= 1 # Cursor correction will fix if <0
        cls._cursor_idx_in_list = cls._y_to_todo_index(cls._target_cursor_y)
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
            TodoDialogController.new_todo(list_idx=cls.cursor_todo_list())
        else:
            GUI.edit_or_display_todo(en, list_idx=cls.cursor_todo_list())


    @classmethod
    def _get_cursor_y(cls) -> float:
        # Return "visual" y of cursor - i.e. y coord as cursor
        # is displayed. Used to calculate which todo item to
        # move to when the cursor is moved right or left.
        y = cls._top_spacing(cls._list_box[cls._cursor_list])
        list_title = cls._current_list_title()
        y += list_title.get_allocated_height()
        list_scroller, listitems_box = cls._current_scroller_itemsbox()
        y += cls._top_spacing(list_scroller)
        y += cls._top_spacing(listitems_box)
        y += listitems_box.get_spacing() * cls._cursor_idx_in_list
        list_item_wids = listitems_box.get_children()
        for i in range(cls._cursor_idx_in_list):
            y += list_item_wids[i].get_allocated_height()
        y -= list_scroller.get_vadjustment().get_value() # Account for scrollbar
        return y # type: ignore


    @classmethod
    def _y_to_todo_index(cls, y:float) -> int:
        # Return index in current list, given a visual y-coord.
        # Used to calculate which todo item to move to when the
        # cursor is moved right or left.
        list_scroller, listitems_box = cls._current_scroller_itemsbox()
        y += list_scroller.get_vadjustment().get_value() # Account for scrollbar
        idx = 0
        list_title = cls._current_list_title()
        spacing = listitems_box.get_spacing()
        ycount = cls._top_spacing(cls._list_box[cls._cursor_list])
        ycount += list_title.get_allocated_height()
        ycount += cls._top_spacing(list_scroller)
        ycount += cls._top_spacing(listitems_box)
        for w in listitems_box.get_children():
            last_ycount = ycount
            ycount += w.get_allocated_height()
            ycount += spacing
            if ycount > y:
                if y-last_ycount > ycount-y:
                    # y is closer to next entry, so choose that one
                    idx += 1
                break
            idx += 1
        return idx


    @classmethod
    def _current_list_title(cls) -> Gtk.Label:
        # Utility function to return current list title Gtk.Label widget
        # ("current" meaning current cursor list).
        lst = cls._list_box[cls._cursor_list]
        tlab = lst.get_children()[0].get_child()
        return tlab


    @classmethod
    def _current_scroller_itemsbox(cls) -> Tuple[Gtk.ScrolledWindow,Gtk.Box]:
        # Utility function to return current list scroller and vbox
        # containing list items ("current" meaning current cursor list).
        list_scroller = cls._list_scroller[cls._cursor_list]
        listitems_box = list_scroller.get_child().get_child()
        return list_scroller, listitems_box
