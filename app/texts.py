"""All bot texts in Uzbek and Russian."""
from .config import (
    LINK_FORBIDDEN, LINK_TRACK_HELP, LINK_VOLUME_HELP,
    WAREHOUSE_ADDRESS_CN, WAREHOUSE_PHONE, WAREHOUSE_ZIP, settings,
)

WELCOME = {
    "uz": (
        "🐉 <b>DRAGON LIFE CARGO 🇨🇳🇺🇿</b>\n\n"
        "📦 Xitoydan O'zbekistonga ishonchli, tezkor va qulay yuk yetkazib berish xizmati!\n\n"
        "Biz sizning yuklaringizni Xitoydan O'zbekistonga xavfsiz va ishonchli yetkazib beramiz. "
        "Biz bilan buyurtmalaringizni oson, qulay va ortiqcha tashvishlarsiz qabul qiling!\n\n"
        "✅ Xitoydan O'zbekistonga yuk tashish\n"
        "🚀 Tezkor va ishonchli yetkazib berish\n"
        "💰 Hamyonbop narxlar\n"
        "📦 Yuklaringizga ehtiyotkorona munosabat\n"
        "🤝 Har bir mijozga individual yondashuv\n\n"
        "Biz uchun sizning ishonchingiz va mamnunligingiz muhim!\n\n"
        "🐉 <b>DRAGON LIFE CARGO — ishonchli logistika, qulay yetkazib berish!</b>"
    ),
    "ru": (
        "🐉 <b>DRAGON LIFE CARGO 🇨🇳🇺🇿</b>\n\n"
        "📦 Надёжная, быстрая и удобная доставка грузов из Китая в Узбекистан!\n\n"
        "Мы помогаем доставлять ваши грузы из Китая в Узбекистан безопасно, удобно и без лишних хлопот. "
        "Наша цель — сделать процесс доставки максимально простым и комфортным для каждого клиента!\n\n"
        "✅ Доставка грузов из Китая в Узбекистан\n"
        "🚀 Быстрая и надёжная логистика\n"
        "💰 Доступные цены\n"
        "📦 Бережное отношение к каждому грузу\n"
        "🤝 Индивидуальный подход к каждому клиенту\n\n"
        "Ваше доверие — наша главная ценность!\n\n"
        "🐉 <b>DRAGON LIFE CARGO — надёжная логистика, удобная доставка!</b>"
    ),
}

CONTACT_BLOCK = {
    "uz": f"👤 Telegram: {settings.CONTACT_USERNAME}\n📞 Aloqa: {settings.CONTACT_PHONE}",
    "ru": f"👤 Telegram: {settings.CONTACT_USERNAME}\n📞 Связь: {settings.CONTACT_PHONE}",
}

T = {
    # ---- buttons ----
    "btn_lang_uz": {"uz": "🇺🇿 O'zbekcha", "ru": "🇺🇿 O'zbekcha"},
    "btn_lang_ru": {"uz": "🇷🇺 Русский", "ru": "🇷🇺 Русский"},
    "btn_back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад"},
    "btn_home": {"uz": "🏠 Asosiy menyu", "ru": "🏠 Главное меню"},
    "btn_send_phone": {"uz": "📱 Raqamni yuborish", "ru": "📱 Отправить номер"},
    "btn_cargo": {"uz": "📦 Kargo xizmati", "ru": "📦 Карго услуги"},
    "btn_tracking": {"uz": "🔍 Treking", "ru": "🔍 Трекинг"},
    "btn_my": {"uz": "🗂 Mening yuklarim", "ru": "🗂 Мои грузы"},
    "btn_faq": {"uz": "❓ Ko'p beriladigan savollar", "ru": "❓ Частые вопросы"},
    "btn_settings": {"uz": "⚙️ Sozlamalar", "ru": "⚙️ Настройки"},
    "btn_contact": {"uz": "☎️ Aloqa", "ru": "☎️ Связь"},
    "btn_avia": {"uz": "✈️ AVIA", "ru": "✈️ АВИА"},
    "btn_fura": {"uz": "🚛 FURA", "ru": "🚛 ФУРА"},
    "btn_enter_track": {"uz": "✍️ Trek kodni kiritish", "ru": "✍️ Ввести трек-код"},
    "btn_no_track": {"uz": "📭 Trek kodim yo'q", "ru": "📭 У меня нет трек-кода"},
    "btn_request": {"uz": "📨 So'rov yuborish", "ru": "📨 Отправить запрос"},
    "btn_active": {"uz": "🟢 Faol yuklar", "ru": "🟢 Активные грузы"},
    "btn_inactive": {"uz": "⚪️ Yakunlangan yuklar", "ru": "⚪️ Завершённые грузы"},
    "btn_change_lang": {"uz": "🌐 Tilni o'zgartirish", "ru": "🌐 Изменить язык"},
    "btn_change_name": {"uz": "✏️ Ismni o'zgartirish", "ru": "✏️ Изменить имя"},
    "btn_change_phone": {"uz": "📱 Raqamni o'zgartirish", "ru": "📱 Изменить номер"},

    # ---- messages ----
    "choose_lang": {"uz": "🌐 Tilni tanlang / Выберите язык:", "ru": "🌐 Tilni tanlang / Выберите язык:"},
    "ask_name": {
        "uz": "👤 Iltimos, ism va familiyangizni kiriting:",
        "ru": "👤 Пожалуйста, введите ваше имя и фамилию:",
    },
    "bad_name": {
        "uz": "❗️ Ism 2 tadan 64 tagacha belgidan iborat bo'lishi kerak. Qayta kiriting:",
        "ru": "❗️ Имя должно содержать от 2 до 64 символов. Введите ещё раз:",
    },
    "ask_phone": {
        "uz": "📱 Telefon raqamingizni yuboring.\n\nPastdagi «📱 Raqamni yuborish» tugmasini bosing "
              "yoki raqamni qo'lda yozing, masalan: <code>+998901234567</code>",
        "ru": "📱 Отправьте ваш номер телефона.\n\nНажмите кнопку «📱 Отправить номер» ниже "
              "или введите номер вручную, например: <code>+998901234567</code>",
    },
    "bad_phone": {
        "uz": "❗️ Raqam noto'g'ri. Masalan: <code>+998901234567</code>",
        "ru": "❗️ Неверный номер. Например: <code>+998901234567</code>",
    },
    "registered": {
        "uz": "🎉 Tabriklaymiz, <b>{name}</b>! Siz muvaffaqiyatli ro'yxatdan o'tdingiz.\n\n"
              "🆔 <b>Sizning doimiy mijoz kodlaringiz:</b>\n"
              "✈️ AVIA: <code>{a}</code>\n🚛 FURA: <code>{f}</code>\n\n"
              "Bu kodlar o'zgarmaydi — barcha yuklaringiz uchun shu kodlardan foydalaning.",
        "ru": "🎉 Поздравляем, <b>{name}</b>! Вы успешно зарегистрировались.\n\n"
              "🆔 <b>Ваши постоянные коды клиента:</b>\n"
              "✈️ АВИА: <code>{a}</code>\n🚛 ФУРА: <code>{f}</code>\n\n"
              "Эти коды не меняются — используйте их для всех ваших грузов.",
    },
    "main_menu": {"uz": "🏠 Asosiy menyu. Kerakli bo'limni tanlang 👇", "ru": "🏠 Главное меню. Выберите раздел 👇"},
    "need_start": {
        "uz": "Iltimos, avval ro'yxatdan o'ting: /start",
        "ru": "Пожалуйста, сначала пройдите регистрацию: /start",
    },
    "choose_kind": {
        "uz": "📦 Yuk yetkazib berish turini tanlang:\n\n✈️ <b>AVIA</b> — havo yo'li orqali, tezkor\n🚛 <b>FURA</b> — avtomobil yo'li orqali, hamyonbop",
        "ru": "📦 Выберите способ доставки:\n\n✈️ <b>АВИА</b> — авиадоставка, быстро\n🚛 <b>ФУРА</b> — автодоставка, выгодно",
    },
    "ask_track": {
        "uz": "✍️ Yukingizning trek kodini yuboring:\n\n"
              f"🔎 Pinduoduo yoki Taobao'dan trek kodni topish yo'riqnomasi: ➡️ {LINK_TRACK_HELP}\n\n"
              "ℹ️ Agar yukingiz trek kodsiz bo'lsa, bizga murojaat qiling — biz sizga trek kod yaratib, xabar beramiz:\n"
              + CONTACT_BLOCK["uz"],
        "ru": "✍️ Отправьте трек-код вашего груза:\n\n"
              f"🔎 Инструкция по поиску трек-кода в Pinduoduo или Taobao: ➡️ {LINK_TRACK_HELP}\n\n"
              "ℹ️ Если у вашего груза нет трек-кода, свяжитесь с нами — мы создадим трек-код и сообщим вам:\n"
              + CONTACT_BLOCK["ru"],
    },
    "bad_track": {
        "uz": "❗️ Trek kod noto'g'ri. U faqat lotin harflari, raqamlar va «-» belgisidan iborat bo'lishi kerak (5–40 belgi).",
        "ru": "❗️ Неверный трек-код. Допускаются только латинские буквы, цифры и «-» (5–40 символов).",
    },
    "track_exists_self": {
        "uz": "ℹ️ Bu trek kod allaqachon sizning yuklaringiz ro'yxatida bor. Holatini «🔍 Treking» bo'limida ko'ring.",
        "ru": "ℹ️ Этот трек-код уже есть в списке ваших грузов. Статус смотрите в разделе «🔍 Трекинг».",
    },
    "track_exists_other": {
        "uz": "❗️ Bu trek kod boshqa mijoz nomiga ro'yxatdan o'tgan. Iltimos, tekshirib qayta kiriting yoki biz bilan bog'laning:\n"
              + CONTACT_BLOCK["uz"],
        "ru": "❗️ Этот трек-код зарегистрирован на другого клиента. Проверьте и введите снова или свяжитесь с нами:\n"
              + CONTACT_BLOCK["ru"],
    },
    "track_saved": {
        "uz": "✅ <b>Yukingiz muvaffaqiyatli ro'yxatga olindi!</b>\n\n"
              "📦 Turi: <b>{kind}</b>\n🔢 Trek kod: <code>{code}</code>\n📍 Holati: {status}\n\n"
              "Yuk holatini «🔍 Treking» bo'limida kuzatib borishingiz mumkin. Holat o'zgarganda sizga xabar beramiz 🔔\n\n"
              "➕ Yana yuk bo'lsa, keyingi trek kodni yuboring.",
        "ru": "✅ <b>Ваш груз успешно зарегистрирован!</b>\n\n"
              "📦 Тип: <b>{kind}</b>\n🔢 Трек-код: <code>{code}</code>\n📍 Статус: {status}\n\n"
              "Следить за статусом груза можно в разделе «🔍 Трекинг». При изменении статуса мы вас уведомим 🔔\n\n"
              "➕ Если есть ещё грузы, отправьте следующий трек-код.",
    },
    "no_track_info": {
        "uz": "📭 <b>Yukingiz trek kodsizmi?</b>\n\n"
              "Bizga murojaat qiling va biz sizga trek kod yaratib, xabar beramiz:\n" + CONTACT_BLOCK["uz"] + "\n\n"
              "Yoki pastdagi «📨 So'rov yuborish» tugmasini bosing — operatorimiz trek kod yaratgach, "
              "sizga shu bot orqali xabar beramiz.",
        "ru": "📭 <b>У вашего груза нет трек-кода?</b>\n\n"
              "Свяжитесь с нами, и мы создадим трек-код и сообщим вам:\n" + CONTACT_BLOCK["ru"] + "\n\n"
              "Или нажмите кнопку «📨 Отправить запрос» ниже — после того как оператор создаст трек-код, "
              "мы уведомим вас через этого бота.",
    },
    "request_sent": {
        "uz": "✅ So'rovingiz qabul qilindi! Operatorimiz trek kod yaratgach, sizga shu yerda xabar beramiz 🔔",
        "ru": "✅ Ваш запрос принят! Как только оператор создаст трек-код, мы сообщим вам здесь 🔔",
    },
    "tracking_header": {"uz": "🔍 <b>Faol yuklaringiz ({n} ta):</b>", "ru": "🔍 <b>Ваши активные грузы ({n}):</b>"},
    "tracking_empty": {
        "uz": "📭 Hozircha faol yuklaringiz yo'q.\n\nYuk qo'shish uchun «📦 Kargo xizmati» bo'limiga o'ting.",
        "ru": "📭 Пока у вас нет активных грузов.\n\nЧтобы добавить груз, перейдите в раздел «📦 Карго услуги».",
    },
    "my_menu": {"uz": "🗂 Qaysi yuklarni ko'rmoqchisiz?", "ru": "🗂 Какие грузы показать?"},
    "inactive_header": {"uz": "⚪️ <b>Yakunlangan yuklaringiz ({n} ta):</b>", "ru": "⚪️ <b>Ваши завершённые грузы ({n}):</b>"},
    "inactive_empty": {"uz": "📭 Yakunlangan yuklaringiz yo'q.", "ru": "📭 Завершённых грузов нет."},
    "no_code": {"uz": "trek kod hali berilmagan", "ru": "трек-код ещё не присвоен"},
    "settings": {
        "uz": "⚙️ <b>Sozlamalar</b>\n\n👤 Ism: {name}\n📱 Telefon: {phone}\n🌐 Til: O'zbekcha\n"
              "🆔 Mijoz kodlari: ✈️ <code>{a}</code> | 🚛 <code>{f}</code>",
        "ru": "⚙️ <b>Настройки</b>\n\n👤 Имя: {name}\n📱 Телефон: {phone}\n🌐 Язык: Русский\n"
              "🆔 Коды клиента: ✈️ <code>{a}</code> | 🚛 <code>{f}</code>",
    },
    "saved": {"uz": "✅ Saqlandi!", "ru": "✅ Сохранено!"},
    "contact": {
        "uz": "☎️ <b>Biz bilan bog'lanish</b>\n\n" + CONTACT_BLOCK["uz"] + "\n\nSavollaringiz bo'lsa, bemalol yozing — yordam beramiz! 🤝",
        "ru": "☎️ <b>Связаться с нами</b>\n\n" + CONTACT_BLOCK["ru"] + "\n\nЕсли есть вопросы — пишите, мы поможем! 🤝",
    },
    "unknown": {"uz": "Iltimos, menyudagi tugmalardan foydalaning 👇", "ru": "Пожалуйста, используйте кнопки меню 👇"},
    "notify_status": {
        "uz": "🔔 <b>Yuk holati yangilandi!</b>\n\n📦 Turi: <b>{kind}</b>\n🔢 Trek kod: <code>{code}</code>\n📍 Yangi holat: <b>{status}</b>",
        "ru": "🔔 <b>Статус груза обновлён!</b>\n\n📦 Тип: <b>{kind}</b>\n🔢 Трек-код: <code>{code}</code>\n📍 Новый статус: <b>{status}</b>",
    },
    "notify_tracking": {
        "uz": "🔔 <b>Yukingizga trek kod berildi!</b>\n\n📦 Turi: <b>{kind}</b>\n🔢 Trek kod: <code>{code}</code>\n📍 Holati: {status}\n\n"
              "Yuk holatini «🔍 Treking» bo'limida kuzatib borishingiz mumkin.",
        "ru": "🔔 <b>Вашему грузу присвоен трек-код!</b>\n\n📦 Тип: <b>{kind}</b>\n🔢 Трек-код: <code>{code}</code>\n📍 Статус: {status}\n\n"
              "Следить за статусом можно в разделе «🔍 Трекинг».",
    },
    "faq": {
        "uz": "❓ <b>Ko'p beriladigan savollar</b>\n\n"
              "<b>1. Mijoz kodi nima?</b>\n"
              "Ro'yxatdan o'tganingizda sizga doimiy kod beriladi: AVIA uchun <code>A001</code>, FURA uchun <code>F001</code> ko'rinishida. "
              "Xitoy saytlarida buyurtma berayotganda manzil va qabul qiluvchi qatoriga albatta shu kodni yozing.\n\n"
              "<b>2. Ombor manzilini qayerdan olaman?</b>\n"
              "«📦 Kargo xizmati» → AVIA yoki FURA ni tanlang. Manzil sizning kodingiz bilan tayyor holda chiqadi — nusxa olib, saytga qo'ying.\n\n"
              "<b>3. Trek kod nima va uni qayerdan topaman?</b>\n"
              f"Trek kod — do'kon yuborgan posilkaning raqami. Yo'riqnoma: {LINK_TRACK_HELP}\n\n"
              "<b>4. Trek kodim bo'lmasa nima qilaman?</b>\n"
              "«📭 Trek kodim yo'q» tugmasi orqali so'rov yuboring yoki biz bilan bog'laning — trek kodni o'zimiz yaratib beramiz.\n\n"
              "<b>5. Yukim qayerdaligini qanday bilaman?</b>\n"
              "«🔍 Treking» bo'limida. Har safar holat o'zgarganda bot sizga avtomatik xabar yuboradi.\n\n"
              "<b>6. Narxlar va muddatlar qanday?</b>\n"
              "«📦 Kargo xizmati» bo'limida har bir yo'nalish uchun ko'rsatilgan.\n\n"
              "<b>7. Gabarit (hajmli) og'irlik qanday hisoblanadi?</b>\n"
              f"Yo'riqnoma: {LINK_VOLUME_HELP}\n\n"
              "<b>8. Qanday yuklarni jo'natib bo'lmaydi?</b>\n"
              f"Taqiqlangan yuklar ro'yxati: {LINK_FORBIDDEN}\n\n"
              "Boshqa savollar bo'yicha:\n" + CONTACT_BLOCK["uz"],
        "ru": "❓ <b>Частые вопросы</b>\n\n"
              "<b>1. Что такое код клиента?</b>\n"
              "При регистрации вам присваивается постоянный код: для АВИА — вида <code>A001</code>, для ФУРЫ — <code>F001</code>. "
              "При заказе на китайских сайтах обязательно указывайте этот код в адресе и в поле получателя.\n\n"
              "<b>2. Где взять адрес склада?</b>\n"
              "«📦 Карго услуги» → выберите АВИА или ФУРА. Адрес будет готов уже с вашим кодом — скопируйте и вставьте на сайте.\n\n"
              "<b>3. Что такое трек-код и где его найти?</b>\n"
              f"Трек-код — номер посылки, отправленной магазином. Инструкция: {LINK_TRACK_HELP}\n\n"
              "<b>4. Что делать, если нет трек-кода?</b>\n"
              "Отправьте запрос кнопкой «📭 У меня нет трек-кода» или свяжитесь с нами — мы сами создадим трек-код.\n\n"
              "<b>5. Как узнать, где мой груз?</b>\n"
              "В разделе «🔍 Трекинг». При каждом изменении статуса бот автоматически пришлёт уведомление.\n\n"
              "<b>6. Какие цены и сроки?</b>\n"
              "Указаны в разделе «📦 Карго услуги» для каждого направления.\n\n"
              "<b>7. Как считается габаритный (объёмный) вес?</b>\n"
              f"Инструкция: {LINK_VOLUME_HELP}\n\n"
              "<b>8. Какие грузы запрещены?</b>\n"
              f"Список запрещённых грузов: {LINK_FORBIDDEN}\n\n"
              "По другим вопросам:\n" + CONTACT_BLOCK["ru"],
    },
}


def t(key: str, lang: str = "uz", **kw) -> str:
    text = T[key].get(lang) or T[key]["uz"]
    return text.format(**kw) if kw else text


def all_variants(key: str) -> set[str]:
    return set(T[key].values())


def kind_name(kind: str, lang: str) -> str:
    if lang == "ru":
        return "АВИА" if kind == "AVIA" else "ФУРА"
    return kind


def kind_info(kind: str, code: str, lang: str, s: dict[str, str]) -> str:
    """Warehouse address (translation first, then the original Chinese) + terms + links."""
    p = "avia" if kind == "AVIA" else "fura"
    price, min_w = s.get(f"{p}_price", ""), s.get(f"{p}_min_weight", "")
    pack, transit = s.get(f"{p}_pack_days", ""), s.get(f"{p}_transit_days", "")
    icon = "✈️" if kind == "AVIA" else "🚛"
    kname = kind_name(kind, lang)

    original = (
        f"收货人：{code}\n"
        f"手机：{WAREHOUSE_PHONE}\n"
        f"地址：{WAREHOUSE_ADDRESS_CN} （客户号 {code} )\n"
        f"邮编{WAREHOUSE_ZIP}"
    )

    if lang == "ru":
        parts = [
            f"{icon} <b>{kname} карго</b>\n",
            "📍 <b>Адрес нашего склада в Китае (перевод):</b>",
            f"👤 Получатель: <b>{code}</b>",
            f"📞 Телефон: {WAREHOUSE_PHONE}",
            "🏠 Адрес: провинция Гуандун, г. Фошань, район Наньхай, посёлок Лишуй, "
            f"промышленная зона Шэнли, д. 29, «Dragon Life» логистика (номер клиента: {code})",
            f"📮 Индекс: {WAREHOUSE_ZIP}\n",
            "📋 <b>Оригинал (скопируйте и вставьте на китайском сайте без изменений):</b>",
            f"<pre>{original}</pre>\n",
        ]
        if pack and transit:
            parts.append(
                f"⏱ Почта «{kname}» по прибытии на наш склад упаковывается и отправляется в путь "
                f"в течение {pack} дней. В Ташкент почта прибывает в течение {transit} дней после отправления.\n"
            )
        else:
            parts.append("⏱ По срокам доставки уточняйте у нашего оператора.\n")
        parts.append(f"💰 <b>Цены на «{kname}» карго:</b>")
        if price:
            parts.append((f"от {min_w} кг, " if min_w else "") + f"за 1 килограмм — <b>{price} USD</b>\n")
        else:
            parts.append("уточняйте у нашего оператора\n")
        parts += [
            f"🔎 Инструкция по поиску трек-кодов входящей почты в Pinduoduo или Taobao: ➡️ {LINK_TRACK_HELP}\n",
            f"📐 Инструкция по измерению габаритных изделий (объёмный вес): ➡️ {LINK_VOLUME_HELP}\n",
            f"🚫 Список запрещённых грузов: ➡️ {LINK_FORBIDDEN}",
        ]
    else:
        parts = [
            f"{icon} <b>{kname} kargo</b>\n",
            "📍 <b>Xitoydagi omborimiz manzili (tarjimasi):</b>",
            f"👤 Qabul qiluvchi: <b>{code}</b>",
            f"📞 Telefon: {WAREHOUSE_PHONE}",
            "🏠 Manzil: Guangdong provinsiyasi, Foshan shahri, Nanhai tumani, Lishui shaharchasi, "
            f"Shengli sanoat zonasi, 29-uy, «Dragon Life» logistika (mijoz raqami: {code})",
            f"📮 Pochta indeksi: {WAREHOUSE_ZIP}\n",
            "📋 <b>Asl nusxasi (nusxa olib, xitoy saytiga o'zgartirmasdan qo'ying):</b>",
            f"<pre>{original}</pre>\n",
        ]
        if pack and transit:
            parts.append(
                f"⏱ «{kname}» pochtasi omborimizga yetib kelgach, {pack} kun ichida qadoqlanib yo'lga jo'natiladi. "
                f"Jo'natilgandan so'ng {transit} kun ichida Toshkentga yetib keladi.\n"
            )
        else:
            parts.append("⏱ Yetkazib berish muddatlarini operatorimizdan aniqlang.\n")
        parts.append(f"💰 <b>«{kname}» kargo narxlari:</b>")
        if price:
            parts.append((f"{min_w} kg dan boshlab, " if min_w else "") + f"1 kilogramm uchun — <b>{price} USD</b>\n")
        else:
            parts.append("operatorimizdan aniqlang\n")
        parts += [
            f"🔎 Pinduoduo yoki Taobao'dan kelayotgan pochtaning trek kodini topish yo'riqnomasi: ➡️ {LINK_TRACK_HELP}\n",
            f"📐 Gabarit mahsulotlarni o'lchash (hajmli og'irlik) yo'riqnomasi: ➡️ {LINK_VOLUME_HELP}\n",
            f"🚫 Taqiqlangan yuklar ro'yxati: ➡️ {LINK_FORBIDDEN}",
        ]
    return "\n".join(parts)
