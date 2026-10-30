"""Excel (.xlsx) export for the web panel."""
import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import Cargo, Client, StatusHistory, Tariff
from .statuses import label

HEADER_FILL = PatternFill("solid", fgColor="141414")
HEADER_FONT = Font(bold=True, color="FFFFFF")
UNITS = {"kg": "1 kg", "m3": "1 m³", "piece": "1 dona"}


def _add_sheet(wb: Workbook, title: str, header: list[str], rows: list[list]) -> None:
    ws = wb.create_sheet(title)
    ws.append(header)
    for row in rows:
        ws.append(row)
    for cell in ws[1]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = ws.dimensions
    # Column widths by content, dates in a readable format
    for i, col in enumerate(ws.columns, 1):
        width = 8
        for cell in col:
            if isinstance(cell.value, datetime):
                cell.number_format = "dd.mm.yyyy hh:mm"
                width = max(width, 17)
            elif cell.value is not None:
                width = max(width, min(len(str(cell.value)) + 2, 60))
        ws.column_dimensions[get_column_letter(i)].width = width


def _save(wb: Workbook) -> bytes:
    if len(wb.sheetnames) > 1 and wb.sheetnames[0] == "Sheet":
        del wb["Sheet"]
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _cargo_rows(cargos: list[Cargo], lang: str) -> list[list]:
    return [[g.id, g.client_code, g.client.full_name, g.client.phone, g.kind, g.tracking_code or "",
             "ha" if g.tracking_auto else "", label(g.status, lang), g.weight_kg, g.note or "",
             g.created_at, g.updated_at] for g in cargos]


def _cargo_header(lang: str) -> list[str]:
    if lang == "ru":
        return ["ID", "Код клиента", "Имя", "Телефон", "Тип", "Трек-код", "Авто трек", "Статус", "Вес (кг)",
                "Примечание", "Создан", "Обновлён"]
    return ["ID", "Mijoz kodi", "Ism", "Telefon", "Turi", "Trek kod", "Avto trek", "Holat", "Og'irlik (kg)",
            "Izoh", "Yaratilgan", "Yangilangan"]


def cargos_xlsx(cargos: list[Cargo], lang: str = "uz") -> bytes:
    """One sheet: the cargo list as filtered in the panel."""
    wb = Workbook()
    _add_sheet(wb, "Грузы" if lang == "ru" else "Yuklar", _cargo_header(lang), _cargo_rows(cargos, lang))
    return _save(wb)


def full_xlsx(clients: list[Client], cargos: list[Cargo], history: list[StatusHistory],
              tariffs: list[Tariff], lang: str = "uz") -> bytes:
    """Whole database: clients, cargo, status history, prices."""
    ru = lang == "ru"
    wb = Workbook()
    _add_sheet(
        wb, "Клиенты" if ru else "Mijozlar",
        ["ID", "АВИА", "ФУРА", "Имя", "Телефон", "Telegram ID", "Username", "Язык", "Зарегистрирован"] if ru else
        ["ID", "AVIA kodi", "FURA kodi", "Ism", "Telefon", "Telegram ID", "Username", "Til", "Ro'yxatdan o'tgan"],
        [[c.id, c.avia_code, c.fura_code, c.full_name, c.phone, str(c.telegram_id or ""),
          ("@" + c.username) if c.username else "", c.lang, c.created_at] for c in clients],
    )
    _add_sheet(wb, "Грузы" if ru else "Yuklar", _cargo_header(lang), _cargo_rows(cargos, lang))
    _add_sheet(
        wb, "История" if ru else "Tarix",
        ["ID", "ID груза", "Трек-код", "Статус", "Оператор", "Комментарий", "Время"] if ru else
        ["ID", "Yuk ID", "Trek kod", "Holat", "Operator", "Izoh", "Vaqt"],
        [[h.id, h.cargo_id, h.cargo.tracking_code or "", label(h.status, lang),
          h.operator.username if h.operator else "bot", h.comment or "", h.created_at] for h in history],
    )
    _add_sheet(
        wb, "Цены" if ru else "Narxlar",
        ["ID", "Тип", "Название (узб.)", "Название (рус.)", "Цена", "Валюта", "Единица", "Минимум", "В боте"] if ru else
        ["ID", "Turi", "Nomi (uz)", "Nomi (ru)", "Narx", "Valyuta", "Birlik", "Minimal", "Botda"],
        [[x.id, x.kind, x.title_uz, x.title_ru, x.price, x.currency, UNITS.get(x.unit, x.unit), x.min_amount,
          ("да" if x.is_active else "нет") if ru else ("ha" if x.is_active else "yo'q")] for x in tariffs],
    )
    return _save(wb)
