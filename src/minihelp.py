import re
from enum import Enum

class HelpType(Enum):
    USAGE_HELP = 1
    MINI_HELP  = 2
    NO_HELP    = 3

def giveHelp(programName_0, helpType = HelpType.MINI_HELP, objectName_0 = '',
                trailingArguments = '[-{option} | {query_component}] [...]'):
    a, b, programName = programName_0.rpartition('/')   # get basename

    if helpType == HelpType.USAGE_HELP:
        # Handle pluralized object names
        if objectName_0.endswith('s'):
            match = re.search(r'(.*)Rows$', objectName_0)
            if match:
                objectName = '[-rowCount] '
                objectName_0 = match.group(1)
            objectName += objectName_0.rstrip('s') + 'NameOrList'
        # Special cases
        elif objectName_0 == both:
            objectName = 'tableNameOrList [columnNameOrList]'
        # Singular object names
        elif objectName_0 != '':
            objectName = objectName_0 + 'Name'
        # Let empty names stay empty
        fi

        print ("MMMM SetError ${rc[HELP_AND_EXIT]}")

    else:
        print ("MMMM SetError ${rc[HELP_AND_EXIT]} " + 'Details to come.')

        #MMMM Figure out a reasonably pythonic way to raise and process error codes
        return 0        #MMMM ${rc[SUCCESS]}

def shouldHelpOrExecute(firstArgument, argumentCount):
    if argumentCount == 0:
        ret = HelpType.USAGE_HELP
    elif re.match('-+h(elp)?$', firstArgument):   # match from beginning
        ret = HelpType.MINI_HELP
    else:
        ret = HelpType.NO_HELP

    return ret

