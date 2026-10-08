"""mini-Scheme 的值类型定义。

这里只放"数据长什么样"，不放任何求值逻辑。
要点：符号（Symbol）、字符串（Python str）、布尔（bool）、数字（int/float）
必须是**互相区分**的类型，否则 (equal? 'a "a")、(equal? #t 1) 会判错。
"""


class SchemeError(Exception):
    """解释器在运行期发现的错误（未绑定变量、类型不符、参数个数不对等）。"""


class Symbol:
    """符号：一个名字。它可能是变量，也可能是操作符。按名字比较。"""

    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Symbol) and other.name == self.name

    def __hash__(self):
        return hash(("Symbol", self.name))

    def __repr__(self):
        return self.name


_SYMBOL_TABLE = {}


def intern(name):
    """符号驻留：同一个名字永远返回同一个对象，方便 eq? 按同一性比较。"""
    symbol = _SYMBOL_TABLE.get(name)
    if symbol is None:
        symbol = Symbol(name)
        _SYMBOL_TABLE[name] = symbol
    return symbol


class Nil:
    """空表 ()，点对链的终点。全局只有一个实例，所以 (eq? '() '()) 为真。"""

    __slots__ = ()

    def __repr__(self):
        return "()"


#: 空表的唯一实例。
NIL = Nil()


class Pair:
    """点对。列表 (1 2 3) 实际就是 (1 . (2 . (3 . ()))) 这条链。"""

    __slots__ = ("car", "cdr")

    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr


class BuiltinProcedure:
    """解释器自带的函数。参数先全部求值再调用。"""

    __slots__ = ("name", "fn", "min_args", "max_args")

    def __init__(self, name, fn, min_args=0, max_args=None):
        self.name = name
        self.fn = fn
        self.min_args = min_args
        self.max_args = max_args  # None 表示不限


class Closure:
    """用户用 lambda / define 造出来的函数，闭包 = 函数体 + 定义时的环境。"""

    __slots__ = ("params", "body", "env", "name")

    def __init__(self, params, body, env, name="lambda"):
        self.params = params
        self.body = body
        self.env = env
        self.name = name


# ---------------------------------------------------------------- 列表工具

def build_list(items, tail=NIL):
    """把 Python 列表转成点对链，tail 是链尾（默认空表）。"""
    result = tail
    for item in reversed(items):
        result = Pair(item, result)
    return result


def unpack_list(value):
    """把点对链拆成 (元素列表, 链尾)。尾不是空表就说明是"点对"而非真列表。"""
    items = []
    while isinstance(value, Pair):
        items.append(value.car)
        value = value.cdr
    return items, value


def expect_proper_list(value, who):
    """要求 value 是真列表，否则报错；返回元素列表。"""
    items, tail = unpack_list(value)
    if tail is not NIL:
        raise SchemeError("%s: 需要一个真列表，得到 %s" % (who, tail))
    return items


def is_proper_list(value):
    """判断是不是真列表（用快慢指针，同时能识别环形结构）。"""
    slow = fast = value
    while True:
        if fast is NIL:
            return True
        if not isinstance(fast, Pair):
            return False
        fast = fast.cdr
        if fast is NIL:
            return True
        if not isinstance(fast, Pair):
            return False
        fast = fast.cdr
        slow = slow.cdr
        if fast is slow:
            return False


def is_number(value):
    """注意 bool 是 int 的子类，必须先排除，否则 (number? #t) 会判成真。"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)
