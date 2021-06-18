# Global program data

# MINIQUERY commands and associated data:
# With the exception of the callback associated with each command, all data
# pertaining to MINIQUERY system commands is stored here. This is because
# the callbacks have to be defined before we can reference them.
#
# MINIQUERY commands can be either explicit or implicit. Explicit commands are
# those beginning with the "leader" prefix defined in the program settings. Any
# input line that does NOT begin with the leader is taken to be an implicit
# command.
#
# The implicit commands are a different form of TQL command that allow the
# user to omit <leader>-commandName in front. (System commands have explicit
# forms only.) For instance, the implicit "myTable +favoriteColumn" is
# equivalent to the explicit "\select myTable +favoriteColumn".
#
# Explicit commands, on the other hand, are the sole means of invoking
# MINIQUERY system commands.
#
# Format of the command list: [command name, argument syntax, short description]
# All 3 items are used together in the "help" command.
# The first item is used for command (auto-)completion.
tqlCommands = [
    'select', '', ''
    ]
commandList = [
    ['sq',      '<query>',        'Execute a literal SQL statement'],
    ['quit',    '',               'Exit MINIQUERY'],
    ['help',    '',               'Summary help for MINIQUERY commands'],
    ['history', '<count>',        'Display command history' ],
    ['db',      '<name>',         'Set the active database'],
    ['table',   '<name>',         'Set the active table name'],
    ['clear',   '',               'Clear the default table name'],
#    ['mode']   : doMode,
    ['format',  '',               'Select a format for query output'],
    ['set',     '<name>=<value>', 'Set a MINIQUERY program setting'],
    ['seta',    '<alias>=<cmd>',  'Set up an alias for a command'],
    ['setv',    '<name>=<value>', 'Set a variable'],
    ['get',     '<setting>',      'Inspect a MINIQUERY program setting'],
    ['geta',    '<alias name>',   'Inspect an alias'],
    ['getv',    '<variable>',     'Inspect a variable'],
    ['save',    '',               'Save MINIQUERY settings, aliases and variables'],
    ['source',  '<file>',         'Read and execute commands from a file'],
    ['unset',   '<name>',         'Unset a MINIQUERY setting'],
    ['unseta',  '<name>',         'Unset an alias'],
    ['unsetv',  '<variable>',     'Unset a variable'],
#    ['cp']     : doCompleter,
]

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
                    'Choose whether to show the generated queries, to run them, or to do both:'),
    'editMode' : (['VI', 'EMACS'],
        'Command editing mode',
        'Choose vi- or emacs-style command editing:'),
    }

