import re
from shlex import split

import miniEnv as env
from appSettings import miniSettings; ms = miniSettings

class argumentClassifier:

    def __init__(self):
        self.mainTableName = ''
        self.options = {}
        self.preSelects = []
        self.postSelects = []
        self.wheres = []
        self.updates = []

    def _toggleOptions(self, setTo, value1, value2):
        if setTo == value1:
            if value2 in self.options:
                del self.options[value2]
        else:
            if value1 in self.options:
                del self.options[value1]
        self.options[setTo] = None

    def classify(self, argList):
        # Turn on the preconfigured settings first
        for arg in split(env.MINI_OPTIONS) + argList:
            if arg[0] == '-':
                # Option arguments
                op, eq, vl = arg.lstrip('-').partition('=')
                
                # Options presented on the cmd line should override
                # any default settings that conflict with them. Some
                # such options must be manually toggled to achieve
                # this behavior.
                try:
                    # Enforce mutual exclusivity for certain option-pairs
                    #   -a, -o      and/or setting
                    #   -2v, -3v    2- or 3-valued logic
                    #   -e, -i      one-and-done or interactive mode
                    # et cetera
                    whichOpt = ['o','a','2v','3v','e','i'].index(op)
                    if whichOpt < 2:
                        self._toggleOptions(op, 'o', 'a')
                    elif whichOpt < 4:
                        self._toggleOptions(op, '2v', '3v')
                    elif whichOpt < 6:
                        self._toggleOptions(op, 'e', 'i')

                except ValueError:
                    # Normal (Non-toggling) options
                    self.options[op] = vl

            elif arg[0] == '+':
                # Selection arguments
                # basic formats: +x, ++x, +1x, ++1x
                if arg[1] == '+':
                    if arg[2] == '1':
                        self.preSelects.append('+' + arg[3:])
                    else:
                        self.postSelects.append(arg[1:])
                elif arg[1] == '1':
                    self.preSelects.append(arg[2:])
                else:
                    self.postSelects.append(arg[1:])
            #TODO: order by / group by
            #elif arg[0] in ['/', '%']:
                #pass
            elif re.search('[+*/%:-]=', arg):
                self.updates.append(arg)
            elif not self.mainTableName:
                self.mainTableName = arg
            else:
                self.wheres.append(arg)

        # Fall back on the program settings when certain important options
        # are not set on the command line
        self.backfillOptions()

    # Options coming from the command line have precedence over the program
    # settings. But we need to incorporate the latter in the final
    # 'options' vector if no option has been explicitly set.
    def backfillOptions(self):
        if {'q','r'}.isdisjoint(set(self.options.keys())):
            mode = ms.settings['Settings']['runMode']
            if mode in ['query', 'both']:
                self.options['q'] = True
            if mode in ['run', 'both']:
                self.options['r'] = True

        if {'tab','vertical','wrap','nowrap'}.isdisjoint(set(self.options.keys())):
            mode = ms.settings['Settings']['format']
            self.options[mode] = True

