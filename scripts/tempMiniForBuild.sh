#!/usr/bin/env bash

# For greatest ease of development and debugging, the main source file (mini.py)
# is designed to be a runnable python script as-is.
# But when building the executable binary, a few changes need to be made so
# the build process can find all the modules and transpile, compile, and link them.
# This script writes a temporary file with those changes.

WORKING_DIR=$HOME/projects/miniquery/scripts
SOURCE_FILE=$WORKING_DIR/mini.py

# Locate python, giving preference to py3 over py
PYTHON=$( { which python3 || which python; } 2>/dev/null) || { echo "ERROR: Python not found."; exit 2; }

fileEditCommand=""

function append_to_edit_command()
{
    importLocation="$1"
    shift
    importList=("$@")
    for import in "${importList[@]}"; do
        fileEditCommand+="s/$import /$importLocation /;"$'\n'
    done
}

includeImports=(
    miniHelp
    appSettings
    errorManager
    configManager
    argumentClassifier
    queryProcessor
    databaseConnection
    prompts
)
utilIncludeImports=(
    miniCompleter
    commandCompleter
    miniGlobals
    miniGlobals
    miniDialogs
)

append_to_edit_command  "includes"      "${includeImports[@]}"
append_to_edit_command  "utilIncludes"  "${utilIncludeImports[@]}"

sed -r -e "$fileEditCommand"  "${SOURCE_FILE}"

exit 0

