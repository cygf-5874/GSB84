交换律、结合律、幂等 —— 这三条是合并的底线，crdtmerge 要满足的是它们。
crdtmerge 是 Python 3 的 CRDT 合并库，只用标准库（unittest 跑用例），没有第三方依赖，
自检走 `scripts/check.sh`（`check/` 是固定验收程序，别改）。

`crdtmerge/` 下三个模块现在都是空壳，只留了签名；`tests/test_crdt.py` 的 12 个用例全红。

任务：按 README「对外契约」的 11 条把它实现出来，让既有用例与固定件全过。

验收：
- python3 -m unittest discover -s tests 退出码 0；
- python3 check/check.py 退出码 0，11 个场景全过（orset 3 + lww 2 + algebra 3 + codec 2 + robust 1）。

约束：
1. 不改 `check/`、不改既有用例的断言；已公开的类与方法签名不变（可新增）。
2. 不引入第三方依赖，只用标准库。
3. 不许用 `random`、`time` 参与结果；结果必须与 `PYTHONHASHSEED` 无关。
4. 不得修改传入的 CRDT 对象（合并必须返回新对象）。
