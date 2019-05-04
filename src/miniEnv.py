import os
from sys import exit

from errorManager import miniErrorManager, ReturnCode

# Declare the environment (for export)
HOME = ''
MINI_HOME = ''
MINI_CACHE = ''
MINI_CONFIG = ''
MINI_DBNAME = ''

# Read the environment
def setEnv():
    # Tend to the defaultable environment settings
    global HOME, MINI_HOME, MINI_CACHE, MINI_CONFIG
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

    # Tend to the required environment settings
    try:
        global MINI_DBNAME
        MINI_DBNAME = os.environ['MINI_DBNAME']
    except KeyError:
        miniErrorManager.setError(ReturnCode.MISSING_ARGUMENT)
        return ReturnCode.MISSING_ARGUMENT

    return ReturnCode.SUCCESS
