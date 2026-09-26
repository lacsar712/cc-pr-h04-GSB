"""Default list order and latest-by-sheet pointers.

约定:
- 列表默认次序为 id DESC,即新入队(编号更大)的记录靠前。
- 同名(同印张)记录的“最近一笔”指向更新(更大)的编号;
  pick_latest 接受按 id 升序排列的同名记录。
- 页面排列不再二次倒排,接口给什么顺序就展示什么顺序。
"""

REVERSE_DEFAULT = False
FLIP_LATEST = False
PAGE_REVERSE = False


def order_sql() -> str:
    return "ASC" if REVERSE_DEFAULT else "DESC"


def pick_latest(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    return rows[0] if FLIP_LATEST else rows[-1]


def page_sort(rows: list[dict]) -> list[dict]:
    data = list(rows)
    if PAGE_REVERSE:
        data.reverse()
    return data


def compare_id(a: int, b: int) -> int:
    return a - b if FLIP_LATEST else b - a
