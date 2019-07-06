import miniEnv as env
from shlex import split

class argumentClassifier:
    # Let data be global as there should only be one instance
    mainTableName = ''
    options = {}
    preSelects = []
    postSelects = []
    wheres = []
    updates = []

    def _toggleOptions(self, setTo, value1, value2):
        if setTo == value1:
            if value2 in self.options:
                del self.options[value2]
        else:
            if value1 in self.options:
                del self.options[value1]
        self.options[setTo] = None

    def classify(self, argList):
        # Turn on the preconfigured settings first, then the command line ones
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

miniArgs = argumentClassifier()
