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
    "operator": {"uz": "Operator", "ru": "Оператор"},
}

# ---- Operator permissions ----
# Stored on the operator as a comma-separated list, chosen by the admin with checkboxes:
#   AVIA / FURA       — which cargo the operator sees and works with
#   s:<status>        — which statuses the operator may set
#   add               — add cargo and new clients
#   export            — download Excel
KINDS = ["AVIA", "FURA"]
EXTRAS = ["add", "export"]
ALL_PERMS = KINDS + [f"s:{x}" for x in ORDER] + EXTRAS

# Roles used before permissions existed → the same rights as checkboxes
LEGACY_ROLES = {
    "china_avia": ["AVIA", f"s:{WAITING}", f"s:{AT_CHINA}", f"s:{SENT}", "add", "export"],
    "china_fura": ["FURA", f"s:{WAITING}", f"s:{AT_CHINA}", f"s:{SENT}", "add", "export"],
    "uzbekistan": ["AVIA", "FURA", f"s:{AT_UZ}", f"s:{DELIVERED}", "add", "export"],
}


def label(status: str, lang: str = "uz") -> str:
    return LABELS.get(lang, LABELS["uz"]).get(status, status)


def parse_perms(text: str | None) -> list[str]:
    items = {p.strip() for p in (text or "").split(",")}
    return [p for p in ALL_PERMS if p in items]  # known ones only, in a fixed order


def perms(op) -> set[str]:
    if op.role == "admin":
        return set(ALL_PERMS)
    return set(parse_perms(getattr(op, "permissions", "")))


def op_kinds(op) -> list[str]:
    """Cargo directions the operator works with."""
    p = perms(op)
    return [k for k in KINDS if k in p]


def op_targets(op) -> list[str]:
    """Statuses the operator may set."""
    p = perms(op)
    return [st for st in ORDER if f"s:{st}" in p]


def can(op, perm: str) -> bool:
    return perm in perms(op)


def can_set(op, kind: str, target: str) -> bool:
    p = perms(op)
    return kind in p and f"s:{target}" in p


def next_status(status: str) -> str | None:
    i = ORDER.index(status) if status in ORDER else -1
    return ORDER[i + 1] if 0 <= i < len(ORDER) - 1 else None
