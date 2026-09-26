"""api.py 端点级集成核对:顶替第三方依赖,直接驱动真实端点函数。

环境里没有 fastapi/psycopg 也能运行(标准库即可):

    cd backend && python3 checks_api.py

覆盖:
- 默认次序:list_jobs 组合的 SQL 以 ORDER BY id DESC 收尾,返回新入队靠前;
- 同名最近:/api/jobs/latest 对同名记录指向更新编号;
- 页面次序:page_sort 直通不倒排;
- 回归:封面-01 经 worker 同款管线仍判套准;checker 不可送复核。
"""

import sys
import types
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

DB: list[dict] = []
SQL_LOG: list[str] = []


# ---- 假 psycopg:内存版 jobs 表,按真实 SQL 语义应答 --------------------
class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def commit(self):
        pass

    def execute(self, sql, params=None):
        s = " ".join(sql.split())
        SQL_LOG.append(s)
        if s.startswith("CREATE TABLE"):
            return FakeResult([])
        if "COUNT(*)" in s:
            return FakeResult([{"n": len(DB)}])
        if s.startswith("INSERT INTO jobs") and "RETURNING" in s:
            sheet, cyan, magenta, user, now = params
            row = {
                "id": max((r["id"] for r in DB), default=0) + 1,
                "sheet": sheet,
                "cyan_mm": cyan,
                "magenta_mm": magenta,
                "status": "pending",
                "verdict": "",
                "reason": "",
                "created_by": user,
                "created_at": now,
            }
            DB.append(row)
            return FakeResult([dict(row)])
        if s.startswith("INSERT INTO jobs"):
            now1, now2 = params
            DB.append({"id": 1, "sheet": "封面-01", "cyan_mm": 0.05, "magenta_mm": -0.04,
                       "status": "pending", "verdict": "", "reason": "", "created_by": "printer", "created_at": now1})
            DB.append({"id": 2, "sheet": "内页-09", "cyan_mm": 0.40, "magenta_mm": 0.02,
                       "status": "pending", "verdict": "", "reason": "", "created_by": "printer", "created_at": now2})
            return FakeResult([])
        if "WHERE sheet = %s" in s:
            rows = sorted((r for r in DB if r["sheet"] == params[0]), key=lambda r: r["id"])
            return FakeResult([dict(r) for r in rows])
        if "ORDER BY id" in s:
            rows = sorted(DB, key=lambda r: r["id"], reverse=("DESC" in s.upper()))
            return FakeResult([dict(r) for r in rows])
        raise AssertionError(f"未预期的 SQL: {s}")


psycopg = types.ModuleType("psycopg")
psycopg.connect = lambda dsn, row_factory=None: FakeConn()
psycopg_rows = types.ModuleType("psycopg.rows")
psycopg_rows.dict_row = dict
psycopg.rows = psycopg_rows

fastapi = types.ModuleType("fastapi")


class HTTPException(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class FastAPI:
    def __init__(self, **kw):
        pass

    def on_event(self, *a, **k):
        return lambda f: f

    def get(self, *a, **k):
        return lambda f: f

    def post(self, *a, **k):
        return lambda f: f


fastapi.FastAPI = FastAPI
fastapi.Depends = lambda dep=None: dep
fastapi.HTTPException = HTTPException

fastapi_security = types.ModuleType("fastapi.security")
fastapi_security.HTTPAuthorizationCredentials = type("HTTPAuthorizationCredentials", (), {})
fastapi_security.HTTPBearer = lambda **kw: None

jose = types.ModuleType("jose")
jose.JWTError = type("JWTError", (Exception,), {})
jose.jwt = types.SimpleNamespace(encode=lambda *a, **k: "tok", decode=lambda *a, **k: {})

passlib = types.ModuleType("passlib")
passlib_context = types.ModuleType("passlib.context")
passlib_context.CryptContext = lambda **kw: types.SimpleNamespace(
    hash=lambda p: "h:" + p, verify=lambda p, h: h == "h:" + p
)

pydantic = types.ModuleType("pydantic")


class BaseModel:
    def __init__(self, **kw):
        self.__dict__.update(kw)


pydantic.BaseModel = BaseModel

sys.modules.update(
    {
        "psycopg": psycopg,
        "psycopg.rows": psycopg_rows,
        "fastapi": fastapi,
        "fastapi.security": fastapi_security,
        "jose": jose,
        "passlib": passlib,
        "passlib.context": passlib_context,
        "pydantic": pydantic,
    }
)

import api  # noqa: E402  真实被测模块
import h04_queue_trap as queue_trap  # noqa: E402
from rules import judge  # noqa: E402

failures: list[str] = []


def check(group, name, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {group} :: {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(f"{group} :: {name} {detail}")


def expect_http(group, name, status, fn, *args):
    try:
        fn(*args)
    except HTTPException as exc:
        check(group, name, exc.status_code == status, f"实际状态码 {exc.status_code}")
    else:
        check(group, name, False, "未抛出预期异常")


# ---- 启动 + 种子 -------------------------------------------------------
api.startup()
check("准备", "种子写入封面-01/内页-09", [r["sheet"] for r in DB] == ["封面-01", "内页-09"])

# ---- 核对一:默认次序,新入队靠前 --------------------------------------
print("\n== 一、默认次序(端点级) ==")
rows = api.list_jobs(None)
check("默认次序", "列表接口新入队靠前(2,1)", [r["id"] for r in rows] == [2, 1])
list_sql = next(s for s in reversed(SQL_LOG) if "FROM jobs ORDER BY id" in s)
check("默认次序", "列表 SQL 以 ORDER BY id DESC 收尾", list_sql.endswith("ORDER BY id DESC"), list_sql)

writer = {"username": "printer", "role": "writer"}
api.enqueue(api.JobIn(sheet="封面-01", cyan_mm=0.05, magenta_mm=-0.04), writer)
api.enqueue(api.JobIn(sheet="封面-01", cyan_mm=0.50, magenta_mm=0.02), writer)
rows = api.list_jobs(None)
check("默认次序", "再入队两笔后次序为 4,3,2,1", [r["id"] for r in rows] == [4, 3, 2, 1])
check("默认次序", "无幻影行、无丢行", len(rows) == 4 and all(r["id"] > 0 for r in rows))

# ---- 核对二:同名最近,指向更新编号 ------------------------------------
print("\n== 二、同名最近(端点级) ==")
latest = api.latest_job("封面-01", None)
check("同名最近", "同名三笔时最近一笔是编号 4", latest["id"] == 4)
check("同名最近", "最近一笔内容确为新入队那条(青 0.5)", latest["cyan_mm"] == 0.50)
expect_http("同名最近", "查无此印张返回 404", 404, api.latest_job, "不存在-99", None)
expect_http("同名最近", "空印张名返回 400", 400, api.latest_job, "   ", None)

# ---- 核对三:页面排列,不再倒排 ----------------------------------------
print("\n== 三、页面排列(端点级) ==")
paged = api.order_skew.page_sort(rows)
check("页面排列", "page_sort 直通不倒排(仍 4,3,2,1)", [r["id"] for r in paged] == [4, 3, 2, 1])

# ---- 回归:封面仍应套准 + 权限 ----------------------------------------
print("\n== 回归:封面套准 / 权限 ==")
seed = next(r for r in DB if r["id"] == 1)
c, m = queue_trap.assemble_colors(seed["cyan_mm"], seed["magenta_mm"])
verdict, _ = queue_trap.maybe_force_fail(*judge(c, m))
check("封面套准", "封面-01 经 worker 同款管线判为套准", verdict == "套准", f"实际:{verdict}")

stored = next(r for r in DB if r["id"] == 4)
check("封面套准", "入库存放青品未互换", (stored["cyan_mm"], stored["magenta_mm"]) == (0.50, 0.02))

expect_http("权限", "checker(reader)送复核被拒 403", 403, api.require_writer, {"username": "checker", "role": "reader"})
check("权限", "printer(writer)可送复核", api.require_writer(writer) is writer)
expect_http("权限", "空白印张名被拒 400", 400, api.enqueue, api.JobIn(sheet="   ", cyan_mm=0.0, magenta_mm=0.0), writer)


print("\n" + "=" * 48)
if failures:
    print(f"共 {len(failures)} 项核对未通过:")
    for f in failures:
        print("  - " + f)
    sys.exit(1)
print("端点级核对全部通过。")
