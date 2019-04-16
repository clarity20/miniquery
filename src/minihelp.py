import re
from enum import Enum

class HelpType(Enum):
    USAGE_HELP = 1
    MINI_HELP  = 2
    NO_HELP    = 3

def giveHelp():
    print("MMMM Inside doHelp")

def shouldHelpOrExecute(firstArgument, argumentCount):
    if argumentCount == 0:
        ret = HelpType.USAGE_HELP
    elif re.match('-+h(elp)?$', firstArgument):   # match from beginning
        ret = HelpType.MINI_HELP
    else:
        ret = HelpType.NO_HELP

    return ret

