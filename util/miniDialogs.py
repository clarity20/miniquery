"""
Collection of reusable components for building full screen applications.
"""
from __future__ import unicode_literals
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
from prompt_toolkit.eventloop import run_in_executor
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.widgets import ProgressBar, Label, Box, TextArea, RadioList, Shadow, Frame

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

        text = '\n'.join(itemList)
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

        self.companionBox = companionBox

        # Set placeholder values for correct object orientation
        # Specialize the values for special types of MiniListBox
        if self.type == LBOX_PATH:
            # For a path box, track the cursor position
            self.cursor_position = 0     # active value
            self.selectedItem = -1
        else:
            # For a list box (general or filename-type), track the selected line
            self.selectedItem = selected_item   # active value
            self.cursor_position = 0 #MMMM -1

        self.itemCount = len(self.itemList)
        kb = KeyBindings()

        @kb.add('enter')
        def _(event):
            def syncFileBoxToDirectory(fileBox, fullpath):
                filenames = ['..' + os.sep] \
                        + ['{}{}'.format(p.name, os.sep) if p.is_dir() else p.name for p in fullpath.iterdir()]
                filenames.sort(key = lambda x: x.lower())
                fileBox.itemList = filenames
                fileBox.sortKeys = [x.lower() for x in filenames]
                fileBox.itemCount = len(filenames)
                fileBox.selectedItem = 0
                fileBox.text = '\n'.join(filenames)

            # For a general-purpose list box, advance the focus to "OK";
            # a click there will finalize the selection.
            if self.type == LBOX_GENERAL:
                get_app().layout.focus(self.ok_button)
                return True

            # For a path box, accept the input. If a directory, update
            # the file box and focus on it. Else focus on "OK".
            elif self.type == LBOX_PATH:
                fileBox = self.companionBox

                # Read_onlies should never get here, but if they do somehow,
                # then immediately jump to the file box
                if self.read_only == True:
                    get_app().layout.focus(fileBox)
                    return True

                # Accept the edit and resolve it
                fullpath = pathlib.Path(self.itemList[0])
                self.itemList[0] = str(fullpath.resolve())
                self.text = '\n'.join(self.itemList)

                # Three possible scenarios: user has entered a directory name,
                # an existing filename, or a new name
                if fullpath.is_dir():
                    #TODO: Clear a stale status msg

                    # Sync the file box to the directory name just accepted
                    syncFileBoxToDirectory(fileBox, fullpath)
                    # Jump to the file box
                    get_app().layout.focus(fileBox)
                    return True

                elif fullpath.is_file():
                    #TODO: Clear a stale status msg

                    # Sync the file box to the filename's parent directory
                    syncFileBoxToDirectory(fileBox, fullpath.parent)
                    # Accept the filename provisionally: Jump to OK
                    get_app().layout.focus(self.ok_button)
                    return True

                elif not fullpath.exists():
                    #TODO: Show a warning msg about non-existent / new file names
                    #TODO: Accept a new directory name if there's a trailing slash

                    # Sync the file box to the filename's parent directory
                    syncFileBoxToDirectory(fileBox, fullpath.parent)
                    get_app().layout.focus(self.ok_button)
                    return True

            # For a file-list box, synchronize with the path box
            elif self.type == LBOX_FILES:
                pathBox = self.companionBox

                # Fetch the basename and the directory
                filename = self.itemList[self.selectedItem]
                path = pathlib.Path(pathBox.itemList[0])

                # If the path box was already showing a file name (not a dir!)
                # then this is a reselection and the path box is stale. Retreat
                # to directory level before adding the new filename
                if not path.is_dir():
                    path = path.parent

                # Append the filename to the directory
                fullpath = path / filename

                # Resolve and refresh the path box
                pathBox.itemList[0] = str(fullpath.resolve())
                pathBox.text = '\n'.join(pathBox.itemList)

                # If the user chose a directory, list its contents
                if fullpath.is_dir():
                    syncFileBoxToDirectory(self, fullpath)
                    # Stay focused on the file box: do nothing further

                # If the user chose a file, accept the choice
                elif fullpath.is_file():
                    get_app().layout.focus(self.ok_button)

                # Finally, a selection from the file box cannot be non-existing

            return True  # Keep text.

        @kb.add('escape')
        def _(event):
            #Hack: caller sets ok_button so the following will work
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
                if self.read_only:
                    return
                curpos = self.cursor_position
                item = self.itemList[0]

                if len(keyPressed) == 1:     # roughly the same as keyPressed.isprintable()
                    self.itemList[0] = '{}{}{}'.format(item[:curpos], keyPressed, item[curpos:])
                    self.text = '\n'.join(self.itemList)
                    if curpos < len(item)-1:
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
                            self.cursor_position = length-1
                    elif keyPressed == 'c-delete':
                        # Chop from here to the end
                        self.itemList[0] = item[:curpos]
                        self.text = '\n'.join(self.itemList)
                        self.cursor_position -= 1
                    # We see 'c-h' instead of 'backspace'
                    elif keyPressed == 'c-h' and curpos > 0:
                        self.itemList[0] = '{}{}'.format(item[:curpos-1], item[curpos:])
                        self.text = '\n'.join(self.itemList)
                        self.cursor_position -= 1
                    # No obvious way to implement 'c-backspace', at least on Android
                    # elif keyPressed == 'c-backspace':
                    #     # Chop everything on the left
                    #     self.itemList[0] = item[curpos:]
                    #     self.text = '\n'.join(self.itemList)
                    #     self.cursor_position = 0
                elif keyPressed == 'left' and curpos > 0:
                    self.cursor_position -= 1
                elif keyPressed == 'right' and curpos < len(item)-1:
                    self.cursor_position += 1
                elif keyPressed == 'delete':
                    self.itemList[0] = '{}{}'.format(item[:curpos], item[curpos+1:])
                    self.text = '\n'.join(self.itemList)
                    # do not change cursor position
                return

            # For a list box, enable letters/numbers as shortcuts for selection
            elif self.type == LBOX_FILES and (keyPressed.isalnum() or keyPressed == '.'):
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

        self.control.key_bindings = kb

    def _get_text_fragments(self):
        item = self.selectedItem
        items = self.itemList
        text = self.text

#MMMM: handler should prolly return the y-value at the clickpoint: "x,y = self.get_cursor_position()"
        def handler(mouse_event):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.handler()

        highlightScheme = 'fg:white bg:blue' if get_app().layout. \
            has_focus(self.control) else 'fg:white bg:gray'

        if self.type == LBOX_PATH:
            # return my entire text in the single, correct color scheme
            idx = self.cursor_position
            return [
                (highlightScheme, text[:idx], handler),
                ('[SetCursorPosition]', ''),
                (highlightScheme, text[idx:], handler),
               ]

        if item == self.itemCount-1:  # last item
            idx = text.rindex(items[item])
            return [
                ('', text[:idx], handler),
                ('[SetCursorPosition]', ''),
                (highlightScheme, text[idx:], handler),
               ]
        elif item > 0:
            searchString = '\n{}\n'.format(items[item])
            startIdx = text.index(searchString) + 1  # skip leading NL
            endIdx = text.find('\n', startIdx) + 1  # enclose next NL
            return [
                ('', text[:startIdx], handler),
                ('[SetCursorPosition]', ''),
                (highlightScheme, text[startIdx:endIdx], handler),
                ('', text[endIdx:], handler),
               ]
        else:    # item == 0
            endIdx = text.find('\n') + 1
            return [
                ('[SetCursorPosition]', ''),
                (highlightScheme, text[:endIdx], handler),
                ('', text[endIdx:], handler),
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
    def __init__(self, text, handler=None, width=12, addHotkey=True):
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

        # ESC should only actuate buttons mapped to act like cancelers
        @kb.add('escape')
        def _(event):
            if self.handler == _return_none:
                self.handler()

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
                  async_=False):
    """
    Display a dialog with button choices (given as a list of tuples).
    Return the value associated with button.
    """
    def button_handler(v, dummy=None):
        get_app().exit(result=v)

    dialog = MiniDialog(
        title=title,
        body=Label(text=text, dont_extend_height=True),
        buttons=[MiniButton(text=t, handler=functools.partial(button_handler, v)) for t, v in buttons],
        with_background=True)

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
    Display a list box. (Make it a drop-down, someday.)
    Return the given text, or None when cancelled.
    """
    def accept(buf):
        get_app().layout.focus(ok_button)
        return True  # Keep text.

    # Reserve a suitable amount of vertical space for the list
    a, screenHeight = os.get_terminal_size()
    listboxHeight = min(screenHeight - 10, len(itemList))

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
    textline. Return the given text, or None when cancelled.

    This MiniFileDialog is based on the ListBoxDialog. The file box is a list
    box that shows the files in the current directory. We add a secondary widget
    called the "path box" that shows the absolute path to the currently-
    selected file. (We might want to add a globbing-pattern widget too.)

    For some applications the path box needs to be read-only, others not, and
    in most applications we want it to be highlighted when it has
    the focus. The FormattedTextControl (FTC) is an ideal widget for these
    needs. However, a control-type object does not work when creating dialogs
    with this software toolkit; it requires container-type objects. Fortunately
    there is a container that has an FTC-type control, namely the MiniListBox.

    As a side effect of implementing both the file box and the path box as
    MiniListBoxes, we need to put their handler code side-by-side in the
    MiniListBox class, which already handles plain old list boxes. In that code
    we add some extra logic to figure out what kind of widget we are truly
    handling. This is not object-oriented but we have to draw the line.

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
    listboxHeight = min(screenHeight - 10, len(itemList))

    text = '{}{}'.format(filePath, fileName)
    pathBox = MiniListBox(
        type=LBOX_PATH,
        itemList=[text],
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
            completer=completer,
            accept_handler=accept)

    pathBox.companionBox = listBox

    def ok_handler(dummy=None):
        get_app().exit(result=pathBox.itemList[0])

    ok_button = MiniButton(text=ok_text, handler=ok_handler)
    cancel_button = MiniButton(text=cancel_text, handler=_return_none)

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


def progress_dialog(title='', text='', run_callback=None, style=None, async_=False):
    """
    :param run_callback: A function that receives as input a `set_percentage`
        function and it does the work.
    """
    assert callable(run_callback)

    progressbar = ProgressBar()
    text_area = TextArea(
        focusable=False,

        # Prefer this text area as big as possible, to avoid having a window
        # that keeps resizing when we add text to it.
        height=D(preferred=10**10))

    dialog = MiniDialog(
        body=HSplit([
            Box(Label(text=text)),
            Box(text_area, padding=D.exact(1)),
            progressbar,
        ]),
        title=title,
        with_background=True)
    app = _create_app(dialog, style)

    def set_percentage(value):
        progressbar.percentage = int(value)
        app.invalidate()

    def log_text(text):
        text_area.buffer.insert_text(text)
        app.invalidate()

    # Run the callback in the executor. When done, set a return value for the
    # UI, so that it quits.
    def start():
        try:
            run_callback(set_percentage, log_text)
        finally:
            app.exit()

    run_in_executor(start)

    if async_:
        return app.run_async()
    else:
        return app.run()


def _run_dialog(dialog, style, async_=False):
    " Turn the `Dialog` into an `Application` and run it. "
    application = _create_app(dialog, style)
    if async_:
        return application.run_async()
    else:
        return application.run()


def _create_app(dialog, style):
    # Key bindings.
    bindings = KeyBindings()
    bindings.add('tab')(focus_next)
    bindings.add('s-tab')(focus_previous)

    return Application(
        layout=Layout(dialog),
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
