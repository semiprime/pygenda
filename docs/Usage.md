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

* The Escape key toggles between the most recent two views.

* In Week and Year views, the space key toggles between Today and
  wherever the cursor was last.

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

* Setting alarms is currently under development and testing is welcome.
  (Note: sounding/displaying/sending alarms will be the job of a
  different program - an alarm server. Pygenda does not, and will not,
  activate the alarms. There is a warning in the UI about this because
  it's important that you understand that you need to do some setup or
  alarms will not be activated. You can get rid of the warning by
  changing the appropriate config setting to False.)
  Keys: +/>/-/< - move alarm time of the selected alarm forward/back;
  N - new alarm; Delete - delete selected alarm; A/D/E - change action
  of selected alarm to Audio/Display/Email. For email alarms, you will
  need to set an email address in the config setting new_event/default_alarm_emailaddr.
