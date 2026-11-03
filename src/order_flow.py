"""Учебная модель статусов заказа, атомарная для одного процесса."""
from dataclasses import dataclass, replace
from threading import Lock


class VersionConflict(ValueError):
    pass


@dataclass(frozen=True)
class Order:
    number: str
    restaurant: str
    status: str = "Создан"
    version: int = 1
    cancellation_reason: str = ""


OPERATOR_TRANSITIONS = {
    "Создан": {"Принят", "Отменён"},
    "Принят": {"Готовится", "Отменён"},
    "Готовится": {"Готов", "Отменён"},
    "Готов": {"Передан курьеру", "Отменён"},
    "Передан курьеру": {"Доставлен"},
    "Доставлен": set(),
    "Отменён": set(),
}


class OrderRepository:
    def __init__(self, order: Order):
        self._orders = {order.number: order}
        self._notification_failures = {}
        self._lock = Lock()

    def get(self, number: str) -> Order:
        with self._lock:
            return self._orders[number]

    def transition(self, number: str, restaurant: str, expected_version: int,
                   target: str, reason: str = "") -> Order:
        with self._lock:
            current = self._orders[number]
            if current.restaurant != restaurant:
                raise PermissionError("Заказ принадлежит другому ресторану")
            if current.version != expected_version:
                raise VersionConflict("Перечитайте актуальную версию заказа")
            if target not in OPERATOR_TRANSITIONS[current.status]:
                raise ValueError("Переход из текущего состояния запрещён")
            if target == "Отменён" and not reason.strip():
                raise ValueError("Укажите причину отмены")
            updated = replace(current, status=target, version=current.version + 1,
                              cancellation_reason=reason.strip() if target == "Отменён" else "")
            self._orders[number] = updated
            return updated

    def record_sms_failure(self, number: str) -> int:
        with self._lock:
            if number not in self._orders:
                raise KeyError(number)
            count = self._notification_failures.get(number, 0) + 1
            self._notification_failures[number] = count
            return count
