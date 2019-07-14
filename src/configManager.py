import sys
import os
import re
import subprocess
from enum import Enum
from sqlalchemy.sql import text
#import pysnooper

import miniEnv as env
from miniUtils import sqlTypeToInternalType
from errorManager import miniErrorManager as em, ReturnCode
from expanderEngine import miniExpanderEngine as exp
from databaseConnection import miniDbConnection as dbConn
#from spellingExpander import spellExpander

class RegexType(Enum):
    NORMAL = 0
    DEFAULT_INT = 1
    DEFAULT_ALPHA = 2
    DEFAULT_FLOAT = 3
    DEFAULT_DATE = 4
    DELETED = 5

class ConfigManager:

    # member data
    def __init__(self):
        self.config = {}                  # dict of k-v pairs
        self.masterTableNameList = []     # list of names
        self.masterColumnNameList = []    # list of tuples

    def loadTableNameList(self, tableListFile):
        try:
            # Create a list of table names
            with open(tableListFile, 'r') as tablesFp:
                self.masterTableNameList = [tuple(l.rstrip().split('\t')) for l in tablesFp]

        except FileNotFoundError:
            query = "SELECT {} FROM {} WHERE {} = '{}'".format(
                        "table_name",
                        "information_schema.tables",
                        "table_schema",
                        env.MINI_DBNAME)

            resultSet = dbConn.getConnection().execute(text(query))
            self.masterTableNameList = resultSet.fetchall()   # list of tuples

        return ReturnCode.SUCCESS


    def loadColumnNameList(self, tableDescFile, metadataType = ''):
        try:
            # Create a list of size-3 tuples
            with open(tableDescFile, 'r') as columnsFp:
                self.masterColumnNameList = [tuple(l.rstrip().split('\t')) for l in columnsFp]

        except FileNotFoundError:
            if metadataType:
                tableSchema = "information_schema"
                tableName = metadataType
            else:
                tableSchema = env.MINI_DBNAME
                tableName = re.search(r'(.*)\.columns$', tableDescFile).group(1)

            query = "SELECT {} FROM {} WHERE {} = '{}' AND {} = '{}'".format(
                    'column_name, column_type, column_default',
                    'information_schema.columns',
                    'table_schema', tableSchema,
                    'table_name', tableName)

            resultSet = dbConn.getConnection().execute(text(query))
            self.masterColumnNameList = resultSet.fetchall()   # list of tuples

        return ReturnCode.SUCCESS


    # Configuration for schema-based programs like mini
    def configureToSchema(self, tableName_0):
        a, b, tableName = tableName_0.rpartition('/')

        if not self.loadTableNameList("{}/{}/{}".format(
                                                env.MINI_CACHE,
                                                env.MINI_DBNAME,
                                                'information_schema.tables')):
            return em.returnCode

        #MMMM: Activate this when the time comes:
#        expander = exp.tableExpander
#        tableList = expander.getExpandedNames(tableName)
        tableName = 'table1'
#        tableName = expander.promptForExpansion(tableName, tableList)
#
        if not self.loadColumnNameList("{}/{}/{}.columns".format(
                                                        env.MINI_CACHE,
                                                        env.MINI_DBNAME,
                                                        tableName)):
            return em.returnCode

        configFile = "{}/{}.cfg".format(env.MINI_CONFIG, env.MINI_DBNAME)
        if not self.loadConfigForTable(configFile, tableName):
            return em.returnCode

        return ReturnCode.SUCCESS


    # Configuration for metadata proograms like findTable
    def configureToMetadata(self, scriptName_0, metadataType):
        a, b, scriptName = scriptName_0.rpartition('/')

        if not self.loadColumnNameList("{}/{}".format(
                                                        env.MINI_CACHE,
                                                        metadataType),
                                                        metadataType):
            return em.returnCode

        # Load the script-specific configuration
        configFile = "{}/metadataScripts.cfg".format(env.MINI_CONFIG)
        if not self.loadConfigForTable(configFile, scriptName):
            return em.returnCode

        return ReturnCode.SUCCESS


    # Load table-specific configuration settings
    def loadConfigForTable(self, configFile, tableName):
        sectionHeader = '['+tableName+']'
        nextSectionRE = re.compile(re.escape('['))
        isInsideSection = False
        regexMode = False
        regexCount = 0

        with open(configFile, 'r') as configFp:
            for line in configFp:
                if not isInsideSection:
                    # Skip lines coming before the section of interest
                    if line.lstrip().startswith(sectionHeader):
                        isInsideSection = True
                else:
                    line = line.strip()
                    if re.match(nextSectionRE, line):
                        break
                    elif line.startswith('#'):
                        continue

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
                                    self.masterColumnNameList if item[0] == value]
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

        self.config['regexCount'] = regexCount

        if 'mainTable' not in self.config.keys():
            self.config['mainTable'] = tableName

        return ReturnCode.SUCCESS

    def _acceptGenericConfig(self, key, value):
        # Substitute values for shell variables, if any
        if '$' in value:
            g = re.match('\$[A-Za-z_]+', value)
            variable = g.group(0)
            value.replace(variable, os.environ[variable[1:]])

        self.config[key] = value
        return False     # the new value of regexMode


miniConfigManager = ConfigManager()
