#!/usr/bin/env python3

import os
import sys

try:
    MINI_HOME = os.environ['MINI_HOME']
except KeyError:
    MINI_HOME = os.environ['HOME'] + '/miniquery'

sys.path.append(MINI_HOME + "/src/")
from minihelp import HelpType, shouldHelpOrExecute, giveHelp
from errorManager import miniErrorManager

def main():
    argc = len(sys.argv)-1;
    helpCode = shouldHelpOrExecute(sys.argv[1] if argc>=1 else '', argc)

    if helpCode != HelpType.NO_HELP:
        giveHelp(sys.argv[0], helpCode, 'table')
        miniErrorManager.doExit()

# Main entry point.
if __name__ == '__main__':
    main()
