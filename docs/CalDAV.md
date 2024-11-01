Pygenda CalDAV use & configuration
==================================

Data storage
------------
Agenda data can be stored as an iCal file, or via a CalDAV server or an
Evolution Data Server (EDS). An iCal file is good for testing, but has
a number of downsides (possible data loss if multiple programs try to
write to the file, slowdown updating large agendas). A server is
recommended.

In general, [EDS](Evolution_Data_Server.md) should be preferred over
CalDAV, because EDS supports activating alarms. However, especially
for older operating systems, some users may prefer CalDAV.

This document describes how to set up Pygenda to use a CalDAV server.

(I've only tried with a local server - a remote server should
theoretically work, but it might be more practical to periodically
sync a local server to the remote and access the local).

Extra Pygenda dependencies for connecting to a CalDAV server
------------------------------------------------------------
Python3 modules: caldav

* Install with pip: `pip3 install caldav`
* Install with apt: `apt install python3-caldav`

Note 1: On Gemian on the Gemini PDA and Cosmo Communicator, new
versions of the caldav module don't work. Suggested ways to
install older versions are in the respective quickstart guides:
[Gemini](quickstart-geminipda.md), [Cosmo](quickstart-cosmocommunicator.md).

Note 2: The Python caldav module has dependencies outside Python:
libxml2 & libxslt development. If you install caldav with pip, you
might also need to install these libraries. On Debian:

    sudo apt install libxml2-dev libxslt-dev

Using the Radicale CalDAV server
--------------------------------
You probably also want to install a CalDAV server. I tested using the
Radicale CalDAV server (v3.0.6). (It seemed lightweight, simple to
setup, and to still be maintained.)

Radicale has good documentation on its website: https://radicale.org/

If you already have a CalDAV server, you can skip to the next section.

If you're using a distro that includes a package for Radicale v3 (e.g.
Debian Bullseye or later), then the best thing is probably to install
that package and follow your distro's config instructions. You'll
want Radicale to launch on startup/login.

If you're using a distro that doesn't package Radicale v3, it can be
installed with pip. See the Gemini and Cosmo quickstart guides for
hints about install/configuration on old operating systems.

With Radicale running, open its web interface: http://localhost:5232/

Login with your username of choice - remember the username for Pygenda
setup, below. (Note, by default the password is ignored. However your
distribution may have configured it to be used.)

Create one or more agendas (or import an existing one, or sync with a
remote one). Note their names, and choose type "calendar and tasks".

Configuring Pygenda to use the local Radicale (or another) server
-----------------------------------------------------------------
Edit/create your `~/.config/pygenda/user.ini` file. Edit/add:

    [calendar]
    type = caldav
    server = http://localhost:5232/
    username = CALDAV_USERNAME
    # Possibly optional:
    password = PASSWORD # Plaintext, so don't reuse your bank password...
    calendar = CALENDAR_NAME # Not needed if there's only one calendar
    # Optional:
    display_name = Personal # The name to display in the Pygenda UI
    entry_type = One of "event", "todo", "all"
    readonly = True/False

It should be clear how to adjust these configuration options if you use
a different CalDAV server.

Note that for Radicale (maybe other servers too) a password is
required, even when it is ignored.

If you would like to add further calendars (i.e. sources/stores for
calendar data), these can be placed in sections titled `calendar1`,
`calendar2`, etc. Example:

    [calendar1]
    type = caldav
    enabled = True
    display_name = Work
    server = http://localhost:5232/
    username = skroob
    password = 12345 # I have the same combination on my luggage
    calendar = Work
    
    [calendar2]
    # Holiday list downloaded from https://....
    type = icalfile
    display_name = Holidays
    filename = ~/.config/pygenda/holidays_UK.ics
    readonly = True
    entry_type = event

Synchronising devices
---------------------
Using a server probably makes it easier to synchronise across devices.
This is still something I'm investigating. Depending on your
configuration and needs, maybe try rsync, git, syncEvolution, Outlook
CalDav Synchronizer, vdirsyncer.
