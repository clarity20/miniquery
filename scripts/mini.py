import os
import sys
from shlex import split
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter, FuzzyCompleter

sys.path.append("../src/")

import miniEnv as env
from minihelp import giveMiniHelp
from errorManager import miniErrorManager as em, ReturnCode
from configManager import miniConfigManager as cfg
from argumentClassifier import argumentClassifier
from queryProcessor import queryProcessor
from databaseConnection import miniDbConnection as dbConn

#Some of these settings should be made configurable
MINI_PROMPT='mini>> '
COMMAND_PREFIX='\\'   # another popular one is ':'

miniVariables = {}
args = argumentClassifier()

#TODO non-writeable hist file gives an error!
histFileName = ''
historyObject = None

def main():
    global args
    global histFileName
    global historyObject

    if '-h' in sys.argv or '--help' in sys.argv:
        giveMiniHelp()
        em.doExit()

    if env.setEnv() != ReturnCode.SUCCESS:
        em.doExit('Environment settings incomplete or incorrect.')

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

    args.classify(sys.argv[1:])
    if cfg.configureToSchema(args.mainTableName) != ReturnCode.SUCCESS:
        em.doExit()

    # In one-and-done mode, execute the cmd and exit
    oneAndDoneMode = 'e' in args.options
    if oneAndDoneMode:
        queryProcessor(args).process()
        em.doExit()

    # If there is a query on the command line, accept it
    if args.mainTableName and args.wheres or args.updates or args.postSelects:
        queryProcessor(args).process() == ReturnCode.SUCCESS or em.doExit()

    # Pseudo-infinite event loop
    print('Welcome to MINIQUERY!\n')
    print('Copyright (c) 2019 Miniquery\n')
    print('Enter {}h or {}help for help.\n'.format(COMMAND_PREFIX, COMMAND_PREFIX))
    histFileName = '{}/mini.hst'.format(env.MINI_CONFIG)
    historyObject = FileHistory(histFileName)
    session = PromptSession(history = historyObject)
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
            if func(argv[1:]) == ReturnCode.USER_EXIT:
                break
        else:
            args.classify(argv)
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
  *c{lear} <name>     : Clear the default table name\n\
  *d{rop}             : Drop a stashed command\n\
  *exit               : Exit MINIQUERY\n\
  *h{elp} <command>   : Detailed help for a command\n\
  *hi{story} <count>  : Display command history\n\
  *l{ist}             : List the stashed commands\n\
  *m{ode}             : Select a SQL subfamily mode\n\
  *o{utput}           : Select an output format\n\
  *q{uit}             : Exit MINIQUERY\n\
  *r{estore}          : Restore a stashed command\n\
  *state              : Summarize Miniquery state: settings & vars\n\
  *set <name> <value> : Set a MINIQUERY variable\n\
  *sq <query>         : Execute a literal SQL statement\n\
  *source <file>      : Read and execute commands from a file\n\
  *stash              : Stash and suspend the current command\n\
  *t{able} <name>     : Set the default table name\n\
  *un{alias} <name>   : Undefine a command alias\n\
  *uns{et}            : Set a MINIQUERY variable\n\
  *. <file>           : Read and execute commands from a file'

        print(helpText.replace('*', COMMAND_PREFIX))
    else:
        #TODO print('FUTURE: command-specific help')
        pass
    return

def doSql(sql):
    global args  # The classified args. Should they be adjustable in the :sq cmd?
    #TODO: Make variable substitutions in the literal sql
    queryProcessor(args).process(" ".join(sql))
    return

def doQuit(argv):
    return ReturnCode.USER_EXIT

def doHistory(argv):
    #TODO: Set a default history depth.
    global historyObject
    l = list(reversed(historyObject.get_strings()))
    print("\n".join(l[0:int(argv[0])]))
    return

def doMode(argv):
    return

def doOutput(argv):
    return

def doSet(argv):
    # Use miniVariables defined up top
    return

def doUnset(argv):
    # Use miniVariables defined up top
    return

def doSetTable(argv):
    return

def doClearTable(argv):
    return

def doAlias(argv):
    return

def doUnalias(argv):
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
        'set'    : doSet,
        'uns'    : doUnset,
        'alias'  : doAlias,
        'al'     : doAlias,
        'unalias': doUnalias,
        'un'     : doUnalias,
        'unset'  : doUnset,
        'table'  : doSetTable,
        't'      : doSetTable,
        'clear'  : doClearTable,
        'c'      : doClearTable,
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

