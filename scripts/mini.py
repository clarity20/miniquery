import os
import sys
import re
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.styles import Style
from prompt_toolkit.enums import EditingMode

# MINIQUERY custom imports:
sys.path.append(".." + os.sep + "src")
import miniEnv as env
from miniHelp import giveMiniHelp
from appSettings import miniSettings as ms
from errorManager import miniErrorManager as em, ReturnCode
from configManager import masterDataConfig as dataConfig
from argumentClassifier import ArgumentClassifier
from queryProcessor import QueryProcessor, HiddenQueryProcessor
from databaseConnection import miniDbConnection as dbConn
from prompts import stringToPrompt

sys.path.append(".." + os.sep + "util")
from miniCompleter import MiniCompleter
from commandCompleter import CommandCompleter
from miniGlobals import settingOptionsMap, commandList, tqlCommands, tqlArgumentSummaries, tqlDescriptions
from miniDialogs import yes_no_dialog, button_dialog, input_dialog, MiniListBoxDialog, MiniFileDialog

class MiniFileHistory(FileHistory):
    '''
    A specialized FileHistory that handles file access issues gracefully
    '''
    def __init__(self, filename):
        self._doStore = True
        super(MiniFileHistory, self).__init__(filename)

    def store_string(self, string: str):
        if self._doStore:
            try:
                FileHistory.store_string(self, string)
            except PermissionError as ex:
                self._doStore = False
                em.setException(ex, "Miniquery command history file", "Commands will not be saved.")

class MiniqueryApp():
    def __init__(self, settingsFile=None):
        self._programSettingsFile=settingsFile
        self._args = None

    def setHistory(self, history):
        self._historyObject = history

    def dispatchCommand(self, cmd):
        # Unravel aliases and variables
        leader = ms.settings['leader']
        if cmd.startswith(leader):
            cmd = self._unravelVariables(self._unravelAliases(cmd, leader))
        else:
            cmd = self._unravelVariables(cmd)
    
        # Preprocess the command and distinguish system commands from queries
        argv = commandToWordList(cmd)
        if em.getError() != ReturnCode.SUCCESS:
            em.doWarn()
            return em.getError()
        self._args = ArgumentClassifier().classify(argv, leader)
    
        # Process the command as a query or as a system command
        if self._args._isQueryCommand:
            retValue = QueryProcessor(self._args).process()
            if retValue != ReturnCode.SUCCESS:
                # Warn the user the query cannot be processed and continue the command loop
                #TODO Verify that changed environments are actually re-loaded
                em.doWarn()
                return retValue
        else:
            # Invoke the callback for the command
            if self._args._commandName:
                try:
                    name = callbackMap[self._args._commandName]
                    callbackName = 'do' + name.replace(name[:1], name[:1].upper(), 1)
                    callback = getattr(self, callbackName, None)
                    result = callback(argv)
                except KeyError:
                    print('Unknown command "'+ self._args._commandName + '"')
                    return ReturnCode.SUCCESS
            else:
                return ReturnCode.SUCCESS
    
            if result in [ReturnCode.SUCCESS, ReturnCode.USER_EXIT]:
                return result
            elif result == ReturnCode.DATABASE_CONNECTION_ERROR:
                # Allow the user to fix the connection settings and keep going.
                #TODO One situation is a failed cxn due to bad cxn strings.
                #TODO Accept changes, & upon "reconnect" cmd, try to reconnect.
                em.doWarn()
                return ReturnCode.SUCCESS
            else:
                print('Unrecognized return code for command "%s".' % cmd)
                return ReturnCode.SUCCESS
    
        return ReturnCode.SUCCESS

    def doHistory(self, argv):
        argc = len(argv)

        if argc > 0 and not argv[0].isdecimal():
            em.setError(ReturnCode.ILLEGAL_ARGUMENT)
            em.doWarn(msg='ERROR: A positive number is required.')
            return ReturnCode.SUCCESS

        l = list(reversed(self._historyObject.get_strings()))
        available = len(l)
        requested = int(argv[0] if argc > 0 else ms.settings['historyLength'])
        print("\n".join(l[0:min(available, requested)]))
        return ReturnCode.SUCCESS

    def doSql(self, sql):
        fullSql = " ".join(sql)
        retValue = QueryProcessor(self._args).process(fullSql)
        if retValue != ReturnCode.SUCCESS:
            em.doWarn()
            return ReturnCode.SUCCESS  #TODO: Keep the "real" error code, here and elsewhere

        # Update program state in the case of a "use" query (database-switching)
        if fullSql.upper().startswith("USE "):
            dbName = fullSql[4:]
            self.doSetDatabase(dbName)

        return ReturnCode.SUCCESS

    def doQuit(self, argv):
        if ms.isChanged():
            choice = button_dialog(title='Save before quitting?',
                    text='Save changes to your MINIQUERY settings before quitting?',
                    buttons=[('Yes',True), ('No',False), ('Cancel',None)])
            if choice:     # User pressed Yes: Try to save then quit
                choice = MiniFileDialog('Save Settings File', self._programSettingsFile,
                        can_create_new=True)
                if not choice:
                    return ReturnCode.SUCCESS
                # Try to write the config file
                self._programSettingsFile = choice
                ms._settings.filename = self._programSettingsFile
                if ms._settings.save() == ReturnCode.FILE_NOT_WRITABLE:
                    exc = em.getException()
                    em.doWarn()
                    return ReturnCode.SUCCESS
                return em.setError(ReturnCode.USER_EXIT)
            elif choice == None:     # User pressed Cancel: Resume normal execution
                return ReturnCode.SUCCESS
            elif choice == False:     # User pressed No: Quit immediately
                return em.setError(ReturnCode.USER_EXIT)
        else:
            if yes_no_dialog(title='Quit MINIQUERY',
                    text='Exit MINIQUERY: Are you sure?'):
                return em.setError(ReturnCode.USER_EXIT)
            return ReturnCode.SUCCESS

    def doSave(self, argv):
        argc = len(argv)

        if ms.isChanged():
            # Save program settings, variables and aliases
            if ms.isOutputTty:
                choice = MiniFileDialog('Save Settings File', self._programSettingsFile,
                        can_create_new=True) if argc<1 else argv[0]
                if not choice:
                    return ReturnCode.SUCCESS
            else:
                choice = argv[0] if argc>=1 else self._programSettingsFile

            if choice:
                self._programSettingsFile = choice
                ms._settings.filename = self._programSettingsFile
                if ms._settings.save() == ReturnCode.FILE_NOT_WRITABLE:
                    exc = em.getException()
                    em.doWarn()
                    return ReturnCode.SUCCESS
        else:
            em.doWarn(msg='No unsaved changes.')

        dbConfig = dataConfig.databases[ms.settings['database']]
        if dbConfig.configChanges:
            # Save DB config and reset configChanges
            if dbConfig.saveConfigChanges() != ReturnCode.SUCCESS:
                em.doWarn()
        return ReturnCode.SUCCESS

    def doSetTable(self, argv):
        currDbName = ms.settings['database']
        tableList = dataConfig.databases[currDbName].tableNames
        if not tableList:
            em.setError(ReturnCode.Clarification)
            em.doWarn("No tables for DB %s." % currDbName)
            return ReturnCode.SUCCESS

        # Do not allow simple erasure of the table name. See doSetDatabase().
        if len(argv) == 0:
            tableName = MiniListBoxDialog(title='Select a table', itemList=tableList)
            if not tableName:
                return ReturnCode.SUCCESS
        else:
            tableName = argv[0]
            if not tableName in tableList:
                em.setError(ReturnCode.TABLE_NOT_FOUND)
                em.doWarn()

        currAnchorTable = ms.settings['table']
        if tableName == currAnchorTable:
            em.setError(ReturnCode.Clarification)
            em.doWarn("Anchor table is already " + currAnchorTable + ".")
            return ReturnCode.SUCCESS
        ms.settings['table'] = tableName
        dataConfig.databases[currDbName].changeAnchorTable(tableName)
        return ReturnCode.SUCCESS

    def doFormat(self, argv):
        argc = len(argv)

        optionsTuple = settingOptionsMap['format']
        choice = self._chooseValueFromList(optionsTuple[0], 'Settings', 'format',
                    optionsTuple[1], optionsTuple[2],
                    userEntry=argv[0] if argc >= 1 else None)
        if choice >= 0:
            self._args._persistentOptions[optionsTuple[0][choice]] = True
        return ReturnCode.SUCCESS

    def doSetDatabase(self, argv):
        # Do not allow simple erasure of the db name. Bring up a selection dlg
        # offering the option to cancel back to the current name. Since the set
        # of DBs is (only) changeable by CREATE DATABASE, use a list box.
        if len(argv) == 0:
            dbList = list(iter(dataConfig.databases))
            dbName = MiniListBoxDialog(title='Select a database', itemList=dbList)
            if not dbName:
                return ReturnCode.SUCCESS
        else:
            dbName = argv[0] if len(argv) > 0 else ''

        currDbName = ms.settings['database']
        if dbName == currDbName:
            em.setError(ReturnCode.Clarification)
            em.doWarn("Database is already " + currDbName + ".")
            return ReturnCode.SUCCESS

        # Quietly run a "use" query to make the change effective.
        # By doing this first, we will cleanly catch invalid DB names.
        from sqlalchemy.exc import ProgrammingError, OperationalError
        useDbSql = 'USE `%s`' % dbName
        hiddenProcessor = HiddenQueryProcessor()
        queryReturn = hiddenProcessor.process(useDbSql)

        if queryReturn != ReturnCode.SUCCESS:
            # An exception/error was raised.
            exc = em.getException()
            if not exc:
                em.doWarn()
                return ReturnCode.SUCCESS
            elif isinstance(exc, OperationalError):
                # The user probably specified a nonexistent DB. Offer to create one.
                em.resetError()
                if yes_no_dialog(title='Database not found',
                                 text='Database %s not found. Create?' % dbName):
                    createDbSql = "CREATE DATABASE %s" % dbName
                    queryReturn = hiddenProcessor.process(createDbSql)
                    if queryReturn == ReturnCode.SUCCESS:
                        em.setError(ReturnCode.Clarification)
                        em.doWarn("Database %s created." % dbName)
                    else:
                        em.doWarn('Unable to create database %s.' % dbName)
                else:
                    # User declined to create a new DB
                    return ReturnCode.SUCCESS
            elif isinstance(exc, ProgrammingError):
                # The proposed db name is probably illegal. This is unlikely
                # to happen since we now backquote it in the above USE query.
                em.doWarn(msg='%s: Cannot switch to db "%s"' % (type(exc), dbName))
                return ReturnCode.SUCCESS

        # Complete the transition to the new / other DB
    #TODO: Clean up / encapsulate this big time.
        activeDb = dataConfig.setActiveDatabase(dbName)
        ms.settings['database'] = activeDb.dbName
        ms.connection['FullString']['MINI_CONNECTION_STRING'] = \
            ms.connection['FullString']['MINI_CONNECTION_STRING'].replace(currDbName, dbName)
        ms.connection['FullPath']['MINI_DBPATH'] = \
            ms.connection['FullPath']['MINI_DBPATH'].replace(currDbName, dbName)
        ms.settings['table'] = activeDb.config.get('anchorTable', '')
        dbConn.changeDatabase(activeDb.dbName)
        return ReturnCode.SUCCESS

    def doSource(self, argv):
        argc = len(argv)

        # Source a command file
        fileName = MiniFileDialog('Open File', os.getcwd()) if argc<1 else argv[0]
        if not fileName:
            return ReturnCode.SUCCESS

        print('Sourcing ' + fileName)
        try:
            with open(fileName, 'r') as sourceFp:
                for line in sourceFp:
                    retValue = self.dispatchCommand(line)
                    if retValue != ReturnCode.SUCCESS:
                        em.doWarn()
                        break
        except FileNotFoundError:
            print('Cannot find file ' + fileName)
        except PermissionError:
            print('Not permissioned to read file ' + fileName)

        return ReturnCode.SUCCESS

    def doHelp(self, argv):
        if not argv:
            ldr = ms.settings['leader']
            print('\nMINIQUERY HELP')

            print('\nQueries:\n')
            leftSide = ['{} {}'.format(c, tqlArgumentSummaries) for c in tqlCommands]
            print('\n'.join(['  {}{:<20}: {}'.format(ldr, l, tqlDescriptions % c.upper()) for (l,c) in zip(leftSide, tqlCommands)]))

            print('\nSystem commands:\n')
            leftSide = ['{} {}'.format(c[0], c[1]) for c in commandList]
            print('\n'.join(['  {}{:<20}: {}'.format(ldr,l,c[2]) for l,c in zip(leftSide,commandList)]))
        else:
            print('FUTURE: command-specific help')
            pass
        return ReturnCode.SUCCESS

    def doClearTable(self, argv):
        ms.settings['table'] = ''
        currDbName = ms.settings['database']
        dataConfig.databases[currDbName].changeAnchorTable('')
        return ReturnCode.SUCCESS

    def doSet(self, argv):
        argc = len(argv)
        category = None
        subcategory = None
        value = None
        settingName = None

        if argc == 2:
            settingName = argv[0]
            value = argv[1]
        elif argc == 1:
            if '=' in argv[0]:
                settingName, eq, value = argv[0].partition('=')
            else:
                settingName = argv[0]
        elif argc == 0:
            # Provide USAGE help.
            self._setArbitraryValue("set", argv, 'settingName', 'value',
                    'Settings', 'your preferred setting')
            return ReturnCode.SUCCESS

        # Locate the setting in the internal configuration data structure
        if settingName in ms.settings:
            category = 'Settings'
        else:
            for (key, value) in ms.connection.items():
                if isinstance(value, dict) and settingName in value:
                    category = 'Connection'
                    subcategory = key
                    break
            if not category:
                print('Invalid setting name "' + settingName + '".')
                return ReturnCode.SUCCESS

        # Certain settable variables are restricted to a small set of values.
        # Others may assume unlimited values, practically speaking.
        try:
            optionsTuple = settingOptionsMap[settingName]
            self._chooseValueFromList(optionsTuple[0], category, settingName,
                    optionsTuple[1], optionsTuple[2], userEntry=value)
        except KeyError:
            self._setArbitraryValue("set", argv, 'settingName', 'value',
                    category, 'your preferred setting', subcategory)

        return ReturnCode.SUCCESS


    def doGet(self, argv):
        argc = len(argv)
        if argc < 1:
            print('USAGE: get <setting>')
            print('Displays the value of a setting.')
            print('Use "get *" to see all settings.')
        else:
            settingName = argv[0]
            if settingName == '*':
                for (key,value) in sorted(ms.settings.items()):
                    print(key + ': ' + str(value))
                print()
                for (key, value) in ms.connection.items():
                    if isinstance(value, dict):
                        for (key1, value1) in value.items():
                            print(key1 + ': ' + str(value1))
                    else:
                        print(key + ': ' + str(value))
            elif settingName in ms.settings:
                print(settingName + ': ' + str(ms.settings[settingName]))
            else:
                found = False
                for (key, value) in ms.connection.items():
                    if isinstance(value, dict) and settingName in value:
                        print(settingName + ': ' + str(ms.connection[key][settingName]))
                        found = True
                        break
                    elif settingName == key:
                        print(settingName + ': ' + str(ms.connection[settingName]))
                        found = True
                        break
                if not found:
                    print('Error: Setting ' + settingName + ' not found.')

        return ReturnCode.SUCCESS

    def doUnset(self, argv):
        argc = len(argv)
        settingName = None
        category = 'Settings'
        subcategory = None

        if argc >= 1:
            settingName = argv[0]

            if not settingName in ms.settings:
                for k,v in ms.connection.items():
                    if isinstance(v, dict) and settingName in v:
                        category = 'ConnectionString'
                        subcategory = k
                        break
                    elif k == settingName:
                        category = 'ConnectionString'
                        break

        self._unsetValueCommand("unset", argv, 'settingName', category, subcategory)

        return ReturnCode.SUCCESS

    def doGetAlias(self, argv):
        argc = len(argv)
        if argc < 1:
            print('USAGE: geta <aliasName>')
            print('Displays the meaning of an alias.')
            print('Use "geta *" to see all aliases.')
        else:
            aliasName = argv[0]
            if aliasName == '*':
                for a in ms.aliases.items():
                    print(a[0] + ': ' + a[1])
            elif aliasName in ms.aliases:
                print(aliasName + ': ' + ms.aliases[aliasName])
            else:
                print('Error: Alias ' + aliasName + ' not found.')

        return ReturnCode.SUCCESS

    def doGetVariable(self, argv):
        argc = len(argv)
        if argc < 1:
            print('USAGE: getv <variableName>')
            print('Displays the value of a MINIQUERY variable.')
            print('Use "getv *" to see all variables.')
        else:
            varName = argv[0]
            if varName == '*':
                for v in ms.variables.items():
                    print(v[0] + ': ' + v[1])
            elif varName in ms.variables:
                print(varName + ': ' + ms.variables[varName])
            else:
                print('Error: Variable ' + varName + ' not found.')

        return ReturnCode.SUCCESS

    def doAlias(self, argv):
        self._setArbitraryValue("seta", argv, 'alias', 'command', 'Aliases', 'a native command')
        return ReturnCode.SUCCESS

    def doUnalias(self, argv):
        self._unsetValueCommand("unseta", argv, 'aliasName', 'Aliases', keepKey=False)
        return ReturnCode.SUCCESS

    def doSetVariable(self, argv):
        self._setArbitraryValue("setv", argv, 'name', 'value', 'Variables', 'text to be substituted')
        return ReturnCode.SUCCESS

    def doUnsetVariable(self, argv):
        self._unsetValueCommand("unsetv", argv, 'variable', 'Variables', keepKey=False)
        return ReturnCode.SUCCESS


    ############ Utilities / helper functions ############

    def _unravelAliases(self, cmd, leader):
        strippedCmd = cmd.lstrip(leader)
        for a in ms.aliases:
            # We have an alias when the cmd "starts with" an alias.
            # We have to recognize false "aliases" that are
            # simply proper substrings of a longer command name
            if strippedCmd.startswith(a):
                try:
                    isAlias = not strippedCmd[len(a)].isidentifier()
                except IndexError:
                    isAlias = True
                if isAlias:
                    cmd = cmd.replace(a, ms.aliases[a], 1)
                    break
        return cmd

    def _unravelVariables(self, cmd):
        while True:
            # We accept {}-protected variable names as well as unprotected ones.
            # For the latter, we will opt for the longest variable name, so that if
            # both "a" and "ab" exist, then "$ab" is equivalent to ${ab} not ${a}b
            protectedVariable = re.search(r'\${(\w+)}', cmd)
            if protectedVariable:
                varName = protectedVariable.group(1)
                try:
                    cmd = re.sub(re.escape(protectedVariable.group(0)), ms.variables[varName], cmd)
                except KeyError:
                    print('Unknown variable "' + varName + "'")
                    return cmd
            nakedVariable = re.search(r'\$(\w+)', cmd)
            if nakedVariable and ms.variables:
                containingString = nakedVariable.group(1)
                maxNameVariable = ('','')
                for var in ms.variables.items():
                    if containingString.startswith(var[0]) and var[0].startswith(maxNameVariable[0]):
                        maxNameVariable = var
                if maxNameVariable[0]:
                    cmd = re.sub(re.escape(nakedVariable.group(0)), maxNameVariable[1], cmd)

            if not (protectedVariable or nakedVariable):
                break

        return cmd


    def _chooseValueFromList(self, lst, category, setting, title, text, userEntry='',
                subcategory=None, canCancel=True):
        '''
        Accepts or prompts for an input value from a small set of valid options.
        '''
        category = category.lower()

        if userEntry:
            if userEntry in lst:
                choice = lst.index(userEntry)
                if subcategory:
                    getattr(ms, category)[subcategory][setting] = userEntry
                else:
                    getattr(ms, category)[setting] = userEntry
            else:
                #TODO: Before assuming a user error, offer pop-up autocompletion from the list provided
                length = len(lst)
                if length >= 3:
                    csv = ' or '.join(lst).replace(' or ', ', ', length-2) \
                            if length >= 3 else ' or '.join(lst)
                print('Illegal option "{}". Please choose one of {}'. format(
                    userEntry, csv))
                choice = -1
        else:
            #TODO: In LOUD mode, offer a dialog. In SOFT mode, offer autocompletion
            # Button list must be a list of pair-tuples: (name, return value)
            buttonList = list(zip( lst+['CANCEL'], list(range(len(lst)))+[-1] ) \
                    if canCancel else zip(lst, range(len(lst))))
            choice = button_dialog(title=title, text=text, buttons=buttonList)
            if choice >= 0:
                if subcategory:
                    getattr(ms, category)[subcategory][setting] = buttonList[choice][0]
                else:
                    getattr(ms, category)[setting] = buttonList[choice][0]
        return choice


    def _setArbitraryValue(self, command, argv, lhs, rhs, category, desc, subcategory=None):
        '''
        Function to set or query a MINIQUERY system setting when an "infinitude"
        of values are allowed. The user-proposed value is NOT validated -- anything
        goes. For finite value sets, _chooseValueFromList() is the way to go.

        N.B.: This function doubles as a setter for "user customizations" that are not
        "settings," per se: aliases, variables and abbreviations. The distinction is
        noted in the "command" argument.
        '''
        argc = len(argv)
        category = category.lower()

        if argc == 0:
            print('USAGE: {0} <{1}>=<{2}>\n   or: {0} <{1}> <{2}>'.format(
                command, lhs, rhs))
            print('    where <{}> is {}'.format(rhs, desc))
        elif argc == 1:
            if '=' in argv[0]:
                # Value assignment from the cmd line
                var, eq, val = argv[0].partition('=')
                if subcategory:
                    getattr(ms, category)[subcategory][var] = val
                else:
                    getattr(ms, category)[var] = val
            else:
                # Value assignment from dialog box
                var = argv[0]
                val = input_dialog(title='Set value',
                            text='Please enter a value for ' + var + ':')
                if not val:
                    # Cancelled! Return without doing anything.
                    return ReturnCode.SUCCESS
                elif subcategory:
                    getattr(ms,category)[subcategory][var] = val
                else:
                    getattr(ms,category)[var] = val
        elif argc == 2:
            var = argv[0]; val = argv[1]
            if subcategory:
                getattr(ms, category)[subcategory][var] = val
            else:
                getattr(ms, category)[var] = val
        return ReturnCode.SUCCESS

    def _unsetValueCommand(self, command, argv, settingName, category, subcategory=None, keepKey=True):
        '''
        Generically handles unset-like commands given the precise location of the
        setting in question in the settings tree.
        '''

        argc = len(argv)
        if argc != 1:
            print('USAGE: {} <{}>'.format(command, settingName))
            return
        else:
            if category == 'Settings':
                # Settings cannot be *removed*
                print('Error: MINIQUERY system setting "' + settingName
                        + '" cannot be unset, only changed.')
                return
            else:
                entryName = argv[0]
                if subcategory:
                    if keepKey:
                        getattr(ms, category)[subcategory][entryName] = None
                    else:
                        del getattr(ms, category)[subcategory][entryName]
                else:
                    if keepKey:
                        getattr(ms, category)[entryName] = None
                    else:
                        del getattr(ms, category)[entryName]
            return


    ############ End MiniqueryApp class definition ############

def main():
    '''
    Main entry point for MINIQUERY
    '''
    # Workaround for a bug in PDB debugger: State is not totally clean after restart
    em.resetError()

    # Make a copy of sys.argv that we can edit. Pop off the program name in cell 0.
    argv = sys.argv.copy()
    programName = argv.pop(0)

    if '-h' in argv or '--help' in argv:
        giveMiniHelp()
        em.doExit()

    if env.setEnv() != ReturnCode.SUCCESS:
        em.doExit('Environment settings incomplete or incorrect.')

    # Load the user settings from the default file or a custom-named file
    programSettingsFile = os.path.join(env.HOME, '.minirc')
    for arg in argv:
        if re.match('[-]+c(fg)?=', arg):
            programSettingsFile = arg.split('=')[1]
            argv.remove(arg)
            break

    miniApp = MiniqueryApp(programSettingsFile)

    if ms.loadSettings(programSettingsFile) == ReturnCode.SUCCESS:
        env.setDatabaseName(ms.settings['database'])
    else:
        em.doExit()

    # Load the initial db config and schema
    if dataConfig.setup() != ReturnCode.SUCCESS:
        em.doExit()

    # If the standard input has been redirected, execute its commands
    # and quickly exit, as in mysql
    if not ms.isInputTty:
        while True:
            cmd = sys.stdin.readline()
            if not cmd:
                break
            retValue = miniApp.dispatchCommand(cmd)

            # Exit early if there is an incident
            if retValue != ReturnCode.SUCCESS:
                em.doExit()

        # Exit at EOF
        em.doExit()

    # In one-and-done mode, execute the cmd and exit
    oneAndDoneMode = '-e' in argv
    if oneAndDoneMode:
        argv.remove('-e')
        cmd = regularizeCommandLine(argv)
        miniApp.dispatchCommand(cmd)
        em.doExit()

    # Display the introductory message
    welcomeColor = 'green' if ms.ostype == 'Windows' else 'lightgreen'
    print_formatted_text(FormattedText([(welcomeColor, '\nWELCOME TO MINIQUERY!\n')]))
    print('Copyright (c) 2019-2021 Miniquery AMDG, LLC')
    print('Enter {}help for help.'.format(ms.settings['leader']))

    # Set up the command history
    histFileName = os.path.join(env.HOME, '.mini_history')
    historyObject = MiniFileHistory(histFileName)
    miniApp.setHistory(historyObject)

    session = PromptSession(history = historyObject)
    cmdBuffer = []

    # If a system command or a query was given on the command line, process it before starting the main loop
    cmd = regularizeCommandLine(argv)
    miniApp.dispatchCommand(cmd)

    # The infinite event loop: Accept and dispatch MINIQUERY commands
    while True:

        if ms.isPromptChanged():
            PS1Prompt, styleDict = stringToPrompt(ms.settings['prompt'])
            PS2Prompt = [('class:symbol', ms.settings['secondarySymbol'])]
            promptStyle = Style.from_dict(styleDict)
            usePS1Prompt = True
            ms.settings._promptChanged = False

        # The command buffering loop: Keep buffering command fragments according to
        # the line-ending protocol until a complete command has been received
        try:
            while True:
                print()
                cmdCompleter = CommandCompleter([])

                editMode = ms.settings['editMode']
                cmd = session.prompt(
                            PS1Prompt if usePS1Prompt else PS2Prompt,
                            style=promptStyle,
                            enable_open_in_editor=True,
                            editing_mode=EditingMode.EMACS if editMode=='EMACS' 
                                                        else EditingMode.VI,
                            completer=cmdCompleter, 
                            complete_while_typing=False
                    )
                if em.getException():
                    em.doWarn()

                # Is end-of-command detected?
                if cmd.endswith(ms.settings['delimiter']) or (
                        not cmd.endswith(ms.settings['continuer']) and ms.settings['endlineProtocol']== 'delimit'):
                    cmdBuffer.append(cmd.rstrip(ms.settings['delimiter']))
                    cmd = ' '.join(cmdBuffer)
                    cmdBuffer.clear()
                    usePS1Prompt = True
                    # The command is complete and ready for dispatch
                    break

                # Command continuation is indicated
                else:
                    cmdBuffer.append(cmd.rstrip(ms.settings['continuer']))
                    usePS1Prompt = False
        except EOFError:
            break

        retValue = miniApp.dispatchCommand(cmd)
        if retValue == ReturnCode.USER_EXIT:
            break

    em.doExit()


def regularizeCommandLine(argv):
    '''
    Commands typed at the shell prompt are intercepted by the shell, where word
    splitting and expansion occur before MINIQUERY sees them; commands entered in
    the REPL-loop are seen exactly as typed. Here we process the former to resemble
    the latter so that subsequent processing can be agnostic of the difference.
    '''

    # Quote arguments which must have been quote-stripped by the shell. We take this
    # to mean arguments containing whitespace.
    for arg in argv:
        m = re.search(r'\s', arg)
        if m and m.group(0):
            # Wrap the argument in (strong) quotes
            arg = re.sub(r'^', "'", re.sub(r'$', "'", arg))

    # Merge into a cmd line string
    cmd = " ".join(argv)

    return cmd


def commandToWordList(cmd):
    '''
    Splits a command string into a list that can be arg-classify()'d.
    This routine is custom-made to handle escape sequences and our subquery syntax.
    '''

    QUOTES = '{"\'}'   # normal quotes plus subquery delimiters

    word = ''
    words = []
    quoteBuffer = []    # Only track {}s and outermost quotes
    isEscaped = False

    for c in cmd:
        if isEscaped or c == '\\':
            # Escape sequences have greatest precedence and are left untouched
            word += c
            isEscaped = not isEscaped
        elif c in QUOTES:
            previousQuote = quoteBuffer[-1] if quoteBuffer else ''
            if c == '"' or c == "'":
                if '{' in quoteBuffer:
                    # Inside {}, treat quotes as normal characters
                    word += c
                elif quoteBuffer:
                    if c == previousQuote:
                        # This is a close-quote. Toss it and unbuffer its partner.
                        del quoteBuffer[-1]
                    else:
                        # This is a literal quote character inside a quoted sequence
                        word += c
                else:
                    # This is an open-quote.
                    quoteBuffer += c
            elif c == '{':
                # Track all {}s
                quoteBuffer += c
                word += c
            else:   # c == '}'
                if previousQuote == '{':
                    del quoteBuffer[-1]
                word += c
        elif c.isspace():
            if quoteBuffer:
                # Preserve protected whitespace
                word += c
            elif word:
                # Treat whitespace as word delimiter
                words.append(word)
                word = ''
        else:
            # Preserve normal characters
            word += c

    if word:
        words.append(word)

    if quoteBuffer:
        em.setError(ReturnCode.UNBALANCED_PARENTHESES_OR_SYMBOLS, cmd)
        return [cmd]

    return words


# Preserved to help test word completion:
def doCompleter(argv):
    words = ['this','that','thought']
    comp = MiniCompleter(words)
    complete_event = CompleteEvent(completion_requested=False)    # from bindings/completion.py:51
    document = Document(text=" ".join(argv))
    # List of Completions: [text, start_position, display]
    matches = list(comp.get_completions(document, complete_event))
    print('Matching candidates:')
    print([m.text for m in matches])
    return ReturnCode.SUCCESS

# Map/zip the command names to the corresponding callback functions
callbackMap = {cmd[0]: cmd[3] if len(cmd)>3 else cmd[0] for cmd in commandList}

# Main entry point.
if __name__ == '__main__':
    main()

