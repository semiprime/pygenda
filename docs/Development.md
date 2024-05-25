Pygenda Development
===================
Miscellaneous hints/notes for development.

Installing in Development mode
------------------------------
In Python, you can install modules in Development (Editable) mode with:

    pip3 install --editable . [--user]

Or, for older versions of pip3 (e.g. on Gemini):

    ./setup_old.py develop --user

Rather than copying the application files, this creates a link to the
source directory, so any changes you make in the source are instantly
available in the "installed" version.

Clipboard library
-----------------
This is a small C library to improve cutting/copying behaviour.
Specifically it allows Pygenda entries to be copied+pasted as text
into applications that expect text, and as calendar entries into
applications that expect calendar entries. Tested on Gemian,
postmarketOS and Slackware, and probably works on other Linux
distributions. It might need tweaking for Windows/MacOS/BSD/other.

In order to be as universally compatible as possible, the clipboard
library is not included in the default wheel package. However, you can
build the library yourself, and if you are packaging Pygenda (e.g. for
a specific OS or a Flatpak) it is recommended that you include an
appropriate version of libpygenda_clipboard.so for improved functionality.

To build and copy to the correct location in the source tree:

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
* If any new dependencies are required, add them to pyproject.toml
* Check `python3 -m build` then `pip3 install dist/pygenda-*.whl` works
  and the installed module runs correctly
* Create various events & todo items. Close & reopen Pygenda and check
  they are still there (with iCal file, EDS, & CalDAV server).
* Check copy/cut/paste works, including e.g. event date/time, multi-day events,
  event status, with alarms, with notes, todo pasted as event & vice-versa,
  text pasted
* Check importing events, todos, and repeated events work
* Check readonly calendars work - missing from calendar dropdown, can't edit
  entries, if all readonly then can't create entries
* Regenerate .po and .mo localisation files (see above)
* Check at least one non-English language
* Check any iCal files in validator, e.g. https://icalendar.org/validator.html
* Run test_entries.py, test_repeats.py, test_import_paste.py & test_ongoing.py
  unit tests
* Check all test files (testxx_*.ics & generated files) display correctly
* Check darkmode & backgrounds CSS still work
* Check mouse clicks/touchscreen taps/swipes work (all views)
* Check start_week_day!=Monday still works (all views)
* Increase version number in pygenda_version.py & pyproject.toml

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

Test packaging
--------------
You can test packaging using a virtual Python environment:

    # In root directory of Pygenda source, build a wheel
    python3 -m build
    # Set up and activate the virtual environment
    cd ~
    python3 -m venv venv_dir
    source venv_dir/bin/activate
    # Install the wheel
    cd PYGENDA_SRC_DIR
    pip3 install dist/pygenda-*.whl
    # Check no install errors
    cd ~
    # Check pygenda runs with a file
    python3 -m pygenda -f test.ics
    # (Optionally install caldav and check pygenda can use it)
    # Exit and tidy up
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
