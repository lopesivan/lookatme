"""
Defines render functions that render lexed markdown block tokens into urwid
representations
"""


import pygments
import pygments.formatters
import pygments.lexers
import pygments.styles
import mistune
import re
import shlex
import urwid


import lookatme.config as config
from lookatme.contrib import contrib_first
import lookatme.render.pygments as pygments_render
import lookatme.render.markdown_inline as markdown_inline_renderer
from lookatme.utils import *
from lookatme.widgets.clickable_text import ClickableText


def _meta(item):
    if not hasattr(item, "meta"):
        meta = {}
        setattr(item, "meta", meta)
    else:
        meta = getattr(item, "meta")
    return meta


def _set_is_list(item, level=1):
    _meta(item).update({
        "is_list": True,
        "list_level": level,
    })


def _is_list(item):
    return _meta(item).get("is_list", False)


def _list_level(item):
    return _meta(item).get("list_level", 1)


@contrib_first
def render_newline(token, body, stack, loop):
    """Render a newline

    See :any:`lookatme.tui.SlideRenderer.do_render` for argument and return
    value descriptions.
    """
    return urwid.Divider()


@contrib_first
def render_heading(token, body, stack, loop):
    """Render markdown headings, using the defined styles for the styling and
    prefix/suffix.

    See :any:`lookatme.tui.SlideRenderer.do_render` for argument and return
    value descriptions.

    Below are the default stylings for headings:

    .. code-block:: yaml

        headings:
          '1':
            bg: default
            fg: '#9fc,bold'
            prefix: "██ "
            suffix: ""
          '2':
            bg: default
            fg: '#1cc,bold'
            prefix: "▓▓▓ "
            suffix: ""
          '3':
            bg: default
            fg: '#29c,bold'
            prefix: "▒▒▒▒ "
            suffix: ""
          '4':
            bg: default
            fg: '#66a,bold'
            prefix: "░░░░░ "
            suffix: ""
          default:
            bg: default
            fg: '#579,bold'
            prefix: "░░░░░ "
            suffix: ""

    :returns: A list of urwid Widgets or a single urwid Widget
    """
    headings = config.STYLE["headings"]
    level = token["level"]
    style = config.STYLE["headings"].get(str(level), headings["default"])

    prefix = styled_text(style["prefix"], style)
    suffix = styled_text(style["suffix"], style)

    rendered = render_text(text=token["text"])
    styled_rendered = styled_text(rendered, style, supplement_style=True)

    return [
        urwid.Divider(),
        ClickableText([prefix] + styled_text(rendered, style) + [suffix]),
        urwid.Divider(),
    ]


@contrib_first
def render_table(token, body, stack, loop):
    """Renders a table using the :any:`Table` widget.

    See :any:`lookatme.tui.SlideRenderer.do_render` for argument and return
    value descriptions.

    The table widget makes use of the styles below:

    .. code-block:: yaml

        table:
          column_spacing: 3
          header_divider: "─"

    :returns: A list of urwid Widgets or a single urwid Widget
    """
    from lookatme.widgets.table import Table

    headers = token["header"]
    aligns = token["align"]
    cells = token["cells"]

    table = Table(cells, headers=headers, aligns=aligns)
    padding = urwid.Padding(table, width=table.total_width + 2, align="center")

    def table_changed(*args, **kwargs):
        padding.width = table.total_width + 2

    urwid.connect_signal(table, "change", table_changed)

    return padding


@contrib_first
def render_list_start(token, body, stack, loop):
    """Handles the indentation when starting rendering a new list. List items
    themselves (with the bullets) are rendered by the
    :any:`render_list_item_start` function.

    See :any:`lookatme.tui.SlideRenderer.do_render` for argument and return
    value descriptions.
    """
    res = urwid.Pile(urwid.SimpleFocusListWalker([]))

    in_list = _is_list(stack[-1])
    list_level = 1
    if in_list:
        list_level = _list_level(stack[-1]) + 1
    _set_is_list(res, list_level)
    stack.append(res)

    widgets = []
    if not in_list:
        widgets.append(urwid.Divider())
    widgets.append(urwid.Padding(res, left=2))
    if not in_list:
        widgets.append(urwid.Divider())
    return widgets


@contrib_first
def render_list_end(token, body, stack, loop):
    """Pops the pushed ``urwid.Pile()`` from the stack (decreases indentation)

    See :any:`lookatme.tui.SlideRenderer.do_render` for argument and return
    value descriptions.
    """
    stack.pop()


def _list_item_start(token, body, stack, loop):
    """Render the start of a list item. This function makes use of the styles:

    .. code-block:: yaml

        bullets:
          '1': "•"
          '2': "⁃"
          '3': "◦"
          default: "•"

    See :any:`lookatme.tui.SlideRenderer.do_render` for argument and return
    value descriptions.
    """
    list_level = _list_level(stack[-1])
    pile = urwid.Pile(urwid.SimpleFocusListWalker([]))

    bullets = config.STYLE["bullets"]
    list_bullet = bullets.get(str(list_level), bullets["default"])

    res = urwid.Columns([
        (2, urwid.Text(("bold", list_bullet + " "))),
        pile,
    ])
    stack.append(pile)
    return res


@contrib_first
def render_list_item_start(token, body, stack, loop):
    """Render the start of a list item. This function makes use of the styles:

    .. code-block:: yaml

        bullets:
          '1': "•"
          '2': "⁃"
          '3': "◦"
          default: "•"

    See :any:`lookatme.tui.SlideRenderer.do_render` for argument and return
    value descriptions.
    """
    return _list_item_start(token, body, stack, loop)


@contrib_first
def render_loose_item_start(token, body, stack, loop):
    """Render the start of a list item. This function makes use of the styles:

    .. code-block:: yaml

        bullets:
          '1': "•"
          '2': "⁃"
          '3': "◦"
          default: "•"

    See :any:`lookatme.tui.SlideRenderer.do_render` for argument and return
    value descriptions.
    """
    return _list_item_start(token, body, stack, loop)


@contrib_first
def render_list_item_end(token, body, stack, loop):
    """Pops the pushed ``urwid.Pile()`` from the stack (decreases indentation)

    See :any:`lookatme.tui.SlideRenderer.do_render` for argument and return
    value descriptions.
    """
    stack.pop()


@contrib_first
def render_text(token=None, body=None, stack=None, loop=None, text=None):
    """Renders raw text. This function uses the inline markdown lexer
    from mistune with the :py:mod:`lookatme.render.markdown_inline` render module
    to render the lexed inline markup to
    `urwid Text markup <http://urwid.org/manual/displayattributes.html#text-markup>`_.
    The created Text markup is then used to create and return a :any:`ClickableText`
    instance.

    Many other functions call this function directly, passing in the extra
    ``text`` argument and leaving all other arguments blank. 

    See :any:`lookatme.tui.SlideRenderer.do_render` for additional argument and
    return value descriptions.
    """
    if text is None:
        text = token["text"]

    inline_lexer = mistune.InlineLexer(markdown_inline_renderer)
    res = inline_lexer.output(text)
    if len(res) == 0:
        res = [""]

    return ClickableText(res)


@contrib_first
def render_paragraph(token, body, stack, loop):
    """Renders the provided text with additional pre and post paddings.

    See :any:`lookatme.tui.SlideRenderer.do_render` for additional argument and
    return value descriptions.
    """
    token["text"] = token["text"].replace("\r\n", " ").replace("\n", " ")
    res = render_text(token, body, stack, loop)
    return [
        urwid.Divider(),
        res,
        urwid.Divider(),
    ]


@contrib_first
def render_block_quote_start(token, body, stack, loop):
    """Begins rendering of a block quote. Pushes a new ``urwid.Pile()`` to the
    stack that is indented, has styling applied, and has the quote markers
    on the left.

    This function makes use of the styles:

    .. code-block:: yaml

        quote:
          top_corner: "┌"
          bottom_corner: "└"
          side: "╎"
          style:
            bg: default
            fg: italics,#aaa

    See :any:`lookatme.tui.SlideRenderer.do_render` for additional argument and
    return value descriptions.
    """
    pile = urwid.Pile([])
    stack.append(pile)

    styles = config.STYLE["quote"]

    quote_side = styles["side"]
    quote_top_corner = styles["top_corner"]
    quote_bottom_corner = styles["bottom_corner"]
    quote_style = styles["style"]

    return [
        urwid.Divider(),
        urwid.LineBox(
            urwid.AttrMap(
                urwid.Padding(pile, left=2),
                spec_from_style(quote_style),
            ),
            lline=quote_side, rline="",
            tline=" ", trcorner="", tlcorner=quote_top_corner,
            bline=" ", brcorner="", blcorner=quote_bottom_corner,
        ),
        urwid.Divider(),
    ]


@contrib_first
def render_block_quote_end(token, body, stack, loop):
    """Pops the block quote start ``urwid.Pile()`` from the stack, taking
    future renderings out of the block quote styling.

    See :any:`lookatme.tui.SlideRenderer.do_render` for additional argument and
    return value descriptions.
    """
    pile = stack.pop()

    # remove leading/trailing divider if they were added to the pile
    if isinstance(pile.contents[0][0], urwid.Divider):
        pile.contents = pile.contents[1:]
    if isinstance(pile.contents[-1][0], urwid.Divider):
        pile.contents = pile.contents[:-1]


@contrib_first
def render_code(token, body, stack, loop):
    """Renders a code block using the Pygments library.

    See :any:`lookatme.tui.SlideRenderer.do_render` for additional argument and
    return value descriptions.
    """
    lang = token.get("lang", "text") or "text"
    text = token["text"]
    res = pygments_render.render_text(text, lang=lang)

    return [
        urwid.Divider(),
        res,
        urwid.Divider(),
    ]
