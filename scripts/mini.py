import os
import sys
from shlex import split
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter, FuzzyCompleter
from prompt_toolkit.shortcuts import yes_no_dialog

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
MINI_PROMPT='mini>> '   #TODO Try 'curDB.curTable >> '
COMMAND_PREFIX='\\'   # another popular one is ':'

args = argumentClassifier()
settingsChanged = False

#TODO non-writeable hist file gives an error!
historyObject = None

def main():
    global args
    global historyObject

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
            #TODO This handles queries only. We should also accept miniquery cmds:
            #TODO look for the command prefix at cmd[0]
            argv = split(cmd)
            args.classify(argv)

            # Reconfigure if/when the table name changes
            if args.mainTableName != oldTableName:
                if cfg.configureToSchema(args.mainTableName) != ReturnCode.SUCCESS:
                    em.doExit()
                oldTableName = args.mainTableName

            # Finally:
            queryProcessor(args).process() == ReturnCode.SUCCESS or em.doExit()

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

    # Pseudo-infinite event loop
    print('WELCOME TO MINIQUERY!\n')
    print('Copyright (c) 2019 Miniquery\n')
    print('Enter {}h or {}help for help.\n'.format(COMMAND_PREFIX, COMMAND_PREFIX))
    histFileName = '{}/mini.hst'.format(env.MINI_CONFIG)
    historyObject = FileHistory(histFileName)
    session = PromptSession(history = historyObject)
    oldTableName = ''
    while 1:
        # Accept normal MINIQUERY input. Break it down into arguments correctly.
        try:
            cmd = session.prompt(MINI_PROMPT)
        except EOFError:
            #TODO: Is cxn closed and is everything cleaned up?
            break

        #TODO: Advise the user about special characters and escape sequences:
        # Literal whitespace (space, tab, etc.) is interpreted as a delimiter
        # unless quoted or \-escaped, which cause it to be embedded as-is.
        # The escape sequences \t, \n, etc. are interpreted as delimiters
        # unless quoted, in which case they are passed as raw character pairs.
        # Otherwise, just about everything is passed raw, bypassing the usual
        # actions of command-shell interpretation that require lots of extra
        # protection or escaping. Be sure to tout the advantage this offers
        # to REPL Miniquery over one-and-done Miniquery.
        argv = split(cmd)

        # Distinguish special commands from queries by looking for the command
        # prefix (on cmd, not argv; when '\' is the prefix, split() strips it.)
        if cmd.startswith(COMMAND_PREFIX):
            # Call the function indicated by the first word
            word = argv[0].lstrip(COMMAND_PREFIX).lower()
            func = callbackMap[word]
            result = func(argv[1:])
            if result == ReturnCode.SUCCESS:
                pass
            elif result == ReturnCode.USER_EXIT:
                break
            elif result == ReturnCode.DATABASE_CONNECTION_ERROR:
                # Allow the user to fix the connection settings and keep going.
                #TODO This requires the ability to change the settings. One sit8n
                #TODO is a failed cxn due to bad cxn strings.
                #TODO Accept changes, & upon "reconnect" cmd, try to reconnect.
                em.doWarn()
                continue
        else:
            args.classify(argv)

            # Reconfigure if/when the table name changes
            #TODO: Move this to the callback for table-name changing
            if args.mainTableName != oldTableName:
                if cfg.configureToSchema(args.mainTableName) != ReturnCode.SUCCESS:
                    em.doExit()
                oldTableName = args.mainTableName

            if queryProcessor(argv).process() != ReturnCode.SUCCESS:
                # Allow the user to fix the connection settings and keep going
                #TODO Verify that changed environments are actually re-loaded
                em.doWarn()
                continue

        # Skip what follows, come back to it later
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


def doHelp(argv):
    if not argv:
        print('\nMINIQUERY COMMANDS:\n')

        helpText = '  *al{ias} <new> <old>: Define an alias for a command\n\
  *s{ave}             : Save MINIQUERY user settings\n\
  *exit, *q{uit}      : Exit MINIQUERY\n\
  *h{elp} <command>   : Detailed help for a command\n\
  *hi{story} <count>  : Display command history\n\
  *t{able} <name>     : Set the default table name\n\
  *clear <name>       : Clear the default table name\n\
  *ct <name>          : Clear the default table name\n\
  *d{rop}             : Drop a stashed command\n\
  *l{ist}             : List the stashed commands\n\
  *o{utput}           : Select an output format\n\
  *r{estore}          : Restore a stashed command\n\
  *st{ate}            : Summarize Miniquery state: settings & vars\n\
  *set <name>=<value> : Set/inspect a MINIQUERY program setting\n\
  *sq <query>         : Execute a literal SQL statement\n\
  *source <file>      : Read and execute commands from a file\n\
  *stash              : Stash and suspend the current command\n\
  *un{alias} <name>   : Undefine a command alias\n\
  *uns{et}            : Unset a MINIQUERY setting\n\
  *v{ariable} <name>=<val> : Set/inspect a variable\n\
  *. <file>           : Read and execute commands from a file'

#TODO: Add these
#*m{ode}             : Select a SQL subfamily mode\n\
#*ab{brev}           : Define an object-name abbreviation\n\

        print(helpText.replace('*', COMMAND_PREFIX))
    else:
        #TODO print('FUTURE: command-specific help')
        pass
    return

def doSql(sql):
    global args  # The classified args. Should they be adjustable in the :sq cmd?
    #TODO: Make variable substitutions in the literal sql
    return queryProcessor(args).process(" ".join(sql))

def doQuit(argv):
    global settingsChanged

    if settingsChanged:
        choice = button_dialog(title='Save before quitting?',
                text='Save changes to your MINIQUERY settings before quitting?'
                buttons=[('Yes',True), ('No',False), ('Cancel',None)])
        if choice:
            ms.settings.filename = env.HOME + '/mini.rc'
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
    return

def doHistory(argv):
    global historyObject
    argc = len(argv)

    l = list(reversed(historyObject.get_strings()))
    available = len(l)
    requested = int(argv[0] if argc > 0 else ms.settings['Settings']['historyLength'])
    print("\n".join(l[0:min(available, requested)]))
    return

def doMode(argv):
    global settingsChanged

    # Not yet implemented
    settingsChanged = True
    return

def doOutput(argv):
    global settingsChanged
    argc = len(argv)

    # Select an output format: tab, nowrap, wrap, vertical
    #TODO: Present options dialog if no arg is given
    if argc >= 1:
        if argv[0] in ['tab','wrap','nowrap','vertical']:
            ms.settings['Settings']['output'] = argv[0]
            settingsChanged = True
        else:
            print('Illegal option. Please choose tab, wrap, nowrap or beetical.')
    return

def doSetTable(argv):
    global settingsChanged

    #TODO: Allow for abbreviated table names by expanding here
    ms.settings['Settings']['table'] = argv[0]
    settingsChanged = True
    return

def doClearTable(argv):
    global settingsChanged

    #TODO: Allow for abbreviated table names by expanding here
    ms.settings['Settings']['table']=''
    settingsChanged = True
    return

def doStash(argv):
    return

def doList(argv):
    return

def doDrop(argv):
    return

def doRestore(argv):
    return

def doSource(argv):
    # Source a command file, a lot like input redirection
    return

def doSet(argv):
    #TODO:This might not work because settings are not flat like aliases and variables are
    argc = len(argv)
    category = 'Settings'
    subcategory = None

    if argc == 2:
        varName = argv[0]
    elif argc == 1 and '=' in argv[0]:
        varName, eq, b = argv[0].partition('=')
    for d in ms.settings['ConnectionString']:`
        if isinstance(d, dict) and varName in d:
            category = 'ConnectionString'
            subcategory = d
            break

    _setValueCommand(argv, 'settingName', 'value', category, 'choice of setting', subcategory)
    return

def doUnset(argv):
    #TODO:This might not work because settings are not flat like aliases and variables are
    category = 'Settings'
    subcategory = None
    for d in ms.settings['ConnectionString']:`
        if isinstance(d, dict) and varName in d:
            category = 'ConnectionString'
            subcategory = d
            break

    _unsetValueCommand(argv, 'settingName', category, subcategory)
    return

def doAlias(argv):
    _setValueCommand(argv, 'alias', 'command', 'Aliases', 'a native command')
    return

def doUnalias(argv):
    _unsetValueCommand(argv, 'aliasName', 'Aliases')
    return

def doSetVariable(argv):
    _setValueCommand(argv, 'name', 'value', 'Variables', 'text to be substituted')
    return

def doUnsetVariable(argv):
    _unsetValueCommand(argv, 'variable', 'Variables')
    return

def _setValueCommand(argv, lhs, rhs, category, desc, subcategory=None):
    global settingsChanged
    argc = len(argv)
    #TODO: handle subcategoried values

    # Set or query a MINIQUERY system value, depending on argc
    if argc == 0:
        print('USAGE: {0} <{1}>=<{2}>\n   or: {0} <{1}>'.format(
            argv[0], lhs, rhs))
        print('    where <{}> is {}'.format(rhs, desc))
    elif argc == 1:
        # Value assignment
        if '=' in argv[0]:
            var, eq, val = argv[0].partition('=')
            if subcategory:
                ms.settings[category][subcategory][var] = val
            else:
                ms.settings[category][var] = val
            settingsChanged = True
        # Value inquiry
        elif argv[0] in ms.settings[category]:
            print('{}: {}'.format(argv[0], ms.settings[category][argv[0]]))
        else:
            print('{} is not defined.'.format(argv[0]))
    elif argc == 2:
        if subcategory:
            ms.settings[category][subcategory][argv[0]] = argv[1]
        else:
            ms.settings[category][argv[0]] = argv[1]
        settingsChanged = True
    return ReturnCode.SUCCESS

def _unsetValueCommand(argv, objName, category):
    global settingsChanged

    argc = len(argv)
    if argc != 2:
        print('USAGE: {} <{}>'.format(argv[0], objName))
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
        'h'      : doHelp,
        'help'   : doHelp,
        'sq'     : doSql,
        'q'      : doQuit,
        'quit'   : doQuit,
        'exit'   : doQuit,
        'history': doHistory,
        'hi'     : doHistory,
        'm'      : doMode,
        'mode'   : doMode,
        'o'      : doOutput,
        'output' : doOutput,
        's'      : doSave,
        'save'   : doSave,
        'set'    : doSet,
        'unset'  : doUnset,
        'uns'    : doUnset,
        'alias'  : doAlias,
        'al'     : doAlias,
        'unalias': doUnalias,
        'un'     : doUnalias,
        'v'      : doSetVariable,
        'setv'   : doSetVariable,
        'unsetv' : doUnsetVariable,
        'table'  : doSetTable,
        't'      : doSetTable,
        'clear'  : doClearTable,
        'ct'     : doClearTable,
        'stash'  : doStash,
        'l'      : doList,
        'list'   : doList,
        'restore': doRestore,
        'source' : doSource,
        '.'      : doSource
        }

# Main entry point.
if __name__ == '__main__':
    main()

