# 🐉 Dragon Life Cargo

Xitoy → O'zbekiston kargo xizmati uchun tizim:

1. **Telegram bot** (o'zbek / rus) — mijozlar uchun.
2. **Veb-panel** — administrator va operatorlar uchun (login/parol bilan).
3. **Ma'lumotlar bazasi** (SQLite yoki PostgreSQL) + **Excel** ga yuklab olish.

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
- **Xitoy operatori (AVIA)** — faqat AVIA yuklarini ko'radi, 1–3 holatlarni qo'yadi.
- **Xitoy operatori (FURA)** — faqat FURA yuklarini ko'radi, 1–3 holatlarni qo'yadi.
- **O'zbekiston operatori** — barcha yuklar, 4–5 holatlarni qo'yadi.

Sahifalar:
- **Yuklar** — statistika, qidiruv (trek kod, A001/F001, ism, telefon), filtrlar. Trek kodsiz yuk uchun «⚡ Trek kod yaratish» tugmasi (bazada yo'q unikal kod: `DLA…` / `DLF…`), har bir yuk uchun «▥ Shtrix-kod» (Code128 yorliq, 100×60 mm, chop etish uchun).
- **Skanerlash** — USB/Bluetooth shtrix-kod skaner, qo'lda kiritish yoki telefon kamerasi. Skanerlangandan keyin tizim keyingi holatni taklif qiladi: «Holatni o'zgartirasizmi? → Xitoydagi omborga yetib keldi» → bir bosish bilan tasdiqlanadi va keyingi skanga qaytadi.
- **Yuk qo'shish** — mijoz kodi (A001/F001) bo'yicha (kod yozilganda mijoz ismi ko'rinadi). Trek kod bo'sh qoldirilsa — avtomatik yaratiladi va mijozga xabar boradi.
  **➕ Yangi mijoz** tugmasi: ism-familiya, telefon va yo'nalish kiritiladi, doimiy kod avtomatik yaratiladi. Shu raqam bazada bo'lsa, yangi mijoz yaratilmaydi — yuk mavjud mijozga yoziladi. Mijoz keyin botga kirib, raqamini «📱 Raqamni yuborish» tugmasi bilan yuborsa, bot uni shu kodga ulaydi va u yuklarini ko'radi (qo'lda yozilgan raqam bilan ulanmaydi — boshqa odam birovning raqamini yozib yuklarini ko'ra olmasligi uchun).
- **Mijozlar** — ro'yxat va har bir mijozning yuklari.
- **Operatorlar** — login/parol va rollar.
- **💰 Narxlar va muddatlar** — AVIA va FURA uchun narxlar ro'yxati: administrator narx qatorlarini qo'shadi, o'zgartiradi, o'chiradi yoki vaqtincha yashiradi (narx, valyuta, birlik: 1 kg / 1 m³ / 1 dona, minimal miqdor, o'zbekcha/ruscha nomi). Muddatlar ham shu yerda. Pastda «Botda shunday ko'rinadi» namunasi bor, o'zgarish botda darhol ko'rinadi.

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

## 🚀 Render'da ishga tushirish (sinov uchun)

Repoda tayyor `render.yaml` bor — Render hamma narsani (server + PostgreSQL bazasi) o'zi yaratadi.

**1. Bot tokenini oling**
1. Telegram'da [@BotFather](https://t.me/BotFather) ni oching → `/newbot`.
2. Bot nomini (masalan `Dragon Life Cargo`) va username'ini (masalan `dragonlife_cargo_bot`) yozing.
3. BotFather bergan tokenni (`123456789:AA...`) saqlab qo'ying. **Uni hech kimga bermang.**

**2. Render'da joylashtiring**
1. [render.com](https://render.com) da GitHub orqali ro'yxatdan o'ting.
2. **New → Blueprint** → `dragon_life_china_cargo` repozitoriyasini tanlang (kerak bo'lsa Render'ga GitHub ruxsatini bering).
3. Branch: kod qaysi branchda bo'lsa o'shani tanlang (`main` ga birlashtirilgan bo'lsa — `main`).
4. Render quyidagilarni so'raydi:
   - `BOT_TOKEN` — 1-qadamdagi token;
   - `ADMIN_PASSWORD` — panelga kirish uchun kuchli parol;
5. **Apply** ni bosing. 3–5 daqiqada tayyor bo'ladi.

**3. Tekshiring**
- Panel manzili Render'da ko'rinadi, masalan `https://dragonlife-cargo.onrender.com` → login `admin` + siz bergan parol.
- Telegram'da botingizni oching → `/start`. Bot webhook rejimida avtomatik ulanadi, qo'shimcha sozlash kerak emas.


### 🔑 Admin parolini tiklash

1. Render → **dragonlife-cargo** → **Environment**.
2. `ADMIN_PASSWORD` ga yangi parol yozing.
3. **Add Environment Variable** → Key: `ADMIN_RESET`, Value: `1` → **Save** (servis qayta ishga tushadi).
4. Panelga `admin` + yangi parol bilan kiring.
5. **Muhim:** `ADMIN_RESET` ni o'chirib, yana **Save** bosing (aks holda har qayta ishga tushishda parol shu qiymatga qaytariladi).

Agar `ADMIN_PASSWORD` umuman berilmagan bo'lsa, birinchi ishga tushishda tasodifiy parol yaratiladi va **Logs** da `Generated admin password: ...` qatorida ko'rinadi.

### Bepul tarifdagi cheklovlar

- Server 15 daqiqa ishlatilmasa **uxlaydi**. Keyingi xabar yoki panelga kirishda ~1 daqiqada uyg'onadi — shu sababli birinchi javob kechikadi. Ma'lumotlar yo'qolmaydi.
- Uyg'onganda bot foydalanuvchi qaysi qadamda turganini unutadi (masalan, trek kod kiritish oynasi) — mijoz menyudan qaytadan tanlaydi. Ro'yxatdan o'tish va yuklar bazada saqlanib qoladi.
- Bepul PostgreSQL bazasining **muddati cheklangan** (Render shartlarini tekshiring) — muddat tugasa ma'lumotlar o'chadi.

**Haqiqiy ish uchun** (mijozlar bilan) pullik tarifga o'ting: Render'da web servisni **Starter** ga, bazani pullik **PostgreSQL** ga o'zgartiring — `render.yaml` dagi `plan: free` qatorlarini almashtirish kifoya. Shunda server uxlamaydi va baza doimiy saqlanadi.

### 📥 Excel'ga yuklab olish

- **Yuklar** sahifasi → kerakli filtrlarni tanlang → **📥 Excel** — ekrandagi ro'yxat (filtr bilan) `.xlsx` bo'lib yuklanadi. Har bir operator faqat o'ziga ruxsat berilgan yuklarni oladi.
- **⚙️ Bot va eksport** (yoki **Mijozlar**) → **Butun bazani yuklab olish** — faqat administrator uchun: «Mijozlar», «Yuklar», «Tarix», «Narxlar» varaqlari bitta faylda.

## Tuzilma

```
main.py                 bot va panelni birga ishga tushiradi
app/config.py           sozlamalar, ombor manzili, havolalar
app/models.py           bazadagi jadvallar
app/statuses.py         holatlar va rollar huquqlari
app/texts.py            bot matnlari (uz/ru)
app/services.py         umumiy logika (trek kod yaratish, holat, xabarnomalar)
app/bot/handlers.py     Telegram bot
app/web/                veb-panel (FastAPI + shablonlar)
```
