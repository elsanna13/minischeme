#!/usr/bin/env python3
"""mini-Scheme 解释器入口。

用法（规范 §2）：
    python3 src/main.py file1.scm [file2.scm ...]
    python3 src/main.py            # 没有参数时从标准输入读

约定：
- 按顺序求值每一个顶层表达式，每个结果独占一行打印；
- 结果为 None（无值，比如 display / newline / 没有 else 分支的 if）时不打印；
- 多个文件共享同一个全局环境。
"""

import os
import sys

# 保证无论从哪个目录调用，都能 import 到同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from primitives import make_global_env  # noqa: E402
from datatypes import SchemeError  # noqa: E402
from evaluator import evaluate  # noqa: E402
from parser import parse  # noqa: E402
from printer import write_repr  # noqa: E402


def _configure_streams():
    """统一输入输出为 UTF-8 + \\n。

    Windows 上 Python 的 stdout 默认是 gbk 编码，而且会把 \\n 翻译成 \\r\\n；
    判分器是**逐字节**比对输出，所以这里必须显式固定下来，否则在 Windows 上
    跑出来的结果和 Linux 上不一样。
    """
    for stream, kwargs in (
        (sys.stdout, {"encoding": "utf-8", "newline": "\n"}),
        (sys.stdin, {"encoding": "utf-8"}),
    ):
        try:
            stream.reconfigure(**kwargs)
        except (AttributeError, ValueError, OSError):
            pass  # 流被重定向成不支持 reconfigure 的对象时忽略


def run_source(source, env, out):
    """解析并求值一段源码，把每个顶层结果打印到 out。"""
    # 有些编辑器会把 UTF-8 文件存成带 BOM 的形式，开头多一个 \ufeff，先去掉，
    # 否则它会被当成符号的一部分导致"未绑定的名字"。
    if source.startswith("\ufeff"):
        source = source[1:]
    for expression in parse(source):
        value = evaluate(expression, env)
        if value is not None:
            out.write(write_repr(value) + "\n")


def main(argv):
    _configure_streams()
    # Scheme 的递归比 Python 深，放宽一点避免误报递归过深
    sys.setrecursionlimit(20000)

    env = make_global_env()  # 每个进程一个全新环境，初始为空（只有内置过程）

    try:
        if argv:
            for path in argv:
                with open(path, "r", encoding="utf-8-sig") as handle:
                    run_source(handle.read(), env, sys.stdout)
        else:
            run_source(sys.stdin.read(), env, sys.stdout)
    except SchemeError as error:
        sys.stdout.flush()
        sys.stderr.write("错误: %s\n" % error)
        return 1
    except RecursionError:
        # 规范不要求尾调用优化，递归太深时给一条清楚的提示而不是抛栈回溯
        sys.stdout.flush()
        sys.stderr.write("错误: 递归层数过深（规范不要求尾调用优化）\n")
        return 1
    except OSError as error:
        sys.stderr.write("无法读取文件: %s\n" % error)
        return 1

    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
