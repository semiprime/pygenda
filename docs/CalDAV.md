Pygenda CalDAV use & configuration
==================================

Data storage
------------
Agenda data can be stored as an ICS file or via a CalDAV server. An
ICS file is good for testing, but has a number of downsides (possible
data loss if multiple programs try to write to the file, slowdown
updating large agendas). A CalDAV server is recommended.

This document describes how to set up Pygenda to use a CalDAV server.

(I've only tried with a local server - a remote server should
theoretically work, but it might be more practical to periodically
sync a local server to the remote and access the local).

Extra dependencies if using CalDAV server
-----------------------------------------
Python3 modules: caldav

    pip3 install caldav # [there's probably an apt equivalent to this]

Note: The Python caldav module has dependencies outside Python: libxml2
& libxslt development. To install these on Debian/Gemian:

    sudo apt install libxml2-dev libxslt-dev

Note 2: Installing caldav with pip3 on a Gemini takes a long time
(around ten minutes). In particular, I thought it had frozen when
running setup.py for lxml.

Using the Radicale CalDAV server
--------------------------------
You probably also want to install a CalDAV server. I tested using the
Radicale CalDAV server (v3.0.6). https://radicale.org/
(Radicale is written in Python, so it fits the ongoing "Python" theme.)

Install:

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
Autostart, and add the command "`python3 -m radicale`".

Configuring Pygenda to use the local Radicale server
----------------------------------------------------
Edit/create your `~/.config/pygenda/pygenda.ini` file. Edit/add:

    [calendar]
    caldav_server=http://localhost:5232/
    caldav_username=CALDAV_USERNAME
    # Optional:
    caldav_password=PASSWORD # Plaintext, so don't reuse your bank password...
    caldav_calendar=CALENDAR_NAME # Not needed if there's only one calendar

It should be clear how to adjust these configuration options if you use
a different CalDAV server.

Synchronising devices
---------------------
Using a server probably makes it easier to synchronise across devices.
This is still something to investigate. Depending on your configuration,
maybe try rsync, git, syncEvolution, Outlook CalDav Synchronizer,
vdirsyncer.
