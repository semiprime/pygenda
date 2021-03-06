Known Issues
============
A list of known bugs in & to-dos for Pygenda.

This is incomplete in-development code, released as a preview for
developers. As such there are many major additions still to do, as
well as numerous bugs. This is a (certainly incomplete) list to help
keep track of these issues.

Note also, that the code is released as-is and there is no guarantee
of any sort.

Major
-----
* Missing views: Day, List, Busy

* Alarms are not implemented (note: a separate server should handle
  the actual alarm notifications)

* Many event properties are not implemented (details, attendees etc.)

* Many todo item properties are not implemented (due date, status etc.)
  and they can only be sorted by priority

* Repeated entries UI missing many elements (more complete repeat by
  BYMONTHDAY, BYSETPOS, Monday & Wednesday every week, extra dates,
  hourly/minutely/secondly repeats).
  See: https://icalendar.org/iCalendar-RFC-5545/3-3-10-recurrence-rule.html
  Doesn't handle repeat by RDATE at all.
  See: https://icalendar.org/iCalendar-RFC-5545/3-8-5-2-recurrence-date-times.html

* Editing exception dates not very clean. E.g. can add "exceptions"
  that are not part of the repeat run, and they are saved without
  problem, and not highlighted in UI as problematic in any way;
  dates can be added that are not visible because box doesn't scroll
  to newly added date; entries can be made invisible (thus uneditable)
  by making all occurrences exceptions; keyboard navigation in menu
  is not intuitive.

* Multi-day entries (i.e. that span multiple days) only displayed on
  first day. (Need to set a config, e.g. "next_day_crossover" for week
  view, year view.  If time goes beyond that, then also show in next
  day.)

* Cutting repeating entries is not implemented. (Not sure how to do UI -
  probably need to bring up a dialog "Cut just this occurrence, or all
  repeats?". That then raises question about behaviour when copying
  repeating entries, where currently just one occurrence is copied. See
  also deleting repeated entries - currently all repeats are deleted.)

* Creating/updating new entries in large calendars is unusably slow.
  (In tests, with .ics file, file writing is slow; with CalDAV server
  re-sorting the lists is slow.)

* No "Find" function

* No "Import" function

* Only one calendar source can be used at a time. (Maybe allow multiple
  CalDAV calendars, each with own style element, so can be coloured
  differently by CSS. No support for multiple .ics files?)

Medium
------
* No "Zoom" function (is this even needed with a decent modern display?)

* Todo View navigation needs work: touchscreen not supported, and
  left/right can make cursor jump up and down

* Todo items cannot be shown in Week or Year views

* When deleting a repeated entry, all are deleted. Should offer option
  of deleting this one (better, also offer delete all from, all before...)

* No file manipulation: open, import, save-as, new file...

* No time-zone support (should at least be part of time widget)
  (Options: "Travels with me" (default), zone xxx (list local first))

* No GUI for configuration settings/preferences

* Only French & English translations are provided (and the French needs
  checking by a native speaker).

* Setting number of days for "all day" entries could be friendlier
  (e.g. show/set end date)

* Timed events can't last more than 24 hours (need to augment duration widget)

* No support for encryption/password protected entries

* Currently, if using CalDAV server & the connection fails (e.g. server
  halted), Pygenda just exits. Unclear what the best course is. To review
  later. (In "delete event" scenario, an error message & event remains
  probably good behaviour.)

* Ctrl+z does not work to undo in text entry fields. (Surprisingly, GTK3
  does not take care of this. Need to wait for GTK4? Port to QT??)

* Copying/cutting entries doesn't work on all platforms. This functionality
  relies on a small C library, due to limits of Python GObject module.
  Builds on my devices and on Gemini. Needs looking at for other Linux
  distributions and Windows/MacOS.

* Soft buttons need work. (Customisable, choose good defaults, add icons?)

* Date/time widgets are not easy to click (tap) on since most of the area
  does not respond to mouse clicks

* On Psion Agenda, could specify letter to use for display in Year view.
  Maybe add similar functionality by allowing user to add a Category
  https://icalendar.org/iCalendar-RFC-5545/3-8-1-2-categories.html
  This would add a "category_xxx" style to element, and css can be
  used to style these as wanted (user-supplied css).

* Potential optimisations when drawing Year View, which might make it
  quicker when going from year to year. (See comments in source for
  thoughts.)

* Some repeat types are slow to calculate (fallback types, e.g. by day
  in month).
  Currently uses dateutil.rrule to calculate most complex repeats,
  see: https://dateutil.readthedocs.io/en/stable/rrule.html
  Check if using recurring-ical-events module could improve speed??
  See: https://pypi.org/project/recurring-ical-events/

* Starting date of repeating entries is not always obvious to the user.
  For example, date 30th March, repeat on last day of month -> starts
  31st March, but change to 3rd-to-last day of month and it starts 28th
  April. (Maybe this will be clearer when cursor moves to edited entry?)

* If calendar data is updated externally while Pygenda is runing (e.g.
  another instance of Pygenda, or some other app, updates database)
  the changes are not detected/displayed.

* In Entry dialog, repeats until/occurrences. Until date can be wrong if
  occurrences very high; occurrences can be wrong if date in far future.

* "Today" marked in views is not updated if day changes (e.g. midnight
  crossover, switch on device in new day, device time(zone) changed).

* For calendars saved in .ics file. Copy/pasting an entry with a timezone
  to a date with a different DST, time displayed (local time) is an hour
  off. This fixes itself if Pygenda is restarted (so .ics file is re-read).
  Probable cause: In new_entry_from_example(), tzinfo of event includes
  timezone name ('Europe/London' etc) and utc offset. When new time is
  calculated it uses utc offset, but stores the timezone name. Hence
  initial display is incorrect, but when event is re-parsed it uses
  the timezone name and re-does calculation of utc offset, so time
  is now correct. This doesn't happen with CalDAV server, because in
  CalendarConnectorCalDAV::add_entry() it re-creates a new ics entry
  and (crucially) parses it, which gives the correct time.

Minor
-----
(Note: minor bugs can still be irritating!)

* After creating/editing an entry, cursor not always on that entry

* Would be nice to be able to edit dates with a calendar interface
  (Like pressing tab in S5)

* Week view: no touchscreen way to go forward/back a week (use swipe??)

* Ctrl+Left-Shift+X/C/V/N don't work on Gemini (UI eats keypress?)
  Workaround: Use Right-Shift.

* Anniversary entry year (e.g. "20 years") not displayed (they're
  just annual repeats). (Maybe add category "Anniversary"?)

* Entry dialog needs some indication if tab contents are non-default
  (e.g. if there are repeats, alarms - maybe show a tick in the tab handle)

* No user feedback for some actions (e.g. copy entry). Should flash or
  recolour cursor or something.

* Menu shortcuts set in glade are not translated (e.g. aller ?? = ctrl+g)

* Menu items are not disabled when not relevant (e.g. cut/copy when cursor
  is not on an entry). (Maybe "fullscreen" could toggle on/off too?)

* When changing from Week View to Year View, if cursor is on an event
  that is out of view, then the view should scroll to show that event.
  (Tried fixing by making cls.scroll_to_row() call at end of
  \_show_entry_cursor() into an idle_add. Worked first time, but not
  subsequent times.)

* If using a .ics file and multiple instances edit the same file, data
  can be lost (note: using .ics file is not recommended => minor)

* In comboboxes, when in "popped out" state, +/-/</> keys don't work

* In code, various places marked with '!!' indicating known bugs or
  temporary/placeholder implementations.

Cosmetic
--------
* If the first entry edited after starting Pygenda has multiple exception
  dates, then it makes room for these in the Entry dialog Repeats tab.
  This means that the Entry dialog is made wide, and stays that way
  until Pygenda is restarted.

* Year View: Pixel missing in grid lines at top-left corner

* On Gemini, shows "no access" icons in instead of "minus" icons (e.g. in
  spin buttons of entry dialog) - Gemian bug?

* Year view is slow to redraw on Gemini, so get black rectangles when
  e.g. closing dialogs.

* Startup spinner is a bit glitchy (visible for large calendars).

* In Entry dialog, Repeats tab, "Repeat until" label doesn't seem to align
  quite correctly with the field content.

Testing
-------
* Need to test that iCal files/data can be read by other applications and
  Pygenda can read files/data from other applications.

* Need to expand unit testing (currently just test_repeats.py) and other
  tests (currently just manually checking a few test*.ics files).

* Need to test with corrupt iCal files. (Including when files become
  corrupt while the program is running.) Use a fuzzer?
  ? https://pypi.org/project/pythonfuzz/

* Need more complete checking from type annotations, so `mypy .` gives
  useful results.
