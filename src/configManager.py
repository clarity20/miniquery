import sys
import os
import re
import subprocess
from enum import Enum
from sqlalchemy.sql import text

import miniEnv as env
from appSettings import miniSettings; ms = miniSettings
from miniUtils import sqlTypeToInternalType
from errorManager import miniErrorManager, ReturnCode; em = miniErrorManager
from expanderEngine import miniExpanderEngine; exp = miniExpanderEngine
from databaseConnection import miniDbConnection; dbConn = miniDbConnection

class RegexType(Enum):
    NORMAL = 0
    DEFAULT_INT = 1
    DEFAULT_ALPHA = 2
    DEFAULT_FLOAT = 3
    DEFAULT_DATE = 4
    DELETED = 5

class MasterDataConfig:
    '''
    Umbrella class that stores both the schematic information and the user
    configuration settings that pertain directly to the database(s),
    organized hierarchically.

    Program settings, OTOH, are stored in the AppSettings class.
    '''
    def __init__(self):
        # Set up a dictionary for the DB-specific configs
        self.databases = {}
        # Make client explicitly call setup(). He should wait until
        # the app settings are ready
        #self.setup()

    def loadDatabaseNames(self, databaseListFile):
        try:
            with open(databaseListFile, 'r') as databasesFp:
                # Create a placeholder dictionary entryfor each DB
                self.databases = dict((key.rstrip(), None) for key in databasesFp)

        except FileNotFoundError:
            query = 'SELECT {} FROM {}'.format('schema_name', 'information_schema.schemas')
            resultSet = dbConn.getConnection().execute(text(query))
            l = resultSet.fetchall()   # list of tuples
            self.databases = dict((key[0], None) for key in l)

        return ReturnCode.SUCCESS

    def changeDatabase(self, dbName):
        ''' Respond to a change of the main DB by lazy-loading its cfg '''
        if not self.databases.get(dbName):
            self.databases[dbName] = DatabaseConfig(dbName)
        return ReturnCode.SUCCESS

    def setup(self):
        filename = "{}/{}".format(env.MINI_CACHE, 'databases')
        self.loadDatabaseNames(filename)
        # Initialize the main DB
        mainDbName = ms.settings['Settings']['database']
        if mainDbName:
            self.databases[mainDbName] = DatabaseConfig(mainDbName)
        return ReturnCode.SUCCESS


class DatabaseConfig:
    '''
    Wrapper to hold list of table names.
    TODO: Add a ChainMap to group the table's column names together in one view.
    This would help tremendously with completion in auto-join situations.
    '''
    def __init__(self, dbName):
        self.dbName = dbName
        self.tableNames = []
        self.tables = {}
        self.setup()

    def loadTableNames(self, tableListFile):
        try:
            # Create a list of table names
            with open(tableListFile, 'r') as tablesFp:
                self.tableNames = [l.rstrip() for l in tablesFp]

        except FileNotFoundError:
            query = "SELECT {} FROM {} WHERE {} = '{}'".format(
                        "table_name",
                        "information_schema.tables",
                        "table_schema",
                        self.dbName)

            resultSet = dbConn.getConnection().execute(text(query))
            self.tableNames = resultSet.fetchall()   # list of tuples

        return ReturnCode.SUCCESS

    def changeMainTable(self, tableName):
        ''' Respond to a change of the main table by lazy-loading its cfg '''
        if tableName not in self.tables:
            self.tables[tableName] = TableConfig(tableName, self)
        return ReturnCode.SUCCESS

    def setup(self):
        filename = "{}/{}/{}".format(env.MINI_CACHE, self.dbName, 'information_schema.tables')
        self.loadTableNames(filename)
        # When initializing a DB, go ahead and initialize its main table
        mainTableName = ms.settings['Settings']['table']
        self.tables[mainTableName] = TableConfig(mainTableName, self)
        return ReturnCode.SUCCESS


class TableConfig:
    '''
    Wrapper to hold list of column names AND the user settings for a single table.
    '''
    def __init__(self, tableName, parent):
        self.config = {'standardColumns':'', 'primaryColumn':''}  # dict of k-v pairs
        self.tableName = tableName
        self.columnNames = []
        self.parent = parent     # reference to the containing db
        if self.tableName:
            self.setup()
        return

    def loadColumnNames(self, columnListFile,  metadataType = ''):
        try:
            # Create a list of size-3 tuples
            with open(columnListFile, 'r') as columnsFp:
                self.columnNames = [tuple(l.rstrip().split('\t')) for l in columnsFp]

        except FileNotFoundError:
            if metadataType:
                tableSchema = "information_schema"
                tableName = metadataType
            else:
                tableSchema = env.MINI_DBNAME
                tableName = re.search(r'(.*)\.columns$', columnListFile).group(1)

            query = "SELECT {} FROM {} WHERE {} = '{}' AND {} = '{}'".format(
                    'column_name, column_type, column_default',
                    'information_schema.columns',
                    'table_schema', tableSchema,
                    'table_name', tableName)

            resultSet = dbConn.getConnection().execute(text(query))
            self.columnNames = resultSet.fetchall()   # list of tuples

        return ReturnCode.SUCCESS

    def setup(self):
        filename = "{}/{}/{}.columns".format(env.MINI_CACHE,
                                                        self.parent.dbName,
                                                        self.tableName)
        self.loadColumnNames(filename)

        #TODO: Consider pre-loading all table configs at once
        configFile = "{}/{}.cfg".format(env.MINI_CONFIG, self.parent.dbName)
        if not self.loadConfigForTable(configFile, self.tableName):
            return em.returnCode

        return ReturnCode.SUCCESS


#    # Configuration for metadata proograms like findTable
#    def configureToMetadata(self, scriptName_0, metadataType):
#        a, b, scriptName = scriptName_0.rpartition('/')
#
#        if not self.loadColumnNameList("{}/{}".format(
#                                                        env.MINI_CACHE,
#                                                        metadataType),
#                                                        metadataType):
#            return em.returnCode
#
#        # Load the script-specific configuration
#        configFile = "{}/metadataScripts.cfg".format(env.MINI_CONFIG)
#        if not self.loadConfigForTable(configFile, scriptName):
#            return em.returnCode
#
#        return ReturnCode.SUCCESS


    # Load table-specific configuration settings
    def loadConfigForTable(self, configFile, tableName):
        sectionHeader = '['+tableName+']'
        nextSectionRE = re.compile(re.escape('['))
        isInsideSection = False
        regexMode = False
        regexCount = 0

        try:
            with open(configFile, 'r') as configFp:
                for line in configFp:

                    # Skip lines coming before the section of interest
                    if not isInsideSection:
                        if line.lstrip().startswith(sectionHeader):
                            isInsideSection = True
                        continue

                    # Stop when the next section begins
                    line = line.strip()
                    if re.match(nextSectionRE, line):
                        break

                    # Skip comments
                    elif line.startswith('#'):
                        continue

                    # Require the format "attributeName=value"
                    attribute, equalsSign, value = line.partition('=')
                    if not equalsSign:
                        continue

                    # Branch on the attribute. First handle the cases that
                    # pre-empt the regex state machine, namely, the "regex" and
                    # "default..." attributes
                    defaultAttr = re.match(r'default([A-Z].*)', attribute)
                    if defaultAttr:
                        regexMode = True

                        # Set the canonical regex and its type
                        regexType_0 = defaultAttr.group(1)
                        if regexType_0 == 'Int':
                            regex = r'^[-]?[:digit:]+$'
                            regexType = RegexType.DEFAULT_INT
                        elif regexType_0 == 'Alpha':
                            regex = r'^[[:alnum:]_\ .]+$'
                            regexType = RegexType.DEFAULT_ALPHA
                        elif regexType_0 == 'Float':
                            regex = r'^[-]?[:digit:]*\.[:digit:]+$'
                            regexType = RegexType.DEFAULT_FLOAT
                        elif regexType_0 == 'Date':
                            regex = r'^[0-9]{4}[/-][0-9]{1,2}[/-][0-9]{1,2}$'
                            regexType = RegexType.DEFAULT_DATE
                        sCount = str(regexCount)
                        self.config['regex' + sCount] = regex
                        self.config['regexType' + sCount] = regexType  #.value
                        # Increment the counter now because there might not be
                        # any further attributes for this regex. If there are,
                        # they will compensate for this pre-incrementation.
                        regexCount += 1

                    elif attribute == 'regex':
                        regexMode = True
                        regex = value
                        regexType = RegexType.NORMAL
                        sCount = str(regexCount)
                        self.config['regex' + sCount] = regex
                        self.config['regexType' + sCount] = regexType
                        # Do not increment the counter. The REQUIRED attribute
                        # "column" will do it.
                        # regexCount += 1

                    # The state machine for regexes. Different types of regex
                    # require or accept different special key-value specifiers.
                    elif regexMode:
                        if regexType == RegexType.DEFAULT_ALPHA:
                            # Optional specifier: length
                            if attribute == 'length':
                                regexCount -= 1   # roll the counter back - see "Increment the counter" above 
                                # Length limit(s) can be a range, a half-empty range or a solitary number
                                rangeMatch = re.match('([0-9]*)([^0-9])?([0-9]*)$', value)
                                sCount = str(regexCount)
                                self.config['lowerBounds' + sCount] = rangeMatch.group(1)
                                if rangeMatch.group(3):   # 5-10 or -10
                                    self.config['upperBounds' + sCount] = rangeMatch.group(3)
                                elif rangeMatch.group(2):   # 5-
                                    self.config['upperBounds' + sCount] = '99999'
                                else:    # a solitary number
                                    self.config['upperBounds' + sCount] = rangeMatch.group(3)
                                regexCount += 1
                                regexMode = False
                            else:
                                # Any other specifier signals that we are no longer in regex mode.
                                # Handle the specifier generically.
                                regexMode = self._acceptGenericConfig(attribute, value)

                        elif regexType == RegexType.NORMAL:
                            # Required specifier: column; no other specifiers are allowed
                            if attribute == 'column':
                                # Store the column, terminate regex mode and accept the regex
                                sCount = str(regexCount)
                                self.config['column' + sCount] = value
                                # Look up the column type in the global column
                                # list and store it. In the column list, accept
                                # a populated or an unpopulated table name column
                                column = [item for item in
                                    self.ColumnNames if item[0] == value]
                                if column and len(column) == 1:
                                    columnType = sqlTypeToInternalType(column[0][1])
                                    sCount = str(regexCount)
                                    self.config['columnType' + sCount] = columnType
                                    regexCount += 1
                                    regexMode = False
                                else:
                                    regexMode = False
                                    return em.setError(ReturnCode.ILL_FORMED_CONFIG_FILE)
                            else:
                                regexMode = False
                                return em.setError(ReturnCode.ILL_FORMED_CONFIG_FILE)

                        else:   # DEFAULT_INT, _FLOAT or _DATE
                            if attribute == 'range':
                                regexCount -= 1
                                #Store the numeric or calendar limits
                                if regexType == RegexType.DEFAULT_INT:
                                    match = re.match('([-]?[0-9]+)-([-]?[0-9]+)$', value)
                                elif RegexType == RegexType.DEFAULT_FLOAT:
                                    match = re.match('([0-9.]+)-([0-9.]+)$', value)
                                else:    # DEFAULT_DATE
                                    match = re.match('([0-9]{4}/[0-9]{1,2}/[0-9]{1,2})-([0-9]{4}/[0-9]{1,2}/[0-9]{1,2})$', value)
                                sCount = str(regexCount)
                                self.config['lowerBounds' + sCount] = match.group(1)
                                self.config['upperBounds' + sCount] = match.group(2)
                                regexCount += 1
                                regexMode = False

                    # Not in regex mode.
                    else:
                        regexMode = self._acceptGenericConfig(attribute, value)

        except FileNotFoundError:
            print('Database config file "{}" not found. Using system defaults.'.format(configFile))

        self.config['regexCount'] = regexCount

        if 'mainTable' not in self.config.keys():
            self.config['mainTable'] = tableName

        return ReturnCode.SUCCESS

    def _acceptGenericConfig(self, key, value):
        # Substitute values for variable names, if any
        if '$' in value:
            g = re.search(r'\$([A-Za-z_]+)', value)
            variable = g.group(0)
            value.replace(variable, ms.settings['Variables'][variable[1:]])

        self.config[key] = value
        return False     # the new value of regexMode

# Keep the data config and cache information in a dictionary indexed by DB name
masterDataConfig = MasterDataConfig()

