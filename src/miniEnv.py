import os
from sys import exit

from errorManager import miniErrorManager as em, ReturnCode

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
    HOME = os.environ['HOME']
    try:
        MINI_HOME = os.environ['MINI_HOME']
    except KeyError:
        MINI_HOME = os.path.join(HOME, 'miniquery')
    try:
        MINI_CACHE = os.environ['MINI_CACHE']
    except KeyError:
        MINI_CACHE = os.path.join(MINI_HOME, 'cache')
    try:
        MINI_CONFIG = os.environ['MINI_CONFIG']
    except KeyError:
        MINI_CONFIG = os.path.join(MINI_HOME, 'config')

    MINI_OPTIONS = _readOptionalVariable('MINI_OPTIONS')

    try:
        os.environ['EDITOR']   # Make sure it is set, but don't need the value
    except KeyError:
        em.doWarn('NOTE: Please set the EDITOR environment variable to your editor of choice for best results.')

    return ReturnCode.SUCCESS

def _readOptionalVariable(varName):
    # The try-except block is required by the language.
    # Use 'None' to enforce the variable's optionality.
    try:
        return os.environ[varName]
    except KeyError:
        return ''

def setDatabaseName(name):
    global MINI_DBNAME
    MINI_DBNAME = name
    return

