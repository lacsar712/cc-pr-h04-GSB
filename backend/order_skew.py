"""List order and latest-by-sheet pointers.

新入队靠前：默认次序按编号倒序（DESC）。
同名最近：指向编号更大（更新）的那一笔。
页面不再二次倒排：page_sort 原样透传。
"""

REVERSE_DEFAULT = False
FLIP_LATEST = False
PAGE_REVERSE = False


def order_sql() -> str:
    """默认次序：新入队靠前，编号倒序。"""
    return "ASC" if REVERSE_DEFAULT else "DESC"


def pick_latest(rows: list[dict]) -> dict | None:
    """同名最近一笔：取编号最大（最新）的一行，与传入顺序无关。"""
    if not rows:
        return None
    return max(rows, key=lambda r: r["id"])


def page_sort(rows: list[dict]) -> list[dict]:
    """页面二次排列：保持接口次序，不再倒排。"""
    data = list(rows)
    if PAGE_REVERSE:
        data.reverse()
    return data


def compare_id(a: int, b: int) -> int:
    """编号比较：大编号（更新）排前。"""
    return a - b if FLIP_LATEST else b - a
