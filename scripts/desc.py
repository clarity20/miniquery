#!/usr/bin/env python3

import os
import sys

sys.path.append("../src")
import miniEnv as env
from miniHelp import HelpType, shouldHelpOrExecute, giveHelp
from errorManager import miniErrorManager as em, ReturnCode
from configManager import masterDataConfig

def main():
    argc = len(sys.argv)-1;
    helpCode = shouldHelpOrExecute(sys.argv[1] if argc>=1 else '', argc)

    if helpCode != HelpType.NO_HELP:
        giveHelp(sys.argv[0], helpCode, 'both')
        em.doExit()

    if env.setEnv() != ReturnCode.SUCCESS:
        em.doExit('Environment settings incomplete or incorrect.')

    if masterDataConfig.configureToMetadata(sys.argv[0], 'columns') != ReturnCode.SUCCESS:
        em.doExit()

# Main entry point.
if __name__ == '__main__':
    main()
