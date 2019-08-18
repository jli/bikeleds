#!/bin/sh

# fswatch is an OS X program like inotifywatch. `brew install fswatch`

DEST=${2:-/Volumes/CIRCUITPY/code.py}


echo initial copy ...
/bin/cp -vf "$1" "$DEST"
echo
echo watching: "$1"  ...
fswatch "$1" | while read i; do echo  $(date '+:%H:%M:%S'); /bin/cp -vf "$i" "$DEST"; done
