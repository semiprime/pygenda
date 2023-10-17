Pygenda config-examples
=======================
This directory contains some example configuration files.

See [defaults.ini](defaults.ini) for a complete list of settings.

Either use them as provided by soft-linking to them from the
`~/.config/pygenda/` directory as `pygenda.css` or `user.ini`, copy
to that directory and edit to your own taste, or for css files
`@import` the files and make your own additions.

You can also check the default css for ideas:
[css/pygenda.css](../../pygenda/css/pygenda.css) in the source directory.

Note: Pygenda reads both `pygenda.ini` and `user.ini` files. However,
`pygenda.ini` is expected to be used in the future as the location
where Pygenda saves settings. Hence users should generally use
`user.ini` to avoid having their settings overwritten in the future.
Settings in `user.ini` take preference over ones in `pygenda.ini`.
