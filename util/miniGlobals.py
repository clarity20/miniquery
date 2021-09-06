# Global program data

# MINIQUERY command summaries:
# All data pertaining to MINIQUERY system commands is stored here except for
# the callbacks associated with the commands.
#
# MINIQUERY commands consist of System commands and TQL/Query commands. (TQL is
# the Terse Query Language that powers MINIQUERY.) Every command can be written
# explicitly, and certain Query commands can also be written implicitly.
# Explicit commands are those preceded by the "leader" as defined in
# the program settings, followed by the command name; any command that does NOT
# begin with <leader>-commandName is an implicit command. When an implicit
# command is properly written, the corresponding explicit command can be
# inferred from the syntax. For instance, the implicit "myTable +favoriteColumn"
# is equivalent to the explicit "\select myTable +favoriteColumn".

# Basic (i.e. DML) TQL commands: command names, generic argument summaries, description template
tqlCommands = ['select', 'update', 'insert', 'delete']
tqlArgumentSummaries = '<options / query particles>'
tqlDescriptions = 'Transpile/run a TQL %s statement'

# Extended TQL commands and arguments for the above description template #TODO: enable these later
extendedTqlCommands= [
#    ['crtable', 'create table'],
#    ['altable', 'alter table'],
#    ['dtable', 'drop table'],
#    ['crdb', 'create database'],
#    ['ddb', 'drop database'],
]

# Format of the command list: [command name, argument syntax, short description]
# All 3 items are used together in the "help" command.
# The first item is used for command (auto-)completion.
commandList = [
    ['sq',      '<query>',        'Execute a literal SQL statement'],
    ['quit',    '',               'Exit MINIQUERY'],
    ['help',    '',               'Summary help for MINIQUERY commands'],
    ['history', '<count>',        'Display command history' ],
    ['db',      '<name>',         'Set the active database'],
    ['table',   '<name>',         'Set the active table name'],
    ['clear',   '',               'Clear the active table name'],
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

