"""词法分析：程序文本 → 词（token）列表。

规范 §3 规定的"零件"：注释、整数、布尔、符号、字符串、引用简写 '、括号。
这一层只认字符，不懂语法，所以可以独立测试。
"""

import re

#: 空白字符。逗号在这里不当分隔符，因为规范没把它列为分隔符。
_WHITESPACE = " \t\r\n\f"

#: 原子的结束字符：遇到这些就说明一个词读完了。
_DELIMITERS = set(_WHITESPACE) | set("()'\";")

#: 字符串里的转义。
_STRING_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    '"': '"',
    "\\": "\\",
}

_INTEGER_RE = re.compile(r"[+-]?\d+\Z")
_FLOAT_RE = re.compile(r"[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?\Z")


class Token:
    """一个词：kind 是类别，value 是它的值，position 用来报错定位。"""

    __slots__ = ("kind", "value", "position")

    def __init__(self, kind, value, position):
        self.kind = kind
        self.value = value
        self.position = position

    def __repr__(self):
        return "Token(%r, %r)" % (self.kind, self.value)


def _parse_atom(text):
    """把一段原子文本变成对应类型的值（布尔 / 整数 / 浮点 / 符号）。"""
    if text == "#t":
        return True
    if text == "#f":
        return False
    if _INTEGER_RE.match(text):
        return int(text)
    if _FLOAT_RE.match(text):
        return float(text)
    return None  # 交给调用方当符号处理


def tokenize(source):
    """把源码拆成 Token 列表。遇到不闭合的字符串会抛 SchemeError。"""
    tokens = []
    i = 0
    n = len(source)

    while i < n:
        ch = source[i]

        # 空白：跳过
        if ch in _WHITESPACE:
            i += 1
            continue

        # 注释：从 ; 到行尾
        if ch == ";":
            while i < n and source[i] != "\n":
                i += 1
            continue

        # 括号
        if ch == "(":
            tokens.append(Token("LPAREN", "(", i))
            i += 1
            continue
        if ch == ")":
            tokens.append(Token("RPAREN", ")", i))
            i += 1
            continue

        # 引用简写 'x 等价于 (quote x)
        if ch == "'":
            tokens.append(Token("QUOTE", "'", i))
            i += 1
            continue

        # 字符串字面量
        if ch == '"':
            start = i
            i += 1
            chars = []
            while True:
                if i >= n:
                    raise _syntax_error("字符串没有闭合的双引号", start)
                current = source[i]
                if current == "\\":
                    if i + 1 >= n:
                        raise _syntax_error("字符串末尾的转义符不完整", i)
                    escape = source[i + 1]
                    chars.append(_STRING_ESCAPES.get(escape, escape))
                    i += 2
                elif current == '"':
                    i += 1
                    break
                else:
                    chars.append(current)
                    i += 1
            tokens.append(Token("STRING", "".join(chars), start))
            continue

        # 原子：符号 / 数字 / 布尔
        start = i
        while i < n and source[i] not in _DELIMITERS:
            i += 1
        text = source[start:i]
        if not text:
            # 兜底：不该出现，避免死循环
            i += 1
            continue
        literal = _parse_atom(text)
        if literal is not None:
            kind = "BOOL" if isinstance(literal, bool) else "NUMBER"
            tokens.append(Token(kind, literal, start))
        else:
            tokens.append(Token("SYMBOL", text, start))

    return tokens


def _syntax_error(message, position):
    from datatypes import SchemeError

    return SchemeError("%s（位置 %d）" % (message, position))
