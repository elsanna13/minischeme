"""求值器：表达式 → 值。整个解释器的心脏。

核心是两个**互相递归**的函数：
    evaluate(表达式, 环境)  ——  算出表达式的值
    apply_procedure(过程, 实参)  ——  调用一个过程

evaluate 遇到函数调用就去调 apply_procedure；apply_procedure 执行函数体
又回头调 evaluate。想通这个循环，解释器就成了一半。

特殊形式（quote/if/cond/and/or/define/lambda/let/begin）也在这里，因为
它们的求值顺序和普通函数调用不同——它们自己决定"先算什么、后算什么"。
"""

from datatypes import (
    NIL,
    BuiltinProcedure,
    Closure,
    Pair,
    SchemeError,
    Symbol,
    unpack_list,
)
from printer import write_repr


# ------------------------------------------------------------------ 主循环

def evaluate(expression, env):
    """求值一个表达式。"""
    # 符号 → 去环境里查它的值
    if isinstance(expression, Symbol):
        return env.lookup(expression)

    # 数字、布尔、字符串、空表这些"基本值"原样返回
    if not isinstance(expression, Pair):
        return expression

    # 括号表达式：先看是不是特殊形式（它们不求值参数）
    head = expression.car
    if isinstance(head, Symbol):
        handler = _SPECIAL_FORMS.get(head.name)
        if handler is not None:
            return handler(expression, env)

    # 普通函数调用：先求值操作符，再求值全部实参，最后调用
    procedure = evaluate(head, env)
    arguments = [evaluate(item, env) for item in _operand_expressions(expression)]
    return apply_procedure(procedure, arguments)


def apply_procedure(procedure, arguments):
    """调用一个过程。内置过程直接调；用户函数（闭包）新建一层环境再求值函数体。"""
    if isinstance(procedure, BuiltinProcedure):
        _check_arity(procedure.name, len(arguments), procedure.min_args, procedure.max_args)
        return procedure.fn(arguments)

    if isinstance(procedure, Closure):
        if len(arguments) != len(procedure.params):
            raise SchemeError(
                "%s: 需要 %d 个参数，得到 %d 个"
                % (procedure.name, len(procedure.params), len(arguments))
            )
        # 关键：外层指向函数**定义时**的环境，而不是调用处的环境 —— 这就是闭包。
        call_env = procedure.env.extend(procedure.params, arguments)
        return evaluate_sequence(procedure.body, call_env)

    raise SchemeError("不能调用非过程: %s" % write_repr(procedure))


def evaluate_sequence(expressions, env):
    """按顺序求值一串表达式，返回最后一个的值；空的话返回 None（无值）。"""
    result = None
    for expression in expressions:
        result = evaluate(expression, env)
    return result


# ------------------------------------------------------------------ 辅助

def _operand_expressions(expression):
    """取出调用表达式的实参表达式（不求值）。"""
    operands, tail = unpack_list(expression.cdr)
    if tail is not NIL:
        raise SchemeError("函数调用必须是真列表: %s" % write_repr(expression))
    return operands


def _form_arguments(expression, name):
    """取特殊形式的参数表达式（不求值）。"""
    arguments, tail = unpack_list(expression.cdr)
    if tail is not NIL:
        raise SchemeError("%s: 参数必须是真列表" % name)
    return arguments


def _check_arity(name, given, minimum, maximum):
    if given < minimum:
        raise SchemeError("%s: 至少需要 %d 个参数，得到 %d 个" % (name, minimum, given))
    if maximum is not None and given > maximum:
        raise SchemeError("%s: 至多需要 %d 个参数，得到 %d 个" % (name, maximum, given))


def _check_parameters(parameters, name):
    for parameter in parameters:
        if not isinstance(parameter, Symbol):
            raise SchemeError("%s: 参数名必须是符号，得到 %s" % (name, write_repr(parameter)))


# ------------------------------------------------------------------ 特殊形式
#
# 每个 handler 都自己决定求值顺序，这是最容易出错的地方。

def _form_quote(expression, env):
    """(quote 数据) —— 原样返回，不求值。"""
    arguments = _form_arguments(expression, "quote")
    if len(arguments) != 1:
        raise SchemeError("quote: 需要 1 个参数，得到 %d 个" % len(arguments))
    return arguments[0]


def _form_if(expression, env):
    """(if 测试 真分支 假分支?) —— 只求值一个分支。"""
    arguments = _form_arguments(expression, "if")
    if len(arguments) not in (2, 3):
        raise SchemeError("if: 需要 2 或 3 个参数，得到 %d 个" % len(arguments))
    if evaluate(arguments[0], env) is not False:
        return evaluate(arguments[1], env)
    if len(arguments) == 3:
        return evaluate(arguments[2], env)
    return None


def _form_cond(expression, env):
    """(cond (测试 表达式...) ... (else 表达式...)) —— 多分支，命中即停。"""
    for clause in _form_arguments(expression, "cond"):
        parts, tail = unpack_list(clause)
        if tail is not NIL:
            raise SchemeError("cond: 每个子句必须是真列表")
        if not parts:
            raise SchemeError("cond: 空子句")

        test = parts[0]
        if isinstance(test, Symbol) and test.name == "else":
            # else 是兜底：后面的表达式按 begin 语义依次求值
            return evaluate_sequence(parts[1:], env)

        value = evaluate(test, env)
        if value is not False:
            # 子句里没有表达式时，返回测试值本身
            if len(parts) == 1:
                return value
            return evaluate_sequence(parts[1:], env)

    return None


def _form_and(expression, env):
    """(and e1 e2 ...) —— 从左到右，遇到 #f 立刻返回 #f（短路）。"""
    result = True
    for argument in _form_arguments(expression, "and"):
        result = evaluate(argument, env)
        if result is False:
            return False
    return result


def _form_or(expression, env):
    """(or e1 e2 ...) —— 从左到右，遇到第一个非 #f 就返回它（短路）。"""
    for argument in _form_arguments(expression, "or"):
        result = evaluate(argument, env)
        if result is not False:
            return result
    return False


def _form_define(expression, env):
    """(define 名 表达式) 或 (define (函数名 参数...) 体...)"""
    arguments = _form_arguments(expression, "define")
    if not arguments:
        raise SchemeError("define: 缺少被定义的名字")
    target = arguments[0]

    # 简写形式：(define (square x) (* x x))
    if isinstance(target, Pair):
        name = target.car
        if not isinstance(name, Symbol):
            raise SchemeError("define: 函数名必须是符号")
        parameters, tail = unpack_list(target.cdr)
        if tail is not NIL:
            raise SchemeError("define: 参数表必须是真列表")
        _check_parameters(parameters, "define")
        if len(arguments) < 2:
            raise SchemeError("define: 函数体不能为空")
        env.define(name, Closure(parameters, arguments[1:], env, name.name))
        return name

    if not isinstance(target, Symbol):
        raise SchemeError("define: 被定义的名字必须是符号")
    if len(arguments) != 2:
        raise SchemeError("define: 需要 1 个表达式，得到 %d 个" % (len(arguments) - 1))
    value = evaluate(arguments[1], env)
    if isinstance(value, Closure) and value.name == "lambda":
        value.name = target.name  # 只是为了让报错信息好看
    env.define(target, value)
    return target


def _form_lambda(expression, env):
    """(lambda (参数...) 体...) —— 制造闭包，函数体此时不求值。"""
    arguments = _form_arguments(expression, "lambda")
    if len(arguments) < 2:
        raise SchemeError("lambda: 需要参数表和至少一个函数体表达式")
    parameters, tail = unpack_list(arguments[0])
    if tail is not NIL:
        raise SchemeError("lambda: 参数表必须是真列表")
    _check_parameters(parameters, "lambda")
    # 闭包记住"定义时"的环境 env，而不是调用时的环境
    return Closure(parameters, arguments[1:], env)


def _form_let(expression, env):
    """(let ((名 表达式)...) 体...) —— 并行绑定：所有表达式先在外层环境求值。"""
    arguments = _form_arguments(expression, "let")
    if not arguments:
        raise SchemeError("let: 缺少绑定表和函数体")
    bindings, tail = unpack_list(arguments[0])
    if tail is not NIL:
        raise SchemeError("let: 绑定表必须是真列表")

    names = []
    values = []
    for binding in bindings:
        parts, binding_tail = unpack_list(binding)
        if binding_tail is not NIL or len(parts) != 2:
            raise SchemeError("let: 每个绑定必须写成 (名 表达式)")
        if not isinstance(parts[0], Symbol):
            raise SchemeError("let: 绑定的名字必须是符号")
        names.append(parts[0])
        # 注意：在外层 env 里求值，所以绑定之间互相看不见（并行绑定）
        values.append(evaluate(parts[1], env))

    local_env = env.extend(names, values)
    return evaluate_sequence(arguments[1:], local_env)


def _form_begin(expression, env):
    """(begin e1 e2 ...) —— 依次求值，返回最后一个。"""
    return evaluate_sequence(_form_arguments(expression, "begin"), env)


#: 特殊形式分发表：名字 → 处理函数。
_SPECIAL_FORMS = {
    "quote": _form_quote,
    "if": _form_if,
    "cond": _form_cond,
    "and": _form_and,
    "or": _form_or,
    "define": _form_define,
    "lambda": _form_lambda,
    "let": _form_let,
    "begin": _form_begin,
}
