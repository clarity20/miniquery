import os
import sys
from shlex import split
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter, FuzzyCompleter

sys.path.append("../src/")

import miniEnv as env
from minihelp import giveMiniHelp
from errorManager import miniErrorManager as em, ReturnCode
from configManager import miniConfigManager as cfg
from argumentClassifier import miniArgs as args
from databaseConnection import miniDbConnection as dbConn
from queryProcessor import miniQueryProcessor as queryProcessor

# Reference: opensource.com/article/17/5/4-practical-python-libraries

MINI_PROMPT='mini>> '

def main():
    if '-h' in sys.argv or '--help' in sys.argv:
        giveMiniHelp()
        em.doExit()

    if env.setEnv() != ReturnCode.SUCCESS:
        em.doExit('Environment settings incomplete or incorrect.')

    args.classify(sys.argv[1:])

    oneAndDoneMode = 'e' in args.options

    if cfg.configureToSchema(args.mainTableName) != ReturnCode.SUCCESS:
        em.doExit()

    if oneAndDoneMode:
        print('In one and done mode.')
        # NO - just one execution, so what we have is what we need:
        #      args.classify(...)
        queryProcessor.process()

        em.doExit()

    # Pseudo-infinite event loop
    while 1:

        # Think through how options should be handled differently in interactive mode
        #   when processing subsequent commands: MINI_OPTIONS, persistent options, etc.

        # Accept normal MINIQUERY input. Break it down into arguments correctly.
        # We prolly do not want to run an autocompleter.
#TODO Test for existence/createability and writeability
        histFileName = '{}/mini.hst'.format(env.MINI_CONFIG)
        cmd = prompt(MINI_PROMPT,
                history = FileHistory(histFileName))
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

        if oneAndDoneMode:
            # cxn must be closed
            sys.exit(0)

# Main entry point.
if __name__ == '__main__':
    main()

