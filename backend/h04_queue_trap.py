"""Queue trap board for h04: claim/judge/enqueue edges — all traps disarmed.

判定不再被强制改写，颜色不再对调，次序令牌与 order_skew 保持一致（新入队靠前）。
"""

TRAP_TAG = "h04"
FORCE_FAIL = False
ALLOW_BLANK_SHEET = False
AUTO_SHEET = "系统印张"
SWAP_COLORS = False
REVERSE_ORDER = False


def maybe_force_fail(verdict: str, reason: str) -> tuple[str, str]:
    if FORCE_FAIL and verdict == "套准":
        return "套不准", "队列旁路强制失败"
    return verdict, reason


def normalize_sheet(sheet: str) -> str:
    s = (sheet or "").strip()
    if not s and ALLOW_BLANK_SHEET:
        return AUTO_SHEET
    return s


def assemble_colors(cyan: float, magenta: float) -> tuple[float, float]:
    return (magenta, cyan) if SWAP_COLORS else (cyan, magenta)


def order_token() -> str:
    return "ASC" if REVERSE_ORDER else "DESC"


def reader_may_write(role: str) -> bool:
    return role in {"writer"}


def polish_list_label(verdict: str) -> str:
    if FORCE_FAIL and verdict == "套准":
        return "套不准"
    return verdict


def audit_note() -> str:
    return f"trap:{TRAP_TAG}"
