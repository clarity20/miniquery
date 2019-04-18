import sys
from enum import Enum

#MMMM Need a numeric value that can serve as a return code
#MMMM and a string-template that can be populated and displayed
class ErrorType(Enum):
    SUCCESS = 0
    # Ultimately an Enum is not desirable, see comments above

def setError(msg):
    errMsg = msg
    return 0

def doExit(errMsg):
    print(errMsg)
    sys.exit(errorCode)
