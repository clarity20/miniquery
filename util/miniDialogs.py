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

import os
import functools
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.completion import DynamicCompleter
from prompt_toolkit.auto_suggest import DynamicAutoSuggest
from prompt_toolkit.layout.margins import ScrollbarMargin, NumberedMargin
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.eventloop import run_in_executor
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.widgets import ProgressBar, Label, Box, TextArea, RadioList, Shadow, Frame

import six
import re
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEventType

__all__ = [
    'MiniListBox',
    'MiniButton',
    'MiniDialog',
    'yes_no_dialog',
    'button_dialog',
    'input_dialog',
    'message_dialog',
    'radiolist_dialog',
    'progress_dialog',
]

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
                 lexer=None, auto_suggest=None, completer=None,
                 complete_while_typing=True, accept_handler=None, history=None,
                 focusable=True, wrap_lines=True,
                 read_only=False, width=None, height=None,
                 dont_extend_height=False, dont_extend_width=False,
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

        itemCount = len(self.itemList)
        self.selectedItem = 0
        kb = KeyBindings()

        # Without this, 'enter' does nothing! So what's the accept_handler for?
        @kb.add('enter')
        def _(event):
            #Hack: caller sets ok_button so the following will work
            if self.ok_button:
                get_app().layout.focus(self.ok_button)
            return True  # Keep text.

        # Disable Ok / Cancel hotkeys within the text area
        #TODO:Remove the formatted underlines.
        @kb.add('O')
        @kb.add('o')
        @kb.add('C')
        @kb.add('c')
        def _(event):
            pass

        @kb.add('down')
        def _(event):
            nonlocal itemCount
            if self.selectedItem == itemCount-1:
                return
            else:
                self.selectedItem = (self.selectedItem + 1) % itemCount

        @kb.add('up')
        def _(event):
            nonlocal itemCount
            if self.selectedItem == 0:
                return
            else:
                self.selectedItem = (self.selectedItem - 1) % itemCount

        @kb.add('pagedown')
        def _(event):
            nonlocal itemCount, height
            jumpSize = min(height-1, itemCount-1-self.selectedItem)
            event.current_buffer.auto_down(jumpSize)
            self.selectedItem = (self.selectedItem + jumpSize) % itemCount

        @kb.add('pageup')
        def _(event):
            nonlocal itemCount, height
            jumpSize = min(height-1, self.selectedItem)
            event.current_buffer.auto_up(jumpSize)
            self.selectedItem = (self.selectedItem - jumpSize) % itemCount

        self.control.key_bindings = kb

    def _get_text_fragments(self):
        item = self.selectedItem
        items = self.itemList
        text = self.text

        def handler(mouse_event):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.handler()

        if item == len(items)-1:  # last item
            idx = text.rindex(items[item])
            return [
                ('', text[:idx], handler),
                ('[SetCursorPosition]', ''),
                ('fg:white bg:blue', text[idx:], handler),
               ]
        elif item > 0:
            searchString = '\n{}\n'.format(items[item])
            startIdx = text.index(searchString) + 1  # skip leading NL
            endIdx = text.find('\n', startIdx) + 1  # enclose next NL
            return [
                ('', text[:startIdx], handler),
                ('[SetCursorPosition]', ''),
                ('fg:white bg:blue', text[startIdx:endIdx], handler),
                ('', text[endIdx:], handler),
               ]
        else:    # item == 0
            endIdx = text.find('\n') + 1
            return [
                ('[SetCursorPosition]', ''),
                ('fg:white bg:blue', text[:endIdx], handler),
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

        # Create a hotkey for every button if so indicated
        for btn in buttons:
            if btn.hotkeyIndex >= 0:
                key = btn.text[btn.hotkeyIndex]
                kb.add(key.upper())(btn.handler)
                kb.add(key.lower())(btn.handler)

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

    textBuffer = '\n'.join(itemList)
    # Reserve a suitable amount of vertical space for the list
    a, screenHeight = os.get_terminal_size()
    listboxHeight = min(screenHeight - 10, len(itemList))

    textfield = MiniListBox(
            itemList=itemList,
            read_only=True,
            focusable=True,
            height=listboxHeight,
            completer=completer,
            accept_handler=accept)

    def ok_handler(dummy=None):
        # Fetch and return the text of the currently selected row. Do not
        # return the row number because in situations such as file browsing,
        # the text can change, rendering the row number unreliable.
        nonlocal textBuffer, textfield
        txt = textBuffer.split()[textfield.selectedItem]
        get_app().exit(result=txt)

    ok_button = MiniButton(text=ok_text, handler=ok_handler)
    cancel_button = MiniButton(text=cancel_text, handler=_return_none)

    textfield.ok_button = ok_button

    dialog = MiniDialog(
        title=title,
        body=HSplit([
            Label(text='Please select one of the following:', dont_extend_height=True),
            textfield,
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
