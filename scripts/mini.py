import os
import sys
import re
from shlex import split
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter, FuzzyCompleter
from prompt_toolkit.shortcuts import yes_no_dialog, button_dialog

sys.path.append("../src/")

import miniEnv as env
from miniHelp import giveMiniHelp
from appSettings import miniSettings as ms
from errorManager import miniErrorManager as em, ReturnCode
from configManager import miniConfigManager as cfg
from argumentClassifier import argumentClassifier
from queryProcessor import queryProcessor
from databaseConnection import miniDbConnection as dbConn

#TODO Some of these settings should be made configurable
MINI_PROMPT='\nmini>> '   #TODO Try 'curDB.curTable >> '
MINI_PROMPT_PS2='   --> '
COMMAND_PREFIX='\\'   # another popular one is ':'

args = argumentClassifier()
settingsChanged = False
continuer = ''; delimiter = ''; endlineProtocol = None

#TODO non-writeable hist file gives an error!
historyObject = None

def main():
    global args
    global historyObject
    global continuer, delimiter, endlineProtocol

    if '-h' in sys.argv or '--help' in sys.argv:
        giveMiniHelp()
        em.doExit()

    if env.setEnv() != ReturnCode.SUCCESS:
        em.doExit('Environment settings incomplete or incorrect.')

    if ms.loadSettings() == ReturnCode.SUCCESS:
        env.setDatabaseName(ms.settings['Settings']['database'])
    else:
        em.doExit()

    # If the standard input has been redirected, execute its commands
    # and quickly exit, as in mysql
    if not sys.stdin.isatty():
        oldTableName = ''
        while 1:
            cmd = sys.stdin.readline()
            if not cmd:
                break
            retValue, oldTableName = dispatchCommand(cmd, oldTableName)

            # Exit early if there is an incident
            if retValue != ReturnCode.SUCCESS:
                em.doExit()

        # Exit at EOF
        em.doExit()

    args.classify(sys.argv[1:])   # skip the program name

    # In one-and-done mode, execute the cmd and exit
    oneAndDoneMode = 'e' in args.options
    if oneAndDoneMode:
        if cfg.configureToSchema(args.mainTableName) != ReturnCode.SUCCESS:
            em.doExit()
        queryProcessor(args).process()
        em.doExit()

    # If there is a query on the command line, accept it
    if args.mainTableName and args.wheres or args.updates or args.postSelects:
        if cfg.configureToSchema(args.mainTableName) != ReturnCode.SUCCESS:
            em.doExit()
        queryProcessor(args).process() == ReturnCode.SUCCESS or em.doExit()

    # Prelude to the pseudo-infinite event loop
    print('WELCOME TO MINIQUERY!\n')
    print('Copyright (c) 2019 Miniquery\n')
    print('Enter {}help for help.'.format(COMMAND_PREFIX, COMMAND_PREFIX))
    histFileName = '{}/mini.hst'.format(env.MINI_CONFIG)
    historyObject = FileHistory(histFileName)
    session = PromptSession(history = historyObject)
    oldTableName = ''
    currentPrompt = MINI_PROMPT
    cmdBuffer = []
    # Cache a few dictionary lookups which should not change very often:
    continuer = ms.settings['Settings']['continuer']
    delimiter = ms.settings['Settings']['delimiter']
    endlineProtocol = ms.settings['Settings']['endlineProtocol']

    # The infinite event loop: Accept and dispatch MINIQUERY commands
    while 1:

        # The command buffering loop: buffer command fragments according to
        # the line protocol until a complete command is detected
        try:
            while 1:
                cmd = session.prompt(currentPrompt)

                # Is end-of-command detected?
                isDelimited = cmd.endswith(delimiter)
                if isDelimited or (
                        not cmd.endswith(continuer) and endlineProtocol == 'delimit'):
                    cmdBuffer.append(cmd.rstrip(delimiter))
                    cmd = ' '.join(cmdBuffer)
                    cmdBuffer.clear()
                    currentPrompt = MINI_PROMPT
                    # The command is complete and ready for dispatch
                    break

                # Command continuation is indicated
                else:
                    cmdBuffer.append(cmd.rstrip(continuer))
                    currentPrompt = MINI_PROMPT_PS2
        except EOFError:
            break

        retValue, oldTableName = dispatchCommand(cmd, oldTableName)
        if retValue == ReturnCode.USER_EXIT:
            break

        # Experiment with autocompletion. Come back to this later.
        if False:

            # The table-name expander should look at argv[1]
            # and return a candidate list. We would then call promptForExpansion() which would
            # call the prompt-toolkit's wordCompleter() as below to resolve any ambiguity.

            subChoiceDict = WordCompleter(['TimeFirst', 'TimeSecond', 'TimeThird'],
                                    ignore_case=True)    # Would be passed in to the resolver
            choiceDict = FuzzyCompleter(subChoiceDict)

            # Set the prompt, showing the menu and providing a default choice
            # Research the options complete_while_typing

            # This updates the popup menu as more letters are typed. Backspacing does NOT bring back
            # old options. Cursor movement disables completion.
            s = prompt('MAW >> ',  # or session.prompt() ?
                    history=FileHistory('t2.hst'),
                    # Visit the GitHub page for python-prompt-toolkit for help writing a custom
                    # autocompleter based on the FuzzyCompleter in the completion subdir.
                    completer=choiceDict,
                    default='Default'
                    )
            if s == 'Done.':
                break
            print ('You said ' + s)

    em.doExit()


def dispatchCommand(cmd, oldTableName):

    # Distinguish commands from queries by looking for the command prefix
    if cmd.startswith(COMMAND_PREFIX):
        cmd = cmd.lstrip(COMMAND_PREFIX)

        # Resolve command aliases
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

        # Substitute values in place of MINIQUERY variables
        varName = ''
        variable = re.search(r'\$(\w+)', cmd)
        while variable:
            varName = variable.group(1)
            try:
                cmd = re.sub('\$'+varName, ms.settings['Variables'][varName], cmd)
            except KeyError:
                print('Unknown variable "' + varName + '"')
            variable = re.search(r'\$(\w+)', cmd)

        argv = split(cmd)

        # Call the function indicated by the first word
        word = argv[0].lower()
        try:
            func = callbackMap[word]
        except KeyError:
            print('Unknown command "'+ word + '"')
            return ReturnCode.SUCCESS, oldTableName
        result = func(argv[1:])
        if result == ReturnCode.SUCCESS:
            return ReturnCode.SUCCESS, oldTableName
        elif result == ReturnCode.USER_EXIT:
            return ReturnCode.USER_EXIT, oldTableName
        elif result == ReturnCode.DATABASE_CONNECTION_ERROR:
            # Allow the user to fix the connection settings and keep going.
            #TODO This requires the ability to change the settings. One sit8n
            #TODO is a failed cxn due to bad cxn strings.
            #TODO Accept changes, & upon "reconnect" cmd, try to reconnect.
            em.doWarn()
            return ReturnCode.SUCCESS, oldTableName
        else:
            print('Unrecognized return code for command "' + cmd + '"')
            return ReturnCode.SUCCESS, oldTableName

    # It's a query, not a command
    else:
        argv.split(cmd)

        # Substitute for variables as above
        varName = ''
        variable = re.search(r'\$(\w+)', cmd)
        while variable:
            varName = variable.group(1)
            try:
                cmd = re.sub('\$'+varName, ms.settings['Variables'][varName], cmd)
            except KeyError:
                print('Unknown variable "' + varName + '"')
            variable = re.search(r'\$(\w+)', cmd)
        if varName:
            argv = split(cmd)

        args.classify(argv)

        # Reconfigure if/when the table name changes
        #TODO: Move this to the callback for table-name changing
        if args.mainTableName != oldTableName:
            if cfg.configureToSchema(args.mainTableName) != ReturnCode.SUCCESS:
                em.doExit()
            oldTableName = args.mainTableName

        retValue = queryProcessor(argv).process()
        if retValue != ReturnCode.SUCCESS:
            # Allow the user to fix the connection settings and keep going
            #TODO Verify that changed environments are actually re-loaded
            em.doWarn()
            return retValue, oldTableName

    return ReturnCode.SUCCESS, oldTableName

def doHelp(argv):
    if not argv:
        print('\nMINIQUERY COMMANDS:\n')

        helpText = '\
  *sq <query>         : Execute a literal SQL statement\n\
  *quit               : Exit MINIQUERY\n\
  *help <command>     : Detailed help for a command\n\
  *history <count>    : Display command history\n\
  *table <name>       : Set the default table name\n\
  *clear <name>       : Clear the default table name\n\
  *format             : Select an output format\n\
  *set <name>=<value> : Set a MINIQUERY program setting\n\
  *seta <new>=<old>   : Set up an alias for a command\n\
  *setv <name>=<val>  : Set a macro variable\n\
  *get                : Inspect a setting value\n\
  *geta               : Inspect a setting value\n\
  *getv               : Inspect a setting value\n\
  *save               : Save MINIQUERY user settings\n\
  *source <file>      : Read and execute commands from a file\n\
  *unalias <name>     : Undefine a command alias\n\
  *unset              : Unset a MINIQUERY setting\n\
  *unseta             : Unset an alias \n\
  *unsetv             : Unset a macro variable'

#TODO: Add these
#*m{ode}             : Select a SQL subfamily mode\n\
#*ab{brev}           : Define an object-name abbreviation\n\
#TODO: Add a list of TOPICS such as the prompt and how to write MINI-queries

        print(helpText.replace('*', COMMAND_PREFIX))
    else:
        #TODO print('FUTURE: command-specific help')
        pass
    return ReturnCode.SUCCESS

def doSql(sql):
    # Most of the classified args should not apply here. The purpose of "sq"
    # is to allow literal SQL exactly as-is, i.e. no alterations. But we still
    # need to fall back on the program settings: runMode, display format, ...
    # So here we clear the options, copy the settings, and then run the query.
    global args
    args.options.clear()
    args.backfillOptions()
    return queryProcessor(args).process(" ".join(sql))

def doQuit(argv):
    global settingsChanged

    if settingsChanged:
        choice = button_dialog(title='Save before quitting?',
                text='Save changes to your MINIQUERY settings before quitting?',
                buttons=[('Yes',True), ('No',False), ('Cancel',None)])
        if choice:
            ms.settings.filename = os.path.join(env.HOME, '.mini.rc')
            ms.settings.write()
            return ReturnCode.USER_EXIT
        elif choice == None:
            return ReturnCode.SUCCESS
        elif choice == False:
            return ReturnCode.USER_EXIT
    else:
        if yes_no_dialog(title='Quit MINIQUERY',
                text='Exit MINIQUERY: Are you sure?'):
            return ReturnCode.USER_EXIT

def doSave(argv):
    global settingsChanged

    if settingsChanged:
        # Save program settings, variables and aliases
        if yes_no_dialog(title='Confirm save',
                text='Save changes to your MINIQUERY settings?'):
            ms.settings.filename = os.path.join(env.HOME, '.mini.rc')
            ms.settings.write()
            settingsChanged = False
    else:
        print('No unsaved changes.')
    return ReturnCode.SUCCESS

def doHistory(argv):
    global historyObject
    argc = len(argv)

    l = list(reversed(historyObject.get_strings()))
    available = len(l)
    requested = int(argv[0] if argc > 0 else ms.settings['Settings']['historyLength'])
    print("\n".join(l[0:min(available, requested)]))
    return ReturnCode.SUCCESS

def doMode(argv):
    global settingsChanged

    # Not yet implemented
    #settingsChanged = True
    return ReturnCode.SUCCESS

def doFormat(argv):
    global settingsChanged
    argc = len(argv)

    optionsTuple = settingOptionsMap['format']
    _chooseValueFromList(optionsTuple[0], 'Settings', 'format',
                optionsTuple[1], optionsTuple[2],
                userEntry=argv[0] if argc >= 1 else None)
    return ReturnCode.SUCCESS

def doSetDatabase(argv):
    global settingsChanged
    global args

    #TODO: MAYBE allow for abbreviated db names by expanding here
    ms.settings['Settings']['database'] = argv[0]
    # Run a "use" query to make the change effective
    queryProcessor(args).process("USE " + argv[0])
    #TODO: Change the prompt
    settingsChanged = True
    return ReturnCode.SUCCESS

def doSetTable(argv):
    global settingsChanged

    #TODO: Allow for abbreviated table names by expanding here
    ms.settings['Settings']['table'] = argv[0]
    #TODO: Change the prompt
    settingsChanged = True
    return ReturnCode.SUCCESS

def doClearTable(argv):
    global settingsChanged

    ms.settings['Settings']['table']=''
    settingsChanged = True
    return ReturnCode.SUCCESS

def doSource(argv):
    argc = len(argv)

    # Source a command file, a lot like input redirection
    #TODO: Consider a "file open" dialog, but it might be hard since the toolkit doesn't have one
    if argc < 1:
        print('A filename is required.')
        return

    print('Sourcing ' + argv[0])
    try:
        with open(argv[0], 'r') as sourceFp:
            oldTableName = ''
            for line in sourceFp:
                retValue, oldTableName = dispatchCommand(line, oldTableName)
                if retValue != ReturnCode.SUCCESS: 
                    em.doWarn()
    except FileNotFoundError:
        print('Unable to open file ' + argv[0])

    return ReturnCode.SUCCESS


# Constants for interactive selection of finite-option settings:
# 3-tuples containing option list, dialog title, and dialog text
settingOptionsMap = {
    'format'   : (['tab','wrap','nowrap','vertical'],
                    'Result set formatting',
                    'Please choose a display format for query results:'),
    'endlineProtocol' : (['delimit','continue'],
                    'Endline interpretation protocol',
                    'Please choose a protocol for interpreting lines of query text:'),
    'runMode'  : (['query','run','both'],
                    'MINIQUERY run mode',
                    'Choose whether to show the generated queries, to run them, or to do both:')
    }

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
                print(s[0] + ': ' + s[1])
            print()
            for s in ms.settings['ConnectionString'].items():
                if isinstance(s[1], dict):
                    for s1 in s[1].items():
                        print(s1[0] + ': ' + s1[1])
                else:
                    print(s[0] + ': ' + s[1])
        elif settingName in ms.settings['Settings']:
            print(settingName + ': ' + ms.settings['Settings'][settingName])
        else:
            found = False
            for s in ms.settings['ConnectionString']:
                if isinstance(s, dict) and settingName in s:
                    print(settingName + ': ' + ms.settings['ConnectionString'][s][settingName])
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


# Function that accepts a value from a small set of valid options.
# Accepts a typed-in value, but if none is provided brings up a selection dialog
def _chooseValueFromList(lst, category, setting, title, text, userEntry='',
            subcategory=None, canCancel=True):
    global endlineProtocol

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
                userChoice, csv))
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

    return settingsChanged


# Function to set or query a MINIQUERY system setting when an "infinitude"
# of values are allowed. The user-proposed value is NOT validated -- anything
# For finite value sets, _chooseValueFromList() is the way to go.
#
# N.B.: This function doubles as a setter for "user customizations" that are not
# "settings," per se: aliases, variables and abbreviations. The distinction is
# noted in the "command" argument.
def _setArbitraryValue(command, argv, lhs, rhs, category, desc, subcategory=None):
    global settingsChanged, continuer, delimiter
    argc = len(argv)

    # Set or query a MINIQUERY system value, depending on argc
    if argc == 0:
        print('USAGE: {0} <{1}>=<{2}>\n   or: {0} <{1}> <{2}>'.format(
            command, lhs, rhs))
        print('    where <{}> is {}'.format(rhs, desc))
    elif argc == 1 and '=' in argv[0]: # Value assignment
        var, eq, val = argv[0].partition('=')
        if subcategory:
            ms.settings[category][subcategory][var] = val
        else:
            ms.settings[category][var] = val
            if var == 'continuer':
                continuer = val
            elif var == 'delimiter':
                delimiter = val
        settingsChanged = True
    elif argc == 2:
        var = argv[0]
        if subcategory:
            ms.settings[category][subcategory][var] = argv[1]
        else:
            ms.settings[category][var] = argv[1]
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
                    + '" can only be changed, not unset.')
            return
        else:
            del ms.settings[category][argv[0]]
            settingsChanged = True
        return

callbackMap = {
        'help'   : doHelp,
        'sq'     : doSql,
        'quit'   : doQuit,
        'history': doHistory,
        'mode'   : doMode,
        'format' : doFormat,
        'save'   : doSave,
        'set'    : doSet,
        'get'    : doGet,
        'unset'  : doUnset,
        'seta'   : doAlias,
        'geta'   : doGetAlias,
        'unseta' : doUnalias,
        'setv'   : doSetVariable,
        'getv'   : doGetVariable,
        'unsetv' : doUnsetVariable,
        'db'     : doSetDatabase,
        'table'  : doSetTable,
        'clear'  : doClearTable,
        'source' : doSource,
        }

# Main entry point.
if __name__ == '__main__':
    main()

