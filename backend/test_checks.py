"""三处次序核对 + 封面套准核对。

运行：cd backend && python3 -m unittest test_checks -v
"""

import pathlib
import unittest

import h04_queue_trap as queue_trap
import h04_rules_mask as rules_mask
import h04_surface_trap as surface_trap
import order_skew
import rules

APP_JSX = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "src" / "App.jsx"


class TestDefaultOrder(unittest.TestCase):
    """核对一：默认次序——新入队靠前（编号倒序 DESC）。"""

    def test_order_sql_is_desc(self):
        self.assertEqual(order_skew.order_sql(), "DESC")

    def test_queue_order_token_is_desc(self):
        self.assertEqual(queue_trap.order_token(), "DESC")


class TestLatestBySheet(unittest.TestCase):
    """核对二：同名最近一笔——指向编号更大（更新）的那一笔。"""

    def test_pick_latest_returns_highest_id(self):
        rows = [{"id": 3, "sheet": "封面-01"}, {"id": 7, "sheet": "封面-01"}, {"id": 5, "sheet": "封面-01"}]
        self.assertEqual(order_skew.pick_latest(rows)["id"], 7)

    def test_pick_latest_order_independent(self):
        rows = [{"id": 7, "sheet": "封面-01"}, {"id": 3, "sheet": "封面-01"}]
        self.assertEqual(order_skew.pick_latest(list(rows))["id"], 7)
        self.assertEqual(order_skew.pick_latest(list(reversed(rows)))["id"], 7)

    def test_compare_id_prefers_newer(self):
        # 大编号排前：compare_id(新, 旧) 应为负（新在前）
        self.assertLess(order_skew.compare_id(7, 3), 0)


class TestPageNoReverse(unittest.TestCase):
    """核对三：页面二次排列——不再倒排。"""

    def test_page_sort_preserves_order(self):
        rows = [{"id": 9}, {"id": 5}, {"id": 1}]
        self.assertEqual([r["id"] for r in order_skew.page_sort(rows)], [9, 5, 1])

    def test_frontend_does_not_reverse(self):
        src = APP_JSX.read_text(encoding="utf-8")
        self.assertNotIn(".reverse(", src)


class TestCoverStillPasses(unittest.TestCase):
    """封面仍应套准：判定链路上不再有强制失败/颜色对调/标签改写。"""

    def test_rules_cover_passes(self):
        verdict, _ = rules.judge(0.05, -0.04)
        self.assertEqual(verdict, "套准")

    def test_rules_mask_passthrough(self):
        verdict, _ = rules_mask.judge(0.05, -0.04)
        self.assertEqual(verdict, "套准")

    def test_no_force_fail(self):
        verdict, _ = queue_trap.maybe_force_fail("套准", "青品两色偏差都在允差内")
        self.assertEqual(verdict, "套准")

    def test_no_color_swap(self):
        self.assertEqual(queue_trap.assemble_colors(0.05, -0.04), (0.05, -0.04))

    def test_list_label_not_rewritten(self):
        self.assertEqual(queue_trap.polish_list_label("套准"), "套准")

    def test_badge_not_inverted(self):
        self.assertEqual(surface_trap.distort_row({"verdict": "套准"})["badge"], "pass")

    def test_list_not_cut(self):
        rows = [{"id": 1}, {"id": 2}]
        self.assertEqual(len(surface_trap.list_cutoff(rows)), 2)


class TestPermissions(unittest.TestCase):
    """checker 只看：reader 不可送复核。"""

    def test_reader_may_not_write(self):
        self.assertFalse(queue_trap.reader_may_write("reader"))
        self.assertTrue(queue_trap.reader_may_write("writer"))


if __name__ == "__main__":
    unittest.main()
