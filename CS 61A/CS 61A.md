

## Primary 

  
==分析机器执行的步骤逻辑。和滴水逆向的课程一样，学习编程语言要掌握机器操作层面（汇编）中实际的工作逻辑。==

Frames & Objects
形参 `formal value` & 实参。

https://pythontutor.com/cp/composingprograms.html#mode=edit

函数的执行，会创建新的环境stack



---


2.2 `赋值语句` 的特点在于不绑定 `数据源`，不跟随其变化而发生变化，是固定的；`function` 则相反，是灵活跟随变量的。

2.5 Pure Functions & Non-Pure Functions
![](<non-pure function.png>)

3.1 Multiple Environments
environment is a ==sequence== of frames.
frames is a ==binding== between names and values.
函数在执行的时候，查找顺序是先查找当前环境，再进入父级stack frames。

3.2 Conditional Statements
Boolean context 关注真值。
从前到后的查找第一个真值并执行；else是真值。

3.3 lteration, repeating things, 重复操作

4.2 Control Statements
Control statements: `if`, `while`, 决定跳过或者执行。
Functions: `print()`, `abs()`, 全部执行后返回。
控制语句`if` `while` 会选择执行和跳过代码。 
调用表达式（函数） 不允许跳过任何参数的求值。所以会因为参数的求值错误而报错。


4.3 Control Expreesions
`and`, `or`, 得到结果立刻返回，所以`error`还没发生就已经结束了计算。

## Higher_Order Functions

4.4 Higher-Order Functions
高阶函数，体现了通用的处理模式，泛化处理, 消除重复；我们可以关注函数之间实现关注点分离。
不仅对 `数字` 层面抽象，也可以对 `计算过程` 。
`assert` 用于返回报错和提醒。

4.5
函数作为返回值。

5.1 高阶函数的环境图
!!! 5.2 Environments for Nested Definitions
!!! 5.3 Local Names

![](<Nested and Local.png>)

5.4 
5.5 Lambda 单个表达式的快速写法
`def`, `lambda` 差异在内部名称上

\!!! 5.6 Currying 就是将多参数`func` 转换成单参`func` 的过程
\!!! 6.1 
6.2 Lambda Function Environments
6.3 Abstraction




