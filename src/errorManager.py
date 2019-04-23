import sys
from enum import Enum

class ReturnCode(Enum):
    SUCCESS = 0
    HELP_AND_EXIT = 1
    INFEASIBLE_EXPR = 2
    MISSING_ARGUMENT = 3
    EMPTY_RESULT_SET = 4
    ILL_FORMED_CONFIG_FILE = 5
    INVALID_TYPE = 6
    DESCRIPTION_FILE_READ = 7
    INVALID_DATE = 8
    UNBALANCED_PARENTHESES = 9

errorMsg = {
    0 : '',
    1 : 'USAGE: {0} {1} {2}\nType {0} -h or --help for detailed help.',
    2 : 'Illegal grammar / no feasible interpretation for "{0}".',
    3 : 'First non-option argument must be a table name.',
    4 : 'No results returned.',
    5 : 'Attribute "{0}" not allowed in regex section of config file.',
    6 : 'Invalid type for expression "{0}".',
    7 : 'Cannot read {0} description file "{1}".',
    8 : 'Invalid date expression.',
    9 : 'Error: Unbalanced parentheses in argument {0}.'
    }

#MMMM: make this class data
errMsg = ''
returnCode = ReturnCode.SUCCESS
errOutputStream = sys.stderr

def setError(code, *args, msg=""):
    if '$' in msg:
        print('Bad call to setError: argument "msg" must be flat.')
        return 99
    else:
        pass

    template = errorMsg[code.value]
    errMsg = template.format(*args) if args else template
    print('MMMM: errMsg: ' + errMsg)

    return 0

def doExit(msg=errMsg):
    print ('MMMM message: ' + msg)
    errOutputStream.write(msg)
    sys.exit(returnCode.value)

