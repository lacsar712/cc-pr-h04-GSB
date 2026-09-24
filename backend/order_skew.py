"""Reverse list order and latest-by-sheet pointers."""

REVERSE_DEFAULT = True
FLIP_LATEST = True
PAGE_REVERSE = True


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
