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
clipboard library manually: cd csrc; make; make cp.)

Building clipboard library
--------------------------
This is a small C library required for cutting/copying entries. Built
automatically with `./setup.py install`. Tested on Gemini, but probably
needs fixing for other Linux distributions/Windows/MacOS. To build and
copy to the correct location:

    cd csrc
    make
    make cp

Translating strings
-------------------
Create a locale/pygenda.pot template from .py and .glade source
files. In the pygenda subdirectory:

    xgettext --package-name Pygenda --copyright-holder "Matthew Lewis" -k_ -kN_ -o locale/pygenda.pot *.py *.glade

Use .pot to make .po for each language.

Existing languages:

    cd locale
    msgmerge -U fr/LC_MESSAGES/pygenda.po pygenda.pot

To add new languages:

    cd locale
    msginit -i pygenda.pot -o de/LC_MESSAGES/pygenda.po -l de_DE

Check/edit the generated .po files, maybe adding translations.

Process each .po to make .mo:

    cd fr/LC_MESSAGES
    msgfmt pygenda.po -o pygenda.mo

Checklist for releases
----------------------
* Check new code is appropriately commented and annotated
* Check any doc changes made (e.g. known issues, config, this checklist)
* Run `mypy .` in source directory, check any new messages
* If any new dependencies are required, add them to setup.py
* Check setup.py install works & the installed module runs correctly
* Create various events & todo items. Close & reopen Pygenda and check
  they are still there (with ics file & CalDAV server).
* Check copy/cut/paste works, including e.g. event date/time, multi-day events,
  event status, todo pasted as event & vice-versa, text pasted
* Regenerate .po and .mo localisation files (see above)
* Check at least one non-English language
* Check any ics files in validator, e.g. https://icalendar.org/validator.html
* Run test_repeats.py unit tests.
* Check all test files (testxx_*.ics & generated files) display correctly
* Check darkmode & backgrounds CSS still work
* Check mouse clicks/touchscreen taps work (all views)
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
