import miniEnv as env
from errorManager import miniErrorManager as em, ReturnCode
from sqlalchemy import create_engine

# Database connection class. Should be used like a singleton.
class databaseConnection():
    _cxn = None

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
        
        # Construct the connection string from the connection parms.
        # See www.github.com/xo/usql for a good discussion of the possibilities.
        # Even better is https://docs.sqlalchemy.org/en/13/core/
        #                       engines.html#sqlalchemy.create_engine
        if env.MINI_CONNECTION_STRING:
            return self._tryToConnect(env.MINI_CONNECTION_STRING)

        # Paths are a simple, special case
        if env.MINI_DBPATH:
            if env.MINI_DBENGINE:
                connStr = '{}:{}'.format(env.MINI_DBENGINE, env.MINI_DBPATH)
            else:
                connStr = env.MINI_DBPATH

            return self._tryToConnect(connStr)

        # General case: Build the string from the ground up
        if env.MINI_DRIVER_OR_TRANSPORT:  # either the driver (odbc) or transport (udp)
            driverPart = '{}+{}'.format(env.MINI_DBENGINE, env.MINI_DRIVER_TRANSPORT)
        else:
            driverPart = env.MINI_DBENGINE

        userPart = ''
        if env.MINI_USER:
            if not env.MINI_PASSWORD:
                from getpass import getpass
                env.MINI_PASSWORD = getpass('Enter password: ')
            userPart = '{}:{}'.format(env.MINI_USER, env.MINI_PASSWORD)

        hostPart = ''
        if env.MINI_HOST:
            if env.MINI_PORT:
                hostPart = '{}:{}'.format(env.MINI_HOST, env.MINI_PORT)
            else:
                hostPart = env.MINI_HOST

        if userPart and hostPart:
            # Insert an @ sign
            userHostPart = '{}@{}'.format(userPart, hostPart)
        else:
            # Take whatever is present, leaving the rest blank
            userHostPart = '{}{}'.format(userPart, hostPart)

        dbNamePart = ''
        if env.MINI_DBNAME:
            if env.MINI_DRIVER_OPTIONS:
                dbNamePart = '{}?{}'.format(env.MINI_DBNAME, env.MINI_DRIVER_OPTIONS)
            else:
                dbNamePart = env.MINI_DBNAME

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
