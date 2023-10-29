Pygenda CalDAV use & configuration
==================================

Data storage
------------
Agenda data can be stored as an iCal file, or via a CalDAV server or an
Evolution Data Server (EDS). An iCal file is good for testing, but has
a number of downsides (possible data loss if multiple programs try to
write to the file, slowdown updating large agendas). A server is
recommended.

This document describes how to set up Pygenda to use a CalDAV server.

(I've only tried with a local server - a remote server should
theoretically work, but it might be more practical to periodically
sync a local server to the remote and access the local).

Extra Pygenda dependencies for connecting to a CalDAV server
------------------------------------------------------------
Python3 modules: caldav

    pip3 install caldav # [or apt install python3-caldav]

Note 1: On the Gemini, new versions of the caldav module don't work,
so you'll need to do:

    pip3 install caldav==0.11.0

Note 2: The Python caldav module has dependencies outside Python: libxml2
& libxslt development. To install these on Debian/Gemian:

    sudo apt install libxml2-dev libxslt-dev

Note 3: Installing caldav with pip3 on a Gemini takes a long time
(around ten minutes). In particular, I thought it had frozen when
running setup.py for lxml.

Using the Radicale CalDAV server
--------------------------------
You probably also want to install a CalDAV server. I tested using the
Radicale CalDAV server (v3.0.6). https://radicale.org/
(Radicale is written in Python, so it fits the ongoing "Python" theme.)

If you already have a CalDAV server, you can skip to the next section.

Install Radicale:

    pip3 install radicale

[I use pip, rather than apt, here because on the Gemini PDA, using apt
gets an older version of Radicale (v1.1.1) while pip gets v3.x. If
you're using a more recent Debian, you might prefer apt.]

Start Radicale:

    python3 -m radicale --storage-filesystem-folder=~/radicale-data

[Change that filesystem path if you want.]

Then go to the web interface in a web browser: http://localhost:5232/

Login with your username of choice - remember the username for Pygenda
setup, below. (Note, by default the password is ignored - see the
Radicale documentation for how to edit your Radicale config to set up
a password at https://radicale.org/).

Create an agenda (or import an existing one, or sync with a remote one).

After configuring Pygenda to use the Radicale server (below), if
you're happy with this setup, you can put your Radicale settings in
`.config/radicale/config` and run radicale on startup. E.g. in LXQt on
the Gemini, go to LXQT Configuration Center -> Session Settings ->
Autostart, and add the command "`python3 -m radicale`" (this will write
a .desktop file in `~/.config/autostart/`).

Configuring Pygenda to use the local Radicale (or another) server
-----------------------------------------------------------------
Edit/create your `~/.config/pygenda/user.ini` file. Edit/add:

    [calendar]
    type = caldav
    server = http://localhost:5232/
    username = CALDAV_USERNAME
    # Optional:
    display_name = Personal # The name you want displayed in the Pygenda UI
    password = PASSWORD # Plaintext, so don't reuse your bank password...
    calendar = CALENDAR_NAME # Not needed if there's only one calendar

It should be clear how to adjust these configuration options if you use
a different CalDAV server.

If you would like to add further calendars (i.e. sources/stores for
calendar data), these can be placed in sections titled `calendar1`,
`calendar2`, etc. Example:

    [calendar1]
    type = caldav
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
This is still something to investigate. Depending on your configuration,
maybe try rsync, git, syncEvolution, Outlook CalDav Synchronizer,
vdirsyncer.
