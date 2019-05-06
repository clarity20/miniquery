import os
from sys import exit

from errorManager import miniErrorManager, ReturnCode

# Declare the environment (for export)
HOME = ''
MINI_HOME = ''
MINI_CACHE = ''
MINI_CONFIG = ''
MINI_DBNAME = ''
MINI_USER = ''
MINI_HOST = ''
MINI_PASSWORD = ''

# Read the environment
def setEnv():
    global HOME, MINI_HOME, MINI_CACHE, MINI_CONFIG
    global MINI_DBNAME, MINI_USER, MINI_HOST, MINI_PASSWORD

    # Load the optional environment settings
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
    try:
        # For security, allow password to be blank
        MINI_PASSWORD = '=' + os.environ['MINI_PASSWORD']
    except KeyError:
        MINI_PASSWORD = ''

    # Load the required environment settings
    try:
        MINI_DBNAME = os.environ['MINI_DBNAME']
        MINI_USER = os.environ['MINI_USER']
        MINI_HOST = os.environ['MINI_HOST']
    except KeyError:
        miniErrorManager.setError(ReturnCode.MISSING_ARGUMENT)
        return ReturnCode.MISSING_ARGUMENT

    return ReturnCode.SUCCESS
