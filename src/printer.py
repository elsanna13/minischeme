"""打印模块：把值变成文本。

规范 §8 规定了每种值的打印形式，尤其是：
- 布尔是 #t / #f（不是 Python 的 True / False）
- 字符串带引号，内部的换行/制表符要转义成 \\n \\t
- 真列表打 (1 2 3)，点对打 (1 . 2)，空表打 ()
- 过程打 #<procedure>
"""

from datatypes import NIL, Closure, BuiltinProcedure, Pair, Symbol, unpack_list

_STRING_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\t": "\\t",
    "\r": "\\r",
}


def _escape_string(text):
    return "".join(_STRING_ESCAPES.get(ch, ch) for ch in text)


def write_repr(value):
    """按规范 §8 的"写"形式转成文本（字符串带引号）。"""
    # bool 必须排在 int 前面判断：Python 里 isinstance(True, int) 是 True。
    if value is True:
        return "#t"
    if value is False:
        return "#f"
    if value is NIL:
        return "()"
    if isinstance(value, Symbol):
        return value.name
    if isinstance(value, str):
        return '"%s"' % _escape_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, Pair):
        return _pair_repr(value)
    if isinstance(value, (BuiltinProcedure, Closure)):
        return "#<procedure>"
    if value is None:
        return ""  # 无值：顶层不打印
    return str(value)


def _pair_repr(pair):
    items, tail = unpack_list(pair)
    body = " ".join(write_repr(item) for item in items)
    if tail is NIL:
        return "(%s)" % body
    return "(%s . %s)" % (body, write_repr(tail))


def display_repr(value):
    """display 的形式：和 write 一样，只是最外层字符串不带引号。"""
    if isinstance(value, str):
        return value
    return write_repr(value)
