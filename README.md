Pygenda
=======
Pygenda is a calendar/agenda application written in Python3/GTK3 and
designed for "PDA" devices such as Planet Computers' Gemini. The user
interface is inspired by the Agenda programs on the Psion Series 3 and
Series 5 range of PDAs.

**WARNING: This is in-development code, released for testing/feedback and
as a preview for developers. The software is provided as-is, with no
guarantees. You should back up any files or data used by Pygenda (e.g. iCal
files or data stored on calendar servers).**

There are currently **lots of missing/incomplete features** as well as
**bugs**. For a list of known issues, see: [known_issues.md](docs/known_issues.md).
If you find any new bugs, please send them to pygenda@semiprime.com,
or raise them as issues on GitHub.

*However*, it currently has Week, Year and Todo Views that are functional
enough that the author is now using Pygenda as his main agenda, so
maybe other people will also find it useful. Feedback is welcome at
pygenda@semiprime.com – suggestions, questions about how to get something
working, or just to say that you tried it out.

Video and screenshots
---------------------
Video: https://www.youtube.com/watch?v=uvQqFmlZ6nM (v0.2.7, April 2023)

Screenshots from a PC running Xfce and rescaled – your results may vary.

Week View:

![Screenshot – Week View](docs/screenshots/week_view.png?raw=true)

Year View:

![Screenshot – Year View](docs/screenshots/year_view.png?raw=true)

Todo View:

![Screenshot – Todo View](docs/screenshots/todo_view.png?raw=true)

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
The simplest way to get started is to follow one of the following "quick start"
guides (only a few devices, so far):

* [**Gemini PDA**](docs/quickstart-geminipda.md) (possibly the **Cosmo Communicator** too, but I don't have one to test)
* [**PostmarketOS**](docs/quickstart-postmarketOS.md)

The sections below are for those running from source (e.g. from a
GitHub clone), or who want to know more technical details.

Dependencies
------------
Python3. Version >=3.5 (because Gemini's "Gemian" Linux provides Python 3.5).

* Install on Debian: `sudo apt install python3 python3-pip`

GTK+3 library:

* Install on Debian: `sudo apt install libgtk+3`

If you are running a recent version of pip then the required Python
modules should be installed automatically, so you can skip to the next
section. If you want to check by hand, the required modules are:
PyGObject3 (for gi), pycairo, icalendar, python-dateutil, tzlocal, num2words.

* Install on Debian: `sudo apt install python3-gi python3-cairo python3-icalendar python3-dateutil python3-tzlocal python3-num2words`
* Or install them using pip3: `pip3 install [--user] pygobject pycairo icalendar python-dateutil tzlocal num2words`

Note: On Gemian on the Gemini, with Python3.5, pip3 installed tzlocal
version 2.x, which did not work, giving errors like "No such file or
directory: 'getprop'" at startup. You may therefore like to specify
another version of tzlocal (v1.5.1 should work).

That should be enough for basic usage of pygenda, but if you want to
use a CalDAV server (recommended for real use) there are some extra
dependencies. See setup details in: [CalDAV.md](docs/CalDAV.md)

Launching Pygenda
-----------------
If you have installed the dependencies by hand then you can run
Pygenda directly from the root directory of the project (containing
this readme), with the command:

	python3 -m pygenda

Better/recommended: install the Python module with (for example)...

	./setup.py install --user

(You can uninstall the module with `pip3 uninstall pygenda`.)

NOTE: Gemian on the Gemini PDA doesn't install the Python module
dependencies. To get it to do this, either update pip (see the
[Gemini quickstart](docs/quickstart-geminipda.md)) or install
the dependencies by hand (see "Dependencies" above).

Now you can now run Pygenda from anywhere with:

	python3 -m pygenda

There are a few command-line options, which you can view using:

	python3 -m pygenda --help

For more complete settings, see "Configuration", below.

Configuration
-------------
Configuration settings go in file: `~/.config/pygenda/pygenda.ini`

Custom CSS goes in: `~/.config/pygenda/pygenda.css`

More information: [docs/config-examples/README.md](docs/config-examples/README.md)

Quick config on Gemini/other handhelds
--------------------------------------
If you're running Pygenda on a Gemini or similar PDA, the default font
sizes will probably not be appropriate for the screen size. To fix
this, use the custom CSS provided in pygenda/css/gemini.css.
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
A sample `pygenda.desktop` file is provided in pygenda/app/.
This should help adding launch icons to the desktop menu/panels etc.
For information about how to add a launcher to your desktop menu
or add a panel launcher in LXQt, see the [Gemini quickstart guide](docs/quickstart-geminipda.md).

Usage
-----
See: [Usage.md](docs/Usage.md)

Calendar data storage – a CalDAV server is recommended
------------------------------------------------------
Calendar data can be stored as an ICS file, or via a CalDAV server.
The ICS file is the default, because it works without configuration,
but a CalDAV server is recommended for real use.

For CalDAV configuration, see: [CalDAV.md](docs/CalDAV.md)

The default ICS file is created in `~/.config/pygenda/pygenda.ics`
but you can change this from the command line or config file.

Contributing
------------
See: [Contributing.md](docs/Contributing.md)

Alternatives
------------
If you want to compare the "competition", the Gemian people also have
an in-development agenda-like app designed for the Gemini/Cosmo.
Details at https://gemian.thinkglobally.org/#Calendar
