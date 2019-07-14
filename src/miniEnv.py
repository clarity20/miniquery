import os
from sys import exit

from errorManager import miniErrorManager, ReturnCode

# Declare the environment (for export)
HOME = ''
MINI_HOME = ''
MINI_CACHE = ''
MINI_CONFIG = ''

MINI_OPTIONS='-q -e'    #TODO: Move hard coded values to a MINI_DEFAULTS hidden from the user.

MINI_CONNECTION_STRING = ''
MINI_DBENGINE = ''
MINI_DRIVER_OR_TRANSPORT = ''
MINI_DBPATH = ''
MINI_USER = ''
MINI_PASSWORD = ''
MINI_HOST = ''
MINI_PORT = ''
MINI_DBNAME = ''
MINI_DRIVER_OPTIONS = ''

# Read the environment
def setEnv():
    global HOME, MINI_HOME, MINI_CACHE, MINI_CONFIG, MINI_OPTIONS
    global MINI_CONNECTION_STRING, MINI_DBENGINE, MINI_DRIVER_OR_TRANSPORT
    global MINI_USER, MINI_PASSWORD, MINI_HOST, MINI_PORT
    global MINI_DBPATH, MINI_DBNAME, MINI_DRIVER_OPTIONS

    # Load the optional-with-defaults settings
    HOME = os.environ['HOME']
    try:
        MINI_HOME = os.environ['MINI_HOME']
    except KeyError:
        MINI_HOME = HOME + '/miniquery'
    try:
        MINI_CACHE = os.environ['MINI_CACHE']
    except KeyError:
        MINI_CACHE = MINI_HOME + '/cache'
    try:
        MINI_CONFIG = os.environ['MINI_CONFIG']
    except KeyError:
        MINI_CONFIG = MINI_HOME + '/config'

    MINI_OPTIONS = _readOptionalVariable('MINI_OPTIONS')

    # Load the required environment settings
    try:
        # Not always needed for connectivity but for certain queries:
        MINI_DBNAME = os.environ['MINI_DBNAME']
    except KeyError:
        miniErrorManager.setError(ReturnCode.MISSING_ARGUMENT)
        return ReturnCode.MISSING_ARGUMENT

    #Load the connection-related settings
    MINI_CONNECTION_STRING = _readOptionalVariable('MINI_CONNECTION_STRING')
    if MINI_CONNECTION_STRING:
        # If we have this, the below connection-related variables are skippable
        return ReturnCode.SUCCESS
    
    MINI_DBENGINE = _readOptionalVariable('MINI_DBENGINE')    # 'mysql', etc.

    MINI_DBPATH = _readOptionalVariable('MINI_DBPATH')
    if MINI_DBPATH:
        # If we have this, the below connection-related variables are skippable
        return ReturnCode.SUCCESS

    MINI_DRIVER_OR_TRANSPORT  = _readOptionalVariable('MINI_DRIVER_OR_TRANSPORT')
    MINI_USER = _readOptionalVariable('MINI_USER')
    MINI_PASSWORD = _readOptionalVariable('MINI_PASSWORD')
    MINI_HOST = _readOptionalVariable('MINI_HOST')
    MINI_PORT = _readOptionalVariable('MINI_PORT')
    MINI_DRIVER_OPTIONS = _readOptionalVariable('MINI_DRIVER_OPTIONS')

    return ReturnCode.SUCCESS

def _readOptionalVariable(varName):
    # The try-except block is required by the language.
    # Use 'None' to enforce the variable's optionality.
    try:
        return os.environ[varName]
    except KeyError:
        return ''

