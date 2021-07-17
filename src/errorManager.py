import sys
import platform
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
    DB_DRIVER_ERROR = 13
    PROMPT_ERROR = 14
    MISSING_PASSWORD = 15
    ILLEGAL_ARGUMENT = 16
    Clarification = 17
    CONFIG_FILE_FORMAT_ERROR = 18
    CONFIG_VALIDATION_ERROR = 19
    CONFIG_MISSING_REQUIRED_SECTION = 20
    TABLE_NOT_FOUND = 21

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
    13 : 'Error/exception thrown by {0} db driver:',
    14 : 'Illegal {0} "{1}" in prompt.',
    15 : 'Unable to prompt for password. Please specify it using "-p" option or config file.',
    16 : 'Illegal argument. {0} is required.',  # This should be specialized to the context
    17 : '', # Reserved for mere warnings
    18 : 'Formatting error with config file {0}.',
    19 : 'Errors in config file {0}:\n{1}',
    20 : 'Config file "{0}" is missing required section {1}.',
    21 : 'Table "{0}" not found.',
    }

class ErrorManager:

    def __init__(self):
        self._errMsg = ''
        self._exception = None
        self._returnCode = ReturnCode.SUCCESS
        self._errOutputStream = sys.stderr

    def setException(self, exc, msg):
        '''
        A pretty flexible approach to exception handling that can make full use of the thrown exception object
        '''
        SQLALCHEMY_ERROR_TEMPLATE = '  error type:   {0}\n  full descr: {1}\n  SQL command:   {2}'

        from sqlalchemy.exc import DBAPIError
        self._exception = exc
        exceptionType = type(exc).__name__

        # Set the err msg based on the exception type
        if isinstance(exc, DBAPIError):
            # Handle errors raised by the DBAPI (and passed on by SQLAlchemy).
            # See the SQLAlchemy help pages and website for further information.
            self._errMsg = msg + ":\n" + SQLALCHEMY_ERROR_TEMPLATE.format(exceptionType, exc.args[0], exc.statement)
            self._returnCode = ReturnCode.DB_DRIVER_ERROR
        else:
            print('Handling for exception type %s not implemented yet.' % exceptionType)

        return self._returnCode

    def getException(self):
        return self._exception

    def setError(self, code, *args, msgOverride=""):
        '''
        A vestigial approach to exception handling. Captures less information than objects.
        '''
        if '$' in msgOverride:
            print('Bad call to setError: argument "msg" must be flat.')
            return 99

        if msgOverride != '':
            self._errMsg = msgOverride
            self._returnCode = code
        else:
            template = errorMsgDict[code.value]
            self._errMsg = template.format(*args) if args else template
            self._returnCode = code

        return self._returnCode

    def getError(self):
        return self._returnCode

    def doExit(self, msg=None):
        if self._errOutputStream.isatty() and self._returnCode.value:
            if self._returnCode == ReturnCode.USER_EXIT:
                color = 'green' if platform.system() == 'Windows' else 'lightgreen'
            else:
                color = 'red'
            print_formatted_text(FormattedText([(color, msg or self._errMsg)]),
                                file=self._errOutputStream)
        else:
            print(msg if msg else self._errMsg, file=self._errOutputStream)

        sys.exit(0 if self._returnCode == ReturnCode.USER_EXIT
                     else self._returnCode.value)

    # Warn: For error conditions or warnings that should be nonfatal
    def doWarn(self, msg=None):
        if self._errOutputStream.isatty() and self._returnCode.value:
            color = 'yellow' if self._returnCode == ReturnCode.Clarification else 'red'
            print_formatted_text(FormattedText([(color, msg or self._errMsg)]),
                                file=self._errOutputStream)
        else:
            print(msg if msg else self._errMsg, file=self._errOutputStream)

        self.resetError()

    def resetError(self):
        # Wipe out the error state so the user can continue
        self._returnCode = ReturnCode.SUCCESS
        self._exception = None
        self._errMsg = ''


miniErrorManager = ErrorManager()
