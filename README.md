# 🐉 Dragon Life Cargo

Xitoy → O'zbekiston kargo xizmati uchun tizim:

1. **Telegram bot** (o'zbek / rus) — mijozlar uchun.
2. **Veb-panel** — administrator va operatorlar uchun (login/parol bilan).
3. **Ma'lumotlar bazasi** (SQLite yoki PostgreSQL) + **Google Sheets** ga avtomatik nusxa.

Hammasi bitta `python main.py` buyrug'i bilan ishga tushadi.

---

## Bot imkoniyatlari

- `/start` → logotip + kutib olish matni (o'zb + rus) → til tanlash.
- Ro'yxatdan o'tish: ism → telefon raqam (tugma orqali yoki qo'lda).
- Har bir mijozga **doimiy va o'zgarmas** kod beriladi: `A001` (AVIA) va `F001` (FURA). Raqam takrorlanmaydi.
- Tanlangan tilga qarab butun bot o'sha tilda ishlaydi. **Har bir menyuda «⬅️ Orqaga»** tugmasi bor.
- Asosiy menyu: 📦 Kargo xizmati · 🔍 Treking · 🗂 Mening yuklarim · ❓ Ko'p beriladigan savollar · ⚙️ Sozlamalar · ☎️ Aloqa.
- **Kargo xizmati → AVIA / FURA**: ombor manzili mijoz kodi bilan — avval tarjimasi, keyin xitoycha asl nusxasi (nusxa olish uchun), muddatlar, narx, yo'riqnoma havolalari.
  - «✍️ Trek kodni kiritish» → yuk ro'yxatga olinadi, holati: *Xitoydagi omborga kelishi kutilmoqda*.
  - «📭 Trek kodim yo'q» → aloqa ma'lumotlari + «📨 So'rov yuborish» (operator panelda trek kod yaratadi, mijozga xabar boradi).
- **Treking** — faqat faol yuklar. **Mening yuklarim** — faol va yakunlangan yuklar.
- **Sozlamalar** — til, ism, telefonni o'zgartirish.
- Yuk holati o'zgarganda yoki trek kod berilganda mijozga **avtomatik xabar** boradi.

## Yuk holatlari

| # | Holat | Kim o'zgartiradi |
|---|-------|------------------|
| 1 | ⏳ Xitoydagi omborga kelishi kutilmoqda | mijoz (bot) / Xitoy operatori |
| 2 | 🏬 Xitoydagi omborga yetib keldi | Xitoy operatori |
| 3 | 🚚 Xitoydan jo'natildi (yo'lda) | Xitoy operatori |
| 4 | 🇺🇿 O'zbekistonga yetib keldi (Toshkent ombori) | O'zbekiston operatori |
| 5 | ✅ Mijozga topshirildi (yakunlangan) | O'zbekiston operatori |

Administrator istalgan holatni qo'ya oladi.

## Veb-panel

Rollar:
- **Administrator** — hamma narsa + operatorlarni qo'shish, narx/muddatlarni o'zgartirish, Google Sheets.
- **Xitoy operatori (AVIA)** — faqat AVIA yuklarini ko'radi, 1–3 holatlarni qo'yadi.
- **Xitoy operatori (FURA)** — faqat FURA yuklarini ko'radi, 1–3 holatlarni qo'yadi.
- **O'zbekiston operatori** — barcha yuklar, 4–5 holatlarni qo'yadi.

Sahifalar:
- **Yuklar** — statistika, qidiruv (trek kod, A001/F001, ism, telefon), filtrlar. Trek kodsiz yuk uchun «⚡ Trek kod yaratish» tugmasi (bazada yo'q unikal kod: `DLA…` / `DLF…`), har bir yuk uchun «▥ Shtrix-kod» (Code128 yorliq, 100×60 mm, chop etish uchun).
- **Skanerlash** — USB/Bluetooth shtrix-kod skaner, qo'lda kiritish yoki telefon kamerasi. Skanerlangandan keyin tizim keyingi holatni taklif qiladi: «Holatni o'zgartirasizmi? → Xitoydagi omborga yetib keldi» → bir bosish bilan tasdiqlanadi va keyingi skanga qaytadi.
- **Yuk qo'shish** — mijoz kodi (A001/F001) bo'yicha. Trek kod bo'sh qoldirilsa — avtomatik yaratiladi va mijozga xabar boradi.
- **Mijozlar** — ro'yxat va har bir mijozning yuklari.
- **Operatorlar** va **Sozlamalar** (narx, minimal og'irlik, muddatlar — botda darhol yangilanadi).

Panel o'zbek va rus tillarida (pastki chap burchakda UZ / RU).

---

## O'rnatish

```bash
pip install -r requirements.txt
cp .env.example .env     # BOT_TOKEN, SECRET_KEY, ADMIN_PASSWORD ni to'ldiring
python main.py
```

Panel: `http://SERVER:8000` — birinchi kirish `.env` dagi `ADMIN_USERNAME` / `ADMIN_PASSWORD` bilan. So'ng «Operatorlar» bo'limida 3 ta operator uchun login/parol yarating.

Docker + PostgreSQL bilan:

```bash
docker compose up -d --build
```

> Telefon kamerasi bilan skanerlash uchun panel **HTTPS** orqali ochilishi kerak (masalan, nginx + Let's Encrypt). USB skaner oddiy HTTP da ham ishlaydi.

### Google Sheets ulash

1. [Google Cloud Console](https://console.cloud.google.com/) → yangi loyiha → **Google Sheets API** va **Google Drive API** ni yoqing.
2. **Service account** yarating → **Keys → JSON** yuklab oling → loyiha papkasiga `google-credentials.json` nomi bilan qo'ying.
3. Yangi Google Sheets jadval oching va uni service account email manziliga (**Editor**) ulashing.
4. `.env` da `GOOGLE_SHEET_ID=` ga jadval ID sini yozing (URL dagi `/d/` va `/edit` orasidagi qism).

Tizim har o'zgarishdan keyin (ko'pi bilan `SHEETS_SYNC_INTERVAL` soniyada bir marta) jadvalga «Mijozlar», «Yuklar», «Tarix» varaqlarini yangilab yozadi. Asosiy ma'lumot bazada saqlanadi, Sheets — nusxa.

## Tuzilma

```
main.py                 bot + panel + Sheets ni birga ishga tushiradi
app/config.py           sozlamalar, ombor manzili, havolalar
app/models.py           bazadagi jadvallar
app/statuses.py         holatlar va rollar huquqlari
app/texts.py            bot matnlari (uz/ru)
app/services.py         umumiy logika (trek kod yaratish, holat, xabarnomalar)
app/sheets.py           Google Sheets nusxasi
app/bot/handlers.py     Telegram bot
app/web/                veb-panel (FastAPI + shablonlar)
```
