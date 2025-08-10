Pygenda "Quick Start" Guide for the Gemini PDA
==============================================
This guide will lead you through installation and basic configuration
of the most recent release of Pygenda on a Gemini PDA running Gemian
Linux.

The guide is intended for users who want to install/run/test Pygenda.
If you want to contribute to or modify Pygenda, then you probably want
to get the latest version from Codeberg or GitHub (which are usually a
little ahead of the latest official release). This guide may be useful
to refer to for dependencies and initial configuration.

Note that Pygenda is alpha software, and as such has **lots of
missing/incomplete features** as well as **bugs**. It is released for
testing and feedback purposes, but you may also find it useful.

This guide may seem rather long. This is partly because Gemian Linux
has not been updated for several years, so it is necessary to make
some changes so that standard Debian packages can be installed. If you
are using these instructions to help you install Pygenda on a different
(relatively up-to-date) Linux distribution, then it should be simpler
than described here: there will be no need to edit the apt sources
files or update pip.

Preliminaries
-------------
First, check that you have the correct device and operating system for
this guide: the Gemini PDA made by Planet Computers. This should be
running Gemian Linux (a version of Debian), *not* Android.

To check your Gemian (Debian) version, open a command prompt on the
Gemini and enter the following command:

    cat /etc/debian_version

It should output one line saying `9.13`.

At the time of writing, version 9.13 is the most recent version. If
you have an older version of Debian, then I suggest you update before
installing Pygenda. Unfortunately, since Debian themselves no longer
support Debian version 9, updating Gemian is not a simple process, and
is not described in this document[^1]. If you have Debian 10.x or
later, then the [quickstart for Debian-like systems](quickstart-debianlike.md)
will be a better starting point than this guide.

Update apt sources
------------------
Since Debian version 9 ("stretch") is no longer supported by Debian,
the packages have moved to Debian's "archive" server. If you have not
already done so, you should update the apt sources to use to the new URL.

To do this, you need to edit the file `/etc/apt/sources.list.d/multistrap-debian.list`.
First, make a backup:

    cp -i /etc/apt/sources.list.d/multistrap-debian.list ~/multistrap-debian.list-BACKUP

Then edit the file with the command:

    sudo nano /etc/apt/sources.list.d/multistrap-debian.list

(You will probably need to enter your password here.)

The file has several lines referring to `http.debian.net`. Change each
of these to `archive.debian.org` (note, two parts change: `http` and
`net`). The final file should look something like:

    deb [arch=arm64] http://archive.debian.org/debian stretch main contrib non-free
    deb-src http://archive.debian.org/debian stretch main contrib non-free

(There may be some variation if you have previously made changes to this
file).

Save the file and exit: ctrl+o (confirm filename), ctrl+x.

Install dependencies
--------------------
The following commands install dependencies for Pygenda. Note that you
will need to be connected to the Internet, since these download packages.

Enter the following command in the command prompt (requires password):

    sudo apt update

This apt update gives me errors relating to the thinkglobally repository,
its certificates and lack of a Release file. For this guide, I don't
believe this matters because everything we need to install comes from
the Debian repository[^2]. So continue...

    sudo apt install python3
    sudo apt install python3-pip
    sudo apt install libgtk+3

Now use the "pip" Python package tool to update itself:

    pip3 install --user pip==20.3.4

(This version of pip has better support for installation of binary
"wheel" packages.)

Install Noto Emoji font
-----------------------
For the candle icon (maybe others) you should install a recent Noto Emoji
font. The easiest way is to download the font from https://fonts.google.com/noto/specimen/Noto+Emoji and save the `NotoEmoji-VariableFont_wght.ttf` file
in the `~/.fonts/` directory. (For more details and alternatives, like
installing the font system wide, see https://wiki.debian.org/Fonts#Manually.)

Install Pygenda
---------------
Enter the following command to download and install Pygenda (and the
Python modules that it depends on) from the PyPI repository:

    pip3 install --user pygenda

(This gives a warning about being invoked by an old script wrapper, and
a notice about deprecation. These can be ignored as they both concern
"future version"s of pip, i.e. ones after version 20.3.4 installed above.)

Test Pygenda runs:

    python3 -m pygenda

Pygenda should start in a small window. Don't worry if the font sizes
are inappropriate, these will be configured below. For now we're just
checking that it starts. (There will be a few warnings on the console
related to the accessibility bus and the theme. This is expected on
the Gemini.)

Configuration
-------------
Enter the following to edit the Pygenda user CSS file:

    mkdir -p ~/.config/pygenda/
    nano ~/.config/pygenda/pygenda.css

(Commands in this section use the Nano text editor, you can use vim or
emacs or something else if you want.)

This should open an empty file. Add the following line:

    @import "../../.local/lib/python3.5/site-packages/pygenda/css/gemini.css";

Save the file and exit: ctrl+o (confirm filename), ctrl+x.

Now edit the Pygenda configuration file:

    nano ~/.config/pygenda/user.ini

Again, this should open an empty file. You have some choice about what
to enter here, depending on your preferences. Here's a reasonable
basic configuration, which you can modify as required:

    [global]
    24hr = True
    # Localisation settings should be picked up from the system.
    # If not, language & date order (DMY, MDY, YMD) can be set with:
    #language = fr
    #date_ord = DMY
    
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

As before, save the file and exit: ctrl+o (confirm filename), ctrl+x.

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
are in the same directory as the gemini.css file, so the directory
path will be the same for the import that you added above). You can
then edit/tweak/add to the CSS as desired.

Add a Pygenda icon to the menu
------------------------------
To add a launch icon to your desktop menu, in a command prompt:

    mkdir -p ~/.local/share/applications/
    ln -s ~/.local/lib/python3.5/site-packages/pygenda/app/pygenda.desktop ~/.local/share/applications/

(This creates a link to the .desktop file included with Pygenda.)

Optional: Add a Pygenda icon to the LXQt panel
----------------------------------------------
To add a launch icon to the LXQt panel (LXQt is the the default
desktop on Gemian), edit the panel configuration file:

    nano ~/.config/lxqt/panel.conf

This file should already exist, with sections named `[General]`,
`[mainmenu]`, etc. Scroll down to the `[quicklaunch]` section. It
should look something like this:

    [quicklaunch]
    type=quicklaunch
    alignment=Left
    apps\size=2
    apps\1\desktop=SOME_APPLICATION
    apps\2\desktop=SOME_OTHER_APPLICATION

You will need to add an extra line:

    apps\NUMBER\desktop=HOME_DIR/.local/lib/python3.5/site-packages/pygenda/app/pygenda.desktop

Note 1: Change `NUMBER` above to the next number in the sequence in
your panel.conf file (so that would be `3` in the example shown above).

Note 2: Change `HOME_DIR` to your home directory (which will be
`/home/gemini` for the default user account, and probably `/home/xyz`
if your user login name is xyz).

Note 3: Also change to line `apps\size=XX` to reflect the number of
applications now listed (that would mean changing `2` to `3` in the
example above).

If you have no `[quicklaunch]` section, you can add a new one at the
end of the file:

    [quicklaunch]
    type=quicklaunch
    alignment=Left
    apps\size=1
    apps\1\desktop=/home/gemini/.local/lib/python3.5/site-packages/pygenda/app/pygenda.desktop

There should already be a reference to the plugin `quicklaunch` in one
of the `panelX` sections. For example:

    [panel1]
    ...
    plugins=... quicklaunch, ...
    ...

If this does not exist, then you will need to add it to the list of
plugins for your chosen panel.

After all this, save the file and exit: ctrl+o (confirm filename), ctrl+x.

You will need to log out and back in again for this change to take effect.

CalDAV Server (Radicale)
------------------------
By default, Pygenda saves entries in a single file. This is convenient
for testing, but it could lead to data loss (if multiple programs try
to update the same file) or slowdown for large files. Hence, if you
want to use Pygenda for more than just testing, we recommended that
you store your agenda data in a server (running on the same device).

Pygenda supports CalDAV servers and the Evolution Data Server.
Unfortunately, the package needed to access EDS is only available in
Debian Bullseye (11) and later, so for the Gemini we will use a CalDAV
server.

In this section we go through a basic install and setup using the
Radicale CalDAV server (version 3).

For those who want more technical details (e.g. to configure Pygenda
to use a different server), more complete information is available
here: [CalDAV.md](CalDAV.md)

First install Radicale and dependencies with pip:

    pip3 install radicale --user

Create a configuration file for Radicale:

    mkdir ~/.config/radicale
    nano ~/.config/radicale/config

Add the following content to the file and save it:

    [storage]
    filesystem_folder = ~/.radicale-data

Now set Radicale to launch when you login. In the LXQt app menu, go to
Preferences -> LXQt Configuration Center -> Session Settings ->
Autostart. Tap the "Add" button and add a command with name "Radicale"
and command "`python3 -m radicale`" (this will create a .desktop file
in `~/.config/autostart/`).

Then logout and login again to start the Radicale server.

To add calendars to Radicale, use the web interface. In a web browser
go to: http://localhost:5232/

In the Radicale web interface, enter the user name of your choice,
leave the password blank, and login. Once logged in you can create a
new calendar. We suggest a Title of "agenda" (but you may want to
create several calendars, e.g. "personal" and "work") and Type
"calendar and tasks". Now close the browser.

### Configuring Pygenda to use CalDAV

Install the Python caldav package and dependencies:

    sudo apt install libxml2-dev libxslt-dev
    pip3 install caldav==0.11.0 --user

Note: Installing caldav takes a long time (around ten minutes). In
particular, I thought it had frozen when running setup.py for lxml.

Now edit the file ~/.config/pygenda/user.ini (see above, Configuration)
and add the following:

    [calendar]
    type = caldav
    server = http://localhost:5232/
    username = USERNAME_ENTERED_ABOVE
    password = pass
    calendar = agenda

A password is required, but it can be anything.

If you used a different Title creating the calendar, in the Radicale
web interface, use that instead of "agenda" for the calendar value (in
fact, if you only have one calendar then you can omit that line). If
you created more than one calendar, you can configure the others as
[calendar1], [calendar2], etc., giving the appropriate names for the
calendar setting in each section.

Now test that Pygenda launches, and that you can create new entries.

Security note: You may be concerned that the Radicale server is
accessible to other people on the network. This should not be a
problem because by default it only binds to localhost.

Finally
-------
I'd be grateful if you emailed me at pygenda@semiprime.com to let me
know that you've tried Pygenda. It's a small project without lots of
testers, so even feedback to say "it worked for me" is useful to let
me know I haven't accidentally broken it. (I also welcome bug reports,
feature requests, bug fixes, translations, corrections & additions to
the documentation, new features, etc.)

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

    pip3 install --user pygenda==0.2.8

(Change 0.2.8 to your desired version.)

[^1]: Seriously, this is much more risky that a standard Debian upgrade.
You risk losing data, breaking your installed apps, or even stopping
Linux from booting (meaning you'll need to re-flash to get it back –
possibly losing data on your Android or other partitions too). You
**must** backup any data/files that you don't want to lose before
starting, including anything on your Android or other partitions. I
can't help you, since it's not going to be the same on every device.
However, I'll mention some things that seemed to work when I was
helping someone upgrade from 9.11 to 9.13. First, you'll need to
update the apt sources as described in this document. Then when doing
`apt update` you may need to use the options to allow insecure
repositories (this is a security risk). Now try the upgrade command:
`sudo apt full-upgrade`. If you get file conflicts with LibreOffice-Base,
you could try forcing it with:
`sudo apt install -o DPkg::options::="--force-overwrite" libreoffice-base`.

[^2]: If you find that you do need something from the thinkglobally
repository, you can try forcing it to trust these repositories with:
`sudo apt -o Acquire::AllowInsecureRepositories=true -o Acquire::AllowDowngradeToInsecureRepositories=true update`.
Obviously, allowing insecure repositories like this is a security risk.
