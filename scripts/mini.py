#!/usr/bin/env python3

import os
import sys

#sys.path.append(MINI_HOME + "/src/")
sys.path.append("/data/data/com.termux/files/home/projects/miniquery/src/")
import miniEnv as env
from minihelp import HelpType, shouldHelpOrExecute, giveHelp
from errorManager import miniErrorManager, ReturnCode
from configManager import miniConfigManager

def main():
    argc = len(sys.argv)-1;
    helpCode = shouldHelpOrExecute(sys.argv[1] if argc>=1 else '', argc)

    if helpCode != HelpType.NO_HELP:
        giveHelp(sys.argv[0], helpCode, 'table')
        miniErrorManager.doExit()

    if env.setEnv() != ReturnCode.SUCCESS:
        miniErrorManager.doExit('Environment settings incomplete or incorrect.')

    if miniConfigManager.configureToSchema(sys.argv[1]) != ReturnCode.SUCCESS:
        miniErrorManager.doExit()

# Main entry point.
if __name__ == '__main__':
    main()
