import sys

class SpellingExpander:

    # This class is home to the generic spelling expander routines such as
    # (the recursive) expandFully() and (the all-purpose) expandAbbrev'dName()

    # The class provides the generic spelling-based expansion functionality
    # which the specialized classes must invoke after setting up to meet their
    # specific needs
    def expandAbbreviatedName(self):
        return 0
    def expandFully(self):
        return 0

