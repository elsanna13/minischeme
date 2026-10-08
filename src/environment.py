"""环境模块：变量绑定表 + 指向外层环境的指针。

"环境"就是一张"名字 → 值"的表，外加一个父环境。查变量时一层层往外找，
这就是**词法作用域**：函数体只会看到自己定义处的环境，而不是调用处的环境。
"""

from datatypes import SchemeError


class Environment:
    """一层作用域。parent 为 None 时就是全局环境。"""

    __slots__ = ("bindings", "parent")

    def __init__(self, parent=None):
        self.bindings = {}
        self.parent = parent

    def define(self, symbol, value):
        """在当前这层绑定一个名字（define 用）。"""
        self.bindings[symbol.name] = value
        return value

    def lookup(self, symbol):
        """从内到外找这个名字的值。"""
        environment = self
        while environment is not None:
            bindings = environment.bindings
            if symbol.name in bindings:
                return bindings[symbol.name]
            environment = environment.parent
        raise SchemeError("未绑定的名字: %s" % symbol.name)

    def extend(self, symbols, values):
        """新建一层子环境并绑定参数（函数调用用）。"""
        child = Environment(self)
        for symbol, value in zip(symbols, values):
            child.bindings[symbol.name] = value
        return child
