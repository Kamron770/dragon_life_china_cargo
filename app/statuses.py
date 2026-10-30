"""Cargo statuses, their labels and who may set them."""

WAITING = "waiting"
AT_CHINA = "at_china"
SENT = "sent_from_china"
AT_UZ = "arrived_uz"
DELIVERED = "delivered"

ORDER = [WAITING, AT_CHINA, SENT, AT_UZ, DELIVERED]
INACTIVE = {DELIVERED}
ACTIVE = [s for s in ORDER if s not in INACTIVE]

LABELS = {
    "uz": {
        WAITING: "⏳ Xitoydagi omborga kelishi kutilmoqda",
        AT_CHINA: "🏬 Xitoydagi omborga yetib keldi",
        SENT: "🚚 Xitoydan jo'natildi (yo'lda)",
        AT_UZ: "🇺🇿 O'zbekistonga yetib keldi (Toshkent ombori)",
        DELIVERED: "✅ Mijozga topshirildi",
    },
    "ru": {
        WAITING: "⏳ Ожидается поступление на склад в Китае",
        AT_CHINA: "🏬 Прибыл на склад в Китае",
        SENT: "🚚 Отправлен из Китая (в пути)",
        AT_UZ: "🇺🇿 Прибыл в Узбекистан (склад в Ташкенте)",
        DELIVERED: "✅ Выдан клиенту",
    },
}

# Short colour class for the web panel
BADGE = {WAITING: "gray", AT_CHINA: "blue", SENT: "orange", AT_UZ: "purple", DELIVERED: "green"}

ROLES = {
    "admin": {"uz": "Administrator", "ru": "Администратор"},
    "china_avia": {"uz": "Xitoy operatori (AVIA)", "ru": "Оператор Китай (АВИА)"},
    "china_fura": {"uz": "Xitoy operatori (FURA)", "ru": "Оператор Китай (ФУРА)"},
    "uzbekistan": {"uz": "O'zbekiston operatori", "ru": "Оператор Узбекистан"},
}


def label(status: str, lang: str = "uz") -> str:
    return LABELS.get(lang, LABELS["uz"]).get(status, status)


def role_kinds(role: str) -> list[str]:
    if role == "china_avia":
        return ["AVIA"]
    if role == "china_fura":
        return ["FURA"]
    return ["AVIA", "FURA"]


def role_targets(role: str) -> list[str]:
    """Statuses this role is allowed to set."""
    if role == "admin":
        return ORDER
    if role in ("china_avia", "china_fura"):
        return [WAITING, AT_CHINA, SENT]
    if role == "uzbekistan":
        return [AT_UZ, DELIVERED]
    return []


def next_status(status: str) -> str | None:
    i = ORDER.index(status) if status in ORDER else -1
    return ORDER[i + 1] if 0 <= i < len(ORDER) - 1 else None


def can_set(role: str, kind: str, target: str) -> bool:
    return kind in role_kinds(role) and target in role_targets(role)
