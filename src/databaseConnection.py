import sys
import miniEnv as env
from appSettings import miniSettings, fakePass; ms = miniSettings
from errorManager import miniErrorManager, ReturnCode; em = miniErrorManager
from sqlalchemy import create_engine
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import FormattedText

# Database connection class. Should be used like a singleton.
class databaseConnection():
    def __init__(self):
        self._cxn = None
        self._gotPassword = False
        self._dialect = None

    def __del__(self):
        if self._cxn:
            self._cxn.close()

    def setDialect(self, dialectNameOrStr, doParseString=False):
        if doParseString:
            # Look for either the form  xxx+  or  xxx:  at the onset of the string
            self._dialect = None
            m = re.match('(.*?)[+:]', driverNameOrStr)
            if m:
                self._dialect = m.groups(0)
        else:
            self._dialect = dialectNameOrStr

    def getDialect(self):
        return self._dialect

    def _tryToConnect(self, connectionString):
        try:
            engine = create_engine(connectionString)
            self._cxn = engine.connect()
        except Exception as e:
            em.setError(ReturnCode.DATABASE_CONNECTION_ERROR,
                         type(e).__name__, e.args)
            return None
        return self._cxn

    def getConnection(self):
        if self._cxn:
            return self._cxn
        
        cxnSettings = ms.settings['ConnectionString']
        defType = cxnSettings['definitionType']

        # Construct the connection string from the connection parms.
        # See www.github.com/xo/usql for a good discussion of the possibilities.
        # Even better is https://docs.sqlalchemy.org/en/13/core/
        #                       engines.html#sqlalchemy.create_engine
        if defType == 'FullString':
            connString = cxnSettings[defType]['MINI_CONNECTION_STRING']
            self.setDialect(connString, True)
            return self._tryToConnect(connString)

        # Paths are a simple, special case
        elif defType == 'FullPath':
            dialect = cxnSettings[defType]['MINI_DIALECT']
            self.setDialect(dialect)
            if dialect:
                connStr = '{}:{}'.format(dialect,
                        cxnSettings[defType]['MINI_DBPATH'])
            else:
                connStr = cxnSettings[defType]['MINI_DBPATH']

            return self._tryToConnect(connStr)

        # The definition type must be 'Components'. In this case we have to
        # build the string from the ground up, in "parts". We start
        # with the "dialect part."
        dialect = cxnSettings[defType]['MINI_DIALECT']
        self.setDialect(dialect)
        if cxnSettings[defType]['MINI_DRIVER']: # odbc, udp, ...
            dialectPart = '{}+{}'.format(dialect,
                    cxnSettings[defType]['MINI_DRIVER'])
        else:
            dialectPart = dialect

        userPart = ''
        if cxnSettings[defType]['MINI_USER']:
            if not cxnSettings[defType]['MINI_PASSWORD'] and not self._gotPassword:
                # In a tty (screen-interactive) situation, ask for a password
                if ms.isOutputTty:
                    msg ='Please enter password for user "{}": '.format(
                            cxnSettings[defType]['MINI_USER'])
                    cxnSettings[defType]['MINI_PASSWORD'] = prompt(
                            message=FormattedText([('yellow', msg)]), is_password=True)
                    self._gotPassword = True  # Prevents repeated asks in a no-password situation
                # In a non-tty situation (i.e. stdout is redirected), throw error
                else:
                    return em.setError(ReturnCode.MISSING_PASSWORD)
            # Use cmdline password if there is one, otherwise use config password
            if cxnSettings[defType]['MINI_PASSWORD'] == fakePass:
                cxnSettings[defType]['MINI_PASSWORD'] = ''
            userPart = '{}:{}'.format(cxnSettings[defType]['MINI_USER'],
                                        cxnSettings[defType]['MINI_PASSWORD'])

        hostPart = ''
        if cxnSettings[defType]['MINI_HOST']:
            if cxnSettings[defType]['MINI_PORT']:
                hostPart = '{}:{}'.format(cxnSettings[defType]['MINI_HOST'],
                                    cxnSettings[defType]['MINI_PORT'])
            else:
                hostPart = cxnSettings[defType]['MINI_HOST']

        if userPart and hostPart:
            # Insert an @ sign
            userHostPart = '{}@{}'.format(userPart, hostPart)
        else:
            # Take whatever is present, leaving the rest blank
            userHostPart = '{}{}'.format(userPart, hostPart)

        dbNamePart = ''
        dbName = ms.settings['Settings']['database']
        if dbName:
            if cxnSettings[defType]['MINI_DRIVER_OPTIONS']:
                dbNamePart = '{}?{}'.format(dbName,
                                cxnSettings[defType]['MINI_DRIVER_OPTIONS'])
            else:
                dbNamePart = dbName

        # Finalize the right-hand side
        rightHandSide = ''
        if userHostPart and dbNamePart:
            # Insert a slash mark
            rightHandSide = '{}/{}'.format(userHostPart, dbNamePart)
        else:
            # Take whatever is present, leaving the rest blank
            rightHandSide = '{}{}'.format(userHostPart, dbNamePart)

        # Finally:
        connStr = '{}://{}'.format(dialectPart, rightHandSide)
        return self._tryToConnect(connStr)

# The global instance
miniDbConnection = databaseConnection()
