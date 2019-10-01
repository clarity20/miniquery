import re
import sys

from six import string_types
from prompt_toolkit.completion import Completer, Completion

sys.path.append("../src/")

__all__ = [
    'CommandCompleter',
]


class CommandCompleter(Completer):
    """
    Subsequence autocompletion on a list of words.

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

    def get_completions(self, document, complete_event):
        # Get list of candidate words.
        words = self.words
        if callable(words):
            words = words()

        # Strip off the MINIQUERY system command leader, leaving the command
        from includes import miniSettings; ms = miniSettings
        if document.text_before_cursor.startswith(ms.settings['Settings']['leader']):
            text = document.text_before_cursor.lstrip(ms.settings['Settings']['leader'])
        else:
            # Non-commands (i.e. queries) are not handled by this Completer
            return

        # Get word before cursor. Determine whether it's a command name
        # or a command argument
        from miniGlobals import commandList, settingOptionsMap
        if ' ' in text:
            # The word is an argument. The candidate list depends on the command
            word_before_cursor = document.get_word_before_cursor(WORD=self.WORD)
            cmd, x, y = text.partition(' ')
            try:
                if cmd in ['geta', 'unseta']:          # user chooses an alias
                    words = list(ms.settings['Aliases'])
                    if cmd == 'geta':
                        words.append('*')
                elif cmd in ['getv', 'unsetv']:        # user chooses a variable
                    words = list(ms.settings['Variables'])
                    if cmd == 'getv':
                        words.append('*')
                elif cmd in ['set', 'get', 'unset']:   # user chooses a setting
                    defType = ms.settings['ConnectionString']['definitionType']
                    words = list(ms.settings['Settings']) + ['definitionType'] \
                            + list(ms.settings['ConnectionString'][defType])
                    if cmd == 'get':
                        words.append('*')
                #TODO Still need to set the list for \db and \table commands
                #TODO elif cmd in ['db', 'table']:
                #TODO     etc.
                else:
                    words = settingOptionsMap[cmd][0]
            except KeyError:
                words = []
        else:
            # The word is a command. Candidates are the commands and aliases.
            word_before_cursor = text
            words = [c[0] for c in commandList] + list(ms.settings['Aliases'])
        if self.ignore_case:
            word_before_cursor = word_before_cursor.lower()

        def word_matches(word):
            """ True when the word before the cursor matches. """
            if self.ignore_case:
                word = word.lower()

            if self.match_middle:
                return word_before_cursor in word
            else:
                # The core of this completer. See also miniCompleter's
                # getSubsequenceRegex()
                regex = '^{}'.format('.*?'.join(word_before_cursor))
                return re.search(regex, word) is not None

        for a in words:
            if word_matches(a):
                display_meta = self.meta_dict.get(a, '')
                yield Completion(a, -len(word_before_cursor), display_meta=display_meta)