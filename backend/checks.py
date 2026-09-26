"""三处次序问题的独立核对,外加封面套准回归。

只用标准库即可运行:

    cd backend && python3 checks.py

每一组核对互不影响,全部跑完后汇总;任一项失败则进程退出码非 0。
"""

import sys
from functools import cmp_to_key
from pathlib import Path

import order_skew
import h04_queue_trap as queue_trap
import h04_surface_trap as surface_trap
from rules import judge

BACKEND_DIR = Path(__file__).resolve().parent
API_SRC = (BACKEND_DIR / "api.py").read_text(encoding="utf-8")
APP_SRC = (BACKEND_DIR.parent / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")

failures: list[str] = []


def check(group: str, name: str, ok: bool, detail: str = ""):
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {group} :: {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(f"{group} :: {name} {detail}")


def section(title: str):
    print(f"\n== {title} ==")


# 模拟数据:按入队先后编号 1..3。
QUEUE_ROWS = [{"id": i, "sheet": f"印张-{i:02d}"} for i in range(1, 4)]


# 核对一:默认次序——新入队(更大编号)靠前 ------------------------------
section("一、默认次序:新入队靠前")

check("默认次序", "order_skew.order_sql() 返回 DESC", order_skew.order_sql() == "DESC")
check("默认次序", "REVERSE_DEFAULT 已关闭", order_skew.REVERSE_DEFAULT is False)
check("默认次序", "queue_trap.order_token() 返回 DESC", queue_trap.order_token() == "DESC")
check(
    "默认次序",
    "api 列表次序取自 order_skew.order_sql()",
    "order_skew.order_sql()" in API_SRC and "queue_trap.order_token()" not in API_SRC,
)

desc_rows = sorted(QUEUE_ROWS, key=lambda r: r["id"], reverse=(order_skew.order_sql() == "DESC"))
check("默认次序", "编号 3 的最新入队排在最前", desc_rows[0]["id"] == 3)
check("默认次序", "整表依次为 3,2,1(老编号被顶到上方的问题已消失)", [r["id"] for r in desc_rows] == [3, 2, 1])


# 核对二:同名最近——指向更新(更大)编号 -------------------------------
section("二、同名最近:指向更新编号")

check("同名最近", "FLIP_LATEST 已关闭", order_skew.FLIP_LATEST is False)

# 同名“封面-01”先后入队两笔:老编号 1、新编号 4。
same_name_asc = [
    {"id": 1, "sheet": "封面-01", "verdict": "套准"},
    {"id": 4, "sheet": "封面-01", "verdict": "套不准"},
]
latest = order_skew.pick_latest(same_name_asc)
check("同名最近", "pick_latest 指向更新编号 4(而非更老的 1)", latest is not None and latest["id"] == 4)
check("同名最近", "pick_latest 空表返回 None", order_skew.pick_latest([]) is None)

# compare_id 排序时同样要把更新编号排在最前。
ordered = sorted(same_name_asc, key=cmp_to_key(lambda a, b: order_skew.compare_id(a["id"], b["id"])))
check("同名最近", "compare_id 排序时更新编号居前", ordered[0]["id"] == 4)
check("同名最近", "compare_id 排序时更老编号垫后", ordered[-1]["id"] == 1)
check(
    "同名最近",
    "api 提供 /api/jobs/latest 并使用 pick_latest",
    "/api/jobs/latest" in API_SRC and "order_skew.pick_latest" in API_SRC,
)


# 核对三:页面二次排列——不再倒排 --------------------------------------
section("三、页面排列:勿再倒排")

check("页面排列", "PAGE_REVERSE 已关闭", order_skew.PAGE_REVERSE is False)
paged = order_skew.page_sort(desc_rows)
check("页面排列", "page_sort 保持接口次序 3,2,1(不翻成 1,2,3)", [r["id"] for r in paged] == [3, 2, 1])
check(
    "页面排列",
    "App.jsx 加载后不再 reverse() 二次倒排",
    "[...data].reverse()" not in APP_SRC and ".reverse()" not in APP_SRC,
)
check("页面排列", "App.jsx 直接按接口顺序 setRows", "setRows(data)" in APP_SRC)


# 回归:封面仍应套准 ----------------------------------------------------
section("回归:封面-01 仍应套准")

v, r = judge(0.05, -0.04)
check("封面套准", "规则判定(0.05,-0.04)为套准", v == "套准", f"实际:{v}/{r}")

c, m = queue_trap.assemble_colors(0.05, -0.04)
check("封面套准", "入队颜色不再青品互换", (c, m) == (0.05, -0.04), f"实际:({c},{m})")

v2, r2 = queue_trap.maybe_force_fail(*judge(c, m))
check("封面套准", "worker 旁路不再强制失败", v2 == "套准", f"实际:{v2}/{r2}")
check("封面套准", "FORCE_FAIL 已关闭", queue_trap.FORCE_FAIL is False)
check("封面套准", "SWAP_COLORS 已关闭", queue_trap.SWAP_COLORS is False)
check("封面套准", "列表标签不再把套准洗成套不准", queue_trap.polish_list_label("套准") == "套准")

# surface 侧不得再丢行、补幻影行、藏原因。
rows_in = [{"id": 1, "verdict": "套准", "reason": "青品两色偏差都在允差内", "cyan_mm": 0.05}]
check("封面套准", "distort_rows 行数不变(无幻影行)", len(surface_trap.distort_rows(rows_in)) == 1)
check("封面套准", "list_cutoff 不再砍掉首行", len(surface_trap.list_cutoff(rows_in)) == 1)
check("封面套准", "footnote 保留判定原因", surface_trap.footnote("套准", rows_in[0]["reason"]) == rows_in[0]["reason"])

# 权限:checker(reader)仍不得送复核。
check("权限", "reader 不可写、writer 可写",
      queue_trap.reader_may_write("reader") is False and queue_trap.reader_may_write("writer") is True)


print("\n" + "=" * 48)
if failures:
    print(f"共 {len(failures)} 项核对未通过:")
    for f in failures:
        print("  - " + f)
    sys.exit(1)
print("全部核对通过。")
