import re
from prompt_toolkit.styles import Style

from appSettings import miniSettings; ms = miniSettings

# Function to create a massively customizable prompt from a string.
# '${u:yBI}' in the string would mean the user name in yellow bold italic
# whereas '${u}' by itself would default to the user name in plain white.
def stringToPrompt(s):

    # stylePrefix holds the unchangeable aspects of the prompt style
    # The order of the fields does not matter.
    stylePrefix = {
        # User input echo styling:
        ''        : 'white bold',
        # Fixed prompt styling:
        'sep'     : 'white',
        'symbol'  : 'blue' if ms.ostype == 'Windows' else 'yellowgreen bold',
        # Styling for the "MINI" program name:
        'program' : 'blue' if ms.ostype == 'Windows' else 'yellow bold',
    }

    # promptPrefix holds the unchangeable "MINI" prefix for the prompt.
    # Prompt components are order-sensitive.
    promptPrefix = [
        ('class:sep'   , '----<['),
        ('class:program', '.MINI.'),
        ('class:sep'   , ']>----'),
        ]

    # Data definitions for converting the input string to a prompt. We want some
    # of these to be re-evaluated every time in case the prompt should change.
    attribs = {
        'p' : ('prompt', ms.settings['promptSymbol']),
        # See comments in mini.cfg: user must set MINI_USER and MINI_HOST for this to work.
        'u' : ('user', ms.connection['Components']['MINI_USER']
            or '<unknown>'),
        'h' : ('host', ms.connection['Components']['MINI_HOST']
            or '<unknown>'),
        'd' : ('db', ms.settings['database'] or '<none>'),
        't' : ('table', ms.settings['table'] or '<none>'),
        }
    colors = {
        'w' : 'white',  'b' : 'blue',   'p' : 'pink',
        'g' : 'green',  'n' : 'brown',  'r' : 'red',
        'y' : 'yellow', 'o' : 'orange', 'k' : 'black',
        'a' : 'gray',
        }
    features = {
        'B' : 'bold', 'U' : 'underline', 'I' : 'italic',
        }

    isAttribute = False

    # Begin prompt and style with the hard-wired prefixes
    prompt1 = promptPrefix.copy()
    styleDict = stylePrefix.copy()

    # Split 's' into pieces that alternate between brace-protected variable names
    # and literal text. 'split()' inserts blanks to make edge cases easier.
    for word in re.split(r'\${(.|.:.[A-Z]*)}', s):
        if isAttribute:

            # Check that the string syntax is "roughly" correct:
            if re.search('\${', word):
                return em.setError(ReturnCode.PROMPT_ERROR, 'value syntax', word)

            # Get the attribute
            try:
                attr, value = attribs[word[0]]
            except KeyError:
                return em.setError(ReturnCode.PROMPT_ERROR, 'attribute name', word[0])

            if ':' in word:
                # Get the color
                try:
                    styleDesc = colors[word[2]]
                except KeyError:
                    return em.setError(ReturnCode.PROMPT_ERROR, 'color', word[2])

                # Get the feature(s)
                for w in word[3:]:
                    try:
                        styleDesc = '{} {}'.format(styleDesc, features[w])
                    except KeyError:
                        return em.setError(ReturnCode.PROMPT_ERROR, 'feature', w)

            else:
                # Default to plain white style
                styleDesc='white'

            # Update the "raw" style definition and the prompt
            styleDict[attr] = styleDesc
            prompt1.append(('class:'+attr, value))

        # The fragment is nonempty and is literal text.
        elif word:  # Do not bother adding an entry for an empty piece
            prompt1.append(('class:sep', word))

        # Finally:
        isAttribute = not isAttribute

    # Finally, add the prompt "arrow"
    prompt1.append(('class:symbol', attribs['p'][1]))

    return prompt1, styleDict

