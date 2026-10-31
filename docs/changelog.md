Changelog
=========
Summary – see git history for full details.

Most recent releases at the top.

v0.3.10
-------
2026-10-25

* When deleting a (non-anniversary) repeating event, there is now a
  dialog to choose to either delete all occurrences or delete the
  selected occurrence.
* Can now create weekly repeats on "work" & "non-work" days. This is
  working towards a more general weekly repeat on arbitrary sets of
  days.
* Added some protection against adding the same calendar multiple
  times (let me know if this breaks any config).
* "New Entry" button activation behaviour fixes for when events and/or
  todos can't be created.
* Doc updates (new screenshots, GenAI non-use, pmOS renamed Nura,
  popout issue workarounds).

v0.3.9
------
2026-06-26

**Note:** Specifying files from the config file has changed. It should
be better, but there might be some changes in the path-resolving
behaviour if you provided an ics filename in there. If your calendar
seems to disappear, or it complains about trying to create one, update
the filename parameter in your Pygenda user.ini config.
(Changed as part of allowing a user CSS filename to be added to the config.)

* Added global/css_file config setting to set user CSS file.
* Import improvements: can import Anniversary entries (if you can find
  anything that exports them), added a counter ("entry n of m"), can
  now import entries without UIDs, displays messages if entries can't
  be imported, can specify todo list when importing todos.
* After creating/editing repeating events, cursor will now move to
  nearest occurrence.
* Bug fix: editing event & changing calendar, cursor stays on event
* Tweaked time/date widget behaviour so when field is full typing
  overwrites.
* Anniversaries in Year View grid now have style class
  yearview_entry_anniversary, so can be styled independently of annual
  repeats.
* Specified ink colour black in calendar example stylesheets for
  better compatibility.
* Reorganised code to sort to-do lists individually (but no way to
  choose sort).
* Removed all mypy errors - can now test new code with `mypy .`

v0.3.8
------
2025-08-30

**Note 1:** There is a new dependency on the Noto Emoji font (for the
anniversary candle icon). Either colour or monochrome versions of the
font will work. If your distro does not provide it, it can be
downloaded from https://fonts.google.com/noto/specimen/Noto+Emoji (the
easiest way to install it is to put the NotoEmoji-VariableFont_wght.ttf
file in the local ~/.fonts directory, although this only applies to
one user).

**Note 2:** There has been some re-organisation of CSS styling. If you
provide your own CSS file then you may need to make some changes.

* Reorganised classes for styling of entries. This shouldn't make any
  difference unless you provide your own custom styles, which you may
  need to modify.
* Added CSS class for calendar to entries (so users can style
  according to the calendar). For possible use, see new example file
  docs/config-examples/calendar-colours.css.
* Added anniversaries as a type of repeat. Anniversary events display
  the number of years since the first occurrence.
* Source code is now available on Codeberg: https://codeberg.org/semiprime/pygenda

v0.3.7
------
2025-01-05

* Compatibility fix to stop crash on startup with icalendar 6.x.

v0.3.6
------
2025-01-04

* Fixed a crash on the Cosmo Communicator when navigating in Week View.

v0.3.5
------
2024-12-15

* Todo entries with a due date are now shown in Week & Year Views (can
  be disabled with show_todos config settings).
* (Related to above.) Rationalised system for determining which
  internal lists entries should go in. Avoided some unnecessary list
  re-building, which should speed up some operations with large
  calendars.
* Allowed switches (in event & todo dialogs) to be toggled with
  left/right cursor keys.
* Calendars can be disabled by setting enabled=False in user.ini.
* Added show_in_grid option to enable/disable showing entries in Year
  View grid (example use: to hide moon phase calendar from the grid so
  it doesn't look like there's an appointment those days).
* Improved docs on CalDAV, particularly for Gemini & Cosmo.
* Added tools/make_css_yearicons.py script in case it's useful to help
  others customise their Year View icons.

v0.3.4
------
2024-08-25

* Added a quickstart guide and custom CSS for the Cosmo Communicator.
* Fixed two startup bugs if locale/timezone couldn't be set/detected
  (reported on the Cosmo).
* Other quickstart document updates.
* If an event start time is in a different timezone, as well as
  showing the local time it now also displays the event's time in its
  given timezone.

v0.3.3
------
2024-05-26

* Improved the pure Python version of cut/copy/paste behaviour (the
  version using the C library is still better, but trickier to package
  in a friendly way).
* Changed packaging to use setuptools and only distribute pure Python
  wheel on PyPI.

v0.3.2
------
2024-05-16

* Added ability to import events and to-dos from iCal files.
* Added Dutch translations (thanks Heimen Stoffels)
* Fixed multiple bugs associated with events in different timezones
  and daylight-saving time.
* Added more tests.

v0.3.1
------
2023-12-31

* In Evolution Data Server connection, Pygenda now uses the display
  name from the EDS server (can be changed with config).
* Changed "New Event" softkey to "New Entry", this opens either a New
  Event or a New Todo dialog, depending on the current view.
* Added location_max_chars config settings for Week & Year Views -
  useful to stop location information visually crowding out entries.
* Added URL and CATEGORIES to Entry Properties Dialog.
* Fixed bug where timestamps weren't updated if status changed via menu.
* Renamed *.glade -> *.ui.

Experimental/in-progress features:
* Added config setting new_event/default_alarm_audiofile - for those
  who need/want to set the sound for alarms.
* More work on displaying ongoing events in Week View - now shows
  events that started before the week being viewed. Currently doesn't
  work for repeating items that started before the viewed week. Also,
  it might slow down display. Disabled by default (see
  week_view/show_ongoing_event config setting).

v0.3.0
------
2023-10-31

Version bump! Because this release include changes to config settings
and to storage of calendar data. New features, but also possibly new
bugs. Please remember to back up any data that is accessed by Pygenda.

* Added capability to use multiple calendars (i.e. calendar data
  stores) at once - check the docs for the configuration changes. If
  there is more than one calendar that an event/todo can be stored in,
  then a drop-down menu will be shown in the edit dialog to allow the
  user to select a calendar.
* Calendars can be set as read-only (useful, for example, for holidays
  or moon-phase calendars). Read-only calendars are not included in
  the drop-down menus.
* Added ability to access Evolution Data Server (EDS)
  calendars. (Note: not on Gemini/Cosmo PDA due to the lack of Python
  GObject introspection components in Gemian).
* Now reads user.ini config file.

**Note** configuration changes:
* You should use user.ini rather than pygenda.ini for configuration
  (both still work, but pygenda.ini might get overwritten by future
  versions of Pygenda).
* Config settings for calendar sources completely changed (and not
  backward compatible).

v0.2.10
-------
2023-09-28

* Can now set/edit 'Notes' for events and to-do items (corresponding
  to ical 'DESCRIPTION' elements). An envelope icon is shown for
  entries with notes. Ctrl+Enter will display the entry properties,
  including the note.
* Made todo lists sort using Due Date as second key (the first key is
  Priority). (In the future I'd like to allow the user to configure
  the sorting for each list.)
* Added basic swipe navigation to Week and Year Views (so people with
  no keyboard can move around).
* Added a "quick start" guide for PostmarketOS. (Note: Support for
  PostmarketOS has just been added. There are some known issues, and
  more testing is needed.)
* Cosmetic: Added icons to softkeys (can be disabled with config
  setting [softkeys]/show_icons=False).
* Fixed inaccuracy in Year View touchscreen navigation.
* Added accelerator key for showing entry info.

**Note** configuration change: the "startup/softbutton_display" config
  option has been renamed to "softkeys/display"

v0.2.9
------
2023-08-09

* Added UI to set a due date for todo items. The due date is displayed
  (in a basic way) in the Todo View and the Entry Properties dialog.
* Added UI to set yearly repeats of the form "2nd Wednesday in May" or
  "Last Tuesday in August".
* Tweaked left/right keyboard navigation in Week View. Hopefully the
  new behaviour is more intuitive.
* Added a "quick start" guide for installation and basic configuration
  on the Gemini PDA.
* Revised "null entry" detection in todo and event dialogs.

v0.2.8
------
2023-07-07

* Redesigned the Event Dialog UI for monthly repeats (e.g. 2nd Sat in
  month, last day of month, last Friday of month...). This adds a
  **new dependency: num2words** Python module.
* Changed Pygenda module building & distribution (**note: gemini.css
  and pygenda.desktop file have moved**, so if you refer to gemini.css
  in your user CSS then update those references, and f you refer to
  pygenda.desktop from your local or global share/applications/
  directory or from ~/.config/lxqt/panel.conf then those will need
  updating).
* Fixed bug where an invalid RRULE in just one entry prevented startup.
* Fixed bug where DTSTAMP & LASTMODIFIED would not be marked as UTC.
* Fixed slowdown with impossible repeats on 0th or 6th Saturdays of month.
* Added BYDAYPOS to entry properties dialog.
* Added Contributing.md.

v0.2.7
------
2023-04-28

* Added Zoom functionality (and associated config settings) to all
  views.
* Todo View navigation fixes & improvements. In particular, fixed
  keyboard navigation to take account of items of different heights
  and scrollbar positions.
* Marked release as Alpha. (There's no big change associated with this -
  I've been encouraging external testing for several releases, so it has
  essentially been at alpha status for a while).
* Added link to a new video.
* Tidied code (signals).
* Started on showing multi-day events in Week View.
* Removed File New/Open/Save-As menu items - replaced with Import File.

v0.2.6
------
2023-03-16

* Added preliminary support for setting alarms. Note that Pygenda does
  *not* act on (e.g. display, play audio) alarms - a separate alarm
  handler should be used for that. This addition allows us to start
  testing alarms.
* The Escape key now toggles between the two most recent Views.
* Find now also searches in todo entries.
* Added an "Entry Properties" dialog to show details of events/todos.
  This is useful to examine entries/properties that can't be edited.
* Reorganised various sections of code.

v0.2.5
------
2022-12-27

* The 'status' of to-do items can now be set (e.g. cancelled, in-progress).
* Location of events can be displayed in Day & Year Views (see
  show_event_location config setting).
* App menu updated: some reorganisation, plus items are now sensitive
  to cursor entry (e.g. cut/copy/delete menu items are not active when
  cursor is not on an entry).

v0.2.4
------
2022-11-19

* Improvements/fixes to cursor code, e.g. after modifying/creating an
  entry, the cursor moves to that entry (except some tricky cases).
* Todo View now supports clicks/touchscreen taps to jump to entries.
* Added rudimentary "Find" functionality.

v0.2.3
------
2022-08-30

* Todo View: User can set to-do item priority and which list it
  appears in. Lists are sorted by priority. View now scrolls with the
  cursor.
* Added a custom iterator for "by weekday in month" repeats. This will
  help to prevent slowdowns with these repeats.

v0.2.2
------
2022-05-31

* Added initial "Todo View" with basic functionality.

v0.2.1
------
2022-05-10

* Added pygenda.desktop file for Linux desktops.
* Display event times as local time (makes a difference when the event
  has a different timezone). This adds a new dependency: tzlocal
  Python module.
* Added unit tests for repeats. Also fixed assorted bugs in repeat
  calculations.

v0.2.0
------
2022-01-31

First public release! An early preview with just Week & Year views.
Many features still to-do.
