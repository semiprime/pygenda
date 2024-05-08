Contributing to Pygenda
=======================
We[^1] welcome contributions, and there are many ways you can help...

[^1]: There's actually only one of "us", but referring to myself as
"I" in documentation felt weird. Besides, I might find someone to work
with, and then I'd need to change all the "I"s to "we"s and "me"s to
"us"es.

Send feedback
-------------
Feedback can be sent to pygenda@semiprime.com, or for bug
reports/feature requests, you can raise an issue on GitHub.

Even a quick note to say you tried it is useful (we want to confirm
that Pygenda runs for other people too). And if you let us know what
device you're running on, that helps give us an idea of what devices
are better tested and what devices we need to consider when making
changes.

If you tried it but couldn't get it to work, please let us know where
you hit problems. Maybe we need to fix something, or improve our
documentation.

If you tried it, but there were some missing features or bugs that
meant it wasn't good for the way you work, let us know. This helps
prioritise what we work on.

Translations
------------
Currently, Pygenda is localised for English (UK & US), French and Dutch.
We'd welcome other languages (or fixes to the existing languages –
the French translation was not done by a native speaker).

The easiest way to create a new translation is to take the most recent
template ([locale/pygenda.pot](../pygenda/locale/pygenda.pot)) and add
the translated strings. You can email the new file to us or make a PR
on GitHub (please check that you agree with the licence – see
[COPYING](../COPYING)).

Other devices
-------------
Currently we test primarily on Linux desktop (Slackware, Xfce) and
Gemian (a Debian port) on Gemini PDA. It would be useful to hear from
people testing on other platforms.

If you do run on another platform, then you probably need to provide a
custom CSS file (to specify font sizes etc). Please consider contributing
a copy to help other users.

You may also need to compile the clipboard code (to be able to cut/copy)
entries. Any build or compatibility fixes for this would be welcome
(including additions to the documentation).

Testing
-------
Testing is time consuming, so help here is welcome. Some specific
suggestions:

* Test with different CalDAV servers (not just Radicale).

* Test compatibility with other calendar applications (create an event/todo
  in OtherApp, try to edit it in Pygenda, and vice-versa).

* Test synchronisation. E.g. use vdirsyncer to sync to a remote CalDAV
  server. Let us know your config, and if it worked.

New features
------------
Code fixes/additions are welcome. If you need some ideas:

* Add a "Transparent", "Organiser", "Attendees" or "Geo" field to the
  Entry Properties Dialog.

* Add a "URL", "Transparent", "Organiser" or "Attendees" field to the
  Event Dialog (or a field for any other property that you find useful).

* Update the "Today" marker at midnight (or if the date changes).

* Deleting a repeated item: Add the choice to "delete all occurrences"
  or "delete only this occurrence" when the user tries to delete a
  repeating item.

* Allow the user to customise the softkeys.

* Add a custom iterator to speed up calculation of repeated entries
  (choose some type of repeat that currently displays a "Notice:
  Fallback to unoptimised repeat" message in the console).

See [known_issues.md](known_issues.md) for more!

The file [Development.md](Development.md) contains some development hints.

If you contribute a change, please do add your name or pseudonym to
the Contributors section in the About dialog, or let us know your
preferred name and we'll add it. (If you'd rather not be listed,
that's fine too.)

Graphic design
--------------
If you know CSS, you can help improve the graphic design/layout.

We'd also welcome custom icons to improve the visual aspect of the
application (e.g. icons to show events in Year View, an app icon,
icons for the softkeys). Contact us about this first (also, no
AI-generated icons, please).

Documentation
-------------
Doc fixes/additions are welcome too. If you have difficulty following
any instructions, then you may be able to suggest improvements. If you
set something up that is not described in our documentation (e.g.
running Pygenda on Windows), then adding details could help others.
