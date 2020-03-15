import os
import platform

from errorManager import miniErrorManager, ReturnCode; em = miniErrorManager

# Declare the environment (for export)
HOME = ''
MINI_HOME = ''
MINI_CACHE = ''
MINI_CONFIG = ''

MINI_OPTIONS='-q -e'    # This env is a back door, NOT to be documented.

MINI_DBNAME = ''

# Read the environment
def setEnv():
    global HOME, MINI_HOME, MINI_CACHE, MINI_CONFIG, MINI_OPTIONS

    # Load the optional-with-defaults settings
    homeVariable = 'USERPROFILE' if platform.system() == 'Windows' else 'HOME'
    HOME = os.getenv(homeVariable)
    MINI_HOME = os.getenv('MINI_HOME', HOME + os.sep + 'miniquery')
    MINI_CACHE = os.getenv('MINI_CACHE', MINI_HOME + os.sep + 'cache')
    MINI_CONFIG = os.getenv('MINI_CONFIG', MINI_HOME + os.sep + 'config')
    MINI_OPTIONS = _readOptionalVariable('MINI_OPTIONS')

    try:
        os.getenv('EDITOR')   # Make sure it is set, but don't need the value
    except KeyError:
        em.doWarn('NOTE: Please set the EDITOR environment variable to your editor of choice for best results.')

    return ReturnCode.SUCCESS

def _readOptionalVariable(varName):
    return os.getenv(varName, '')

def setDatabaseName(name):
    global MINI_DBNAME
    MINI_DBNAME = name
    return

