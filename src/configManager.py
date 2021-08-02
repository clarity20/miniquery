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
        self.activeDatabase = None
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

    def setActiveDatabase(self, dbName):
        ''' Lazy-load and point to the new main DB when it changes '''
        if not self.databases.get(dbName):
            self.databases[dbName] = DatabaseConfig(dbName)
        return self.databases[dbName]

    def setup(self):
        ''' Load the list of DB names and the config of the main DB '''
        filename = "{}/{}".format(env.MINI_CACHE, 'databases')
        self.loadDatabaseNames(filename)
        # Initialize the active DB
        activeDbName = ms.settings['Settings']['database']
        self.activeDatabase = self.setActiveDatabase(activeDbName)
        return ReturnCode.SUCCESS

class DatabaseConfig:
    '''
    Wrapper to hold a list of table names plus configs for each table.
    TODO: Add a ChainMap to group the table's column names together in one view.
    This would help tremendously with completion in auto-join situations.
    '''

    DB_CONFIG_SECTION_HEADER = 'DBCONFIG'

    def __init__(self, dbName):
        self.dbName = dbName
        self.config = {}
        self.tableNames = []
        self.tables = {}

        # Track which config attributes have changed since the last save, and whether to save them.
        # This will tell us how the next save operation has to touch the DB config file.
        #TODO: For now, we track just the 'anchorTable' to keep it in sync with
        #TODO: settings['settings']['table']. If we set up a proper DB config
        #TODO: wizard we would also keep track of *all* attributes which
        #TODO: have changed so the user can choose which changes to save.
        self.configChanges = dict()

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

    def changeAnchorTable(self, anchorTableName):
        ''' Respond to a change of the anchor table by lazy-loading its cfg '''
        if not self.tables.get(anchorTableName):
            # Table not loaded. Time to lazy-load it.
            self.tables[anchorTableName] = TableConfig(anchorTableName, self)
        else:
            # This table is already known to MINIQUERY. We are simply
            # changing the choice of anchor table.
            self.configChanges.add({'anchorTable':True})    # format={attrName : bDoSave}

        self.config['anchorTable'] = anchorTableName
        return ReturnCode.SUCCESS

    def setup(self):
        filename = "{}/{}/{}".format(env.MINI_CACHE, self.dbName, 'information_schema.tables')
        self.loadTableNames(filename)
        # When initializing a DB, go ahead and initialize its anchor table
        self.config = self.readDatabaseConfig()
        anchorTableName = self.config.get('anchorTable')
        if anchorTableName:
            self.tables[anchorTableName] = TableConfig(anchorTableName, self)
        return ReturnCode.SUCCESS

    def readDatabaseConfig(self):
        ''' Reads the db-level config settings atop the config file '''
        configFile = "{}/{}.cfg".format(env.MINI_CONFIG, self.dbName)
        dbLevelConfig = TableConfig(None, self)
        dbLevelConfig.loadConfigForTable(configFile, DatabaseConfig.DB_CONFIG_SECTION_HEADER)
        return dbLevelConfig.config

    def _findSectionHeaderInConfigFile(self, data, sectionName):
        lineCount = 0
        foundSection = False
        sectionHeader = '[{}]'.format(sectionName)
        for line in data:
            if line == sectionHeader:
                foundSection = True
                break
            else:
                lineCount += 1
        if not foundSection:
            #TODO: Use errorMgr for proper error handling
            print('"%s" section missing from DB config file.' % sectionName)
            return -1
        return lineCount


    def saveConfigChanges(self):
        # The DB configs are too irregular to admit of easy manipulation through
        # the ConfigObj class. So we go primitive: To save the config file
        # we load it as a list of lines, modify the lines as appropriate, and
        # resave the whole file.
        configFile = "{}/{}.cfg".format(env.MINI_CONFIG, self.dbName)

        configFile = "{}/{}.cfg".format(env.MINI_CONFIG, "foo")

        with open(configFile, 'r') as configFp:
            configLines = [l.rstrip() for l in configFp]

        # Walk the collection of config changes, tweaking the lines of the config file
        for changeItem in self.configChanges.items():
            if isinstance(changeItem, dict):
                # The current changeItem is actually the full set of config changes for
                # a specific subsection (= table name). Find the subsection and change the lines therein.
                tableName, changeDict = changeItem
                sectionHeader = '[{}]'.format(tableName)

                # Find the section header in the file lines
                lineCount = self._findSectionHeaderInConfigFile(configLines, tableName)

                # Now we are in the section
                for line in configLines[lineCount:]:
                    # If all changes have been found and processed, stop
                    if not changeDict:
                        break
                    # Detect end of current section
                    elif line.startswith('['):
                        # end of section and not all entries of changeDict found
                        #TODO: Use errorMgr for proper error handling
                        print('Attributes not found in DB config: %s' % [x for x in changeDict.keys()])
                        break
                    # See if the current config line is one that needs to be changed
                    else:
                        key, eq, value = line.partition('=')
                        if key in changeDict and changeDict[key] == True:
                            # Edit the config line by pasting in the value from the "hot" table config
                            value = self.tables[tableName].config[key]
                            configLines[lineCount] = '{0}={1}'.format(key, value)
                            lineCount += 1
                            # Drop the change from the changeDict
                            del changeDict[key]

            else:
                # The current changeItem is a key-value pair: (attributeName, bDoSave).
                # Change the matching line in the special DBCONFIG section holding the db-level changes
                attributeName, shouldSaveChange = changeItem

                # Find the section header in the file lines
                lineCount = self._findSectionHeaderInConfigFile(configLines, self.DB_CONFIG_SECTION_HEADER)

                # Go through the section until we find the matching line
                for line in configLines[lineCount:]:
                    if line.startswith('['):
                        # End of section and matching line not found
                        print('Attribute %s not found in DB config' % attributeName)
                        break
                    else:
                        # Set the value to be saved equal to the value in memory
                        key, eq, value = line.partition('=')
                        if key == attributeName and shouldSaveChange == True:
                            value = self.config[key]
                            configLines[lineCount] = '{0}={1}'.format(key, value)
                            lineCount += 1

        # Write the file and make sure the whole change set is emptied out / reset
        try:
            with open(configFile, 'w') as configFp:
                for line in configLines:
                    configFp.write("%s\n", line)
        except PermissionError as ex:
            return em.setException(ex, "Unable to write DB config file")

        self.configChanges.clear()
        return ReturnCode.SUCCESS

class TableConfig:
    '''
    Wrapper to hold list of column names AND the user settings for a single table.
    '''
    def __init__(self, tableName, parent):
        self.config = {'standardColumns':'', 'primaryColumn':''} if tableName else {}
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

                    # Require the lines to have format "attributeName=value"
                    attribute, equalsSign, value = line.partition('=')
                    if not equalsSign:
                        continue

                    # Branch on the attribute. First handle the attribute names that
                    # pre-empt the regex state machine, namely, the "default..."
                    # and "regex" attributes
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
                                    self.columnNames if item[0] == value]
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
                                # Store the numeric or calendar limits
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

        if self.tableName:
            self.config['regexCount'] = regexCount

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

