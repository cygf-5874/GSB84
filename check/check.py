#!/usr/bin/env python3
"""Fixed acceptance checks for the crdtmerge task.

Scenarios (11): orset 3 + lww 2 + algebra 3 + codec 2 + robust 1.
The file is part of the fixed judge and must not be edited by the solver.
"""

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from crdtmerge import LWWRegister, ORSet, load, merge, state  # noqa: E402
from crdtmerge.errors import CorruptState  # noqa: E402


# --------------------------------------------------------------------------
# scenario helpers
# --------------------------------------------------------------------------

def _verdict(ok, expected, actual):
    return (bool(ok), expected, actual)


def _show(value):
    return repr(value)


# --------------------------------------------------------------------------
# orset group
# --------------------------------------------------------------------------

def scenario_orset_concurrent_add():
    a = ORSet("A")
    a.add("x")
    b = merge(ORSet("B"), a)
    b.add("x")
    a = merge(a, ORSet("A"))
    a.remove("x")
    c = merge(a, b)
    got = set(c.elements())
    return _verdict("x" in got, "含 x", _show(sorted(got, key=repr)))


def scenario_orset_observed_removed():
    a = ORSet("A")
    a.add("x")
    b = merge(ORSet("B"), a)
    a.remove("x")
    c = merge(a, b)
    got = set(c.elements())
    return _verdict("x" not in got, "不含 x", _show(sorted(got, key=repr)))


def scenario_orset_global_counter():
    s = ORSet("A")
    s.add("x")
    s.add("y")
    s.remove("x")
    got = set(s.elements())
    return _verdict(got == {"y"}, "['y']", _show(sorted(got, key=repr)))


# --------------------------------------------------------------------------
# lww group
# --------------------------------------------------------------------------

def scenario_lww_ts_then_replica():
    a = LWWRegister("A")
    a.set("va", 5)
    b = LWWRegister("B")
    b.set("vb", 5)
    ab = merge(a, b).value()
    ba = merge(b, a).value()
    hi = LWWRegister("A")
    hi.set("high", 9)
    lo = LWWRegister("B")
    lo.set("low", 1)
    top = merge(hi, lo).value()
    ok = ab == "vb" and ba == "vb" and top == "high"
    return _verdict(ok, "vb / vb / high", f"{ab} / {ba} / {top}")


def scenario_lww_same_ts_determinism():
    r = LWWRegister("A")
    r.set("first", 7)
    r.set("second", 7)
    sequential = r.value()
    a = LWWRegister("A")
    a.set("p", 3)
    b = LWWRegister("A")
    b.set("q", 3)
    ab = merge(a, b).value()
    ba = merge(b, a).value()
    ok = sequential in ("first", "second") and ab == ba
    return _verdict(ok, "确定性取值", f"{sequential} / {ab} / {ba}")


# --------------------------------------------------------------------------
# algebra group (fixed order table, no random)
# --------------------------------------------------------------------------

def _algebra_states():
    a = ORSet("A")
    a.add("x")
    b = ORSet("B")
    b.add("x")
    b.add("y")
    c = ORSet("C")
    c.add("y")
    c.remove("y")
    c.add("z")
    return [a, b, c]


# every permutation of the three states, written out explicitly
MERGE_PATHS = (
    (0, 1, 2),
    (0, 2, 1),
    (1, 0, 2),
    (1, 2, 0),
    (2, 0, 1),
    (2, 1, 0),
)


def scenario_algebra_commutative():
    a, b, _ = _algebra_states()
    ab = state(merge(a, b))
    ba = state(merge(b, a))
    ok = ab == ba
    return _verdict(ok, "逐字节相同", "相同" if ok else "不同")


def scenario_algebra_associative():
    states = _algebra_states()
    blobs = set()
    for path in MERGE_PATHS:
        acc = states[path[0]]
        for idx in path[1:]:
            acc = merge(acc, states[idx])
        blobs.add(state(acc))
    ok = len(blobs) == 1
    return _verdict(ok, "全部路径收敛为 1 种结果", f"{len(blobs)} 种")


def scenario_algebra_idempotent():
    a, b, c = _algebra_states()
    checks = (
        state(merge(a, a)) == state(a),
        state(merge(b, b)) == state(b),
        state(merge(c, c)) == state(c),
    )
    ok = all(checks)
    return _verdict(ok, "merge(x,x) == x", "全部成立" if ok else _show(checks))


# --------------------------------------------------------------------------
# codec group (state bytes compared across PYTHONHASHSEED values)
# --------------------------------------------------------------------------

class _Child(object):
    def __init__(self, ok, out, err):
        self.ok = ok
        self.out = out
        self.err = err


def _run_child(kind, seed):
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = seed
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = REPO_ROOT + (os.pathsep + prev if prev else "")
    cmd = [sys.executable or "python3", os.path.abspath(__file__), "--emit", kind]
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=120,
        )
    except Exception as exc:  # pragma: no cover - environmental failure
        return _Child(False, "", repr(exc))
    return _Child(proc.returncode == 0, proc.stdout.strip(), proc.stderr.strip())


def _codec_compare(kind):
    first = _run_child(kind, "0")
    second = _run_child(kind, "1")
    if not first.ok or not second.ok:
        detail = (first.err or second.err or "子进程失败").splitlines()[-1:]
        return _verdict(False, "两次子进程均成功", detail[0] if detail else "子进程失败")
    if not first.out:
        return _verdict(False, "非空状态字节", "空输出")
    ok = first.out == second.out
    return _verdict(ok, "两个 PYTHONHASHSEED 下逐字节相同", "相同" if ok else "不同")


def scenario_codec_canonical():
    return _codec_compare("canonical")


def scenario_codec_roundtrip():
    return _codec_compare("roundtrip")


# --------------------------------------------------------------------------
# robust group
# --------------------------------------------------------------------------

def scenario_robust_reject_corrupt():
    s = ORSet("A")
    s.add("x")
    s.add("y")
    s.remove("x")
    blob = state(s)
    bad_blobs = (
        b"",
        blob[:-1],
        blob[: len(blob) // 2],
        b"\xff" * len(blob),
    )
    problems = []
    for bad in bad_blobs:
        try:
            load(bad)
            problems.append("未拒绝")
        except CorruptState:
            pass
        except Exception as exc:
            problems.append(type(exc).__name__)
    ok = not problems
    return _verdict(ok, "全部抛 CorruptState", "全部拒绝" if ok else _show(problems))


SCENARIOS = (
    ("orset", "concurrent-add-survives", scenario_orset_concurrent_add),
    ("orset", "observed-tag-removed", scenario_orset_observed_removed),
    ("orset", "global-counter", scenario_orset_global_counter),
    ("lww", "ts-then-replica", scenario_lww_ts_then_replica),
    ("lww", "same-ts-determinism", scenario_lww_same_ts_determinism),
    ("algebra", "commutative", scenario_algebra_commutative),
    ("algebra", "associative", scenario_algebra_associative),
    ("algebra", "idempotent", scenario_algebra_idempotent),
    ("codec", "canonical-bytes", scenario_codec_canonical),
    ("codec", "roundtrip-identity", scenario_codec_roundtrip),
    ("robust", "reject-corrupt", scenario_robust_reject_corrupt),
)


# --------------------------------------------------------------------------
# child mode: emit deterministic state bytes for cross-seed comparison
# --------------------------------------------------------------------------

def _emit_canonical():
    s1 = ORSet("A")
    for elem in ("x", "y", "z"):
        s1.add(elem)
    s1.remove("y")
    s2 = ORSet("B")
    for elem in ("z", "x"):
        s2.add(elem)
    r1 = LWWRegister("A")
    r1.set("v", 5)
    r2 = LWWRegister("B")
    r2.set("w", 5)
    return (
        state(merge(s1, s2))
        + state(merge(s2, s1))
        + state(merge(r1, r2))
        + state(merge(r2, r1))
    )


def _emit_roundtrip():
    objs = []
    s = ORSet("A")
    s.add("x")
    s.add("y")
    s.remove("x")
    objs.append(s)
    s2 = ORSet("副本一")
    s2.add("汉字")
    objs.append(s2)
    r = LWWRegister("A")
    r.set("v", 3)
    objs.append(r)
    objs.append(LWWRegister("B"))
    out = b""
    for obj in objs:
        blob = state(obj)
        back = state(load(blob))
        if back != blob:
            raise ValueError("load∘state 不是恒等")
        out += back
    return out


def _emit(kind):
    try:
        if kind == "canonical":
            payload = _emit_canonical()
        elif kind == "roundtrip":
            payload = _emit_roundtrip()
        else:
            return 2
    except Exception:
        return 3
    sys.stdout.write(payload.hex())
    return 0


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(prog="check.py")
    parser.add_argument("-list", dest="list_scenarios", action="store_true",
                        help="列出全部场景后退出")
    parser.add_argument("--only", dest="only", default=None,
                        help="只运行指定组")
    parser.add_argument("--emit", dest="emit", default=None,
                        help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.emit is not None:
        return _emit(args.emit)

    if args.list_scenarios:
        for group, name, _func in SCENARIOS:
            print(f"{group}/{name}")
        return 0

    selected = [s for s in SCENARIOS if args.only is None or s[0] == args.only]
    passed = 0
    for group, name, func in selected:
        try:
            ok, expected, actual = func()
        except NotImplementedError:
            ok, expected, actual = False, "已实现", "NotImplementedError"
        except Exception as exc:
            ok, expected, actual = False, "无异常", f"{type(exc).__name__}: {exc}"
        if ok:
            passed += 1
            print(f"PASS {group}/{name}")
        else:
            print(f"FAIL {group}/{name}  期望={expected} 实际={actual}")

    print(f"结果：通过 {passed}/{len(selected)}")
    return 0 if selected and passed == len(selected) else 1


if __name__ == "__main__":
    sys.exit(main())
