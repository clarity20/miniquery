import sys

from errorManager import miniErrorManager, ReturnCode
from spellingExpander import spellExpander

class ConfigManager:

    # Class-level member data
    config = {}                  # dict of k-v pairs
    masterTableNameList = []     # list of names
    masterColumnNameList = []    # list of tuples

    def loadConfigForTable(self, configFile, tableName):
        return ReturnCode.SUCCESS

    def loadTableNameList(self, tableListFile):
        return ReturnCode.SUCCESS

    def loadColumnNameList(self, tableDescFile):
        return ReturnCode.SUCCESS

    # Configuration for schema-based programs like mini
    def configureToSchema(self, tableName_0):
        a, b, tableName = tableName_0.rpartition('/')

#        masterTableNameList = self.loadTableNameList("{}/{}/{}".format(
#                                                    MINI_CACHE,
#                                                    MINI_DBNAME,
#                                                    'information_schema.tables'))
#        expander = miniExpanderEngine.tableExpander   #MMMM Need an accessor fcn???
#        tableList = expander.getExpandedNames(tableName)
#        tableName = expander.promptForExpansion(tableName, tableList)
#
#        #MMMM: in old code, this fcn can throw an error - notice the "|| return $?"
#        masterColumnNameList = self.loadColumnNameList("{}/{}/{}.columns".format(
#                                                        MINI_CACHE,
#                                                        MINI_DBNAME,
#                                                        tableName))
#
        configFile = "{}/{}.cfg".format(MINI_CONFIGS, MINI_DBNAME)
        #MMMM as above, handle possible error:
        tableName='table1'
        loadConfigForTable(configFile, tableName)

        return ReturnCode.SUCCESS

    # Configuration for metadata proograms like findTable
    def configureToMetadata(self, scriptName, metadataType):
        return ReturnCode.SUCCESS

miniConfigManager = ConfigManager()
