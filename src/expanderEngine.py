from tableNameExpander import TableNameExpander
from columnNameExpander import ColumnNameExpander
from functionNameExpander import FunctionNameExpander
from grammarExpander import GrammarExpander

class ExpanderEngine:

    # Include specialized expanders of each kind
    tableExpander = TableNameExpander()
    columnExpander = ColumnNameExpander()
    functionExpander = FunctionNameExpander()

    grammarExpander = GrammarExpander()

    # The big enchilada of name expansion, incorporating the helpers below
    def performFullExpansion(self):
        return 0

    # Convenient utility
    def promptForExpansion(self):
        return 0

    # To be called for every expandable word
    def doSpellingExpansion(self):
        return 0

    # To be called once, with all candidate lists
    def doGrammarExpansion(self):
        return 0

miniExpanderEngine = ExpanderEngine()
