Pygenda EDS use & configuration
===============================

Data storage
------------
Agenda data can be stored as an iCal file, or via a CalDAV server or an
Evolution Data Server (EDS). An iCal file is good for testing, but has
a number of downsides (possible data loss if multiple programs try to
write to the file, slowdown updating large agendas). A server is
recommended.

This document describes how to set up Pygenda to use an EDS.

Note: EDS access from Pygenda does not work in Gemian (Gemini PDA)
because Debian Stretch does not include ECal object introspection
(package gir*-ecal-*). A possible workaround (e.g. to get alarms
activated through EDS) is to use a CalDAV backend for Pygenda,
and add a calendar source to EDS that uses that CalDAV calendar
as its backend.

Installing EDS
--------------
Use your package manager to install the following:

* Evolution Data Server
* GObject introspection for the EDataServer
* GObject introspection for the ECal

The latter two may be installed as part of Evolution Data Server
(e.g. on Alpine/postmarketOS), or not (e.g. on Debian, where the
packages are `gir1.2-edataserver-1.2` and `gir1.2-ecal-2.0`
respectively).

The default EDS configuration will probably be fine (using "system"
calendar and task list). See below if you want to add other calendar
sources.

Configuring Pygenda to use the EDS
----------------------------------
Edit/create your `~/.config/pygenda/user.ini` file. For the default
"Personal" calendar and task list, add the following:

    [calendar]
    type = evolution
    entry_type = event
    uid = system-calendar
    
    [calendar1]
    type = evolution
    entry_type = todo
    uid = system-task-list

If you use different calendars or task lists from the defaults, you
will need to provide the uid. If you don't know the uid, omit it in
the config, and start Pygenda from the command-line. A list of uids
will be shown in the terminal.

You can optionally add a `display_name = SOME_NAME` line to either
calendar if you want to override the name provided by EDS.

You can add further calendars to Pygenda, these should be placed in
sections titled `calendar2`, `calendar3`, etc. Example:

    [calendar2]
    # Holiday list downloaded from https://....
    type = icalfile
    display_name = Holidays
    filename = ~/.config/pygenda/holidays_UK.ics
    entry_type = event
    readonly = True

Error messages
--------------
If you run Pygenda from the command line, for each EDS source you will
see an error message like:
`e-data-server-CRITICAL **: ...: client_set_source: assertion 'E_IS_SOURCE (source)' failed`.
These sound serious, but seem to be harmless. I've not found a way to
get rid of them.

Adding calendar sources
-----------------------
If you want to add a new calendar source to EDS, create a file called
`~/.config/evolution/sources/MY_DESIRED_UID.source` containing something
like:

    [Data Source]
    DisplayName=MY_DISPLAY_NAME
    Enabled=true
    Parent=local-stub
    
    [Calendar]
    BackendName=local
    Selected=true
    
    [Task List]
    BackendName=local
    Selected=true
    
    [Alarms]
    IncludeMe=true
    
    [Conflict Search]
    IncludeMe=true

If you wish, you can include only one of the `Calendar` and `Task List`
sections, or you can split them into two different .source files (each
will have a uid corresponding to its filename).

To add a CalDAV source, the procedure is similar, with the contents of
the .source file something like:

    [Data Source]
    DisplayName=MY_DISPLAY_NAME
    Enabled=true
    Parent=caldav-stub
    
    [Offline]
    StaySynchronized=true
    
    [WebDAV Backend]
    AvoidIfmatch=false
    CalendarAutoSchedule=false
    DisplayName=MY_CALDAV_DISPLAY_NAME
    ResourcePath=/PATH_ON_SERVER/WITHOUT_DOMAIN_NAME/
    
    [Calendar]
    BackendName=caldav
    Selected=true
    
    [Task List]
    BackendName=caldav
    Selected=true
    
    [Security]
    Method=none
    
    [Refresh]
    Enabled=true
    IntervalMinutes=30
    
    [Authentication]
    Host=HOSTNAME_OF_SERVER (maybe localhost)
    Method=plain/password
    Port=PORT_OF_SERVER
    ProxyUid=system-proxy
    User=USER_ID_ON_CALDAV_SERVER
    
    [Alarms]
    IncludeMe=true
    
    [Conflict Search]
    IncludeMe=true

Where is the data stored?
-------------------------
It might be useful to know where your calendar data is being stored
(e.g. to back it up). On Linux it lives in `~/.local/share/evolution/calendar/`
and `~/.local/share/evolution/tasks/`.
