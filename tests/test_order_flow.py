import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from src.order_flow import Order, OrderRepository, VersionConflict


class OrderFlowTests(unittest.TestCase):
    def test_only_one_simultaneous_action_wins(self):
        repo = OrderRepository(Order("FD-101", "R-04"))
        barrier = Barrier(2)

        def act(target):
            barrier.wait(timeout=5)
            try:
                repo.transition("FD-101", "R-04", 1, target, "Кухня закрыта")
                return "accepted"
            except VersionConflict:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(act, ["Принят", "Отменён"]))
        self.assertCountEqual(result, ["accepted", "conflict"])
        self.assertEqual(repo.get("FD-101").version, 2)

    def test_other_restaurant_cannot_change_order(self):
        repo = OrderRepository(Order("FD-101", "R-04"))
        with self.assertRaises(PermissionError):
            repo.transition("FD-101", "R-09", 1, "Принят")
        self.assertEqual(repo.get("FD-101").version, 1)

    def test_operator_cannot_skip_preparation(self):
        repo = OrderRepository(Order("FD-101", "R-04", "Готовится", 3))
        with self.assertRaises(ValueError):
            repo.transition("FD-101", "R-04", 3, "Доставлен")
        self.assertEqual(repo.get("FD-101").status, "Готовится")

    def test_delivered_order_is_terminal(self):
        repo = OrderRepository(Order("FD-101", "R-04", "Доставлен", 6))
        with self.assertRaises(ValueError):
            repo.transition("FD-101", "R-04", 6, "Принят")

    def test_sms_failure_does_not_change_business_state(self):
        repo = OrderRepository(Order("FD-101", "R-04", "Готов", 4))
        before = repo.get("FD-101")
        self.assertEqual(repo.record_sms_failure("FD-101"), 1)
        self.assertEqual(repo.get("FD-101"), before)


if __name__ == "__main__":
    unittest.main()
