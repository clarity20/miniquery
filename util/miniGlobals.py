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

# Format of the command list: [command name, argument syntax, short description, 'do'+callbackName if different from 'do'+Cmd]
# This is used for help, autocompletion, and dispatch to callbacks
commandList = [
    ['sq',      '<query>',        'Execute a literal SQL statement',    'Sql'],
    ['quit',    '',               'Exit MINIQUERY'],
    ['help',    '',               'Summary help for MINIQUERY commands'],
    ['history', '<count>',        'Display command history'],
    ['db',      '<name>',         'Set the active database',            'SetDatabase'],
    ['table',   '<name>',         'Set the active table name',          'SetTable'],
    ['clear',   '',               'Clear the active table name',        'ClearTable'],
    ['format',  '',               'Select a format for query output'],
    ['set',     '<name>=<value>', 'Set a MINIQUERY program setting'],
    ['seta',    '<alias>=<cmd>',  'Set up an alias for a command',      'Alias'],
    ['setabb',  '<abbr>=<full>',  'Set up an abbreviation for db object naming', 'Abbreviate'],
    ['setv',    '<name>=<value>', 'Set a variable',                     'SetVariable'],
    ['get',     '<setting>',      'Inspect a MINIQUERY program setting'],
    ['geta',    '<alias name>',   'Inspect an alias',                   'GetAlias'],
    ['getabb',  '<abbreviation>', 'Inspect an abbreviation',            'GetAbbreviation'],
    ['getv',    '<variable>',     'Inspect a variable',                 'GetVariable'],
    ['save',    '<file>',         'Save MINIQUERY settings, aliases and variables'],
    ['source',  '<file>',         'Read and execute commands from a file'],
    ['unset',   '<name>',         'Unset a MINIQUERY setting'],
    ['unseta',  '<name>',         'Unset an alias',                     'Unalias'],
    ['unsetabb','<abbreviation>', 'Unset an abbreviation',              'Unabbreviate'],
    ['unsetv',  '<variable>',     'Unset a variable'                    'UnsetVariable'],
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

