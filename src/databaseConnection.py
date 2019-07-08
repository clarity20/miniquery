import miniEnv as env
from sqlalchemy import create_engine

# Database connection class. Should be used like a singleton.
class databaseConnection():
    _cxn = None

    def getConnection(self):
        if self._cxn:
            return self._cxn
        
        # Construct the connection string from the connection parms.
        # See www.github.com/xo/usql for a good discussion of the possibilities.

        if env.MINI_CONNECTION_STRING:
            engine = create_engine(env.MINI_CONNECTION_STRING)
            self._cxn = engine.connect()
            return self._cxn

        # Paths are a simple, special case
        if env.MINI_DBPATH:
            if env.MINI_DBENGINE:
                connStr = '{}:{}'.format(env.MINI_DBENGINE, env.MINI_DBPATH)
            else:
                connStr = env.MINI_DBPATH

            engine = create_engine(connStr)
            self._cxn = engine.connect()
            # Short circuit the subsequent logic, it is not needed
            return self._cxn

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
        print("Connection string:")
        print(connStr)

        engine = create_engine(connStr)
        print("engine:")
        print(engine)
        self._cxn = engine.connect()
        print("dbConn:")
        print(self._cxn)

        return self._cxn

# The global instance
miniDbConnection = databaseConnection()
