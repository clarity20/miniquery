#!/usr/bin/env python3

import os
import sys

sys.path.append("../src/")
from minihelp import HelpType, shouldHelpOrExecute, giveHelp
from error import doExit

def main():
    try:
        MINI_HOME = os.environ['MINI_HOME']
    except KeyError:
        MINI_HOME = os.environ['HOME'] + '/miniquery'

    argc = len(sys.argv)-1;
    helpCode = shouldHelpOrExecute(sys.argv[1] if argc>=1 else '', argc)

    if helpCode != HelpType.NO_HELP:
        giveHelp(sys.argv[0], helpCode, 'table')
        doExit()

# Main entry point.
if __name__ == '__main__':
    main()
