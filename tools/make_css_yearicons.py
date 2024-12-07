#!/usr/bin/env python3
#
# Quick-n-dirty script to generate CSS to associate various
# combinations of entry properties to icons in the Year View grid.
# As provided, this script generates the CSS found in the provided
# pygenda.css file. Users can customise this script to generate CSS
# for icons matching their own preferences, and put the code in their
# ~/.config/pygenda/pygenda.css file.


# Elements in the groups below correspond to the same icon.
# For example, the same icon is used for weekly & monthly repeated items.
groups = [
    ['yearview_entry_single', 'yearview_entry_repeated_day', 'yearview_entry_repeated_hour', 'yearview_entry_repeated_minute', 'yearview_entry_repeated_second'],
    ['yearview_entry_repeated_month', 'yearview_entry_repeated_week'],
    ['yearview_entry_repeated_year'],
    ['yearview_entry_todo']
]


# Icon image files should be called "disc.svg", "loop.svg", etc.
# The order is the same as the elements above (e.g. todo entry -> T.svg).
# Multi-icon image files are also needed, called "disc+loop.svg" etc.
# The icon image files should be in the same directory as the CSS file.
icons = ['disc','loop','star','T']


def print_groups(gps, cursor):
    if len(gps)==1:
        tuples = ['.{:s}'.format(a) for a in gps[0]]
    elif len(gps)==2:
        tuples = ['.{:s}.{:s}'.format(a,b) for a in gps[0] for b in gps[1]]
    elif len(gps)==3:
        tuples = ['.{:s}.{:s}.{:s}'.format(a,b,c) for a in gps[0] for b in gps[1] for c in gps[2]]
    elif len(gps)==4:
        tuples = ['.{:s}.{:s}.{:s}.{:s}'.format(a,b,c,d) for a in gps[0] for b in gps[1] for c in gps[2] for d in gps[3]]
    else:
        print('Unhandled number of groups to print:', len(gps))
        exit()
    if cursor:
        tuples = [ t+'.yearview_cursor' for t in tuples ]
    print(', '.join(tuples), end='')


# In the CSS file, the styles need to be listed with all single-icon
# groups first, then all double-icon groups, then triple-icon groups,
# etc. The mapping below sets this order.
if len(groups)==2:
    order = [1,2,3]
elif len(groups)==3:
    order = [1,2,4,3,5,6,7]
elif len(groups)==4:
    order = [1,2,4,8,3,5,9,6,10,12,7,11,13,14,15]
else:
    print('Unhandled number of groups for order')

for i in order:
    gps = []
    icon = []
    for j in range(0,len(groups)):
        if 2**j & i:
            gps.append(groups[j])
            icon.append(icons[j])
    icon = '+'.join(icon)
    print_groups(gps, False)
    print(' {')
    print('\tbackground-image:url("{:s}.svg");'.format(icon))
    print('\tbackground-size:100% auto;')
    print('\tbackground-position:center;')
    print('\tbackground-repeat:no-repeat;')
    print('}\n')
    print_groups(gps, True)
    print(' {')
    print('\tbackground-image:url("{:s}.svg"), linear-gradient(90deg, #000 9%, transparent 9%, transparent 91%, #000 91%), linear-gradient(#000 8%, transparent 8%, transparent 92%, #000 92%);'.format(icon))
    print('}\n')
