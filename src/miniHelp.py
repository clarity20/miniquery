import re
from enum import Enum

from errorManager import ReturnCode, miniErrorManager

class HelpType(Enum):
    USAGE_HELP = 1
    FULL_HELP  = 2
    NO_HELP    = 3

def giveMiniHelp():
    print('MINIQUERY')
    print('Copyright (c) 2019-2020 by Miniquery AMDG, LLC\n')
    print('Usage:')
    print('    mini [options] [table] [query parts ...]')
    print('With no arguments, enters the MiniQuery command prompt.\n')
    print('Options:')
    print('    -e  Process a single query and exit')
    print('    -q  Show the generated SQL query')
    print('    -r  Run the query')
    print('\n')
    print('table: main table name for query.')

    return ReturnCode.SUCCESS


def giveHelp(programName_0, helpType = HelpType.FULL_HELP, objectName_0 = '',
                trailingArguments = '[-{option} | {query_component}] [...]'):
    a, b, programName = programName_0.rpartition('/')   # get basename

    # For USAGE-type msgs, set the object name(s) to display and the exit code
    if helpType == HelpType.USAGE_HELP:

        # Handle pluralized object names
        if objectName_0.endswith('s'):
            match = re.search(r'(.*)Rows$', objectName_0)
            if match:
                objectName = '[-rowCount] '
                objectName_0 = match.group(1)
            objectName += objectName_0.rstrip('s') + 'NameOrList'
        # Special cases
        elif objectName_0 == 'both':
            objectName = 'tableNameOrList [columnNameOrList]'
        # Singular object names
        elif objectName_0 != '':
            objectName = objectName_0 + 'Name'
        # Let empty names stay empty
        else:
            pass     # do nothing

        miniErrorManager.setError(ReturnCode.HELP_AND_EXIT, programName,
                objectName, trailingArguments)

    # For detailed help, choose the right text from a text archive
    else:
        # Fetch the detailed help, and then...
        miniErrorManager.setError(ReturnCode.HELP_AND_EXIT,
                msgOverride='Details to come.')

    return ReturnCode.SUCCESS

def shouldHelpOrExecute(firstArgument, argumentCount):
    if argumentCount == 0:
        ret = HelpType.USAGE_HELP
    elif re.match('-+h(elp)?$', firstArgument):   # match from beginning
        ret = HelpType.FULL_HELP
    else:
        ret = HelpType.NO_HELP

    return ret

