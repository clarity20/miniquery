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

MINI_PROMPT='mini>> '

def main():
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
            args = argumentClassifier()
            args.classify(argv)

            # Reconfigure if/when the table name changes
            if args.mainTableName != oldTableName:
                if cfg.configureToSchema(args.mainTableName) != ReturnCode.SUCCESS:
                    em.doExit()
                oldTableName = args.mainTableName

            # Finally:
            queryProcessor(args).process() == ReturnCode.SUCCESS or em.doExit()

        em.doExit()

    args = argumentClassifier()
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
    print('Enter :h or :help for help.\n')
    histFileName = '{}/mini.hst'.format(env.MINI_CONFIG)
    session = PromptSession(history = FileHistory(histFileName))
    while 1:

        # Accept normal MINIQUERY input. Break it down into arguments correctly.
        # We prolly do not want to run an autocompleter.
#TODO Test for existence/createability and writeability
        try:
            cmd = session.prompt(MINI_PROMPT)
            print('Received data: ' + cmd)
        except EOFError:
            # Is cxn closed and is everything cleaned up?
            break

        argv = split(cmd)

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
            s = prompt('MAW >> ',
                    history=FileHistory('t2.hst'),
                    # Visit the GitHub page for python-prompt-toolkit for help writing a custom
                    # autocompleter based on the FuzzyCompleter in the completion subdir.
                    completer=choiceDict,
                    default='Default'
                    )
            if s == 'Done.':
                break
            print ('You said ' + s)

# Main entry point.
if __name__ == '__main__':
    main()

