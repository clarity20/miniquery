import re
import sys

from six import string_types
from prompt_toolkit.completion import Completer, PathCompleter, Completion, CompleteEvent
from prompt_toolkit.document import Document

sys.path.append("../src/")
from configManager import masterDataConfig; cfg = masterDataConfig

__all__ = [
    'CommandCompleter',
]


class CommandCompleter(Completer):
    """
    Context-sensitive subsequence completion of a word against a list of words:

    - Line-leading words prefixed with the 'leader' are assumed to be MINIQUERY
    system commands and are completed against a list of all MINIQUERY commands.
    - Line-leading words NOT prefixed with the 'leader' are assumed to be
    MINIQUERY queries, and completion is not attempted.
    - Words following commands are assumed to be first arguments and are
    expanded against a list of words proper to that command.

    (Distantly) adapted from the prompt-toolkit's WordCompleter. Not all of the
    parameters below are meaningful.

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
        from appSettings import miniSettings; ms = miniSettings
        if document.text_before_cursor.startswith(ms.settings['leader']):
            text = document.text_before_cursor.lstrip(ms.settings['leader'])
        else:
            # Non-commands (i.e. queries) are not handled by this Completer
            return

        # Get word before cursor. Determine whether it's a command name
        # or a command argument
        from miniGlobals import commandList, settingOptionsMap
        if ' ' in text:
            # The word is an argument. The candidate list depends on the command
            #word_before_cursor = document.get_word_before_cursor(WORD=self.WORD)
            cmd, x, word_before_cursor = text.partition(' ')
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
                    defType = ms.connection['definitionType']
                    words = list(ms.settings) + ['definitionType'] \
                            + list(ms.connection[defType])
                    if cmd == 'get':
                        words.append('*')
                elif cmd in ['source', 'save']:
                    completions = list(PathCompleter().get_completions(
                                Document(word_before_cursor, len(word_before_cursor)), CompleteEvent()))
                    words = [c.display[0][1] for c in completions]
                elif cmd == 'db':
                    words = [db for db in cfg.databases.keys()]
                elif cmd == 'table':
                    db = ms.settings['database']
                    words = [t for t in cfg.databases[db].tableNames]
                else:
                    words = settingOptionsMap[cmd][0]
            except KeyError:
                words = []
        else:
            # The word is a command. Candidates are the commands and aliases.
            word_before_cursor = text
            words = [c[0] for c in commandList] + list(ms.aliases)
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
