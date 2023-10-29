Pygenda "Quick Start" Guide for PostmarketOS
============================================
This guide will lead you through installation and basic configuration
of the most recent release of Pygenda on PostmarketOS (a Linux-based
operating system for mobile devices such as phones). It is intended
for users who want to install/run/test Pygenda.

If you want to contribute to or modify Pygenda, then you probably want
to get the latest version from GitHub (which is usually a little ahead
of the latest release). This guide may be useful to refer to for
initial configuration.

Pygenda is designed for devices with a physical keyboard (e.g. a Gemini PDA,
a Nokia N900, a Chromebook, or a PinePhone with its keyboard attachment).
It will likely not be very usable on devices with a virtual keyboard.
Unfortunately, I've not been able to test Pygenda on a postmarketOS device
with a keyboard, so would welcome feedback at pygenda@semiprime.com.

Note that Pygenda is alpha software, and as such has **lots of
missing/incomplete features** as well as **bugs**. It is released for
testing and feedback purposes, but you may also find it useful.

This guide has been tested on a Wileyfox Swift ('crackling') device
running PostmarketOS 23.06 with Phosh 0.30.0 (pre-built postmarketOS
image, id 20230912-0014, with python3-3.11.5-r0 and gtk+3.0-3.24.38-r1).

Known issues
------------
I've only recently started testing on postmarketOS, so it's not yet at
parity with other platforms. Also, postmarketOS and the Phosh UI are
both under development, so bugs are expected.

In addition, the main targets for Pygenda are devices with a physical
keyboard and a landscape display. Hence certain elements of the UI do
not work well in portrait mode or with a touchscreen keyboard.

Known issues specific to postmarketOS (with Phosh) include:

* Translations are not loaded for strings in .glade files (i.e. most of the UI)
* The menu behaves badly (and inconsistently) when using the touchscreen: submenus often do not appear
* Sometimes the UI stops responding to taps (I'm not sure when this occurs)

Install dependencies
--------------------
The following commands install dependencies for Pygenda. Note that you
will need to be connected to the Internet, since these download packages.

Enter the following commands in a command prompt (requires password):

    sudo apk update
    sudo apk add python3
    sudo apk add py3-pip
    sudo apk add gtk+3.0
    sudo apk add py3-gobject3 py3-cairo py3-icalendar py3-dateutil py3-tzlocal py3-num2words

(Note: I'm using the apk versions of the Python3 module dependencies here.
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

Pygenda should start. The UI size may not be what you want – it might
be smaller than the screen or it might overflow the screen – but this
can be changed (see the next section). For now we're just checking
that it starts.

Configuration
-------------
Enter the following to edit the Pygenda ini file:

    mkdir -p ~/.config/pygenda/
    nano ~/.config/pygenda/user.ini

(You can use vi or emacs or a text editor other than nano if you want.)

This should open an empty file. You have some choice about what to
enter here, depending on your preferences. Here's a reasonable basic
configuration that you can select from or modify as required:

    [global]
    24hr = True
    hide_titlebar_when_maximized = True
    
    [startup]
    # Fullscreen UIs are often preferable on handheld devices.
    # The fullscreen and maximised are two possible options for this.
    # Their behaviour might differ depending on the UI of the device.
    fullscreen = True
    # maximize = True
    
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

Style sheet/CSS (fixing a UI that's too large)
----------------------------------------------
Depending on your device and app scaling settings, you may find the
size of the UI, font sizes or scroll-bar widths are not appropriate.
These can be customised with a `~/.config/pygenda/pygenda.css` file.

In particular, if the Pygenda UI is larger than the screen, try adding
a CSS file as follows:

    nano ~/.config/pygenda/pygenda.css

This should open an empty file, where you can add the following

    .view, #view_loading {
        min-width:400px;
        min-height:200px;
    }
    
    /* The following two options reduce the width of the Year View */
    .yearview_day_label, .yearview_month_label {
        font-size:10.5pt;
    }
    
    .yearview_daycell {
        font-size:7pt;
    }
    
    /* To reduce the width of individual to-do lists */
    .todoview_list {
        min-width:270px;
    }

You may want to adjust the exact values, depending on your taste and
device.

Much of the UI can be customised using the user CSS file (colours, fonts,
etc.). See the example [gemini.css](../pygenda/css/gemini.css) for a
practical example of adjusting the UI for a (different) handheld device.

Add a Pygenda icon to the menu
------------------------------
If you have installed Pygenda "locally" (in your user directory), as
described above, you can create a soft link to the pygenda.desktop file
from the user's ~/.local/share/applications directory:

    cd ~/.local/share/applications
    ln -s ~/.local/lib/python3.11/site-packages/pygenda/app/pygenda.desktop

Evolution Data Server
---------------------
The default setting stores calendar data in a file. This is OK for
testing and requires no setup. However, for real use you should store
the data in a server. An Evolution Data Server (EDS) is the natural
choice on PostmarketOS.

Another option: you can store data in a CalDAV server. This is probably
not advisable unless you have a specific requirement. If you are using
a remote CalDAV server, it would be better to set that up as a backend
for EDS.

First, install EDS (it is installed by default, but best to check):

    sudo apk add evolution-data-server

Then add the following to your `~/.config/pygenda/user.ini` file:

    [calendar]
    display_name = Personal
    type = evolution
    entry_type = event
    uid = system-calendar
    
    [calendar1]
    display_name = Todos
    type = evolution
    entry_type = todo
    uid = system-task-list

(The above example uses the default system calendar and task-list.
If you use different ones, provide their uids in place of the values
used above.)

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

    pip3 install --user pygenda==0.2.9

(Change 0.2.9 to your desired version.)
