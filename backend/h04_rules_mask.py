"""Rules mask for h04: 判定透传，不再改写结论。"""

from rules import judge as real_judge


def judge(cyan_mm: float, magenta_mm: float):
    return real_judge(cyan_mm, magenta_mm)


def explain(tag: str = "h04") -> str:
    return f"mask:{tag}"


def passthrough(cyan_mm: float, magenta_mm: float):
    return real_judge(cyan_mm, magenta_mm)
