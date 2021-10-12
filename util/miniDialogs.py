#Problematic to cython/py3.8:
#from __future__ import unicode_literals

"""
Collection of reusable components for building full screen applications.
"""
from prompt_toolkit.filters import has_completions, has_focus, Condition, is_true
from prompt_toolkit.formatted_text import is_formatted_text
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.key_binding.key_bindings import KeyBindings, merge_key_bindings
from prompt_toolkit.layout.containers import VSplit, HSplit, DynamicContainer, Window, WindowAlign
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.keys import Keys

import os
import functools
from bisect import bisect_left
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.completion import DynamicCompleter, PathCompleter, CompleteEvent
from prompt_toolkit.auto_suggest import DynamicAutoSuggest
from prompt_toolkit.layout.margins import ScrollbarMargin, NumberedMargin
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.widgets import ProgressBar, Label, Box, TextArea, RadioList, Shadow, Frame, SearchToolbar

import pathlib
import six
import re
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEventType

__all__ = [
    'MiniListBox',
    'MiniButton',
    'MiniDialog',
    'MiniFileDialog',
    'yes_no_dialog',
    'button_dialog',
    'input_dialog',
    'message_dialog',
    'radiolist_dialog',
    'progress_dialog',
]

LBOX_GENERAL=0
LBOX_FILES=1
LBOX_PATH=2

BTNORDER_FIRST=0
BTNORDER_MIDDLE=1
BTNORDER_LAST=2

# Define a space character that's appended to a line of editable text in the GUI.
# This will allow appending of characters to work the same way as inserting them.
EOL_PADCHAR=' '

class MiniListBox(object):
    """
    Based on prompt-toolkit's TextArea, this class uses a FormattedTextControl
    instead of a BufferControl to enable a specific kind of formatting/
    stylization of the text to implement "highlighting" of the user selection
    as in normal list boxes.

    This implementation borrows class Button`s idea of "trading" in flat
    text while internally stylizing it before passing it to the control.

    This is a higher level abstraction on top of several other classes with
    sane defaults.

    Buffer attributes:

    :param itemList: The choices as a list of strings.
    :param multiline: If True, allow multiline input.
    :param companionBox: If set, indicates this is an "Open file" list box and
         points to the "other" widget: either the files box or the path box
    :param read_only: Can the user edit the text of the list box control?
    :param completer: :class:`~prompt_toolkit.completion.Completer` instance
        for auto completion.
    :param complete_while_typing: Boolean.
    :param accept_handler: Called when `Enter` is pressed (This should be a
        callable that takes a buffer as input).
    :param history: :class:`~prompt_toolkit.history.History` instance.
    :param auto_suggest: :class:`~prompt_toolkit.auto_suggest.AutoSuggest`
        instance for input suggestions.

    FormattedTextControl attributes:

    :param focusable: When `True`, allow this widget to receive the focus.

    Window attributes:

    :param lexer: :class:`~prompt_toolkit.lexers.Lexer` instance for syntax
        highlighting.
    :param wrap_lines: When `True`, don't scroll horizontally, but wrap lines.
    :param width: Window width. (:class:`~prompt_toolkit.layout.Dimension` object.)
    :param height: Window height. (:class:`~prompt_toolkit.layout.Dimension` object.)
    :param scrollbar: When `True`, display a scroll bar.
    :param style: A style string.
    :param dont_extend_width: When `True`, don't take up more width then the
                              preferred width reported by the control.
    :param dont_extend_height: When `True`, don't take up more width then the
                               preferred height reported by the control.
    :param get_line_prefix: None or a callable that returns formatted text to
        be inserted before a line. It takes a line number (int) and a
        wrap_count and returns formatted text. This can be used for
        implementation of line continuations, things like Vim "breakindent" and
        so on.

    Other attributes:

    :param search_field: An optional `SearchToolbar` object.
    """
    def __init__(self, itemList=None, multiline=True, password=False,
                 lexer=None, auto_suggest=None, completer=None, type=LBOX_GENERAL,
                 complete_while_typing=True, accept_handler=None, history=None,
                 focusable=True, wrap_lines=True, companionBox=None,
                 read_only=False, width=None, height=None, selected_item=0,
                 dont_extend_height=False, dont_extend_width=False, sortKeys = [],
                 line_numbers=False, get_line_prefix=None, scrollbar=False,
                 style='', search_field=None, preview_search=True, prompt=''):
        assert isinstance(itemList, list)
        assert search_field is None or isinstance(search_field, SearchToolbar)

        if search_field is None:
            search_control = None
        elif isinstance(search_field, SearchToolbar):
            search_control = search_field.control

        # Writeable attributes.
        self.completer = completer
        self.complete_while_typing = complete_while_typing
        self.lexer = lexer
        self.auto_suggest = auto_suggest
        self.read_only = read_only
        self.wrap_lines = wrap_lines
        self.itemList = itemList
        self.sortKeys = sortKeys
        self.type = type

        text = '{}{}'.format(itemList[0], EOL_PADCHAR) if type == LBOX_PATH else '\n'.join(itemList)
        self.buffer = Buffer(
            document=Document(text, 0),
            multiline=multiline,
            read_only=Condition(lambda: is_true(self.read_only)),
            completer=DynamicCompleter(lambda: self.completer),
            complete_while_typing=Condition(
                lambda: is_true(self.complete_while_typing)),
            auto_suggest=DynamicAutoSuggest(lambda: self.auto_suggest),
            accept_handler=accept_handler,
            history=history)

        self.control = FormattedTextControl(
                self._get_text_fragments,
                key_bindings=self._get_key_bindings(),
                focusable=True)

        if multiline:
            if scrollbar:
                right_margins = [ScrollbarMargin(display_arrows=True)]
            else:
                right_margins = []
            if line_numbers:
                left_margins = [NumberedMargin()]
            else:
                left_margins = []
        else:
            height = D.exact(1)
            left_margins = []
            right_margins = []

        style = 'class:text-area ' + style

        self.window = Window(
            height=height,
            width=width,
            dont_extend_height=dont_extend_height,
            dont_extend_width=dont_extend_width,
            content=self.control,
            style=style,
            wrap_lines=Condition(lambda: is_true(self.wrap_lines)),
            left_margins=left_margins,
            right_margins=right_margins,
            get_line_prefix=get_line_prefix)

        self.pathExists = True
        if self.type == LBOX_PATH:
            self.previousPath = self.itemList[0]
        self.companionBox = companionBox
        self.itemCount = len(self.itemList)
        self.cursor_position = 0
        self.selectedItem = -1 if self.type == LBOX_PATH else selected_item

        kb = KeyBindings()

        @kb.add('enter')
        def _(event):
            # For a general-purpose list box, advance the focus to "OK";
            # a click there will finalize the selection.
            if self.type == LBOX_GENERAL:
                get_app().layout.focus(self.ok_button)
                return True

            # For a path box, accept the input. If a directory, update
            # the file box and focus on it. Else focus on "OK".
            elif self.type == LBOX_PATH:
                fileBox = self.companionBox

                # Accept the edit and resolve it
                fullpath = pathlib.Path(self.itemList[0]).resolve()
                self.populatePathBox(str(fullpath))

                # Three possible scenarios: user has entered a directory name,
                # an existing filename, or a new name

                if fullpath.is_dir():
                    # Sync the file box to the directory name just accepted
                    self.syncFileBoxToDirectory(fileBox, fullpath)
                    # Jump to the file box, and the path-dance continues
                    get_app().layout.focus(fileBox)
                    self.previousPath = self.itemList[0]
                    return True

                elif fullpath.is_file():
                    # Sync the file box to the filename's directory
                    self.syncFileBoxToDirectory(fileBox, fullpath)
                    # Accept the filename provisionally: Jump to OK
                    get_app().layout.focus(self.ok_button)
                    self.previousPath = self.itemList[0]
                    return True

                elif not fullpath.exists():
                    # For a read-only path box, do not allow creation of new files
                    if self.read_only:
                        # Revert to a known good path
                        #TODO: A visible warning msg would be good here
                        self.populatePathBox(self.previousPath)
                        return True

                    else:
                        #TODO: Recognize & accept a new directory name if there's a trailing slash

                        # Allow the user to create new files. Jump to "OK" to make
                        # this as easy as possible.
                        get_app().layout.focus(self.ok_button)

                        # New filenames can gum up the works if the user opts
                        # not to click either "OK" or "Cancel", so we set up
                        # a mechanism to roll back to a known path if that happens.
                        self.pathExists = False

                        return True

            # For a file-list box, synchronize with the path box
            elif self.type == LBOX_FILES:
                pathBox = self.companionBox

                # Fetch the base file name and the directory
                filename = self.itemList[self.selectedItem]
                path = pathlib.Path(pathBox.itemList[0])

                # Address a corner case where the path box contents are stale:
                # If the path box has a file name (not a directory), it
                # reflects the user's choice the previous time he was in
                # the file box. Retreat up to directory level
                # before appending the new filename.
                if path.is_file():
                    path = path.parent

                # The following situation should never come up. When the user
                # presses 'enter' with a nonexistent path, the focus jumps
                # to the OK button, not the fileBox. (What if he tabs to the filebox?)
                #elif not path.exists():
                #    path = pathBox.previousPath.parent
                #    filename = pathBox.previousPath.name

                # Append the filename to the directory
                fullpath = (path / filename).resolve()

                # Refresh the path box
                pathBox.populatePathBox(str(fullpath))

                # If the user chose a directory, list its contents
                if fullpath.is_dir():
                    self.syncFileBoxToDirectory(self, fullpath)
                    pathBox.previousPath = pathBox.itemList[0]
                    # Stay focused on the file box: do nothing further

                # If the user chose a file, accept the choice
                elif fullpath.is_file():
                    get_app().layout.focus(self.ok_button)
                    pathBox.previousPath = pathBox.itemList[0]

                # Note that a selection from the file box cannot be non-existing

            return True  # Keep text.

        @kb.add('escape')
        def _(event):
            if self.ok_button:
                # Advance the focus to Cancel via OK
                get_app().layout.focus(self.ok_button)
                get_app().layout.focus_next()
            return False  # Keep text.

        @kb.add(Keys.Any)
        def _(event):

            keyPressed = event.key_sequence[0].key

            # For path boxes, implement standard editing and navigation keys
            if self.type == LBOX_PATH:
                curpos = self.cursor_position
                item = self.itemList[0]

                if len(keyPressed) == 1:     # roughly the same as keyPressed.isprintable()
                    self.populatePathBox('{}{}{}'.format(item[:curpos], keyPressed, item[curpos:]))
                    if curpos <= len(item):
                        self.cursor_position += 1
                # Small optimization: separate search tree for control characters
                elif keyPressed.startswith('c-'):
                    if keyPressed == 'c-left':
                        try:
                            self.cursor_position = item.rindex(os.sep, 0, curpos)
                        except ValueError:
                            self.cursor_position = 0
                    elif keyPressed == 'c-right':
                        length = len(item)
                        try:
                            self.cursor_position = item.index(os.sep, curpos+1, length)
                        except ValueError:
                            self.cursor_position = length
                    elif keyPressed == 'c-delete':
                        # Chop from here to the end
                        self.populatePathBox(item[:curpos])
                        self.cursor_position -= 1
                    # System sends us 'c-h' instead of 'backspace'
                    elif keyPressed == 'c-h' and curpos > 0:
                        self.populatePathBox('{}{}'.format(item[:curpos-1], item[curpos:]))
                        self.cursor_position -= 1
                    # No obvious way to handle 'c-backspace', at least on Android
                    # elif keyPressed == 'c-backspace':
                    #     # Chop everything on the left
                    #     self.itemList = [item[curpos:]]
                    #     self.text = '\n'.join(self.itemList)
                    #     self.cursor_position = 0
                elif keyPressed == 'left' and curpos > 0:
                    self.cursor_position -= 1
                elif keyPressed == 'right' and curpos < len(item):
                    self.cursor_position += 1
                elif keyPressed == 'delete':
                    self.populatePathBox('{}{}'.format(item[:curpos], item[curpos+1:]))
                    # do not change cursor position
                elif keyPressed == 'home':
                    self.cursor_position = 0
                elif keyPressed == 'end':
                    self.cursor_position = len(item)
                return

            # For a list box, enable letters/numbers as shortcuts for selection
            elif self.type in [LBOX_FILES, LBOX_GENERAL] and len(keyPressed) == 1:
                item = self.selectedItem
                keyPressed = keyPressed.lower()
                if item < self.itemCount - 1 \
                   and self.itemList[item+1][0].lower() == keyPressed:
                    self.selectedItem += 1
                else:
                    self.selectedItem = min(self.itemCount-1,
                            bisect_left(self.sortKeys, keyPressed))

        @kb.add('down')
        def _(event):
            if self.type == LBOX_PATH:
                return
            if self.selectedItem == self.itemCount-1:
                return
            else:
                self.selectedItem = (self.selectedItem + 1) % self.itemCount

        @kb.add('up')
        def _(event):
            if self.type == LBOX_PATH:
                return
            if self.selectedItem == 0:
                return
            else:
                self.selectedItem = (self.selectedItem - 1) % self.itemCount

        @kb.add('pagedown')
        def _(event):
            if self.type == LBOX_PATH:
                return
            jumpSize = min(self.window.height-1, self.itemCount-1-self.selectedItem)
            self.selectedItem = (self.selectedItem + jumpSize) % self.itemCount

        @kb.add('pageup')
        def _(event):
            if self.type == LBOX_PATH:
                return
            jumpSize = min(self.window.height-1, self.selectedItem)
            self.selectedItem = (self.selectedItem - jumpSize) % self.itemCount

        @kb.add('home')
        def _(event):
            if self.type == LBOX_PATH:
                self.cursor_position = 0
                return
            self.selectedItem = 0

        @kb.add('end')
        def _(event):
            if self.type == LBOX_PATH:
                self.cursor_position = len(self.itemList[0]) - 1
                return
            self.selectedItem = self.itemCount-1

        self.control.key_bindings = kb

    @staticmethod
    def syncFileBoxToDirectory(fileBox, fullpath):
        directory = fullpath.parent if fullpath.is_file() else fullpath
        filenames = ['..' + os.sep] \
                + ['{}{}'.format(f.name, os.sep) if f.is_dir() else f.name for f in directory.iterdir()]
        filenames.sort(key = lambda x: x.lower())
        fileBox.itemList = filenames
        fileBox.sortKeys = [x.lower() for x in filenames]
        fileBox.itemCount = len(filenames)
        fileBox.selectedItem = bisect_left(fileBox.sortKeys, fullpath.name.lower()) if fullpath.is_file() else 0
        fileBox.text = '\n'.join(filenames)

    def populatePathBox(self, text):
        assert self.type == LBOX_PATH
        self.itemList = [text]
        self.text = '{}{}'.format(text, EOL_PADCHAR)

    def _get_text_fragments(self):
        def mouse_handler(mouse_event):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                if self.type == LBOX_PATH:
                    self.cursor_position = mouse_event.position.x
                else:
                    self.selectedItem = mouse_event.position.y

        item = self.selectedItem
        items = self.itemList
        text = self.text

        highlightScheme = 'fg:white bg:blue' if get_app().layout. \
            has_focus(self.control) else 'fg:white bg:gray'

        if self.type == LBOX_PATH:
            # return the entire text in the single, correct color scheme
            idx = self.cursor_position
            return [
                (highlightScheme, text[:idx], mouse_handler),
                ('[SetCursorPosition]', ''),
                (highlightScheme, text[idx:], mouse_handler),
               ]

        if item == self.itemCount-1:  # last item
            idx = text.rindex(items[item])
            return [
                ('', text[:idx], mouse_handler),
                ('[SetCursorPosition]', ''),
                (highlightScheme, text[idx:], mouse_handler),
               ]
        elif item > 0:
            searchString = '\n{}\n'.format(items[item])
            startIdx = text.index(searchString) + 1  # skip leading NL
            endIdx = text.find('\n', startIdx) + 1  # enclose next NL
            return [
                ('', text[:startIdx], mouse_handler),
                ('[SetCursorPosition]', ''),
                (highlightScheme, text[startIdx:endIdx], mouse_handler),
                ('', text[endIdx:], mouse_handler),
               ]
        else:    # item == 0
            endIdx = text.find('\n') + 1
            return [
                ('[SetCursorPosition]', ''),
                (highlightScheme, text[:endIdx], mouse_handler),
                ('', text[endIdx:], mouse_handler),
               ]

    def _get_key_bindings(self):
        kb = KeyBindings()

        @kb.add(' ')
        @kb.add('enter')
        def _(event):
            if self.handler is not None:
                self.handler()

        return kb

    @property
    def text(self):
        """
        The `Buffer` text.
        """
        return self.buffer.text

    @text.setter
    def text(self, value):
        self.buffer.set_document(Document(value, 0), bypass_readonly=True)

    @property
    def document(self):
        """
        The `Buffer` document (text + cursor position).
        """
        return self.buffer.document

    @document.setter
    def document(self, value):
        self.buffer.document = value

    @property
    def accept_handler(self):
        """
        The accept handler. Called when the user accepts the input.
        """
        return self.buffer.accept_handler

    @accept_handler.setter
    def accept_handler(self, value):
        self.buffer.accept_handler = value

    def __pt_container__(self):
        return self.window


class MiniButton(object):
    """
    Clickable button.

    :param text: The caption for the button.
    :param handler: `None` or callable. Called when the button is clicked.
    :param width: Width of the button.
    :param addHotkey: Create a hotkey for this button, using the prefix '&'
        or defaulting to the first character.
    """
    def __init__(self, text, handler=None, width=12, addHotkey=True, order=BTNORDER_MIDDLE, neighborBox=None):
        assert isinstance(text, six.text_type)
        assert handler is None or callable(handler)
        assert isinstance(width, int)

        if addHotkey:
            # Locate the hotkey in the text
            hotkeyFlag = '&'
            try:
                self.hotkeyIndex = text.index(hotkeyFlag)
            except ValueError:
                text = '{}{}'.format(hotkeyFlag, text)
                self.hotkeyIndex = 0
        else:
            self.hotkeyIndex = -1

        self.text = text.replace(hotkeyFlag, '')
        self.handler = handler
        self.width = width
        self.control = FormattedTextControl(
            self._get_text_fragments,
            key_bindings=self._get_key_bindings(),
            focusable=True)
        self.order = order
        self.neighborBox = neighborBox

        def get_style():
            if get_app().layout.has_focus(self):
                return 'class:button.focused'
            else:
                return 'class:button'

        self.window = Window(
            self.control,
            align=WindowAlign.CENTER,
            height=1,
            width=width,
            style=get_style,
            dont_extend_width=True,
            dont_extend_height=True)

    def _get_text_fragments(self):
        textlen = len(self.text)
        offset = (self.width - 2 - textlen) // 2
        text = ('{:^%s}' % (self.width - 2)).format(self.text)

        def handler(mouse_event):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.handler()

        if self.hotkeyIndex >= 0:
            # Button gets a hotkey by default
            return [
                ('class:button.arrow', '<', handler),
                ('[SetCursorPosition]', ''),
                ('class:button.text',text[: self.hotkeyIndex + offset], handler),
                ('underline', text[self.hotkeyIndex + offset], handler),
                ('class:button.text', text[self.hotkeyIndex + offset + 1 :], handler),
                ('class:button.arrow', '>', handler),
                    ]
        else:
            # User declined a hotkey
            return [
                ('class:button.arrow', '<', handler),
                ('[SetCursorPosition]', ''),
                ('class:button.text',text[: self.hotkeyIndex + offset], handler),
                ('class:button.arrow', '>', handler),
                    ]

    def _get_key_bindings(self):
        " Key bindings for the MiniButton. "
        kb = KeyBindings()

        @kb.add(' ')
        @kb.add('enter')
        def _(event):
            if self.handler is not None:
                self.handler()

        # ESC should trigger the cancel-button behavior no matter which button has the focus
        @kb.add('escape')
        def _(event):
            _return_none()

        @kb.add('tab')
        def _(event):
            get_app().layout.focus_next()
            if self.order == BTNORDER_LAST:
                # We are tabbing past the last button ("Cancel") of a MiniFileDialog.
                # Reset the path and file boxes
                pathBox = self.neighborBox
                if not pathBox.pathExists:
                    pathBox.pathExists = True
                    pathBox.itemList = [pathBox.previousPath]
                    pathBox.text = '\n'.join(pathBox.itemList)
                    pathBox.syncFileBoxToDirectory(pathBox.companionBox, pathlib.Path(pathBox.itemList[0]))

        @kb.add('s-tab')
        def _(event):
            get_app().layout.focus_previous()
            if self.order == BTNORDER_FIRST:
                # See the 'tab' handler above. We are shift-tabbing behind the "OK" button.
                pathBox = self.neighborBox.companionBox
                if not pathBox.pathExists:
                    pathBox.pathExists = True
                    pathBox.itemList = [pathBox.previousPath]
                    pathBox.text = '\n'.join(pathBox.itemList)
                    pathBox.syncFileBoxToDirectory(pathBox.companionBox, pathlib.Path(pathBox.itemList[0]))

        return kb

    def __pt_container__(self):
        return self.window


class MiniDialog(object):
    """
    Simple dialog window. This is the base for input dialogs, message dialogs
    and confirmation dialogs.

    Changing the title and body of the dialog is possible at runtime by
    assigning to the `body` and `title` attributes of this class.

    :param body: Child container object.
    :param title: Text to be displayed in the heading of the dialog.
    :param buttons: A list of `MiniButton` widgets, displayed at the bottom.
    """
    def __init__(self, body, title='', buttons=None, modal=True, width=None,
                 with_background=False):
        assert is_formatted_text(title)
        assert buttons is None or isinstance(buttons, list)

        self.body = body
        self.title = title

        buttons = buttons or []

        # When a button is selected, handle left/right key bindings.
        buttons_kb = KeyBindings()
        if len(buttons) > 1:
            first_selected = has_focus(buttons[0])
            last_selected = has_focus(buttons[-1])

            buttons_kb.add('left', filter=~first_selected)(focus_previous)
            buttons_kb.add('right', filter=~last_selected)(focus_next)

        # Create a hotkey for every button if so indicated
        for btn in buttons:
            if btn.hotkeyIndex >= 0:
                key = btn.text[btn.hotkeyIndex]
                buttons_kb.add(key.upper())(btn.handler)
                buttons_kb.add(key.lower())(btn.handler)

        if buttons:
            frame_body = HSplit([
                # Add optional padding around the body.
                Box(body=DynamicContainer(lambda: self.body),
                    padding=D(preferred=1, max=1),
                    padding_bottom=0),
                # The buttons.
                Box(body=VSplit(buttons, padding=1, key_bindings=buttons_kb),
                    height=D(min=1, max=3, preferred=3))
            ])
        else:
            frame_body = body

        # Key bindings for whole dialog.
        kb = KeyBindings()
        kb.add('tab', filter=~has_completions)(focus_next)
        kb.add('s-tab', filter=~has_completions)(focus_previous)

        frame = Shadow(body=Frame(
            title=lambda: self.title,
            body=frame_body,
            style='class:dialog.body',
            width=(None if with_background is None else width),
            key_bindings=kb,
            modal=modal,
        ))

        if with_background:
            self.container = Box(
                body=frame,
                style='class:dialog',
                width=width)
        else:
            self.container = frame

    def __pt_container__(self):
        return self.container

def yes_no_dialog(title='', text='', yes_text='Yes', no_text='No', style=None,
                  async_=False):
    """
    Display a Yes/No dialog.
    Return a boolean.
    """
    def yes_handler(dummy=None):
        get_app().exit(result=True)

    def no_handler(dummy=None):
        get_app().exit(result=False)

    dialog = MiniDialog(
        title=title,
        body=Label(text=text, dont_extend_height=True),
        buttons=[
            MiniButton(text=yes_text, handler=yes_handler),
            MiniButton(text=no_text, handler=no_handler),
        ], with_background=True)

    return _run_dialog(dialog, style, async_=async_)


def button_dialog(title='', text='', buttons=[], style=None,
                  async_=False, initialChoice=None):
    """
    Display a dialog with button choices (given as a list of tuples).
    Return the value associated with button.
    """
    def button_handler(v, dummy=None):
        get_app().exit(result=v)

    buttonObjects = [MiniButton(text=t, handler=functools.partial(button_handler, v)) for t, v in buttons]
    dialog = MiniDialog(
        title=title,
        body=Label(text=text, dont_extend_height=True),
        buttons=buttonObjects,
        with_background=True)

    if initialChoice:
        fil = filter(lambda btn: btn.text==initialChoice, buttonObjects)
        btn = next(fil)

        return _run_dialog(dialog, style, async_=async_, focused_element=btn.control)
    else:
        return _run_dialog(dialog, style, async_=async_)


def input_dialog(title='', text='', ok_text='OK', cancel_text='Cancel',
                 completer=None, password=False, style=None, async_=False):
    """
    Display a text input box.
    Return the given text, or None when cancelled.
    """
    def accept(buf):
        get_app().layout.focus(ok_button)
        return True  # Keep text.

    def ok_handler(dummy=None):
        get_app().exit(result=textfield.text)

    ok_button = MiniButton(text=ok_text, handler=ok_handler)
    cancel_button = MiniButton(text=cancel_text, handler=_return_none)

    textfield = TextArea(
        multiline=False,
        password=password,
        completer=completer,
        accept_handler=accept)

    dialog = MiniDialog(
        title=title,
        body=HSplit([
            Label(text=text, dont_extend_height=True),
            textfield,
        ], padding=D(preferred=1, max=1)),
        buttons=[ok_button, cancel_button],
        with_background=True)

    return _run_dialog(dialog, style, async_=async_)


def MiniListBoxDialog(title='', itemList=[], ok_text='OK', cancel_text='Cancel',
                 completer=None, password=False, style=None, async_=False):
    """
    Display a list box.
    Return the given text, or None when cancelled.
    """
    def accept(buf):
        get_app().layout.focus(ok_button)
        return True  # Keep text.

    # Reserve a suitable amount of vertical space for the list
    a, screenHeight = os.get_terminal_size()
    itemCount = len(itemList)
    listboxHeight = min(screenHeight - 10, itemCount)
    useScrollbar = listboxHeight < itemCount

    # Set up a case-agnostic sort-and-lookup
    itemList.sort(key = lambda x: x.lower())
    sortKeys = [x.lower() for x in itemList]

    listBox = MiniListBox(
            type=LBOX_GENERAL,
            itemList=itemList,
            sortKeys=sortKeys,
            read_only=True,
            focusable=True,
            height=listboxHeight,
            scrollbar=useScrollbar,
            completer=completer,
            accept_handler=accept)

    def ok_handler(dummy=None):
        get_app().exit(result=listBox.itemList[listBox.selectedItem])

    ok_button = MiniButton(text=ok_text, handler=ok_handler)
    cancel_button = MiniButton(text=cancel_text, handler=_return_none)

    listBox.ok_button = ok_button

    dialog = MiniDialog(
        title=title,
        body=HSplit([
            Label(text='Please select one of the following:', dont_extend_height=True),
            listBox,
        ], padding=D(preferred=1, max=1)),
        buttons=[ok_button, cancel_button],
        with_background=True)

    return _run_dialog(dialog, style, async_=async_)


def MiniFileDialog(title='', filePath='./', ok_text='OK', cancel_text='Cancel',
                 can_create_new=False,
                 completer=None, password=False, style=None, async_=False):
    """
    Display a file selection dialog with filename list box and absolute path
    textline. Return the chosen pathname, or None when cancelled.

    This MiniFileDialog is based on the ListBoxDialog. The file box is a list
    box that shows the files in the current directory. We add a secondary widget
    called the "path box" that shows the absolute path to the currently-
    selected file. (We might want to add a globbing-pattern widget too.)

    For some applications the path box needs to reject nonexisting paths,
    and in most applications we want it to be highlighted when it has
    the focus. The FormattedTextControl (FTC) is an ideal widget for these
    needs. However, this software toolkit requires container-type objects,
    not controls, when creating dialogs. Fortunately
    there is a container that has an FTC for its control, namely the MiniListBox.

    As a side effect of implementing both the file box and the path box as
    MiniListBoxes, we need to put their handler code side-by-side in the
    MiniListBox class, which already handles plain old list boxes. In that code
    we add some extra logic to figure out what kind of widget we are truly
    handling. This is not object-oriented but we have to draw the line somewhere.

    """

    def accept(buf):
        get_app().layout.focus(ok_button)
        return True  # Keep text.

    if os.path.isdir(filePath):
        fileName = ''
        if not filePath.endswith(os.sep):
            filePath += os.sep
    else:
        fileName = os.path.basename(filePath)
        filePath = os.path.dirname(filePath) + os.sep

    completions = list(PathCompleter().get_completions(
                Document(filePath, len(filePath)), CompleteEvent()))

    itemList = ['..' + os.sep] + [c.display[0][1] for c in completions]
    itemList.sort(key = lambda x: x.lower())
    sortKeys = [x.lower() for x in itemList]
    selected_item = bisect_left(sortKeys, fileName.lower()) if fileName else 0

    # Reserve a suitable amount of vertical space for the list
    a, screenHeight = os.get_terminal_size()
    itemCount = len(itemList)
    listboxHeight = min(screenHeight - 10, itemCount)
    useScrollbar = listboxHeight < itemCount

    fullpath = '{}{}'.format(filePath, fileName)
    pathBox = MiniListBox(
        type=LBOX_PATH,
        itemList=[fullpath],
        read_only= not can_create_new,
        focusable=True,
        height=1,
            )

    listBox = MiniListBox(
            type=LBOX_FILES,
            companionBox=pathBox,
            itemList=itemList,
            sortKeys=sortKeys,
            read_only=True,
            selected_item=selected_item,
            focusable=True,
            height=listboxHeight,
            scrollbar=useScrollbar,
            completer=completer,
            accept_handler=accept)

    pathBox.companionBox = listBox

    def ok_handler(dummy=None):
        get_app().exit(result=pathBox.itemList[0])

    ok_button = MiniButton(text=ok_text, handler=ok_handler, order=BTNORDER_FIRST, neighborBox=listBox)
    cancel_button = MiniButton(text=cancel_text, handler=_return_none, order=BTNORDER_LAST, neighborBox=pathBox)

    #hack: see MiniListBox code with ok_button
    listBox.ok_button = ok_button
    pathBox.ok_button = ok_button

    dialog = MiniDialog(
        title=title,
        body=HSplit([
            Label(text='Please navigate to the file of your choice:', dont_extend_height=True),
            pathBox,
            listBox
        ], padding=D(preferred=1, max=1)),
        buttons=[ok_button, cancel_button],
        with_background=True)

    return _run_dialog(dialog, style, async_=async_)


def message_dialog(title='', text='', ok_text='Ok', style=None, async_=False):
    """
    Display a simple message box and wait until the user presses enter.
    """
    dialog = MiniDialog(
        title=title,
        body=Label(text=text, dont_extend_height=True),
        buttons=[
            MiniButton(text=ok_text, handler=_return_none),
        ],
        with_background=True)

    return _run_dialog(dialog, style, async_=async_)


def radiolist_dialog(title='', text='', ok_text='Ok', cancel_text='Cancel',
                     values=None, style=None, async_=False):
    """
    Display a simple list of element the user can choose amongst.

    Only one element can be selected at a time using Arrow keys and Enter.
    The focus can be moved between the list and the Ok/Cancel button with tab.
    """
    def ok_handler(dummy=None):
        get_app().exit(result=radio_list.current_value)

    radio_list = RadioList(values)

    dialog = MiniDialog(
        title=title,
        body=HSplit([
            Label(text=text, dont_extend_height=True),
            radio_list,
        ], padding=1),
        buttons=[
            MiniButton(text=ok_text, handler=ok_handler),
            MiniButton(text=cancel_text, handler=_return_none),
        ],
        with_background=True)

    return _run_dialog(dialog, style, async_=async_)


def _run_dialog(dialog, style, async_=False, focused_element=None):
    " Turn the `Dialog` into an `Application` and run it. "
    application = _create_app(dialog, style, focused_element)
    if async_:
        return application.run_async()
    else:
        return application.run()


def _create_app(dialog, style, focused_element=None):
    # Key bindings.
    bindings = KeyBindings()
    bindings.add('tab')(focus_next)
    bindings.add('s-tab')(focus_previous)

    return Application(
        layout=Layout(dialog, focused_element=focused_element),
        key_bindings=merge_key_bindings([
            load_key_bindings(),
            bindings,
        ]),
        mouse_support=True,
        style=style,
        full_screen=True)


def _return_none(dummy=None):
    " MiniButton handler that returns None. "
    get_app().exit()
