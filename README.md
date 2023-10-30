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

* [**Gemini PDA**](docs/quickstart-geminipda.md) running Gemian (possibly the **Cosmo Communicator** too, but I don't have one to test)
* [**PostmarketOS**](docs/quickstart-postmarketOS.md)
* [**Debian-like systems**](docs/quickstart-debianlike.md) e.g. Raspberry Pi OS (but see above for Gemian)

The sections below are for those running from source (e.g. from a
GitHub clone), or who want to know more technical details.

Dependencies
------------
* Python3. Version >=3.5 (because Gemini's "Gemian" Linux provides Python 3.5).
* GTK+3 library
* Python libraries: PyGObject3 (for gi), pycairo, icalendar, python-dateutil, tzlocal, num2words.

If you want to access a CalDAV server from Pygenda there are some
extra dependencies. See setup details in: [CalDAV.md](docs/CalDAV.md)

If possible, install the Python libraries from the OS repositories.
This should reduce the chance of pip3 installing a version of a
library that is not compatible with other OS components.

Installing
----------
If you have pip installed, this is the simplest way to get the latest
release (best for testing). The "quickstart" guides above can serve
as a guide.

If you want to try the latest development code (best for contributing)
then get the version from GitHub.

Launching Pygenda from Source
-----------------------------
If you have installed the dependencies then you can run Pygenda
directly from the root directory of the project (containing this
readme), with the command:

	python3 -m pygenda

Better/recommended: install the Python module with (for example)...

	./setup.py develop --user

(You can uninstall the module with `pip3 uninstall pygenda`.)

Now you can now run Pygenda from anywhere with:

	python3 -m pygenda

There are a few command-line options, which you can view using:

	python3 -m pygenda --help

For more complete settings, see "Configuration", below.

Configuration
-------------
Configuration settings go in file: `~/.config/pygenda/user.ini`

Custom CSS goes in: `~/.config/pygenda/pygenda.css`

More information: [docs/config-examples/README.md](docs/config-examples/README.md)

Handheld config
---------------
If you're running Pygenda on a handheld device, the default font sizes
etc. will probably not be appropriate for the screen size. These can
be fixed by providing custom CSS. An example for the Gemini PDA is in
`pygenda/css/gemini.css`. It it works as provided, then it can be
imported into your `~/.config/pygenda/pygenda.css` file by adding the
line:

	@import "PATH_TO_GEMINI_CSS_FILE";

The "startup/maximized" and "startup/fullscreen" options are also
useful for devices with small screens.

Desktop/panel/menu launchers
----------------------------
A sample `pygenda.desktop` file is provided in pygenda/app/. This
should help adding launch icons to the desktop menu/panels etc.
For example, to add it to your menu, create a softlink from
`~/.local/share/applications/`.

Usage
-----
See: [Usage.md](docs/Usage.md)

Calendar data storage – a server is recommended
-----------------------------------------------
Calendar data can be stored as an iCal file, or via a CalDAV server,
or via an Evolution Data Server (EDS). An iCal file is the default,
because it works without configuration, but a server is recommended
for real use. Using EDS is simpler than a CalDAV server and will
probably be the preferred way going forward. However, it is new and
less well tested than using CalDAV, so it might be more buggy.

* CalDAV configuration: [CalDAV.md](docs/CalDAV.md)
* EDS configuration: [Evolution_Data_Server.md](docs/Evolution_Data_Server.md)

The default iCal file is created in `~/.config/pygenda/pygenda.ics`
but you can change this from the command line or config file.

Contributing
------------
See: [Contributing.md](docs/Contributing.md)

Alternatives
------------
If you want to compare the "competition", the Gemian people also have
an in-development agenda-like app designed for the Gemini/Cosmo.
Details at https://gemian.thinkglobally.org/#Calendar
