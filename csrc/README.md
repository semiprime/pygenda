Pygenda Clipboard Library
=========================
This is a small C library to improve cutting/copying behaviour.
Specifically, it allows Pygenda entries to be copied+pasted as text
into applications that expect text, and as calendar entries into
applications that expect calendar entries. It has been tested on
Gemian, Nura and Slackware, and probably works on other Linux
distributions. It might need tweaking for Windows/MacOS/BSD/other.

In order to be as universally compatible as possible, the clipboard
library is not included in the default wheel package. However, you can
build the library yourself, and if you are packaging Pygenda (e.g. for
a specific OS) I recommend that you include an appropriate version of
libpygenda_clipboard.so for improved functionality.

Building
--------
Build dependencies are: a C compiler, make, pkg-config, CMake,
development files for your libc (e.g. `libc-dev`, or on Nura
`musl-dev`), and GTK3 development files (package `libgtk-3-dev` on
Debian-like systems, or `gtk+3.0-dev` on Nura).

To build and copy to the correct location in the source tree, from
this (`csrc/`) directory:

    mkdir build
    cd build
    cmake ..
    make
    make cp

Building without CMake/make
---------------------------
If, for some reason, you want to build without CMake or make,
something like the following should work on Linux:

    cc -I/usr/include/gtk-3.0 \
       -I/usr/include/cairo \
       -I/usr/include/pango-1.0 \
       -I/usr/include/harfbuzz \
       -I/usr/include/atk-1.0 \
       -I/usr/include/gdk-pixbuf-2.0 \
       -I/usr/include/glib-2.0 \
       -I/usr/lib/glib-2.0/include \
       -fPIC -shared \
       -o libpygenda_clipboard.so \
       pygenda_clipboard.c
    
    strip libpygenda_clipboard.so # optional
    cp libpygenda_clipboard.so ../pygenda

You'll need the correct path for all the include directories in the
`cc` command. The tricky one is `/usr/lib/glib-2.0/include` for
`glibconfig.h`. On the devices that I tried, I needed to use one of
the following:

* `-I/usr/lib/glib-2.0/include` (Nura)
* `-I/usr/lib64/glib-2.0/include` (Slackware)
* `-I/usr/lib/aarch64-linux-gnu/glib-2.0/include` (Gemian)
