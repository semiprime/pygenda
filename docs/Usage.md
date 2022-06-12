Pygenda usage
=============
Usage is intended to be intuitive, but a few things are worth noting:

* New entries can be created by starting to type a description.

* Pressing Enter on an existing entry edits that entry.

* **Primary navigation** is with the cursor keys (e.g. in Year View, the
  cursor keys move the cursor around the year grid; in dialogs, cursor
  keys move between widgets).
  **Secondary navigation** is with shift+cursor keys (e.g. in Year View,
  shift+up/down moves the second cursor between entries on the same
  day; in dialogs, shift+up/down possibly modifies the widget content,
  maybe by increasing/decreasing the value).

* In addition, date/time fields, spin buttons (GUI elements to enter a
  number), and comboboxes (choose option from dropdown list) can be
  increased with + or >, and decreased with - or <.

* Space toggles between Today and wherever the cursor was last.

* If you want the Tab key to move within elements in date/time/duration
  widgets then set the global/tab_elts_datetime config option to True.

* Pressing y/m/d keys in date widget moves the cursor to year/month/day
  fields respectively. Similarly, pressing h/m keys in time or duration
  widget moves to hour/minute fields. (These shortcut keys are localised,
  for example in French they are a/m/j/h/m.)

* The icons in Year View are configurable via CSS (although it can be
  a bit fiddly). The default CSS shows a star for yearly events, a
  purple circle for other repeating events, and a yellow disc for other
  events.

* Hint: To convert To-dos into Events, or vice-versa, cut & paste them.
