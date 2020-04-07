#!/usr/bin/env bash

# The main source file (mini.py) is written to be immediately buildable into
# an executable binary using the project's build scripts.
# This script on the other hand will run Miniquery as a python script by making a
# temporary copy of the main source file in which we edit the import statements
# so the interpreter can find the modules the program needs to load. This way, we don't
# have to do a full rebuild of the project every time we want to test something.

WORKING_DIR=$HOME/projects/miniquery/scripts
SOURCE_FILE=$WORKING_DIR/mini.py
TEMP_SOURCE_FILE=$WORKING_DIR/temp_mini.py

# Locate a python, giving preference to py3 over py
PYTHON=$( { which python3 || which python; } 2>/dev/null) || { echo "ERROR: Python not found."; exit 2; }

sed -r -e 's/includes(.*giveMini)/miniHelp\1/
s/includes(.*Sett)/appSettings\1/
s/includes(.*Error)/errorManager\1/
s/includes(.*Config)/configManager\1/
s/includes(.*argument)/argumentClassifier\1/
s/includes(.*query)/queryProcessor\1/
s/includes(.*miniDb)/databaseConnection\1/
s/includes(.*stringTo)/prompts\1/
s/utilIncludes(.*MiniComp)/miniCompleter\1/
s/utilIncludes(.*CommandComp)/commandCompleter\1/
s/utilIncludes(.*settingOp)/miniGlobals\1/
s/utilIncludes(.*commandList)/miniGlobals\1/
s/utilIncludes(.*yes_no)/miniDialogs\1/'  "${SOURCE_FILE}"  >  "${TEMP_SOURCE_FILE}"

if grep -q [Ii]ncludes "${TEMP_SOURCE_FILE}"; then
    echo "************************************************************************************************"
    echo Please add lines to $BASH_SOURCE that will convert these \"includes\" imports to the original files.
    echo "************************************************************************************************"
    exit 1
fi

chmod a+x "${TEMP_SOURCE_FILE}"

"$PYTHON"  "${TEMP_SOURCE_FILE}"  "$@"

rm -f "${TEMP_SOURCE_FILE}"
