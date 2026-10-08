# mini-Scheme 解释器

一个用 Python 3 从零实现的 mini-Scheme 解释器，作为浙江大学学生机器人协会 2026 年干事纳新题
3.3.3（程序部分）的作答。

## 运行方式

```bash
python src/main.py 程序1.scm [程序2.scm ...]
python src/main.py            # 不给参数时从标准输入读
```

- 按顺序求值每一个顶层表达式，每个结果独占一行打印；
- 结果为「无值」时（`display`、`newline`、没有 else 分支的 `if`）不打印；
- 多个文件共享同一个全局环境。

## 模块结构

代码按「程序文本 → 表达式 → 值 → 结果」这条流水线拆成职责单一的小模块：

| 模块 | 职责 |
|---|---|
| `lexer.py` | 程序文本 → 词（token）列表 |
| `parser.py` | 词 → 表达式（嵌套点对链） |
| `datatypes.py` | 值类型：符号、点对、空表、闭包等 |
| `printer.py` | 值 → 文本 |
| `environment.py` | 变量绑定表 + 指向外层环境的指针 |
| `primitives.py` | 全部内置过程 |
| `evaluator.py` | 表达式 → 值（8 个特殊形式 + evaluate / apply 互相递归） |
| `main.py` | 入口：读文件或标准输入，逐行打印结果 |

## 实现范围

- **特殊形式**：`quote` `if` `cond` `and` `or` `define` `lambda` `let` `begin`
- **内置过程**：算术、链式比较、列表操作、类型谓词、`eq?` / `equal?`、`display` / `newline`
- **语义要点**：词法作用域与闭包、`and` / `or` 短路、`let` 并行绑定、整数相除得整数商

## 说明

本题按题面要求使用 AI agent 辅助完成编码。具体使用了哪些工具、帮助完成了哪些环节，以及本人对结果
做了哪些检查，见答题文档末尾的说明。
