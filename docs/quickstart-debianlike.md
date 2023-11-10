Pygenda "Quick Start" Guide for Debian-like distributions
=========================================================
This guide will lead you through installation and basic configuration
of the most recent release of Pygenda on Debian-like Linux distributions
(that is, ones that use apt for package management). It is intended
for users who want to install/run/test Pygenda.

(If you have a Gemini PDA with Gemian installed, see the
[Gemini PDA quickstart](quickstart-geminipda.md).)

If you want to contribute to or modify Pygenda, then you probably want
to get the latest version from GitHub (which is usually a little ahead
of the latest release). This guide may be useful to refer to for
initial configuration.

Note that Pygenda is alpha software, and as such has **lots of
missing/incomplete features** as well as **bugs**. It is released for
testing and feedback purposes, but you may also find it useful.

This guide has been tested on a Raspberry Pi 2 running Raspberry Pi OS
2023-05-03, updated with patches to 2023-10-06 (based on Debian Bullseye,
32-bit), with Python3 3.9.2-3 and libgtk+3 3.24.24-4+rpt12+deb11u3.

Install dependencies
--------------------
The following commands install dependencies for Pygenda. Note that you
will need to be connected to the Internet, since these download packages.

Enter the following commands in the command prompt (requires password):

    sudo apt update
    sudo apt install python3
    sudo apt install python3-pip
    sudo apt install libgtk-3-0
    sudo apt install fonts-dejavu
    sudo apt install python3-gi python3-cairo python3-icalendar python3-dateutil python3-tzlocal python3-num2words

(Note: I'm using the apt versions of the Python3 module dependencies here.
This is for better compatibility (hopefully) with other operating system
components. If you are already using different versions of these modules,
you may want to stick with those versions. Alternatively, you may want to
keep the Pygenda module dependencies separate from the OS modules by
running Pygenda in a Python virtual environment.)

Install Pygenda
---------------
Enter the following command to download and install Pygenda from the
PyPI repository:

    pip3 install --user pygenda

Test Pygenda runs:

    python3 -m pygenda

Pygenda should start in a window. This may not be what you want, but
this can be changed (see the next section). For now we're just
checking that it starts.

Configuration
-------------
Enter the following to edit the Pygenda user.ini file:

    mkdir -p ~/.config/pygenda/
    nano ~/.config/pygenda/user.ini

(You can use vim or emacs or something other than nano if you want.)

This should open an empty file. You have some choice about what to
enter here, depending on your preferences. Here's a reasonable basic
configuration that you can select from or modify as required:

    [global]
    24hr = True
    
    [startup]
    # Fullscreen UIs are often preferable on handheld devices.
    # The fullscreen and maximised are two possible options for this.
    # Their behaviour might differ depending on the UI of the device.
    maximize = True
    fullscreen = False
    
    [todo_view]
    list0_filter = UNCATEGORIZED
    list1_title = Shopping list
    list1_filter = shopping
    # ...and so on for additional todo lists: list2_title, list2_filter etc.
    # listN_title gives the todo list name as displayed in the UI.
    # listN_filter gives the tag to use internally in the icalendar data.

(Lines starting with a `#` are comments, so can be changed or omitted.
For other settings, see [defaults.ini](config-examples/defaults.ini).)

Save the file and exit. (In nano: ctrl+o, confirm filename, ctrl+x.)

Now you can start Pygenda again, and your options should take effect.

Style sheet/CSS (font sizes etc)
--------------------------------
Depending on your device, you may find the font sizes, window size, or
scroll-bar widths are not appropriate. These can be customised with a
`~/.config/pygenda/pygenda.css` file:

    nano ~/.config/pygenda/pygenda.css

Some ideas for a Raspberry Pi desktop:

    /* Make default window slightly larger */
    .view, #view_loading {
        min-width:700px;
        min-height:400px;
    }
    
    /* Smaller font sizes for Year View grid */
    .yearview_day_label, .yearview_month_label {
        font-size:10pt;
    }
    
    .yearview_daycell {
        font-size:7pt;
    }

For more ideas, see [the default pygenda.css](../pygenda/css/pygenda.css).
For an example for a mobile device, see [gemini.css](../pygenda/css/gemini.css).

Add a Pygenda icon to the menu
------------------------------
If you have installed Pygenda "locally" (in your user directory), as
described above, you can create a soft link to the pygenda.desktop file
from the user's ~/.local/share/applications directory:

    cd ~/.local/share/applications
    ln -s ~/.local/lib/python3.9/site-packages/pygenda/app/pygenda.desktop

(If you're using a different version of Python3 then change python3.9
to the appropriate version.)

Calendar server (EDS)
---------------------
If you want to use Pygenda as an agenda, rather than just testing it,
then you should store your data in a server rather than in an iCal
file (which is the default). You can either use an Evolution Data
Server (EDS) or a local CalDAV server. EDS support is new, but offers
advantages such as activating alarms. If you want to use a remote
CalDAV server, then you can set that up as a remote source for the
local EDS server.

Information about using a CalDAV server is here: [CalDAV.md](CalDAV.md)

EDS setup is described below.

First, install EDS and its object introspection packages:

    sudo apt install evolution-data-server
    sudo apt install gir1.2-edataserver-1.2
    sudo apt install gir1.2-ecal-2.0

The default EDS configuration will probably be fine (using "system"
calendar and task list) unless you have set up any other calendars.

Now add the following to your `~/.config/pygenda/user.ini` file:

    [calendar]
    type = evolution
    entry_type = event
    uid = system-calendar
    
    [calendar1]
    type = evolution
    entry_type = todo
    uid = system-task-list

(The above example uses the default "system" calendar and task-list.
If you use different ones, provide their uids in place of the values
used above.)

You can optionally add a `display_name = SOME_NAME` line to either
calendar if you want to override the name provided by EDS.

For more details/options, see [Evolution_Data_Server.md](Evolution_Data_Server.md).

Finally
-------
Please email me at pygenda@semiprime.com to let me know you've tried
Pygenda. I also welcome bug reports, feature requests, bug fixes, and
corrections to the documentation.

Appendix: Updating Pygenda
--------------------------
To update to the latest release of Pygenda, enter the following command:

    pip3 install --user pygenda --upgrade

You can check the latest available version at https://pypi.org/project/pygenda/

To see which version is currently installed, either check the "About"
menu in Pygenda, or run:

    pip3 show pygenda

If an update breaks something, please let us know about the problem at
pygenda@semiprime.com. Then you can go back to an older version using:

    pip3 install --user pygenda==0.3.0

(Change 0.3.0 to your desired version.)
