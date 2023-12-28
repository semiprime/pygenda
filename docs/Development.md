Pygenda Development
===================
Miscellaneous hints/notes for development.

Installing in Develop mode
--------------------------
In Python, you can install modules in Develop mode with:

    ./setup.py develop [--user]

Rather than copying the files over, this just creates a link to the
source directory, so any changes you make in the source are instantly
available in the "installed" version.

(Note that if you install in Develop mode, you'll need to build the
clipboard library manually, as in the section below.)

Building clipboard library
--------------------------
This is a small C library required for cutting/copying entries. Built
automatically with `./setup.py install`. Tested on Gemian, postmarketOS
and Slackware, and probably works on other Linux distributions. It might
need tweaking for Windows/MacOS/BSD/other. To build by hand and copy to
the correct location in the source tree:

    cd csrc
    cmake .
    make
    make cp

Build dependencies are: a C compiler, make, CMake (or you could build
by calling your compiler directly), development files for your libc
(e.g. `libc-dev`, or `musl-dev` on postmarketOS) and GTK3 development
files (if these are not already installed, it's probably package
`libgtk-3-dev` or `gtk+3.0-dev` in your package manager).

Translating strings
-------------------
Use the provided pygenda/locale/pygenda.pot file to create/update the
.po for the target language.

Existing languages:

    cd pygenda/locale
    msgmerge -U fr/LC_MESSAGES/pygenda.po pygenda.pot

To add new languages:

    cd pygenda/locale
    msginit -i pygenda.pot -o de/LC_MESSAGES/pygenda.po -l de_DE

Check/edit the generated .po files, maybe adding translations.

Process each .po to generate the .mo:

    cd fr/LC_MESSAGES
    msgfmt pygenda.po -o pygenda.mo

In general, use the locale/pygenda.pot provided (since the automatic
tools don't find all the strings, and you'll need to check/edit/add
things). However, if you have added, removed or changed strings, and
wish to generate a pygenda.pot, in the pygenda subdirectory:

    xgettext --package-name Pygenda --copyright-holder "Matthew Lewis" -k_ -kN_ -o locale/pygenda.pot *.py ui/*.ui

Then compare against the previous pygenda.pot and integrate any
strings that xgettext missed.

Checklist for releases
----------------------
* Check new code is appropriately commented and annotated
* Check any doc changes made (e.g. known issues, config, this checklist)
* Run `mypy .` in source directory, check any new messages
* If any new dependencies are required, add them to setup.py
* Check setup.py install works & the installed module runs correctly
* Create various events & todo items. Close & reopen Pygenda and check
  they are still there (with iCal file, EDS, & CalDAV server).
* Check copy/cut/paste works, including e.g. event date/time, multi-day events,
  event status, with alarms, with notes, todo pasted as event & vice-versa,
  text pasted
* Check readonly calendars work - missing from calendar dropdown, can't edit
  entries, if all readonly then can't create entries
* Regenerate .po and .mo localisation files (see above)
* Check at least one non-English language
* Check any iCal files in validator, e.g. https://icalendar.org/validator.html
* Run test_entries.py, test_repeats.py & test_ongoing.py unit tests
* Check all test files (testxx_*.ics & generated files) display correctly
* Check darkmode & backgrounds CSS still work
* Check mouse clicks/touchscreen taps/swipes work (all views)
* Check start_week_day!=Monday still works (all views)
* Increase version number

Checking repeats
----------------
In addition to test_repeats.py unit tests...
Repeated event display can be checked by hand (plan to automate later) by
enabling checking in repeats_in_range() method (file pygenda_calendar.py)
and skipping through the test02_repeats.ics file. (Try Year View.)

Debugging
---------
* On Gemini:

    sudo apt install libgtk-3-dev
    gsettings set org.gtk.Settings.Debug enable-inspector-keybinding true

  Launch Pygenda & press ctrl+shift+d

* Other Linux (tested on Slackware):

    GTK_DEBUG=interactive python3 -m pygenda

Test setup
----------
Can test setup.py by using a virtual Python environment:

    python3 -m venv venv_dir
    source venv_dir/bin/activate
    cd PYGENDA_SRC_DIR
    ./setup.py install
    # Check no install errors
    cd ~
    # Check pygenda runs with file
    python3 -m pygenda -f test.ics
    # (Optionally install caldav and check pygenda can use it)
    deactivate
    rm -r venv_dir

Logging
-------
To log errors when Pygenda is launched from an icon, change the
.desktop file used to launch Pygenda so that the Exec line reads:

    Exec=bash -c "python3 -m pygenda 2>>FULL_PATH_OF_PYGENDA_LOG_FILE"

You may also want to log errors from whatever server you are using.
For Radicale, edit the .desktop file in ~/.config/autostart/:

    Exec=bash -c "python3 -m radicale 2>>FULL_PATH_OF_RADICALE_LOG_FILE"
