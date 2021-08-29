import os
import re
import sys
from shlex import split

import miniEnv as env
from appSettings import miniSettings as ms, fakePass

sys.path.append(".." + os.sep + "util")
from miniGlobals import tqlCommands

class ArgumentClassifier:
    # Define the legal values for radio-button options
    RADIOSET_CONJUNCTIONS = {'a', 'o'}    # and/or
    RADIOSET_VALUE_LOGICS = {'2v', '3v'}  # 2- or 3-valued logic
    RADIOSET_EXECUTION_MODES = {'e', 'int'} # one-and-done or interactive
    RADIOSET_DISPLAY_MODES = {'tab', 'wrap', 'nowrap', 'vertical'}
    RADIO_OPTIONS_BY_SET = [(setId, opt) for (setId, options) in enumerate([
                                    RADIOSET_CONJUNCTIONS,
                                    RADIOSET_VALUE_LOGICS,
                                    RADIOSET_EXECUTION_MODES,
                                    RADIOSET_DISPLAY_MODES
                                    ])
                                for opt in options]

    # Use class-level storage for the option flags that need to be in effect
    # across commands until changed
    _persistentOptions = {}

    def __init__(self, optionList=[]):
        """
        Initialize an ArgumentClassifier object.
        """
        self.mainTableName = ''
        self._commandName = ''
        self._argumentTree = {}
        self._operators = []
        self._literalSql = None    # Used in the special case of \sq commands
        self._isQueryCommand = None
        self._isExplicitCommand = None

        # The options in effect for the current command, defined as the persistent options
        # adjusted by any transient overrides specified by option flags in the command.
        self._options = {}

        # Caller can force a given option list upon a command, overriding the persistent/transient
        # distinction, by specifying the optionList
        if optionList:
            for opt in optionList:
                op, eq, vl = opt.partition('=')
                self._addOption(op, vl)

    def initPersistentOptions(self):
        '''
        We do not expect the persistent options to change often. This method
        is a slight optimization for when they all need to be set at program
        startup. Subsequent changes to these options should be handled by addOption().
        '''

        # If the persistent options have already been initialized, do nothing
        if ArgumentClassifier._persistentOptions:
            return ArgumentClassifier._persistentOptions

        # Translate the config settings to options (at least those which
        # can be so translated), since these are the ultimate fallbacks which
        # everything else, when present, serves to override

        # 1. runMode
        settings = ms.settings['Settings']
        if settings['runMode'] == 'both':
            ArgumentClassifier._persistentOptions['r'] = True
            ArgumentClassifier._persistentOptions['q'] = True
        elif settings['runMode'] == 'query':
            ArgumentClassifier._persistentOptions['q'] = True
        else:
            ArgumentClassifier._persistentOptions['r'] = True
        # 2. display format
        mode = settings['format']
        ArgumentClassifier._persistentOptions[mode] = True
#TODO: 3. Anything else ??? continuer/delimiter?

        # Secondly, append the hidden (env) options. They have precedence over the above.
        for arg in split(env.MINI_OPTIONS):
            option, eq, value = arg.lstrip('-').partition('=')
            self._addOption(option, value, True)   # Do we need "value or True" instead?

        # We skip any options set on the command line because they are transient.
        return ArgumentClassifier._persistentOptions


    def addOption(self, option, value=None, isPersistent=False):
        '''
        Exposes the option settings for write access, either transiently
        or persistently. In particular, whenever an option is changed through
        a System Command, call this to ensure the change is propagated to
        the (internal) persistent options, not just the program settings.
        '''
        return self._addOption(option, value, isPersistent)


    def _addOption(self, option, value=None, isPersistent=False):
        '''
        Add an option to the options (or the persistent options) or change the value
        of an existing option while enforcing exclusivity of the "radio button" ones
        '''

        optionList = ArgumentClassifier._persistentOptions if isPersistent else self._options

        # Find the radio group containing this option, if any
        try:
            groupIdOptionPair = [x for x in self.RADIO_OPTIONS_BY_SET if x[1] == option][0]
            groupId = groupIdOptionPair[0]

        # For non-radio-type options, do a quick set-and-return
        except IndexError:
            optionList[option] = value
            return self

        # Get the whole radio group
        radioGroup = {x for x in self.RADIO_OPTIONS_BY_SET if x[0] == groupId}
        # Enforce radio behavior: Turn on the selected option and turn off its companions
        optionList[option] = True       # In radio groups the value should always be True
        for (groupId, opt) in radioGroup - {groupIdOptionPair}:
            optionList.pop(opt, None)

        return self


    class Operator():
        def __init__(self, operator, position):
            self._operator = operator
            self._position = position

    def classify(self, argList, isExplicitCommand=None):     #TODO: Would *argList be better?
        '''
        Determine whether the arguments denote a System Command or a Query Command,
        and whether the command is implicit or explicit.
        If there is a table-name argument, identify it.
        Sort the other arguments into sublists according to their prefixes.

        Option-type arguments are flagged by the "-" prefix.
        Here we construct a command's full option list by appending the
        explicitly-provided options to the options implied by the program settings.
        We also enforce some mutual exclusivity restrictions that apply to certain
        families of options.

        Non-option-type arguments can occur in the case of Query Commands and
        can have various prefixes and special embedded operators. We sort them
        by prefix and catalogue the operators.

        This class & method are about fully classifying the arguments into a
        convenient data structure. We do not attempt to derive
        the arguments' meanings here.

        Before calling this function, unravel all aliases and variables,
        leaving a "flat" command, then split it into a list of words.
        '''

        if not argList:
            return self

        if isExplicitCommand is None:
            leader = ms.settings['Settings']['leader']
            isExplicitCommand = argList[0].startswith(leader)
            argList[0] = argList[0].lstrip(leader)

        self._commandName = argList[0].lower() if isExplicitCommand else None
        argIndex = 1 if isExplicitCommand else 0
        self._isQueryCommand = self._commandName in tqlCommands or not isExplicitCommand

        # Initialize the table name now if it's been set
        self.mainTableName = ms.settings['Settings']['table']

        # Begin the options vector with the fallback options
        self._options = self.initPersistentOptions()

        # The 'sq' command has a special syntax: options followed by literal
        # SQL in that order with nothing else allowed.
        if self._commandName == 'sq':
            inOptions = True   # Accept options at the beginning and only there
            for arg in argList[argIndex:]:
                if inOptions and re.match('-+\w', arg):
                    op, eq, vl = arg.lstrip('-').partition('=')
                    self._addOption(op, vl)
                    argIndex += 1
                else:
                    inOptions = False
                    # Beyond the last option, every argument is to be treated
                    # as literal sql.
                    self._literalSql = " ".join(argList[argIndex:])

        # Other System commands that don't follow the arg-classifier paradigm
        # require no further preprocessing
        elif not self._isQueryCommand:
            return self

        # For TQL query commands we apply the main classifier logic
        else:
            # Walk the argument list, accumulating arguments into lists
            # by their prefix (including options, whose
            # prefix is '-') and take note of operators (+= := etc.)
            for arg in argList[argIndex:]:

                # Separate prefix and word
                m = re.fullmatch(r'(\W*)(\w.*)', arg)
                prefix, word = m.groups()

                # If an option, process and continue
                if re.fullmatch(r'-+', prefix):
                    op, eq, vl = word.partition('=')
                    self._addOption(op, vl)
                    continue

                # Make note of any modification operators inside the arguments.
                # These include += .= etc. Operators like <= and != are not modifiers.
                m = re.search(r'\W+=', word)
                operator = m.group(0) if m else None
                if operator and operator not in ['<=', '>=', '!=', '==']:
                    cellNumber = len(self._argumentTree[prefix]) if self._argumentTree.get(prefix) else 0
                    self._operators.append(self.Operator(operator, cellNumber))

                # For query commands, if the table is not set the first non-prefix argument is table name
                if self._isQueryCommand and not prefix and not self.mainTableName:
                    self.mainTableName = word
                # Otherwise store the argument in the prefix-based classification tree
                else:
                    if not self._argumentTree.get(prefix):
                        self._argumentTree[prefix] = [word]
                    else:
                        self._argumentTree[prefix].append(word)

        # Kluge: For the password, give the option precedence over
        # the config setting. The code that cares about this is in databaseCxn.py
        # where "args" is not readily accessible. So we set the value here.
        if 'p' in self._options:
            defType = ms.settings['ConnectionString']['definitionType']
            ms.settings['ConnectionString'][defType]['MINI_PASSWORD'] = self._options['p'] or fakePass

        return self

