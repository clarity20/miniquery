import sys
from enum import Enum
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

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
    USER_EXIT = 10
    DATABASE_CONNECTION_ERROR = 11
    MISSING_SETTINGS_FILE = 12
    INVALID_QUERY_SYNTAX = 13
    PROMPT_ERROR = 14
    MISSING_PASSWORD = 15
    ILLEGAL_ARGUMENT = 16

errorMsgDict = {
    0 : '',
    1 : 'USAGE: {0} {1} {2}\nType {0} -h or --help for detailed help.',
    2 : 'Illegal grammar / no feasible interpretation for "{0}".',
    3 : 'First non-option argument must be a table name.',
    4 : 'No results returned.',
    5 : 'Attribute "{0}" not allowed in regex section of config file.',
    6 : 'Invalid type for expression "{0}".',
    7 : 'Cannot read {0} description file "{1}".',
    8 : 'Invalid date expression.',
    9 : 'Error: Unbalanced parentheses in argument {0}.',
    10 : '\nThank you for using MINIQUERY!\n',
    11 : 'Database connection error: {0}, {1}',
    12 : 'Application settings file "{0}" missing or unreadable.',
    13 : 'Query syntax error: {0}, {1}',
    14 : 'Illegal {0} "{1}" in prompt.',
    15 : 'Unable to prompt for password. Please specify it using "-p" option or config file.',
    16 : 'Illegal argument. {0} is required.',  # This should be specialized to the context
    }

class ErrorManager:

    def __init__(self):
        self.errMsg = ''
        self.returnCode = ReturnCode.SUCCESS
        self.errOutputStream = sys.stderr

    def setError(self, code, *args, msgOverride=""):
        if '$' in msgOverride:
            print('Bad call to setError: argument "msg" must be flat.')
            return 99
        else:
            pass

        if msgOverride != '':
            self.errMsg = msgOverride
            self.returnCode = code
        else:
            template = errorMsgDict[code.value]
            self.errMsg = template.format(*args) if args else template
            self.returnCode = code

        return self.returnCode

    def getError(self):
        return self.returnCode

    def doExit(self, msg=None):
        if self.errOutputStream.isatty() and self.returnCode.value:
            color = 'lightgreen' if self.returnCode == ReturnCode.USER_EXIT else 'red'
            print_formatted_text(FormattedText([(color, msg or self.errMsg)]),
                                file=self.errOutputStream)
        else:
            print(msg if msg else self.errMsg, file=self.errOutputStream)

        sys.exit(0 if self.returnCode == ReturnCode.USER_EXIT
                     else self.returnCode.value)

    # Warn: For situations that warrant giving the user a chance to
    # fix things up instead of totally exiting the program
    def doWarn(self, msg=None):
        if self.errOutputStream.isatty() and self.returnCode.value:
            print_formatted_text(FormattedText([('red', msg or self.errMsg)]),
                                file=self.errOutputStream)
        else:
            print(msg if msg else self.errMsg, file=self.errOutputStream)

        # Wipe out the error state so the user can continue
        self.returnCode = ReturnCode.SUCCESS
        self.errMsg = ''

miniErrorManager = ErrorManager()
