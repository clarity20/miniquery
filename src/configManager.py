import sys
import os
import re
import subprocess
from enum import Enum
import pysnooper

import miniEnv as env
from errorManager import miniErrorManager as em, ReturnCode
#from spellingExpander import spellExpander

class RegexType(Enum):
    NORMAL = 0
    DEFAULT_INT = 1
    DEFAULT_ALPHA = 2
    DEFAULT_FLOAT = 3
    DEFAULT_DATE = 4
    DELETED = 5

class ConfigManager:

    # Class-level member data
    config = {}                  # dict of k-v pairs
    masterTableNameList = []     # list of names
    masterColumnNameList = []    # list of tuples

    @pysnooper.snoop()
    def loadTableNameList(self, tableListFile):
        try:
            tablesFp = open(tableListFile, 'r')
            self.masterTableNameList = tablesFp.read().splitlines()
            tablesFp.close()
        except FileNotFoundError:
            #TODO Eventually we should use the pythonic db connection interfaces 
            #TODO but for now we spawn the DB commandline utility as a subprocess.
            #TODO How we do this will of course depend on the DBMS type.
            #TODO We need to invoke it so as to produce a headless tab-delimited result set.
            program = 'mysql'
            args = '-B -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema=\'' \
            + env.MINI_DBNAME + '\'"'
            proc = subprocess.run([program, args], stdout=subprocess.PIPE).stdout.decode('utf-8')
            self.masterTableNameList = proc.splitlines()

        return ReturnCode.SUCCESS


    def loadColumnNameList(self, tableDescFile):
        return ReturnCode.SUCCESS


    # Configuration for schema-based programs like mini
    def configureToSchema(self, tableName_0):
        a, b, tableName = tableName_0.rpartition('/')

        self.masterTableNameList = self.loadTableNameList("{}/{}/{}".format(
                                                    env.MINI_CACHE,
                                                    env.MINI_DBNAME,
                                                    'information_schema.tables'))
#        expander = miniExpanderEngine.tableExpander   #MMMM Need an accessor fcn???
#        tableList = expander.getExpandedNames(tableName)
#        tableName = expander.promptForExpansion(tableName, tableList)
#
#        #MMMM: in old code, this fcn can throw an error - notice the "|| return $?"
#        masterColumnNameList = self.loadColumnNameList("{}/{}/{}.columns".format(
#                                                        env.MINI_CACHE,
#                                                        env.MINI_DBNAME,
#                                                        tableName))
#
        configFile = "{}/{}.cfg".format(env.MINI_CONFIG, env.MINI_DBNAME)
        #MMMM as above, handle possible error:
        tableName = 'table1'
        self.loadConfigForTable(configFile, tableName)

        return ReturnCode.SUCCESS


    # Configuration for metadata proograms like findTable
    def configureToMetadata(self, scriptName, metadataType):
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
                    line = line.lstrip()
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
                                self.config[attribute] = value
                                regexMode = False

                        elif regexType == RegexType.NORMAL:
                            # Required specifier: column; no other specifiers are allowed
                            if attribute == 'column':
                                # Store the column, terminate regex mode and accept the regex
                                sCount = str(regexCount)
                                self.config['column' + sCount] = value
                                # Look up the column type in the global column
                                # list and store it. In the column list, accept
                                # a populated or an unpopulated table name column
                                print('MMMM build and search masterColumnList the new way')
                                # This does not work because masterCNL is a list of tuples, not a string:
#                                match = re.search('\n [^ ]*\ +' + value + '[\ ]+([a-z]+)', self.masterColumnNameList)
#                                if match:
#                                    columnType = match.group(1)
#                                    #TODO sqlTypeToInternalType (columnType)
#                                    sCount = str(regexCount)
#                                    self.config[columnType + sCount] = columnType
#                                    regexCount += 1
#                                    regexMode = False
#                                else:
#                                    regexMode = False
#                                    return em.setError(ReturnCode.ILL_FORMED_CONFIG_FILE)
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
                            else:
                                self.config[attribute] = value
                                regexMode = False


        self.config[regexCount] = regexCount

        if 'mainTable' not in self.config.keys():
            self.config['mainTable'] = tableName

        return ReturnCode.SUCCESS


miniConfigManager = ConfigManager()
