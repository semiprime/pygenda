Known Issues
============
A list of known bugs in, and to-dos for, Pygenda.

This is in-development code, released for testing and feedback. As
such there are many major features still to add, as well as numerous
bugs. This is a (certainly incomplete) list to help keep track of
these issues.

Note also, that the code is released as-is and there is no guarantee
of any sort.

Major
-----
* Missing views: Day, List, Anniversary, Busy.
  (Also, a Month View, e.g. https://www.rmrsoft.com/epoc/month.htm )

* Setting alarms is under development. See [Usage.md](Usage.md) for
  current details. Alarms with absolute times are not supported at all.
  (Note: a separate alarm program should handle the actual alarm
  notifications.)

* Several event properties are not implemented (attendees, url,
  transparency (i.e. free/busy), user tags, attachments, etc.)

* Many todo item properties are not implemented (start date, user tags,
  timed-but-undated (use daily repeating?), etc.)

* Todo items can only be sorted by priority - add sort by duedate,
  by status, manual...

* Repeated event UI missing many elements (more complete repeat by
  BYMONTHDAY, BYSETPOS, Monday & Wednesday every week, first weekday
  of month, extra dates, hourly/minutely/secondly repeats).
  See: https://icalendar.org/iCalendar-RFC-5545/3-3-10-recurrence-rule.html
  Doesn't handle repeat by RDATE at all.
  See: https://icalendar.org/iCalendar-RFC-5545/3-8-5-2-recurrence-date-times.html

* Editing exception dates not very clean. E.g. can add "exceptions"
  that are not part of the repeat run, and they are saved without
  problem, and not highlighted in UI as problematic in any way;
  dates can be added that are not visible because box doesn't scroll
  to newly added date; events can be made invisible (thus uneditable)
  by making all occurrences exceptions; keyboard navigation in menu
  is not intuitive.

* When editing repeated entries, what is the best behaviour if, for
  example, the 5th occurrence is an exception (or is cancelled, or
  the time for that one repeat is different) and the start date is
  changed. Should the exception be moved? How should this be communicated
  to the user?

* Multi-day events (i.e. ones that span multiple days) only displayed
  on first day. (In progress - started on Week View.) (Future: config
  option "next_day_crossover" to determine if an entry crosses over.)

* Cutting repeating events is not implemented. (Not sure how to do UI -
  probably need to bring up a dialog "Cut just this occurrence, or all
  repeats?". That then raises question about behaviour when copying
  repeating events, where currently just one occurrence is copied. See
  also deleting repeated events - currently all repeats are deleted.)

* Creating/updating new entries in large calendars is unusably slow.
  (In tests, with iCal file, file writing is slow; with CalDAV server
  re-sorting the lists is slow.)

* "Find" function is rudimentary/placeholder (no options, just searches
  for full string, only searches in the Summary, can't jump to entries
  from results, not progressive, order of results is not useful, ...)

Medium
------
* Support for multiple calendar sources is basic. To add: styling,
  set default calendar.

* Import functionality is work-in-progress (can't specify todo list,
  can't replace existing entries, needs better error messages when
  file could not be parsed, filechooser dialog isn't good on mobile,
  how should alarms be handled?, a progress indicator when there are
  multiple entries would be nice, more keyboard shortcuts).

* How do we share events? Do we need an "Export" function?

* How to handle setting the status of a repeating event? (E.g., a
  reasonable use-case would be to cancel just one occurrence of a
  repeating event. Need to use RECURRENCE-ID in icalendar, see
  https://icalendar.org/iCalendar-RFC-5545/3-8-4-4-recurrence-id.html)

* Need InfoPrints (a.k.a. toast notifications) for some situations

* Todo items cannot be shown in Week or Year views

* Todo due-dates display improvements: date without year; date with day;
  date like "tomorrow", "today", "2 days", "yesterday!"; don't show if
  completed/cancelled; formatting for today/overdue items.

* A natural way to organise todo lists is to have a dedicated calendar
  source for each todo list. There is currently no support for this
  (except manually placing items in each calendar).

* When deleting a repeated event, all are deleted. Should offer option
  of deleting this one (better, also offer delete all from, all before...)

* No goto next/previous entry (for those without endless appointments)

* No time-zone support (should at least be part of time widget)
  (Options: "Travels with me" (default), zone xxx (list local first))

* No GUI for configuration settings/preferences

* More translations are needed - only French, English & Dutch so far.
  (And the French needs checking by a native speaker.)

* Setting number of days for "all day" events could be friendlier
  (e.g. show/set end date)

* Timed events can't last more than 24 hours (need to augment duration widget)

* No support for encryption/password protected entries

* Currently, if using CalDAV server & the connection fails (e.g. server
  halted), Pygenda just exits. Unclear what the best course is. To review
  later. (In "delete event" scenario, an error message & event remains
  probably good behaviour.)

* Ctrl+z does not work to undo in text entry fields. (Surprisingly, GTK3
  does not take care of this. Need to wait for GTK4? Port to QT??)

* An undo/redo function would be useful

* Softkeys should be user-customisable

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
  in year, entries with timezones - see messages on the console).
  Several options to speed this up: custom iterators, or add
  "shortcuts" (e.g. if repeat is on Wednesdays, but retrieving events
  for a Sunday, check early to skip most of the calculations).
  Currently uses dateutil.rrule to calculate most complex repeats,
  see: https://dateutil.readthedocs.io/en/stable/rrule.html
  Check if using recurring-ical-events module could improve speed??
  See: https://pypi.org/project/recurring-ical-events/

* Startup is slow on Gemini. Possible optimisation: run independent
  tasks asynchronously.

* If calendar data is updated externally while Pygenda is runing (e.g.
  another instance of Pygenda, or some other app, updates database)
  the changes are not detected/displayed.

* In Event dialog, repeats until/occurrences. Until date can be wrong if
  occurrences very high; occurrences can be wrong if date in far future.

* "Today" marked in views is not updated if day changes (e.g. midnight
  crossover, switch on device in new day, device time(zone) changed).

* It would be better if the device was detected automatically at launch
  and the appropriate CSS loaded, rather than the user having to setup
  a user CSS to import the appropriate device CSS. (Before doing this,
  we should test on, and have CSS for, more than two platforms.)

* It's sometimes easy to accidentally cancel edits to an entry. One
  possible factor is that up/down navigation in the dialog by default
  takes the focus to the Cancel button. Maybe add a "Discard changes?"
  dialog if changes have been made and editing is cancelled.

* On the Gemini, touchscreen taps in Week View in the left pane get the
  wrong x-coordinate. The result of this is that individual entries are
  not correctly selected if taps are to the left of the space. This
  seems to be a bug in GTK, and does not happen with GTK3.24 (desktop).
  Added: The same bug occurs on postmarketOS, and that uses GTK3.24.
  Maybe it's connected with the touchscreen?

* There's no portrait mode. This would be particularly useful on "transformer"
  phones like the Astro Slide.

* If a single instance of Pygenda opens one iCal file twice (e.g. once for
  events, once for todos) there is potential for data loss when saving.
  (This can also happen if different programs open the same iCal file.)
  Not sure about the best way to handle this situation. Might be solved
  if Pygenda can detect changes in the file and re-read it.

Minor
-----
(Note: minor bugs can still be irritating!)

* If editable calendars only accept todo items, then trying to import an
  event gives internal errors. (Probably similar importing a todo when
  only events are accepted.)

* If editable calendars only accept todo items then "New entry" softkey
  is disabled - even in Todo View.

* After creating/editing a repeating event, cursor not always on that event

* Todo View navigation refinements: left/right can sometimes make the cursor
  move to an unexpected entry (need to find a better algorithm); if there
  is a border/margin/padding, up/down navigation not obviously at start/end.

* Would be nice to be able to edit dates with a calendar interface
  (Like pressing tab in S5)

* Ctrl+Left-Shift+X/C/V/N don't work on Gemini (UI eats keypress?)
  Workaround: Use Right-Shift.

* Anniversary event year (e.g. "20 years") not displayed (they're
  just annual repeats). (Maybe add category "Anniversary"?)
  (Symbian seem to have used X-EPOCAGENDAENTRYTYPE:ANNIVERSARY)

* Event dialog needs some indication if tab contents are non-default
  (e.g. if there are repeats, alarms - maybe show a tick in the tab handle)

* No user feedback for some actions (e.g. copy entry). Should flash or
  recolour cursor or something.

* Menu shortcuts set in .ui files are not translated (e.g. aller à = ctrl+g)

* If using a iCal file and multiple instances edit the same file, data
  can be lost (note: using iCal file is not recommended => minor)

* In comboboxes, when in "popped out" state, +/-/</> keys don't work

* In the Entry Properties dialog, some properties are missing (attendees),
  and dates aren't localised

* In untranslated languages, there can be some awkward mixing of languages
  of fixed and generated content (e.g. "2. to last Sonntag of month")

* Newline behaviour in the Notes field in Event and Todo dialogs is not
  user-friendly. Possible improvements: display a note in the field when it
  is empty; a config option to swap with/without-modifier behaviours.

* There are accelerators to go to Time/Repeats/Alarm... subtabs for Event
  editing. The same should exist for Todo editing.

* In code, various places marked with '!!' indicating known bugs or
  temporary/placeholder implementations.

Cosmetic
--------
* If the first event edited after starting Pygenda has multiple exception
  dates, then it makes room for these in the Event dialog Repeats tab.
  This means that the Event dialog is made wide, and stays that way
  until Pygenda is restarted.

* In Event dialog, "Repeat on" combobox can change width when date is
  changed (due to expanding to contain longer strings - it stops once
  maximum width has been reached).

* Year View: Pixel missing in grid lines at top-left corner

* If Todo View is initial view, the vertical separator is not shown until
  there is a redraw.

* On Gemini, shows "no access" icons in instead of "minus" icons (e.g. in
  spin buttons of Event dialog) - Gemian bug?

* Year view is slow to redraw on Gemini, so get black rectangles when
  e.g. closing dialogs.

* Startup spinner is a bit glitchy (visible for large calendars).

* In Event dialog, Repeats tab, "Repeat until" label doesn't seem to align
  quite correctly with the field content.

* In Event and Todo dialogs, in Notes field, the scrollbar does not go to
  the border: there is a 1-pixel gap.

* When using EDS calendars, there are error messages like: `e-data-server-CRITICAL: client_set_source: assertion 'E_IS_SOURCE (source)' failed`.

Testing
-------
* Need to test with corrupt iCal files. (Including when files become
  corrupt while the program is running.) Use a fuzzer?
  ? https://pypi.org/project/pythonfuzz/

* Need more complete checking from type annotations, so `mypy .` gives
  useful results.
