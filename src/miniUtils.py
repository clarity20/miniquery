import re
from enum import Enum

class TokenType(Enum):
    INTEGER = 1,
    STRING_CONSTANT = 2,
    DECIMAL = 3,
    DATE = 4,
    TIME = 5,
    TIMESTAMP = 6,
    BLOB = 7,
    SET = 8,
    INVALID_TYPE = 0


def sqlTypeToInternalType(sqlType_0):
    sqlType_0, a, b = sqlType_0.partition(' ')
    sqlType = sqlType_0.lower()

    # Note carefully the differing semantics of the following comparisons
    if 'int' in sqlType or re.match('bool|bit|year', sqlType):
        internalType = TokenType.INTEGER
    elif 'char' in sqlType or re.search('binary|enum', sqlType):
        internalType = TokenType.STRING_CONSTANT
    elif re.match('dec|num|double|float|fix', sqlType):
        internalType = TokenType.DECIMAL
    elif sqlType == 'date':
        internalType = TokenType.DATE
    elif sqlType == 'time':
        internalType = TokenType.TIME
    elif 'time' in sqlType:    #datetimes and timestamps
        internalTime = TokenType.TIMESTAMP
    elif 'blob' in sqlType or 'text' in sqlType:
        internalType = TokenType.BLOB
    elif sqlType == 'set':
        internalType = TokenType.SET
    else:
        internalType = TokenType.INVALID_TYPE

    return internalType
