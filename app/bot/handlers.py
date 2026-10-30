import html
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, KeyboardButton, Message, ReplyKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .. import sheets
from ..db import SessionLocal
from ..models import Cargo, Client, StatusHistory
from ..services import get_settings, get_tariffs, normalize_phone, normalize_tracking
from ..statuses import ACTIVE, INACTIVE, WAITING, label
from ..texts import WELCOME, all_variants, kind_info, kind_name, t

router = Router()
LOGO = Path(__file__).resolve().parent.parent / "web" / "static" / "logo.jpg"
_logo_file_id: str | None = None


class Reg(StatesGroup):
    lang = State()
    name = State()
    phone = State()


class CargoSt(StatesGroup):
    kind = State()
    info = State()
    track = State()
    no_track = State()


class MySt(StatesGroup):
    menu = State()


class SetSt(StatesGroup):
    menu = State()
    lang = State()
    name = State()
    phone = State()


# ---------------- helpers ----------------

def kb(*rows: list[str], contact_btn: str | None = None) -> ReplyKeyboardMarkup:
    keyboard = []
    if contact_btn:
        keyboard.append([KeyboardButton(text=contact_btn, request_contact=True)])
    keyboard += [[KeyboardButton(text=x) for x in row] for row in rows]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def btn(key: str):
    """Filter: message text equals the button in any language."""
    return F.text.in_(all_variants(key))


async def get_client(tg_id: int) -> Client | None:
    async with SessionLocal() as s:
        return await s.scalar(select(Client).where(Client.telegram_id == tg_id))


async def lang_of(m: Message, state: FSMContext) -> str:
    c = await get_client(m.from_user.id)
    if c:
        return c.lang
    return (await state.get_data()).get("lang", "uz")


def main_kb(lang: str) -> ReplyKeyboardMarkup:
    return kb(
        [t("btn_cargo", lang), t("btn_tracking", lang)],
        [t("btn_my", lang), t("btn_faq", lang)],
        [t("btn_settings", lang), t("btn_contact", lang)],
    )


async def send_long(m: Message, text: str, reply_markup=None) -> None:
    chunks, cur = [], ""
    for block in text.split("\n\n"):
        if len(cur) + len(block) + 2 > 3800:
            chunks.append(cur)
            cur = ""
        cur += ("\n\n" if cur else "") + block
    chunks.append(cur)
    for i, ch in enumerate(chunks):
        await m.answer(ch, reply_markup=reply_markup if i == len(chunks) - 1 else None,
                       disable_web_page_preview=True)


async def send_logo(m: Message) -> None:
    global _logo_file_id
    try:
        msg = await m.answer_photo(_logo_file_id or FSInputFile(LOGO))
        _logo_file_id = msg.photo[-1].file_id
    except Exception:
        pass


def cargo_list_text(cargos: list[Cargo], lang: str, header: str) -> str:
    lines = [header]
    for i, g in enumerate(cargos, 1):
        icon = "✈️" if g.kind == "AVIA" else "🚛"
        code = f"<code>{html.escape(g.tracking_code)}</code>" if g.tracking_code else f"<i>{t('no_code', lang)}</i>"
        lines.append(
            f"<b>{i}.</b> {icon} {kind_name(g.kind, lang)} | {code}\n"
            f"     📍 {label(g.status, lang)}\n"
            f"     📅 {g.updated_at:%d.%m.%Y %H:%M}"
        )
    return "\n\n".join(lines)


async def client_cargos(client_id: int, statuses) -> list[Cargo]:
    async with SessionLocal() as s:
        return list((await s.scalars(
            select(Cargo).where(Cargo.client_id == client_id, Cargo.status.in_(list(statuses)))
            .order_by(Cargo.updated_at.desc())
        )).all())


# ---------------- screens ----------------

async def show_lang(m: Message, state: FSMContext, back: bool = False) -> None:
    lang = await lang_of(m, state)
    rows = [[t("btn_lang_uz", lang), t("btn_lang_ru", lang)]]
    if back:
        rows.append([t("btn_back", lang)])
    await m.answer(t("choose_lang", lang), reply_markup=kb(*rows))


async def show_main(m: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(None)
    await m.answer(t("main_menu", lang), reply_markup=main_kb(lang))


async def show_kinds(m: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(CargoSt.kind)
    await m.answer(t("choose_kind", lang),
                   reply_markup=kb([t("btn_avia", lang), t("btn_fura", lang)], [t("btn_back", lang)]))


async def show_kind_info(m: Message, state: FSMContext, client: Client, kind: str) -> None:
    lang = client.lang
    await state.set_state(CargoSt.info)
    await state.update_data(kind=kind)
    async with SessionLocal() as s:
        st = await get_settings(s)
        tariffs = await get_tariffs(s, kind)
    await m.answer(
        kind_info(kind, client.code(kind), lang, st, tariffs),
        disable_web_page_preview=True,
        reply_markup=kb([t("btn_enter_track", lang)], [t("btn_no_track", lang)], [t("btn_back", lang), t("btn_home", lang)]),
    )


async def show_settings(m: Message, state: FSMContext, client: Client) -> None:
    lang = client.lang
    await state.set_state(SetSt.menu)
    await m.answer(
        t("settings", lang, name=html.escape(client.full_name), phone=client.phone, a=client.avia_code, f=client.fura_code),
        reply_markup=kb([t("btn_change_lang", lang)], [t("btn_change_name", lang), t("btn_change_phone", lang)],
                        [t("btn_back", lang)]),
    )


async def require_client(m: Message, state: FSMContext) -> Client | None:
    c = await get_client(m.from_user.id)
    if not c:
        await state.clear()
        await m.answer(t("need_start", (await state.get_data()).get("lang", "uz")))
    return c


# ---------------- /start & registration ----------------

@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    client = await get_client(m.from_user.id)
    await send_logo(m)
    if client:
        await m.answer(WELCOME[client.lang])
        await show_main(m, state, client.lang)
        return
    await m.answer(WELCOME["uz"])
    await m.answer(WELCOME["ru"])
    await state.set_state(Reg.lang)
    await show_lang(m, state)


@router.message(Reg.lang, btn("btn_lang_uz") | btn("btn_lang_ru"))
async def reg_lang(m: Message, state: FSMContext):
    lang = "ru" if m.text in all_variants("btn_lang_ru") else "uz"
    await state.update_data(lang=lang)
    await state.set_state(Reg.name)
    await m.answer(t("ask_name", lang), reply_markup=kb([t("btn_back", lang)]))


@router.message(Reg.name, F.text)
async def reg_name(m: Message, state: FSMContext):
    lang = (await state.get_data()).get("lang", "uz")
    if m.text in all_variants("btn_back"):
        await state.set_state(Reg.lang)
        return await show_lang(m, state)
    name = " ".join(m.text.split())
    if not 2 <= len(name) <= 64 or name.startswith("/"):
        return await m.answer(t("bad_name", lang))
    await state.update_data(name=name)
    await state.set_state(Reg.phone)
    await m.answer(t("ask_phone", lang), reply_markup=kb([t("btn_back", lang)], contact_btn=t("btn_send_phone", lang)))


@router.message(Reg.phone)
async def reg_phone(m: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    if m.text and m.text in all_variants("btn_back"):
        await state.set_state(Reg.name)
        return await m.answer(t("ask_name", lang), reply_markup=kb([t("btn_back", lang)]))
    raw = m.contact.phone_number if m.contact else (m.text or "")
    phone = normalize_phone(raw)
    if not phone:
        return await m.answer(t("bad_phone", lang))

    async with SessionLocal() as s:
        client = await s.scalar(select(Client).where(Client.telegram_id == m.from_user.id))
        if not client:
            client = Client(telegram_id=m.from_user.id)
            s.add(client)
        client.username = m.from_user.username
        client.lang = lang
        client.full_name = data.get("name", m.from_user.full_name)
        client.phone = phone
        await s.commit()
    sheets.mark_dirty()

    await m.answer(t("registered", lang, name=html.escape(client.full_name), a=client.avia_code, f=client.fura_code))
    await show_main(m, state, lang)


# ---------------- universal buttons (any state) ----------------

@router.message(btn("btn_home"))
async def go_home(m: Message, state: FSMContext):
    if c := await require_client(m, state):
        await show_main(m, state, c.lang)


@router.message(btn("btn_back"))
async def go_back(m: Message, state: FSMContext):
    c = await require_client(m, state)
    if not c:
        return
    cur = await state.get_state()
    data = await state.get_data()
    if cur in (CargoSt.info.state,):
        await show_kinds(m, state, c.lang)
    elif cur in (CargoSt.track.state, CargoSt.no_track.state):
        await show_kind_info(m, state, c, data.get("kind", "AVIA"))
    elif cur in (SetSt.lang.state, SetSt.name.state, SetSt.phone.state):
        await show_settings(m, state, c)
    else:  # CargoSt.kind, MySt.menu, SetSt.menu, no state
        await show_main(m, state, c.lang)


# ---------------- main menu ----------------

@router.message(btn("btn_cargo"))
async def menu_cargo(m: Message, state: FSMContext):
    if c := await require_client(m, state):
        await show_kinds(m, state, c.lang)


@router.message(btn("btn_tracking"))
async def menu_tracking(m: Message, state: FSMContext):
    c = await require_client(m, state)
    if not c:
        return
    cargos = await client_cargos(c.id, ACTIVE)
    await state.set_state(None)
    if not cargos:
        return await m.answer(t("tracking_empty", c.lang), reply_markup=main_kb(c.lang))
    await send_long(m, cargo_list_text(cargos, c.lang, t("tracking_header", c.lang, n=len(cargos))), main_kb(c.lang))


@router.message(btn("btn_my"))
async def menu_my(m: Message, state: FSMContext):
    c = await require_client(m, state)
    if not c:
        return
    await state.set_state(MySt.menu)
    await m.answer(t("my_menu", c.lang),
                   reply_markup=kb([t("btn_active", c.lang), t("btn_inactive", c.lang)], [t("btn_back", c.lang)]))


@router.message(MySt.menu, btn("btn_active") | btn("btn_inactive"))
async def my_list(m: Message, state: FSMContext):
    c = await require_client(m, state)
    if not c:
        return
    active = m.text in all_variants("btn_active")
    cargos = await client_cargos(c.id, ACTIVE if active else INACTIVE)
    if not cargos:
        return await m.answer(t("tracking_empty" if active else "inactive_empty", c.lang))
    header = t("tracking_header" if active else "inactive_header", c.lang, n=len(cargos))
    await send_long(m, cargo_list_text(cargos, c.lang, header))


@router.message(btn("btn_faq"))
async def menu_faq(m: Message, state: FSMContext):
    if c := await require_client(m, state):
        await state.set_state(None)
        await m.answer(t("faq", c.lang), disable_web_page_preview=True, reply_markup=main_kb(c.lang))


@router.message(btn("btn_contact"))
async def menu_contact(m: Message, state: FSMContext):
    if c := await require_client(m, state):
        await state.set_state(None)
        await m.answer(t("contact", c.lang), reply_markup=main_kb(c.lang))


# ---------------- cargo service ----------------

@router.message(CargoSt.kind, btn("btn_avia") | btn("btn_fura"))
async def cargo_kind(m: Message, state: FSMContext):
    if c := await require_client(m, state):
        await show_kind_info(m, state, c, "AVIA" if m.text in all_variants("btn_avia") else "FURA")


@router.message(CargoSt.info, btn("btn_enter_track"))
async def cargo_enter(m: Message, state: FSMContext):
    if c := await require_client(m, state):
        await state.set_state(CargoSt.track)
        await m.answer(t("ask_track", c.lang), disable_web_page_preview=True,
                       reply_markup=kb([t("btn_back", c.lang), t("btn_home", c.lang)]))


@router.message(CargoSt.track, F.text)
async def cargo_track(m: Message, state: FSMContext):
    c = await require_client(m, state)
    if not c:
        return
    code = normalize_tracking(m.text)
    if not code:
        return await m.answer(t("bad_track", c.lang))
    kind = (await state.get_data()).get("kind", "AVIA")
    async with SessionLocal() as s:
        existing = await s.scalar(select(Cargo).where(Cargo.tracking_code == code))
        if existing:
            key = "track_exists_self" if existing.client_id == c.id else "track_exists_other"
            return await m.answer(t(key, c.lang))
        cargo = Cargo(client_id=c.id, kind=kind, tracking_code=code, status=WAITING)
        s.add(cargo)
        try:
            await s.flush()
            s.add(StatusHistory(cargo_id=cargo.id, status=WAITING, comment="Mijoz botda ro'yxatga oldi"))
            await s.commit()
        except IntegrityError:
            return await m.answer(t("track_exists_other", c.lang))
    sheets.mark_dirty()
    await m.answer(t("track_saved", c.lang, kind=kind_name(kind, c.lang), code=html.escape(code),
                     status=label(WAITING, c.lang)))


@router.message(CargoSt.info, btn("btn_no_track"))
async def cargo_no_track(m: Message, state: FSMContext):
    if c := await require_client(m, state):
        await state.set_state(CargoSt.no_track)
        await m.answer(t("no_track_info", c.lang),
                       reply_markup=kb([t("btn_request", c.lang)], [t("btn_back", c.lang), t("btn_home", c.lang)]))


@router.message(CargoSt.no_track, btn("btn_request"))
async def cargo_request(m: Message, state: FSMContext):
    c = await require_client(m, state)
    if not c:
        return
    kind = (await state.get_data()).get("kind", "AVIA")
    async with SessionLocal() as s:
        cargo = Cargo(client_id=c.id, kind=kind, tracking_code=None, status=WAITING)
        s.add(cargo)
        await s.flush()
        s.add(StatusHistory(cargo_id=cargo.id, status=WAITING, comment="Mijoz trek kodsiz so'rov yubordi"))
        await s.commit()
    sheets.mark_dirty()
    await m.answer(t("request_sent", c.lang))
    await show_main(m, state, c.lang)


# ---------------- settings ----------------

@router.message(btn("btn_settings"))
async def menu_settings(m: Message, state: FSMContext):
    if c := await require_client(m, state):
        await show_settings(m, state, c)


@router.message(SetSt.menu, btn("btn_change_lang"))
async def set_lang_ask(m: Message, state: FSMContext):
    await state.set_state(SetSt.lang)
    await show_lang(m, state, back=True)


@router.message(SetSt.lang, btn("btn_lang_uz") | btn("btn_lang_ru"))
async def set_lang(m: Message, state: FSMContext):
    lang = "ru" if m.text in all_variants("btn_lang_ru") else "uz"
    async with SessionLocal() as s:
        c = await s.scalar(select(Client).where(Client.telegram_id == m.from_user.id))
        c.lang = lang
        await s.commit()
    sheets.mark_dirty()
    await m.answer(t("saved", lang))
    await show_settings(m, state, c)


@router.message(SetSt.menu, btn("btn_change_name"))
async def set_name_ask(m: Message, state: FSMContext):
    if c := await require_client(m, state):
        await state.set_state(SetSt.name)
        await m.answer(t("ask_name", c.lang), reply_markup=kb([t("btn_back", c.lang)]))


@router.message(SetSt.name, F.text)
async def set_name(m: Message, state: FSMContext):
    name = " ".join(m.text.split())
    async with SessionLocal() as s:
        c = await s.scalar(select(Client).where(Client.telegram_id == m.from_user.id))
        if not 2 <= len(name) <= 64 or name.startswith("/"):
            return await m.answer(t("bad_name", c.lang))
        c.full_name = name
        await s.commit()
    sheets.mark_dirty()
    await m.answer(t("saved", c.lang))
    await show_settings(m, state, c)


@router.message(SetSt.menu, btn("btn_change_phone"))
async def set_phone_ask(m: Message, state: FSMContext):
    if c := await require_client(m, state):
        await state.set_state(SetSt.phone)
        await m.answer(t("ask_phone", c.lang),
                       reply_markup=kb([t("btn_back", c.lang)], contact_btn=t("btn_send_phone", c.lang)))


@router.message(SetSt.phone)
async def set_phone(m: Message, state: FSMContext):
    phone = normalize_phone(m.contact.phone_number if m.contact else (m.text or ""))
    async with SessionLocal() as s:
        c = await s.scalar(select(Client).where(Client.telegram_id == m.from_user.id))
        if not phone:
            return await m.answer(t("bad_phone", c.lang))
        c.phone = phone
        await s.commit()
    sheets.mark_dirty()
    await m.answer(t("saved", c.lang))
    await show_settings(m, state, c)


# ---------------- fallback ----------------

@router.message()
async def fallback(m: Message, state: FSMContext):
    cur = await state.get_state()
    if cur == Reg.lang.state:
        return await show_lang(m, state)
    c = await get_client(m.from_user.id)
    if not c:
        return await m.answer(t("need_start", "uz"))
    if cur is None:
        return await m.answer(t("unknown", c.lang), reply_markup=main_kb(c.lang))
    await m.answer(t("unknown", c.lang))
