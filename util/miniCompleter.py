import sys
import re
from six import string_types
from prompt_toolkit.completion import Completer, Completion

sys.path.append("../src/")

__all__ = [
    'MiniCompleter',
]

class _abbrRecord:
    def __init__(self, text, substitution, start, end):
        self.text = text
        self.substitution = substitution
        self.start = start
        self.end = end

class MiniCompleter(Completer):
    """
    Adapted from WordCompleter, which is simple completion by extension

    :param words: List of words or callable that returns a list of words.
    :param ignore_case: If True, case-insensitive completion.
    :param meta_dict: Optional dict mapping words to their meta-text. (This
        should map strings to strings or formatted text.)
    :param WORD: When True, use WORD characters.
    :param sentence: When True, don't complete by comparing the word before the
        cursor, but by comparing all the text before the cursor. In this case,
        the list of words is just a list of strings, where each string can
        contain spaces. (Can not be used together with the WORD option.)
    :param match_middle: When True, match not only the start, but also in the
                         middle of the word.
    """
    def __init__(self, words, ignore_case=False, meta_dict=None, WORD=False,
                 sentence=False, match_middle=False):
        assert not (WORD and sentence)
        assert callable(words) or all(isinstance(w, string_types) for w in words)

        self.words = words
        self.ignore_case = ignore_case
        self.meta_dict = meta_dict or {}
        self.WORD = WORD
        self.sentence = sentence
        self.match_middle = match_middle

    def build_regexes(self, given_word):
        # Build the regex(es) that we will use to identify all possible
        # substitutions while allowing for non-substitution of the same by
        # applying the straightforward subsequence-matching algorithm as well as any
        # additional regexes to accommodate abbreviations in given_word.

        # Build a list of abbreviations found in the text, and
        # sort the found abbreviations by their starting position
        abbrList=[]
        from includes import miniSettings; ms = miniSettings
        abbrs = ms.settings['Abbreviations']
        for abb in abbrs.items():
            m = re.search(abb[0], given_word)
            if m:
                abbrList.append(_abbrRecord(m.group(0), abb[1], m.start(), m.end()))
        def sortKey(abbrList):
            return abbrList.start
        abbrList = sorted(abbrList, key=sortKey)
        abbrCount = len(abbrList)

        # Group the matching regions so as to shrink their effective number.
        # The rule for the grouping is to avoid overlapping match-regions
        # within any single group. We will create as many groups as necessary
        # to satisfy this condition, but no more.

        abbrIndex = -1; lookAheadIndex = 0
        lowerBoundforAppend = 0; workingList = []
        maximalLists = []; allFeasibleLists = []      # lists of lists
        while True:
            # Look ahead for the next interval that can be added to the group
            lookAheadIndex = abbrIndex + 1
            while lookAheadIndex < abbrCount \
                    and abbrList[lookAheadIndex].start < lowerBoundforAppend:
                lookAheadIndex += 1
            if lookAheadIndex < abbrCount:  # Can add this node and maybe more
                workingList.append(lookAheadIndex)
                # Continue building the working group
                lowerBoundforAppend = abbrList[lookAheadIndex].end
                abbrIndex = lookAheadIndex
            else:   # Cannot add any further nodes; the group is maximal
                ln = len(workingList)-1
                if not workingList in allFeasibleLists:
                    # Record this group as a maximal group
                    maximalLists.append(workingList.copy())
                    # Record all of the group's unrecorded subsets as feasible
                    for i in range(2**(ln+1)):   # walk the power set
                        subset = []
                        for j in range(ln+1):   # construct subset item-by-item
                            if i & 2**j:
                                subset.append(workingList[j])
                        if not subset in allFeasibleLists:
                            allFeasibleLists.append(subset)

                # Advance in the lexical order. Since the current set is
                # maximal, we do not try to append to it. We will try to
                # increase the last digit or else retreat by one cell

                last = workingList.pop(ln)   # capture and remove the trailer
                if last == abbrCount-1 and not workingList:
                    # Termination condition: the highest singleton
                    break
                elif not workingList:
                    # Non-highest singleton. Increase to the next singleton.
                    workingList = [last+1]
                    abbrIndex = last+1
                else:
                    # The usual case: Try to increase the last digit
                    abbrIndex = last

        def getSubsequenceRegex(s):
            '''
            Generate a regex for MINIQUERY-enhanced subsequence matching.
            Essentially, we apply our own magic to the basic transformation
                'abc' --> 'a.*b.*c'

            :param s: The user-provided abbreviation to be expanded
            '''

            if not s:
                return ''

            # Join the characters with the non-greedy "anything" regex.
            # The individual characters are treated in 3 different ways
            # based on letterness and case.
            return ".*?".join([(
                # Capital letters are word-delimiters. (We can relax this
                # assumption later in the match algorithm.)
                # Allow camel case AND snake case.
                    '({}|_{})'.format(x, x.lower())      if x.isupper()
                # Lowercase letters can represent either case
                    else '[{}{}]'.format(x.upper(),x))   if x.isalpha()
                # Non-letters are literal
                    else x
                for x in s])
            return t

        breakpoint()

        # The "maximal lists" represent the combinations of substitutions that
        # we have to check in order to know for certain whether a candidate
        # "works" as an expansion of the abbreviated name, the "given_word"

        # Build the regex corresponding to each maximal list and check it
        # against the given word
        workingList.clear()
        for maximalList in maximalLists:

            # Create a scratch copy of the given_word with parentheses inserted
            workingList = list(given_word)
            for i in maximalList[::-1]:
                workingList.insert(abbrList[i].end, ')')
                workingList.insert(abbrList[i].start, '(')
            workingWord = ''.join(workingList)

            # Break the parenthesized word into a sequence of pairs: non-()
            # followed by () (Avoid empty pairs by putting 'if x' at the end.)
            sequencePairs = [x.split('(') for x in workingWord.split(')') if x]

            # Convert the sequence pairs into actual regexes
            abbrIndex = 0
            for pair in sequencePairs:
                # For the non-parenthesized part we require a subsequence match
                firstPart = '{}.*?'.format(getSubsequenceRegex(pair[0])) if pair[0] else ''
                # For the parenthesized part we allow substitution OR subsequence
                secondPart = '({}|{}).*?'.format(abbrList[maximalList[abbrIndex]].substitution,
                            getSubsequenceRegex(pair[1])) if pair[1] else ''
                if pair[1]:
                    abbrIndex += 1

            # Impose the assumeInitial option (my favorite!) if it's turned on
            #TODO Needs implementation.
            finalRegexes.append()

            # (Finally!) check whether the given word matches the substitution group
            #TODO This probably belongs in the caller, not here.
            if re.search()




    def word_matches(self, word, given_word):
        """ True when the word before the cursor matches. """
        if self.ignore_case:
            word = word.lower()

#TODO implement the new stuff here.


#        if self.match_middle:
#            return given_word in word
#        else:
#            # This is the word completer in a nutshell
#            return word.startswith(given_word)


    def get_completions(self, document, complete_event):
        # Get list of words.
        words = self.words
        if callable(words):
            words = words()

        # Get word/text before cursor.
        if self.sentence:
            word_before_cursor = document.text_before_cursor
        else:
            word_before_cursor = document.get_word_before_cursor(WORD=self.WORD)

        if self.ignore_case:
            word_before_cursor = word_before_cursor.lower()

        self.build_regexes(word_before_cursor)

        for a in words:
            if self.word_matches(a, word_before_cursor):
                display_meta = self.meta_dict.get(a, '')
                yield Completion(a, -len(word_before_cursor), display_meta=display_meta)

