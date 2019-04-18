#!/usr/bin/env python3

import os
import sys

sys.path.append("../src/")
from minihelp import HelpType, shouldHelpOrExecute, giveHelp

def main():
    try:
        MINI_HOME = os.environ['MINI_HOME']
    except KeyError:
        MINI_HOME = os.environ['HOME'] + '/miniquery'

    argc = len(sys.argv);
    helpCode = shouldHelpOrExecute(sys.argv[1] if argc>1 else '', argc)

    if helpCode != HelpType.NO_HELP:
        giveHelp(sys.argv[0], argc)
        print("MMMM Put doExit here.")

    print("MMMM Finished.")

# Main entry point.
if __name__ == '__main__':
    main()
