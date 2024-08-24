Pygenda "Quick Start" Guide for the Cosmo Communicator
======================================================
This guide will lead you through installation and basic configuration
of the most recent release of Pygenda on a Cosmo Communicator running
Gemian Linux.

The guide is intended for users who want to install/run/test Pygenda.
If you want to contribute to or modify Pygenda, then you probably want
to get the latest version from GitHub (which is usually a little ahead
of the latest official release). This guide may be useful to refer to
for dependencies and configuration information.

Note that Pygenda is alpha software, and as such has **lots of
missing/incomplete features** as well as **bugs**. It is released for
testing and feedback purposes, but you may also find it useful.

Preliminaries
-------------
First, check that you have the correct device and operating system for
this guide: the Cosmo Communicator made by Planet Computers. This should
be running Gemian Linux (a version of Debian), *not* Android.

To check your Gemian (Debian) version, open a command prompt on the
Cosmo (either on the device or via ssh) and enter the following command:

    cat /etc/debian_version

It should output one line saying `10.13`.

At the time of writing, version 10.13 is the most recent version. If
you have an older version of Debian, then I suggest you update before
installing Pygenda.

Install dependencies
--------------------
The following commands install dependencies for Pygenda. Note that you
will need to be connected to the Internet, since these download packages.

Enter the following command in the command prompt (requires password):

    sudo apt update

This apt update gives me errors relating to the thinkglobally repository,
its certificates and lack of a Release file. For this guide, I don't
believe this matters because everything we need to install comes from
the Debian repository[^1]. So continue...

    sudo apt install python3
    sudo apt install python3-pip
    sudo apt install fonts-dejavu
    sudo apt install gir1.2-gtk-3.0
    sudo apt install python3-gi python3-cairo python3-gi-cairo python3-icalendar python3-dateutil python3-tzlocal python3-num2words

(Note: I'm using the apt versions of the Python3 module dependencies here.
This is for better compatibility with other operating system components.
If you are already using different versions of these modules, you may
want to stick with those versions. Alternatively, you may want to keep
the Pygenda module dependencies separate from the OS modules by running
Pygenda in a Python virtual environment.)

(Note 2: You may also need to install a libgtk3 package. This should be
installed either as a general GUI component or with gir1.2-gtk-3.0.
However, if it doesn't seem to be installed, try `sudo apt install libgtk-3-0`.)

Install Pygenda
---------------
Enter the following command to download and install Pygenda from the
PyPI repository:

    pip3 install pygenda --user --no-deps

Test Pygenda runs:

    python3 -m pygenda

Pygenda should start in a small window. Don't worry if the font sizes
are inappropriate, these will be configured below. For now we're just
checking that it starts. (There will be a few warnings on the console
related to theme parsing. This is expected on the Cosmo.)

Configuration
-------------
Enter the following to edit the Pygenda user CSS file:

    mkdir -p ~/.config/pygenda/
    nano ~/.config/pygenda/pygenda.css

(Commands in this section use the Nano text editor, you can use vim or
emacs or something else if you want.)

This should open an empty file. Add the following line:

    @import "../../.local/lib/python3.7/site-packages/pygenda/css/cosmo.css";

(If you've installed Pygenda some other way, or are using a different
version of Python3, change the path as appropriate.)

Save the file and exit (on Nano: ctrl+o (confirm filename), ctrl+x).

Now edit the Pygenda configuration file:

    nano ~/.config/pygenda/user.ini

Again, this should open an empty file. You have some choice about what
to enter here, depending on your preferences. Here's a reasonable
basic configuration, which you can modify as required:

    [global]
    24hr = True
    
    [startup]
    # You probably want the UI either maximised or full-screen,
    # so choose one of the following to be True...
    maximize = True
    fullscreen = False
    
    [softkeys]
    # Uncomment one of these if you want the soft keys on the left
    # or hidden:
    #display = left
    #display = hide
    
    [todo_view]
    list0_filter = UNCATEGORIZED
    list1_title = Shopping list
    list1_filter = shopping
    # ...and so on for additional todo lists: list2_title, list2_filter etc.
    # listN_title gives the todo list name as displayed in the UI.
    # listN_filter gives the tag to use internally in the icalendar data.

(Lines starting with a `#` are comments, so can be changed or omitted.
For other settings, see [defaults.ini](config-examples/defaults.ini).)

As before, save the file and exit.

Now you can start Pygenda again, and it should look better
(appropriate font sizes and other elements).

Optional: Personalise your CSS (e.g. dark mode)
-----------------------------------------------
The custom CSS file `~/.config/pygenda/pygenda.css` gives the user
lots of scope to customise the appearance of Pygenda to their own
needs.

One possibility is a "dark mode". An example dark mode CSS file is
available: [darkmode.css](config-examples/darkmode.css). To use this,
copy its contents into your user CSS file, below the import line, and
edit the URLs in the CSS so that they point to the .svg files in the
Pygenda install (these are the files for the icons in Year View; they
are in the same directory as the cosmo.css file, so the directory
path will be the same for the import that you added above). You can
then edit/tweak/add to the CSS as desired.

Add a Pygenda icon to the menu
------------------------------
To add a launch icon to your desktop menu, in a command prompt:

    mkdir -p ~/.local/share/applications/
    ln -s ~/.local/lib/python3.7/site-packages/pygenda/app/pygenda.desktop ~/.local/share/applications/

(This creates a link to the .desktop file included with Pygenda.
As before, change the path if Pygenda is installed elsewhere.)

Optional: Add a Pygenda icon to the KDE panel
---------------------------------------------
To add a launch icon to the KDE panel (KDE is the the default
desktop on Gemian for Cosmo), launch Pygenda and then drag the app
icon in the task bar to a space on the panel (e.g. next to the
clock, or next to the launcher). This can be a bit fiddly with
the touchscreen, so you might want to try plugging in a mouse.
In any case, I could only delete or move the Pygenda icon with
a mouse (right click -> Panel Options -> Configure Panel, then
hover the mouse pointer over the icon for options).

CalDAV
------
Full information about using a CalDAV server is here: [CalDAV.md](CalDAV.md)

To-do: add a CalDAV quickstart for Cosmo

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

    pip3 install --user pygenda==0.3.4

(Change 0.3.4 to your desired version.)

[^1]: If you find that you do need something from the thinkglobally
repository, you can try forcing it to trust these repositories with:
`sudo apt -o Acquire::AllowInsecureRepositories=true -o Acquire::AllowDowngradeToInsecureRepositories=true update`.
Obviously, allowing insecure repositories like this is a security risk.
