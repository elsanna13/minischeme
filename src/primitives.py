"""内置过程库（规范 §5）。

这里只放"函数"，不放特殊形式——特殊形式在 evaluator.py 里，因为它们的
求值顺序和普通函数调用不一样（比如 if 只求值一个分支）。

每个内置过程都写成"接收一个已求值的参数列表、返回一个值"的函数，
由 BuiltinProcedure 包起来放进初始环境。
"""

import sys

from datatypes import (
    NIL,
    BuiltinProcedure,
    Closure,
    Pair,
    SchemeError,
    Symbol,
    build_list,
    expect_proper_list,
    is_number,
    is_proper_list,
    unpack_list,
)
from environment import Environment
from printer import display_repr, write_repr


# ------------------------------------------------------------------ 小工具

def _num(value, who):
    """要求是个数字。bool 不算数字，否则 (abs #t) 会算出 1。"""
    if not is_number(value):
        raise SchemeError("%s: 需要一个数字，得到 %s" % (who, write_repr(value)))
    return value


def _trunc_div(a, b):
    """整数除法，商向零截断：(/ -7 2) → -3 而不是 -4。"""
    if b == 0:
        raise SchemeError("除数不能为 0")
    quotient = abs(a) // abs(b)
    return quotient if (a < 0) == (b < 0) else -quotient


def _comparable(value, who):
    """比较用的键：数字按数值，符号按名字。"""
    if isinstance(value, Symbol):
        return value.name
    if is_number(value):
        return value
    raise SchemeError("%s: 只能比较数字或符号，得到 %s" % (who, write_repr(value)))


# ------------------------------------------------------------------ 算术

def b_add(args):
    total = 0
    for value in args:
        total = total + _num(value, "+")
    return total


def b_sub(args):
    if len(args) == 1:
        return -_num(args[0], "-")
    total = _num(args[0], "-")
    for value in args[1:]:
        total = total - _num(value, "-")
    return total


def b_mul(args):
    total = 1
    for value in args:
        total = total * _num(value, "*")
    return total


def b_div(args):
    """整数相除得整数商；单参数求倒数（浮点）。"""
    if len(args) == 1:
        divisor = _num(args[0], "/")
        if divisor == 0:
            raise SchemeError("/: 除数不能为 0")
        return 1 / divisor

    result = _num(args[0], "/")
    for value in args[1:]:
        divisor = _num(value, "/")
        if isinstance(result, int) and isinstance(divisor, int):
            result = _trunc_div(result, divisor)
        else:
            if divisor == 0:
                raise SchemeError("/: 除数不能为 0")
            result = result / divisor
    return result


def b_modulo(args):
    """取模，结果符号跟着除数（Scheme 的 modulo 语义）。"""
    a = _num(args[0], "modulo")
    b = _num(args[1], "modulo")
    if b == 0:
        raise SchemeError("modulo: 除数不能为 0")
    return a % b


def b_quotient(args):
    """整除商，向零截断。"""
    return _trunc_div(_num(args[0], "quotient"), _num(args[1], "quotient"))


def b_expt(args):
    base = _num(args[0], "expt")
    exponent = _num(args[1], "expt")
    if isinstance(base, int) and isinstance(exponent, int) and exponent >= 0:
        return base ** exponent
    return float(base) ** float(exponent)


def b_abs(args):
    return abs(_num(args[0], "abs"))


# ------------------------------------------------------------------ 比较（链式）

def _make_comparison(name, predicate):
    """(< 2 3 4) 表示相邻两两都要成立，所以是链式比较。"""

    def compare(args):
        for left, right in zip(args, args[1:]):
            try:
                if not predicate(_comparable(left, name), _comparable(right, name)):
                    return False
            except TypeError:
                raise SchemeError(
                    "%s: 不能比较 %s 和 %s" % (name, write_repr(left), write_repr(right))
                )
        return True

    return compare


def b_not(args):
    # 只有 #f 是假：0、()、"" 都为真。
    return args[0] is False


# ------------------------------------------------------------------ 列表

def b_cons(args):
    return Pair(args[0], args[1])


def b_car(args):
    value = args[0]
    if not isinstance(value, Pair):
        raise SchemeError("car: 需要一个点对，得到 %s" % write_repr(value))
    return value.car


def b_cdr(args):
    value = args[0]
    if not isinstance(value, Pair):
        raise SchemeError("cdr: 需要一个点对，得到 %s" % write_repr(value))
    return value.cdr


def b_list(args):
    return build_list(args)


def b_length(args):
    items, _ = unpack_list(args[0])
    if not is_proper_list(args[0]):
        raise SchemeError("length: 需要一个真列表，得到 %s" % write_repr(args[0]))
    return len(items)


def b_append(args):
    """把前面的列表依次接到最后一个参数前面；最后一个可以是任意值。"""
    if not args:
        return NIL
    result = args[-1]
    for value in reversed(args[:-1]):
        items = expect_proper_list(value, "append")
        result = build_list(items, result)
    return result


def b_null_p(args):
    return args[0] is NIL


def b_pair_p(args):
    return isinstance(args[0], Pair)


def b_list_p(args):
    return is_proper_list(args[0])


# ------------------------------------------------------------------ 谓词

def b_number_p(args):
    return is_number(args[0])


def b_boolean_p(args):
    return isinstance(args[0], bool)


def b_symbol_p(args):
    return isinstance(args[0], Symbol)


def b_string_p(args):
    return isinstance(args[0], str)


def b_procedure_p(args):
    return isinstance(args[0], (BuiltinProcedure, Closure))


def b_zero_p(args):
    return _num(args[0], "zero?") == 0


def b_even_p(args):
    return _num(args[0], "even?") % 2 == 0


def b_odd_p(args):
    return _num(args[0], "odd?") % 2 != 0


def b_eq_p(args):
    """eq?：基本值按值比，复合数据按同一性比（是不是同一个对象）。"""
    a, b = args[0], args[1]
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if a is NIL or b is NIL:
        return a is b
    if isinstance(a, Symbol) or isinstance(b, Symbol):
        return isinstance(a, Symbol) and isinstance(b, Symbol) and a.name == b.name
    if isinstance(a, str) or isinstance(b, str):
        return isinstance(a, str) and isinstance(b, str) and a == b
    if is_number(a) and is_number(b):
        return a == b
    return a is b


def b_equal_p(args):
    """equal?：结构相等，逐层比较。注意先比类型再比值。"""
    return _equal(args[0], args[1])


def _equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        # (equal? #t 1) 必须是 #f —— Python 里 True == 1，所以先拦住布尔。
        return a is b
    if a is NIL or b is NIL:
        return a is b
    if isinstance(a, Symbol) or isinstance(b, Symbol):
        # (equal? 'a "a") 必须是 #f —— 符号和字符串是两种值。
        return isinstance(a, Symbol) and isinstance(b, Symbol) and a.name == b.name
    if isinstance(a, str) or isinstance(b, str):
        return isinstance(a, str) and isinstance(b, str) and a == b
    if is_number(a) and is_number(b):
        return a == b
    if isinstance(a, Pair) and isinstance(b, Pair):
        return _equal(a.car, b.car) and _equal(a.cdr, b.cdr)
    return a is b


# ------------------------------------------------------------------ 输出

def b_display(args):
    sys.stdout.write(display_repr(args[0]))
    return None


def b_newline(args):
    sys.stdout.write("\n")
    return None


# ------------------------------------------------------------------ 组装初始环境

def _builtin(name, fn, min_args, max_args=None):
    return name, BuiltinProcedure(name, fn, min_args, max_args)


#: 全部内置过程：(名字, 实现, 最少参数, 最多参数)
_BUILTINS = [
    _builtin("+", b_add, 0),
    _builtin("-", b_sub, 1),
    _builtin("*", b_mul, 0),
    _builtin("/", b_div, 1),
    _builtin("modulo", b_modulo, 2, 2),
    _builtin("quotient", b_quotient, 2, 2),
    _builtin("expt", b_expt, 2, 2),
    _builtin("abs", b_abs, 1, 1),

    _builtin("=", _make_comparison("=", lambda a, b: a == b), 1),
    _builtin("<", _make_comparison("<", lambda a, b: a < b), 1),
    _builtin(">", _make_comparison(">", lambda a, b: a > b), 1),
    _builtin("<=", _make_comparison("<=", lambda a, b: a <= b), 1),
    _builtin(">=", _make_comparison(">=", lambda a, b: a >= b), 1),
    _builtin("not", b_not, 1, 1),

    _builtin("cons", b_cons, 2, 2),
    _builtin("car", b_car, 1, 1),
    _builtin("cdr", b_cdr, 1, 1),
    _builtin("list", b_list, 0),
    _builtin("length", b_length, 1, 1),
    _builtin("append", b_append, 0),
    _builtin("null?", b_null_p, 1, 1),
    _builtin("pair?", b_pair_p, 1, 1),
    _builtin("list?", b_list_p, 1, 1),

    _builtin("number?", b_number_p, 1, 1),
    _builtin("boolean?", b_boolean_p, 1, 1),
    _builtin("symbol?", b_symbol_p, 1, 1),
    _builtin("string?", b_string_p, 1, 1),
    _builtin("procedure?", b_procedure_p, 1, 1),
    _builtin("zero?", b_zero_p, 1, 1),
    _builtin("even?", b_even_p, 1, 1),
    _builtin("odd?", b_odd_p, 1, 1),
    _builtin("eq?", b_eq_p, 2, 2),
    _builtin("equal?", b_equal_p, 2, 2),

    _builtin("display", b_display, 1, 1),
    _builtin("newline", b_newline, 0, 0),
]


def make_global_env():
    """造出初始环境：只装内置过程，不放任何用户变量。"""
    env = Environment()
    for name, procedure in _BUILTINS:
        env.bindings[name] = procedure
    return env
