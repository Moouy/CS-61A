# CS 61A

**重点是把握代码执行时，机器环境实际发生了什么变化。**

[YouTube原视频链接](https://www.youtube.com/playlist?list=PLHODd-fpPyMC5Mho6PIjIGsGgBW_syyHi) Bili有AI翻译版本体验更好。[pythontutor](https://pythontutor.com/cp/composingprograms.html#mode=edit)用于观察代码执行时机器实际的行为。

---

函数的执行，会创建新的环境stack。

`def` 函数只有被调用的时候才开始执行。1. 先会插件一个环境。2. 传入`value`会绑定`formal value`

2 - Names, Assignment, and User-Defined Functions
`赋值语句` 的特点在于不绑定 `数据源`，不跟随其变化而发生变化，是固定的；`function` 则相反，是灵活跟随变量的。

5 - Print and None
Pure Functions & Non-Pure Functions

7 - Multiple Environments
environment is a ==sequence== of frames.
frames is a ==binding== between names and values.
函数在执行的时候，查找顺序是先查找当前环境，再进入父级stack frames。

9 - Conditional Statements
Boolean context 关注真值。
从前到后的查找第一个真值并执行；else是真值。

10 - lteration, repeating things, 重复操作

11 - Control Statements
Control statements: `if`, `while`, 决定跳过或者执行。
Functions: `print()`, `abs()`, 全部执行后返回。
控制语句`if` `while` 会选择执行和跳过代码。
调用表达式（函数） 不允许跳过任何参数的求值。所以会因为参数的求值错误而报错。

12 - Control Expressions
`and`, `or`, 得到结果立刻返回，所以`error`还没发生就已经结束了计算。

## Higher_Order Functions

13 - Higher-Order Functions
高阶函数，体现了通用的处理模式，泛化处理, 消除重复；我们可以关注函数之间实现关注点分离。不仅对 `数字` 层面抽象，也可以对 `计算过程` 。
`assert` 用于返回报错和提醒。

14 - Functions as Return Values

⭐16 - Environments for Nested Definitions
⭐17 - Local Names

19 - Lambda
单个表达式的快速写法
`def`, `lambda` 差异在内部名称上

⭐20 - Function Currying
就是将多参数`func` 转换成单参`func` 的过程

22 - Lambda Function Environments
23 - Abstraction
24 - Errors & Tracebacks
语法错误、运行时错误、逻辑错误
解释器发现错误，真正的错误在附近

⭐⭐⭐闭包是函数把它定义时所在作用域里的变量一起“带走”的现象。
`def` 先创建函数，再把名称和函数进行`binding`

⭐⭐⭐25 - Midterm 1 Review

⭐27 - Decorators
高阶函数、闭包、装饰器

## Recursion

28 - Recursive Functions
29 - Recursion in Environments Diagrams
31 - Mutual Recursion

33 - List
34 - Containers
35 - Range
37 - Box-and-Pointer Notation

95 - Measuring Efficiency

```python
def fib(n):
    if n == 0 or n == 1:
        return n
    else:
        return fib(n-2) + fib(n-1)
        
def count(f):
    def counted(n):
        counted.call_count += 1
        return f(n)
    counted.call_count = 0
    return counted

fib = count(fib)
fib(5)
```
