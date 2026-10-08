"""语法分析：词列表 → 表达式（嵌套的点对链）。

规范 §3 的"列表语法"和"引用简写"在这里处理：
    'x        →  (quote x)
    (1 2 3)   →  一条点对链
    (1 . 2)   →  点对（规范没要求，顺手支持，打印时才有 (1 . 2) 的形式）
"""

from datatypes import NIL, Pair, SchemeError, build_list, intern
from lexer import tokenize

_QUOTE = intern("quote")


def parse(source):
    """把一段源码解析成顶层表达式的列表。"""
    tokens = tokenize(source)
    expressions = []
    position = 0
    while position < len(tokens):
        expression, position = _parse_expression(tokens, position)
        expressions.append(expression)
    return expressions


def _parse_expression(tokens, position):
    """读一个表达式，返回 (表达式, 下一个位置)。"""
    if position >= len(tokens):
        raise SchemeError("表达式不完整：内容意外结束")

    token = tokens[position]

    if token.kind == "LPAREN":
        return _parse_list(tokens, position + 1)

    if token.kind == "RPAREN":
        raise SchemeError("多余的右括号（位置 %d）" % token.position)

    if token.kind == "QUOTE":
        inner, position = _parse_expression(tokens, position + 1)
        return build_list([_QUOTE, inner]), position

    # 数字、布尔、字符串、符号都直接是表达式的值
    if token.kind == "SYMBOL":
        return intern(token.value), position + 1
    return token.value, position + 1


def _parse_list(tokens, position):
    """读括号里的内容，直到匹配的右括号。"""
    items = []
    while True:
        if position >= len(tokens):
            raise SchemeError("缺少右括号")
        token = tokens[position]

        if token.kind == "RPAREN":
            return build_list(items), position + 1

        # 点对写法 (a . b)
        if token.kind == "SYMBOL" and token.value == ".":
            if not items:
                raise SchemeError("点对写法前面缺少元素（位置 %d）" % token.position)
            tail, position = _parse_expression(tokens, position + 1)
            if position >= len(tokens) or tokens[position].kind != "RPAREN":
                raise SchemeError("点对写法后面只能跟一个表达式和一个右括号")
            return build_list(items, tail), position + 1

        item, position = _parse_expression(tokens, position)
        items.append(item)
