import os
import sys
import re
from shlex import split
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
from configManager import masterDataConfig as cfg
from argumentClassifier import ArgumentClassifier
from queryProcessor import QueryProcessor, HiddenQueryProcessor
from databaseConnection import miniDbConnection as dbConn
from prompts import stringToPrompt

sys.path.append(".." + os.sep + "util")
from miniCompleter import MiniCompleter
from commandCompleter import CommandCompleter
from miniGlobals import settingOptionsMap
from miniDialogs import yes_no_dialog, button_dialog, input_dialog, MiniListBoxDialog, MiniFileDialog

setupPrompt = True
settingsChanged = False
continuer = ''; delimiter = ''; endlineProtocol = None
userConfigFile = ''
args = ArgumentClassifier()

historyObject = None

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

def main():
    global args, setupPrompt
    global historyObject, userConfigFile
    global continuer, delimiter, endlineProtocol
    if '-h' in sys.argv or '--help' in sys.argv:
        giveMiniHelp()
        em.doExit()

    if env.setEnv() != ReturnCode.SUCCESS:
        em.doExit('Environment settings incomplete or incorrect.')

    # Load the user settings from the default file or a custom file
    userConfigFile = os.path.join(env.HOME, '.minirc')
    for arg in sys.argv:
        if arg.startswith('-') and re.match('[-]+c(fg)?=', arg):
            userConfigFile = arg.split('=')[1]
            break
    if ms.loadSettings(userConfigFile) == ReturnCode.SUCCESS:
        env.setDatabaseName(ms.settings['Settings']['database'])
    else:
        em.doExit()

    # If the standard input has been redirected, execute its commands
    # and quickly exit, as in mysql
    if not ms.isInputTty:
        while True:
            cmd = sys.stdin.readline()
            if not cmd:
                break
            retValue = dispatchCommand(cmd)

            # Exit early if there is an incident
            if retValue != ReturnCode.SUCCESS:
                em.doExit()

        # Exit at EOF
        em.doExit()

    args.classify(sys.argv[1:])   # skip the program name
    
    # The configs and the cache must be loaded before any commands are
    # processed. This is because the first cmd can be a sys cmd that needs
    # a list of tab-completion candidates that comes from the db schema.
    if cfg.setup() != ReturnCode.SUCCESS:
        em.doExit()

    # In one-and-done mode, execute the cmd and exit
    oneAndDoneMode = 'e' in args._options
    if oneAndDoneMode:
        # Take everything after '-e' to be the command;
        # all option flags need to come *before* it
        which = sys.argv.index('-e') + 1
        cmd = " ".join(sys.argv[which:])

        dispatchCommand(cmd, '')
        em.doExit()

    # Prelude to the pseudo-infinite event loop
    welcomeColor = 'green' if ms.ostype == 'Windows' else 'lightgreen'
    print_formatted_text(FormattedText([(welcomeColor, '\nWELCOME TO MINIQUERY!\n')]))
    print('Copyright (c) 2020 Miniquery AMDG, LLC')
    print('Enter {}help for help.'.format(ms.settings['Settings']['leader']))

    # If there is a command or a query on the command line, accept it before starting the main loop
    cmd = " ".join(sys.argv[1:])    # skip "mini"
    if cmd.startswith(ms.settings['Settings']['leader']):
        dispatchCommand(cmd, '')
    elif cmd:
        if args.mainTableName and args._argumentTree:     # args.wheres or args.updates or args.postSelects:
            dispatchCommand(cmd, '')

    histFileName = os.path.join(env.HOME, '.mini_history')
    historyObject = MiniFileHistory(histFileName)
    session = PromptSession(history = historyObject)

    cmdBuffer = []
    # Cache a few dictionary lookups which should not change very often:
    continuer = ms.settings['Settings']['continuer']
    delimiter = ms.settings['Settings']['delimiter']
    endlineProtocol = ms.settings['Settings']['endlineProtocol']

    # The infinite event loop: Accept and dispatch MINIQUERY commands
    while 1:

        if setupPrompt:    # Initialize or update the prompt
            PS1Prompt, styleDict = stringToPrompt(ms.settings['Settings']['prompt'])
            PS2Prompt = [('class:symbol', ms.settings['Settings']['secondarySymbol'])]
            promptStyle = Style.from_dict(styleDict)
            usePS1Prompt = True; setupPrompt = False

        # The command buffering loop: Keep buffering command fragments
        # according to the line protocol until a complete command is received
        try:
            while 1:
                print()
                cmdCompleter = CommandCompleter([])

                editMode = ms.settings['Settings']['editMode']
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
                if cmd.endswith(delimiter) or (
                        not cmd.endswith(continuer) and endlineProtocol == 'delimit'):
                    cmdBuffer.append(cmd.rstrip(delimiter))
                    cmd = ' '.join(cmdBuffer)
                    cmdBuffer.clear()
                    usePS1Prompt = True
                    # The command is complete and ready for dispatch
                    break

                # Command continuation is indicated
                else:
                    cmdBuffer.append(cmd.rstrip(continuer))
                    usePS1Prompt = False
        except EOFError:
            break

        retValue = dispatchCommand(cmd)
        if retValue == ReturnCode.USER_EXIT:
            break

    em.doExit()


def _unravelAliases(cmd):
    for a in ms.settings['Aliases']:
        # We have an alias when the cmd "starts with" an alias.
        # We have to recognize false "aliases" that are
        # simply proper substrings of a longer command name
        if cmd.startswith(a):
            try:
                isAlias = not cmd[len(a)].isalnum()
            except IndexError:
                isAlias = True
            if isAlias:
                cmd = cmd.replace(a, ms.settings['Aliases'][a], 1)
                break
    return cmd


def _unravelVariables(cmd):
    varName = ''
    variable = re.search(r'\$(\w+)', cmd)
    while variable:
        varName = variable.group(1)
        try:
            cmd = re.sub('\$'+varName, ms.settings['Variables'][varName], cmd)
        except KeyError:
            print('Unknown variable "' + varName + '"')
        variable = re.search(r'\$(\w+)', cmd)
    return cmd


def dispatchCommand(cmd):

    # Flatten aliases and variables
    if cmd.startswith(ms.settings['Settings']['leader']):
        cmd = cmd.lstrip(ms.settings['Settings']['leader'])
        isExplicitCommand = True
        cmd = _unravelVariables(_unravelAliases(cmd))
    else:
        isExplicitCommand = False
        cmd = _unravelVariables(cmd)

    # Preprocess the command and distinguish system commands from queries
    argv = split(cmd)
    args.classify(argv, isExplicitCommand)

    # Process the command as a query or as a system command
    if args._isQueryCommand:
        retValue = QueryProcessor(args).process()
        if retValue != ReturnCode.SUCCESS:
            # Warn the user the query cannot be processed and continue the command loop
            #TODO Verify that changed environments are actually re-loaded
            em.doWarn()
            return retValue
    else:
        # Call the function indicated by the first word
        try:
            callback = callbackMap[args._commandName]
        except KeyError:
            print('Unknown command "'+ args._commandName + '"')
            return ReturnCode.SUCCESS
        result = callback(argv[1:])

        if result == ReturnCode.SUCCESS:
            return ReturnCode.SUCCESS
        elif result == ReturnCode.USER_EXIT:
            return ReturnCode.USER_EXIT
        elif result == ReturnCode.DATABASE_CONNECTION_ERROR:
            # Allow the user to fix the connection settings and keep going.
            #TODO One situation is a failed cxn due to bad cxn strings.
            #TODO Accept changes, & upon "reconnect" cmd, try to reconnect.
            em.doWarn()
            return ReturnCode.SUCCESS
        else:
            print('Unrecognized return code for command "' + cmd + '"')
            return ReturnCode.SUCCESS

    return ReturnCode.SUCCESS

def doHelp(argv):
    if not argv:
        print('\nMINIQUERY COMMANDS:\n')
        ldr = ms.settings['Settings']['leader']
        leftSide = ['{} {}'.format(c[0], c[1]) for c in commandList]
        print('\n'.join(['  {}{:<20}: {}'.format(ldr,l,c[2]) for l,c in zip(leftSide,commandList)]))

#TODO: Add these
#*m{ode}             : Select a SQL subfamily mode\n\
#*ab{brev}           : Define an object-name abbreviation\n\
#TODO: Add a list of TOPICS such as the prompt and how to write MINI-queries
#TODO: Add a list of cmdline opts/flags with a few general instructions as follows:
#TODO:   Flags with values must be written -x=1234, i.e. equal sign with no spaces.
#TODO:     e: one-and-done, followed ONLY by the command. Any other option flags must precede the -e.
#TODO:     p: password (Useful when stdout is redirected; then, without a PW the program errors-out)
#TODO:     2v/3v: logic       a,o: conjunction
#TODO: Finally, point the user to a tutorial.

    else:
        #TODO print('FUTURE: command-specific help')
        pass
    return ReturnCode.SUCCESS

def doSql(sql):
    # Most of the classified args should not apply here. But we still
    # need to fall back on a few things like runMode, display format, ...
    # So we clear the options, copy the settings, and then run the query.
    global args, setupPrompt
    args._options.clear()
#TODO: removed this method    args.backfillOptions()
    fullSql = " ".join(sql)
    retValue = QueryProcessor(args).process(fullSql)
    if retValue != ReturnCode.SUCCESS:
        em.doWarn()
        return ReturnCode.SUCCESS  #TODO: Keep the "real" error code, here and elsewhere

    # Update program state in the case of a "use" query (database-switching)
    if fullSql[:4].lower() == "use ":
        ms.settings['Settings']['database'] = fullSql[4:]
        ms.settings['Settings']['table'] = ''
        args.mainTableName = ''
        # Update the prompt
        setupPrompt = True

    return ReturnCode.SUCCESS

def doQuit(argv):
    global settingsChanged, userConfigFile

    if settingsChanged:
        choice = button_dialog(title='Save before quitting?',
                text='Save changes to your MINIQUERY settings before quitting?',
                buttons=[('Yes',True), ('No',False), ('Cancel',None)])
        if choice:     # User pressed Yes
            choice = MiniFileDialog('Save Settings File', userConfigFile,
                    can_create_new=True)
            if not choice:
                return ReturnCode.SUCCESS
            # Try to write the config file
            userConfigFile = choice
            ms.settings.filename = userConfigFile
            if ms.settings.write() != ReturnCode.SUCCESS:
                exc = em.getException()
                em.doWarn()
                return ReturnCode.SUCCESS
            settingsChanged = False
            return em.setError(ReturnCode.USER_EXIT)
        elif choice == None:     # User pressed Cancel
            return ReturnCode.SUCCESS
        elif choice == False:     # User pressed No
            return em.setError(ReturnCode.USER_EXIT)
    else:
        if yes_no_dialog(title='Quit MINIQUERY',
                text='Exit MINIQUERY: Are you sure?'):
            return em.setError(ReturnCode.USER_EXIT)
        return ReturnCode.SUCCESS

def doSave(argv):
    global settingsChanged, userConfigFile
    argc = len(argv)

    if settingsChanged:
        # Save program settings, variables and aliases
        if ms.isOutputTty:
            choice = MiniFileDialog('Save Settings File', userConfigFile,
                    can_create_new=True) if argc<1 else argv[0]
            if not choice:
                return ReturnCode.SUCCESS
        else:
            choice = argv[0] if argc>=1 else userConfigFile

        if choice:
            userConfigFile = choice
            ms.settings.filename = userConfigFile
            if ms.settings.write():    # Returns None on success. Do not use RC.SUCCESS here.
                exc = em.getException()
                em.doWarn()
                return ReturnCode.SUCCESS
            settingsChanged = False
    else:
        em.doWarn(msg='No unsaved changes.')

    dbConfig = cfg.databases[ms.settings['Settings']['database']]
    if dbConfig.configChanges:
        # Save DB config and reset configChanges
        if dbConfig.saveConfigChanges() != ReturnCode.SUCCESS:
            em.doWarn()
    return ReturnCode.SUCCESS

def doHistory(argv):
    global historyObject
    argc = len(argv)

    if argc > 0 and not argv[0].isdecimal():
        em.setError(ReturnCode.ILLEGAL_ARGUMENT)
        em.doWarn(msg='ERROR: A positive number is required.')
        return ReturnCode.SUCCESS

    l = list(reversed(historyObject.get_strings()))
    available = len(l)
    requested = int(argv[0] if argc > 0 else ms.settings['Settings']['historyLength'])
    print("\n".join(l[0:min(available, requested)]))
    return ReturnCode.SUCCESS

def doFormat(argv):
    argc = len(argv)

    optionsTuple = settingOptionsMap['format']
    _chooseValueFromList(optionsTuple[0], 'Settings', 'format',
                optionsTuple[1], optionsTuple[2],
                userEntry=argv[0] if argc >= 1 else None)
    return ReturnCode.SUCCESS

def doSetDatabase(argv):
    global args, setupPrompt, settingsChanged

    # Do not allow simple erasure of the db name. Bring up a selection dlg
    # offering the option to cancel back to the current name. Since the set
    # of DBs is (only) changeable by CREATE DATABASE, use a list box.
    if len(argv) == 0:
        dbList = list(iter(cfg.databases))
        dbName = MiniListBoxDialog(title='Select a database', itemList=dbList)
        if not dbName:
            return ReturnCode.SUCCESS
    else:
        dbName = argv[0] if len(argv) > 0 else ''

    currDbName = ms.settings['Settings']['database']
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
    activeDb = cfg.setActiveDatabase(dbName)
    ms.settings['Settings']['database'] = activeDb.dbName
    ms.settings['Settings']['table'] = activeDb.config.get('anchorTable', '')
    args.mainTableName = activeDb.config.get('anchorTable', '')
    # Update the prompt
    setupPrompt = True
    settingsChanged = True
    return ReturnCode.SUCCESS

def doSetTable(argv):
    global args, setupPrompt, settingsChanged

    currDbName = ms.settings['Settings']['database']
    tableList = cfg.databases[currDbName].tableNames
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

    currAnchorTable = ms.settings['Settings']['table']
    if tableName == currAnchorTable:
        em.setError(ReturnCode.Clarification)
        em.doWarn("Anchor table is already " + currAnchorTable + ".")
        return ReturnCode.SUCCESS
    ms.settings['Settings']['table'] = tableName
    cfg.databases[currDbName].changeAnchorTable(tableName)
    args.mainTableName = tableName
    setupPrompt = True
    settingsChanged = True
    return ReturnCode.SUCCESS

def doClearTable(argv):
    global setupPrompt, settingsChanged

    ms.settings['Settings']['table']=''
    currDbName = ms.settings['Settings']['database']
    cfg.databases[currDbName].changeAnchorTable('')
    args.mainTableName = ''
    setupPrompt = True
    settingsChanged = True
    return ReturnCode.SUCCESS

def doSource(argv):
    argc = len(argv)

    # Source a command file
    fileName = MiniFileDialog('Open File', os.getcwd()) if argc<1 else argv[0]
    if not fileName:
        return ReturnCode.SUCCESS

    print('Sourcing ' + fileName)
    try:
        with open(fileName, 'r') as sourceFp:
            for line in sourceFp:
                retValue = dispatchCommand(line)
                if retValue != ReturnCode.SUCCESS:
                    em.doWarn()
                    break
    except FileNotFoundError:
        print('Cannot find file ' + fileName)
    except PermissionError:
        print('Not permissioned to read file ' + fileName)

    return ReturnCode.SUCCESS

def doSet(argv):
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
        #TODO: Put the code here, don't make a subfunction call
        _setArbitraryValue("set", argv, 'settingName', 'value',
                category, 'your preferred setting', subcategory)
        return ReturnCode.SUCCESS

    # Locate the setting in the internal configuration data structure
    if settingName in ms.settings['Settings']:
        category = 'Settings'
    else:
        for d in ms.settings['ConnectionString']:
            if isinstance(d, dict) and settingName in d:
                category = 'ConnectionString'
                subcategory = d
                break
        if not category:
            print('Invalid setting name "' + settingName + '".')
            return ReturnCode.SUCCESS

    # Certain settable variables are restricted to a small set of values.
    # Others may assume unlimited values, practically speaking.
    # We have special functions to manage both cases.
    try:
        optionsTuple = settingOptionsMap[settingName]
        _chooseValueFromList(optionsTuple[0], category, settingName,
                optionsTuple[1], optionsTuple[2], userEntry=value)
    except KeyError:
        _setArbitraryValue("set", argv, 'settingName', 'value',
                category, 'your preferred setting', subcategory)

    return ReturnCode.SUCCESS

def doGet(argv):
    argc = len(argv)
    if argc < 1:
        print('USAGE: get <setting>')
        print('Displays the value of a setting.')
        print('Use "get *" to see all settings.')
    else:
        settingName = argv[0]
        if settingName == '*':
            for s in ms.settings['Settings'].items():
                print(s[0] + ': ' + str(s[1]))
            print()
            for s in ms.settings['ConnectionString'].items():
                if isinstance(s[1], dict):
                    for s1 in s[1].items():
                        print(s1[0] + ': ' + str(s1[1]))
                else:
                    print(s[0] + ': ' + str(s[1]))
        elif settingName in ms.settings['Settings']:
            print(settingName + ': ' + str(ms.settings['Settings'][settingName]))
        else:
            found = False
            for s in ms.settings['ConnectionString']:
                if isinstance(s, dict) and settingName in s:
                    print(settingName + ': ' + str(ms.settings['ConnectionString'][s][settingName]))
                    found = True
                    break
            if not found:
                print('Error: Setting ' + settingName + ' not found.')

    return ReturnCode.SUCCESS

def doGetAlias(argv):
    argc = len(argv)
    if argc < 1:
        print('USAGE: geta <aliasName>')
        print('Displays the meaning of an alias.')
        print('Use "geta *" to see all aliases.')
    else:
        aliasName = argv[0]
        if aliasName == '*':
            for a in ms.settings['Aliases'].items():
                print(a[0] + ': ' + a[1])
        elif aliasName in ms.settings['Aliases']:
            print(aliasName + ': ' + ms.settings['Aliases'][aliasName])
        else:
            print('Error: Alias ' + aliasName + ' not found.')

    return ReturnCode.SUCCESS

def doGetVariable(argv):
    argc = len(argv)
    if argc < 1:
        print('USAGE: getv <variableName>')
        print('Displays the value of a MINIQUERY variable.')
        print('Use "getv *" to see all variables.')
    else:
        varName = argv[0]
        if varName == '*':
            for v in ms.settings['Variables'].items():
                print(v[0] + ': ' + v[1])
        elif varName in ms.settings['Variables']:
            print(varName + ': ' + ms.settings['Variables'][varName])
        else:
            print('Error: Variable ' + varName + ' not found.')

    return ReturnCode.SUCCESS

def doUnset(argv):
    argc = len(argv)
    category = 'Settings'
    subcategory = None

    if argc >= 1:
        settingName = argv[0]

    if not settingName in ms.settings['Settings']:
        for d in ms.settings['ConnectionString']:
            if isinstance(d, dict) and settingName in d:
                category = 'ConnectionString'
                subcategory = d
                break

    _unsetValueCommand("unset", argv, 'settingName', category, subcategory)
    return ReturnCode.SUCCESS

def doAlias(argv):
    _setArbitraryValue("seta", argv, 'alias', 'command', 'Aliases', 'a native command')
    return ReturnCode.SUCCESS

def doUnalias(argv):
    _unsetValueCommand("unseta", argv, 'aliasName', 'Aliases')
    return ReturnCode.SUCCESS

def doSetVariable(argv):
    _setArbitraryValue("setv", argv, 'name', 'value', 'Variables', 'text to be substituted')
    return ReturnCode.SUCCESS

def doUnsetVariable(argv):
    _unsetValueCommand("unsetv", argv, 'variable', 'Variables')
    return ReturnCode.SUCCESS

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

# Function that accepts a value from a small set of valid options.
# Accepts a typed-in value, but if none is provided brings up a selection dialog
def _chooseValueFromList(lst, category, setting, title, text, userEntry='',
            subcategory=None, canCancel=True):
    global endlineProtocol, settingsChanged

    if userEntry:
        if userEntry in lst:
            if subcategory:
                ms.settings[category][subcategory][setting] = userEntry
            else:
                ms.settings[category][setting] = userEntry
                # Update cached local copies of settings
                if setting == 'endlineProtocol':
                    endlineProtocol = userEntry
            settingsChanged = True
        else:
            #TODO: Before assuming a user error, offer pop-up autocompletion from the list provided
            length = len(lst)
            if length >= 3:
                csv = ' or '.join(lst).replace(' or ', ', ', length-2) \
                        if length >= 3 else ' or '.join(lst)
            print('Illegal option "{}". Please choose one of {}'. format(
                userEntry, csv))
    else:
        #TODO: In LOUD mode, offer a dialog. In SOFT mode, offer autocompletion
        # Button list must be a list of pair-tuples: (name, return value)
        buttonList = list(zip( lst+['CANCEL'], list(range(len(lst)))+[-1] ) \
                if canCancel else zip(lst, range(len(lst))))
        choice = button_dialog(title=title, text=text, buttons=buttonList)
        if choice >= 0:
            if subcategory:
                ms.settings[category][subcategory][setting] = buttonList[choice][0]
            else:
                ms.settings[category][setting] = buttonList[choice][0]
                # Update cached local copies of settings
                if setting == 'endlineProtocol':
                    endlineProtocol = buttonList[choice][0]
            settingsChanged = True

    return ReturnCode.SUCCESS


# Function to set or query a MINIQUERY system setting when an "infinitude"
# of values are allowed. The user-proposed value is NOT validated -- anything
# goes. For finite value sets, _chooseValueFromList() is the way to go.
#
# N.B.: This function doubles as a setter for "user customizations" that are not
# "settings," per se: aliases, variables and abbreviations. The distinction is
# noted in the "command" argument.
def _setArbitraryValue(command, argv, lhs, rhs, category, desc, subcategory=None):
    global settingsChanged, continuer, delimiter
    argc = len(argv)

    if argc == 0:
        print('USAGE: {0} <{1}>=<{2}>\n   or: {0} <{1}> <{2}>'.format(
            command, lhs, rhs))
        print('    where <{}> is {}'.format(rhs, desc))
    elif argc == 1:
        if '=' in argv[0]:
            # Value assignment from the cmd line
            var, eq, val = argv[0].partition('=')
            if subcategory:
                ms.settings[category][subcategory][var] = val
            else:
                ms.settings[category][var] = val
                if var == 'continuer':
                    continuer = val
                elif var == 'delimiter':
                    delimiter = val
        else:
            # Value assignment from dialog box
            var = argv[0]
            val = input_dialog(title='Set value',
                        text='Please enter a value for ' + var + ':')
            if not val:
                # Cancelled! Return without doing anything.
                return ReturnCode.SUCCESS
            elif subcategory:
                ms.settings[category][subcategory][var] = val
            else:
                ms.settings[category][var] = val
        settingsChanged = True
    elif argc == 2:
        var = argv[0]; val = argv[1]
        if subcategory:
            ms.settings[category][subcategory][var] = val
        else:
            ms.settings[category][var] = val
            if var == 'continuer':
                continuer = val
            elif var == 'delimiter':
                delimiter = val
        settingsChanged = True
    return ReturnCode.SUCCESS

def _unsetValueCommand(command, argv, objName, category):
    global settingsChanged

    argc = len(argv)
    if argc != 2:
        print('USAGE: {} <{}>'.format(command, objName))
        return
    else:
        if category == 'Settings':
            # Settings cannot be *removed*
            print('Error: MINIQUERY system setting "' + objName
                    + '" cannot be unset, only changed.')
            return
        else:
            del ms.settings[category][argv[0]]
            settingsChanged = True
        return

# Fcn names cannot be used until the fns have been defined, so this is 
# way down here
from miniGlobals import commandList

callbackList = [
    doSql,
    doQuit,
    doHelp,
    doHistory,
    doSetDatabase,
    doSetTable,
    doClearTable,
    doFormat,
    doSet,
    doAlias,
    doSetVariable,
    doGet,
    doGetAlias,
    doGetVariable,
    doSave,
    doSource,
    doUnset,
    doUnalias,
    doUnsetVariable,
    #doCompleter,
]

# Map/zip the command names to the corresponding callback functions
callbackMap = dict(zip([c[0] for c in commandList], callbackList))

# Main entry point.
if __name__ == '__main__':
    main()

