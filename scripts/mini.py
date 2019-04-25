#!/usr/bin/env python3

import os
import sys

# Defaultable environment
try:
    HOME = os.environ['HOME']
    MINI_HOME = os.environ['MINI_HOME']
    MINI_CACHE = os.environ['MINI_CACHE']
    MINI_CONFIGS = os.environ['MINI_CONFIGS']
except KeyError:
    MINI_HOME = HOME + '/miniquery'
    MINI_CACHE = HOME + '/miniquery/cache'
    MINI_CONFIGS = HOME + '/miniquery/config'
# Required environment
try:
    MINI_DBNAME = os.environ['MINI_DBNAME']
except KeyError:
    sys.exit(1)

sys.path.append(MINI_HOME + "/src/")
from minihelp import HelpType, shouldHelpOrExecute, giveHelp
from errorManager import miniErrorManager
from configManager import miniConfigManager

def main():
    argc = len(sys.argv)-1;
    helpCode = shouldHelpOrExecute(sys.argv[1] if argc>=1 else '', argc)

    if helpCode != HelpType.NO_HELP:
        giveHelp(sys.argv[0], helpCode, 'table')
        miniErrorManager.doExit()

    if miniConfigManager.configureToSchema() != ReturnCode.SUCCESS
        miniErrorManager.doExit()

# Main entry point.
if __name__ == '__main__':
    main()
