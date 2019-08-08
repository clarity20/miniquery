import miniEnv as env
from appSettings import miniSettings as ms
from errorManager import miniErrorManager as em, ReturnCode
from sqlalchemy import create_engine

# Database connection class. Should be used like a singleton.
class databaseConnection():
    def __init__(self):
        self._cxn = None
        self._gotPassword = False

    def __del__(self):
        if self._cxn:
            self._cxn.close()

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
            return self._tryToConnect(cxnSettings[defType]['MINI_CONNECTION_STRING'])

        # Paths are a simple, special case
        elif defType == 'FullPath':
            if cxnSettings[defType]['MINI_DBENGINE']:
                connStr = '{}:{}'.format(cxnSettings[defType]['MINI_DBENGINE'],
                        cxnSettings[defType]['MINI_DBPATH'])
            else:
                connStr = cxnSettings[defType]['MINI_DBPATH']

            return self._tryToConnect(connStr)

        # General case: Build the string from the ground up
        if cxnSettings[defType]['MINI_DRIVER_OR_TRANSPORT']: # odbc, udp, ...
            driverPart = '{}+{}'.format(cxnSettings[defType]['MINI_DBENGINE'],
                    cxnSettings[defType]['MINI_DRIVER_OR_TRANSPORT'])
        else:
            driverPart = cxnSettings[defType]['MINI_DBENGINE']

        userPart = ''
        if cxnSettings[defType]['MINI_USER']:
            if not cxnSettings[defType]['MINI_PASSWORD'] and not self._gotPassword:
                from getpass import getpass
                cxnSettings[defType]['MINI_PASSWORD'] = getpass('Please enter password: ')
                self._gotPassword = True  # Prevents repeated asks in a no-password situation
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
        connStr = '{}://{}'.format(driverPart, rightHandSide)
        return self._tryToConnect(connStr)

# The global instance
miniDbConnection = databaseConnection()
