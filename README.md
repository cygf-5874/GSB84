# crdtmerge · 对外契约

`crdtmerge` 是 Python 3 的 CRDT 合并库，只用标准库（`unittest` 跑用例），无第三方依赖。
`crdtmerge/` 下四个模块现在是空壳（签名齐全、方法体一律 `raise NotImplementedError`），
`tests/test_crdt.py` 的 12 个用例全红。自检走 `scripts/check.sh`（`check/` 是固定验收程序，别改）。

## 对外契约（11 条）

1. `ORSet(replica: str)`：`add(elem)`、`remove(elem)`、`elements() -> frozenset`；
   内部标签是 `(replica, counter)`，`counter` 是该副本内**全局单调递增**的整数
   （不是每元素各自计数）；
2. `remove` 只移除**本副本已观察到的**标签；未观察到的并发 `add` 必须在合并后存活
   （add-wins 语义）；
3. `LWWRegister(replica: str)`：`set(value, ts: int)`、`value()`；
   比较键是 `(ts, replica)`，`replica` 用**字典序**裁决并列（保证交换律）；
4. `merge(a, b)` 对同一个副本类型返回**新对象**，两个入参**不得被修改**（深度不变）；
5. 合并必须满足**交换律、结合律、幂等**三条：对任意 3 个状态与任意合并顺序，
   `state()` 的输出逐字节相同；
6. `state()` 返回**规范形式**的 `bytes`：同一语义状态的序列化结果必须逐字节相同 ——
   标签、元素、副本名一律按确定规则排序后再编码，长度前缀必须自描述；
7. `load(blob: bytes) -> obj` 与 `state()` 互逆（`load(state())` 后 `state()` 逐字节相同）；
8. `load` 必须拒绝被截断的、长度前缀超界的、含未知类型标记的输入 → `CorruptState`
   （不得 `IndexError` / `struct.error` / `UnicodeDecodeError` 泄漏出来）；
9. 三个或更多副本按任意顺序两两合并，最终状态必须收敛（固定件用**固定顺序表**遍历合并路径，
   不用随机数）；
10. 边界：空集合、空注册表、副本名含非 ASCII、并发 `set` 同一 `ts`、`add` 后立刻 `remove`
    都不得抛异常；`replica` 为空串 → `ValueError`；
11. 结果不依赖 `dict` 迭代顺序与 `PYTHONHASHSEED`（固定件在子进程里用不同的
    `PYTHONHASHSEED` 各跑一次比对）。

## 公开接口

```python
from crdtmerge import ORSet, LWWRegister, merge, state, load
from crdtmerge.errors import CorruptState, CrdtError
```

## 验收

```bash
python3 -m unittest discover -s tests   # 退出码 0
python3 check/check.py                   # 退出码 0，11 个场景全过
```
