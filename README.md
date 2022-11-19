Pygenda
=======
Pygenda is a calendar/agenda application written in Python3/GTK3 and
designed for "PDA" devices such as Planet Computers' Gemini. The user
interface is inspired by the Agenda programs on the Psion Series 3 and
Series 5 range of PDAs.

**WARNING: This is in-development code, released as a preview for
developers. The software is provided as-is, with no guarantees. You
should back up any data or files used by Pygenda (e.g. iCal files
or data stored on calendar servers).**

There are currently **lots of missing/incomplete features** as well as
**bugs**. For a list of known issues, see: [known_issues.md](docs/known_issues.md).
If you find any new bugs (or have any feature requests), please send
them to: pygenda@semiprime.com.

*However*, it currently has Week, Year and Todo Views that are functional
enough that the author is now using Pygenda as his main agenda, so
maybe other people will also find it useful. Feedback is welcome at
pygenda@semiprime.com - suggestions, questions about how to get something
working, or just to say that you tried it out.

Video (from March 2021): https://www.youtube.com/watch?v=QjHcgeRudMo

Source code
-----------
Source is available at: https://github.com/semiprime/pygenda

License (GPL3)
--------------
Pygenda is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, version 3.

Pygenda is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with Pygenda (see COPYING file). If not, see <https://www.gnu.org/licenses/>.

Run/install
-----------
(See note about dependencies below.)

To run without installing, cd to the root pygenda directory, and do:

	python3 -m pygenda

Better/recommended: install the Python module with (for example)...

	./setup.py install --user

(You can uninstall the module with `pip3 uninstall pygenda`.)

NOTE: Gemian (Debian port for Gemini PDA) doesn't install the Python module
dependencies. The reason for this appears to be old pip/setuptools on Gemian.
I recommend installing these dependencies manually - see "Dependencies" below.

Then you can now run Pygenda from anywhere with:

	python3 -m pygenda

There are a few command-line options, which you can view using:

	python3 -m pygenda --help

For more complete settings, see "Configuration", below.

Dependencies
------------
Python3. Version >=3.5 (because Gemini's "Gemian" Linux provides Python 3.5).

* Install on Debian/Gemian: `sudo apt install python3`

GTK+3

* Install on Debian: `sudo apt install gtk+3`

Python3 modules: PyGObject3 (for gi), icalendar, python-dateutil, tzlocal

* Install on Debian: `sudo apt install python3-gi python3-icalendar python3-dateutil python3-tzlocal`
* Or install them using pip3: `pip3 install pygobject icalendar python-dateutil tzlocal`

Note: When I tested on Gemian on the Gemini, pip3 installed tzlocal
version 2.1, which did not work (although versions 1 to 4 worked on a
Linux laptop). If you get errors like "No such file or directory:
'getprop'" at startup, try installing a different version of tzlocal
with either apt or pip3 (v1.5.1 should work on Gemian with Python 3.5).

That should be enough to start Pygenda, but if you want to use a
CalDAV server (recommended for real use) there are some extra
dependencies. See setup details in: [CalDAV.md](docs/CalDAV.md)

Configuration
-------------
Configuration settings go in file: `~/.config/pygenda/pygenda.ini`

Custom CSS goes in: `~/.config/pygenda/pygenda.css`

More information: [docs/config-examples/README.md](docs/config-examples/README.md)

Quick config on Gemini/other handhelds
--------------------------------------
If you're running Pygenda on a Gemini or similar PDA, the default font
sizes will probably not be appropriate for the screen size. To fix
this, use the custom CSS provided in docs/config-examples/gemini.css.
The easiest way to do this is to import the gemini.css file from your
own ~/.config/pygenda/pygenda.css file, by adding the line:

	@import "PATH_TO_GEMINI_CSS_FILE";

You can then add your own custom CSS after this. (This way, if you
git pull an update to the Pygenda source, then you'll automatically
get any new css rules included in the new version.)

The "startup/maximized" and "startup/fullscreen" options are also
useful for devices with small screens. See "Configuration" above.

Desktop/panel/menu launchers
----------------------------
A sample `pygenda.desktop` file is provided in docs/config-examples/.
This should help adding launch icons to the desktop menu/panels etc.
For example, to add Pygenda to the desktop menu, copy (or create a
link to) the pygenda.desktop file in the `/usr/share/applications/` or
`~/.local/share/applications/` directory; to add a launcher to the
LXQt panel, edit the `~/.config/lxqt/panel.conf` file and add a line
in the [quicklaunch] section (& restart LXQt).

Usage
-----
See: [Usage.md](docs/Usage.md)

Calendar data storage - a CalDAV server is recommended
------------------------------------------------------
Calendar data can be stored as an ICS file, or via a CalDAV server.
The ICS file is the default, because it works without configuration,
but a CalDAV server is recommended for real use.

For CalDAV configuration, see: [CalDAV.md](docs/CalDAV.md)

The default ICS file is created in `~/.config/pygenda/pygenda.ics`
but you can change this from the command line or config file.

Alternatives
------------
If you want to compare the "competition", the Gemian people also have
an in-development agenda-like app designed for the Gemini/Cosmo.
Details at https://gemian.thinkglobally.org/#Calendar
