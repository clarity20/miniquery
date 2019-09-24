#!/usr/bin/env bash

# Runs the program as a python script (the "classic" way) by making an
# executable temp copy of mini.py with the necessary edits. This way, we don't
# have to do a full rebuild of the dependencies with every edit, which can take a little while.

WORKING_DIR=$HOME/projects/miniquery/scripts
SOURCE_FILE=$WORKING_DIR/mini.py
TEMP_SOURCE_FILE=$WORKING_DIR/temp_mini.py

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
s/utilIncludes(.*commandList)/miniGlobals\1/'  "${SOURCE_FILE}"  >  "${TEMP_SOURCE_FILE}"

if grep -q [Ii]ncludes "${TEMP_SOURCE_FILE}"; then
    echo "************************************************************************************************"
    echo Please add lines to $BASH_SOURCE that will convert these \"includes\" imports to the original files.
    echo "************************************************************************************************"
    exit 1
fi

chmod a+x "${TEMP_SOURCE_FILE}"
python3  "${TEMP_SOURCE_FILE}"  "$@"
rm -f "${TEMP_SOURCE_FILE}"
