#!/usr/bin/env python3
"""
🏋️ ФОРМА — AI Персональный Тренер & Диетолог
Telegram Bot | Полная версия с оплатой, рефералами и админ-панелью
"""

import os
import logging
import sqlite3
import hashlib
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler,
    PreCheckoutQueryHandler
)

# ─── НАСТРОЙКИ ────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOOKASSA_TOKEN = os.getenv("YOOKASSA_TOKEN")   # Вставить токен ЮКассы
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x]  # ID админов через запятую

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ─── СОСТОЯНИЯ ДИАЛОГА ────────────────────────────────────────
(
    MAIN_MENU, CHOOSE_GOAL, CHOOSE_LEVEL, CHOOSE_PLACE,
    SHOW_PLAN, NUTRITION_MENU, SUBSCRIPTION_MENU, PROFILE_MENU,
    ADMIN_MENU
) = range(9)

# ─── ТАРИФЫ ───────────────────────────────────────────────────
PLANS = {
    "start": {
        "name": "🆓 Старт",
        "price": 0,
        "desc": "7 дней бесплатно • Базовый план • 1 цель",
        "features": ["✅ 7-дневный план тренировок", "✅ Базовые советы по питанию", "✅ Трекер прогресса", "❌ AI-чат с тренером", "❌ План питания"],
    },
    "forma": {
        "name": "💪 Форма",
        "price": 199,
        "desc": "199 ₽/мес • Полный план тренировок + питание",
        "features": ["✅ Персональный план тренировок", "✅ Трекер прогресса", "✅ Базовый план питания", "✅ Еженедельная адаптация", "❌ AI-чат 24/7"],
    },
    "pro": {
        "name": "🔥 Прокачка",
        "price": 499,
        "desc": "499 ₽/мес • Полный план + AI-тренер 24/7",
        "features": ["✅ Полный план тренировок", "✅ Детальный план питания", "✅ Фото-анализ еды", "✅ AI-чат с тренером 24/7", "✅ Адаптация плана каждую неделю"],
    },
    "result": {
        "name": "🏆 Результат",
        "price": 999,
        "desc": "999 ₽/мес • Всё + живой куратор раз в месяц",
        "features": ["✅ Всё из тарифа Прокачка", "✅ Анализ техники по фото", "✅ Приоритетные ответы", "✅ Разбор с куратором 1×/мес", "✅ Программа под ваше событие"],
    },
}

# ─── ТРЕНИРОВКИ ───────────────────────────────────────────────
WORKOUTS = {
    "похудение": {
        "beginner": [
            "День 1: 🏃 Кардио 30 мин + Приседания 3×15 + Планка 3×30 сек",
            "День 2: 🧘 Активное восстановление — растяжка 20 мин",
            "День 3: 🔥 Берпи 3×10 + Выпады 3×12 + Скакалка 15 мин",
            "День 4: 😴 Отдых",
            "День 5: 🏃 Интервальный бег 25 мин + Пресс 3×20",
            "День 6: 💪 Отжимания 3×10 + Приседания 3×20 + Планка 3×45 сек",
            "День 7: 🧘 Йога 30 мин",
        ],
        "intermediate": [
            "День 1: 🔥 HIIT 40 мин + Присед с весом 4×15",
            "День 2: 🏃 Бег 5 км + Планка 4×1 мин",
            "День 3: 💪 Круговая тренировка: 5 упр × 4 подхода",
            "День 4: 😴 Активный отдых — плавание или велосипед",
            "День 5: 🔥 Табата 30 мин + Выпады 4×15",
            "День 6: 🏃 Кардио 45 мин + Пресс комплекс",
            "День 7: 🧘 Растяжка и МФР",
        ],
    },
    "набор массы": {
        "beginner": [
            "День 1: 💪 Грудь/Трицепс — Жим лёжа 3×8, Отжимания 3×12, Разводка 3×10",
            "День 2: 🦵 Ноги — Приседания 3×10, Жим ногами 3×12, Выпады 3×10",
            "День 3: 😴 Отдых",
            "День 4: 🔙 Спина/Бицепс — Тяга 3×8, Подтягивания 3×max, Сгибания 3×12",
            "День 5: 🏋️ Плечи — Жим стоя 3×10, Разводки 3×12, Шраги 3×15",
            "День 6: 💪 Руки + Пресс — Суперсеты 4 упр × 3 подхода",
            "День 7: 😴 Отдых",
        ],
    },
    "поддержание": {
        "beginner": [
            "День 1: 🏃 Кардио 30 мин + Силовой комплекс 3×12",
            "День 2: 🧘 Йога или пилатес 45 мин",
            "День 3: 💪 Функциональный тренинг 40 мин",
            "День 4: 😴 Отдых",
            "День 5: 🔥 Круговая тренировка 35 мин",
            "День 6: 🏊 Плавание или велосипед 45 мин",
            "День 7: 🧘 Растяжка 30 мин",
        ],
    },
}

# ─── ПЛАНЫ ПИТАНИЯ ────────────────────────────────────────────
NUTRITION_PLANS = {
    "похудение": """🥗 *План питания — Похудение*

📊 *Калорийность:* ~1600–1800 ккал/день
💧 *Вода:* 2–2.5 литра в день

━━━━━━━━━━━━━━━━━━
🌅 *Завтрак (7:00–9:00)*
• Овсянка на воде — 150г
• 2 яйца варёных
• Зелёный чай без сахара

🍎 *Перекус (11:00)*
• Яблоко или груша
• Горсть орехов (20г)

🌿 *Обед (13:00–14:00)*
• Куриная грудка — 150г
• Бурый рис или гречка — 100г (сухой)
• Свежий овощной салат

🥜 *Перекус (16:00)*
• Творог 0% — 150г
• Ягоды — 50г

🌙 *Ужин (18:00–19:00)*
• Рыба запечённая — 150г
• Овощи на пару — 200г
• Кефир — 200 мл
━━━━━━━━━━━━━━━━━━
💡 *Совет:* Ужин не позже 19:00. Голод вечером — норма!""",

    "набор массы": """🥩 *План питания — Набор массы*

📊 *Калорийность:* ~2800–3200 ккал/день
💧 *Вода:* 3–3.5 литра в день

━━━━━━━━━━━━━━━━━━
🌅 *Завтрак (7:00)*
• Овсянка на молоке — 200г
• 4 яйца (2 целых + 2 белка)
• Банан + стакан молока

🍎 *Перекус (10:00)*
• Творог 5% — 200г с мёдом
• Хлеб цельнозерновой — 2 куска

🌿 *Обед (13:00)*
• Говядина/курица — 200г
• Рис/гречка — 150г (сухой)
• Салат с оливковым маслом

🥤 *После тренировки*
• Протеиновый коктейль
• Банан или рисовые хлебцы

🌙 *Ужин (19:00)*
• Лосось — 200г
• Картофель отварной — 200г
• Овощи — 150г
━━━━━━━━━━━━━━━━━━
💡 *Совет:* Главное — профицит калорий 300–500 ккал/день""",
}

# ══════════════════════════════════════════════════════════════
# БАЗА ДАННЫХ
# ══════════════════════════════════════════════════════════════

def init_db():
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            plan TEXT DEFAULT 'free',
            plan_expires TEXT,
            goal TEXT,
            level TEXT,
            ref_code TEXT UNIQUE,
            referred_by INTEGER,
            bonus_months INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan TEXT,
            amount INTEGER,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referee_id INTEGER,
            bonus_given INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_or_create_user(user_id, username, first_name):
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        ref_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8]
        c.execute(
            "INSERT INTO users (user_id, username, first_name, ref_code) VALUES (?,?,?,?)",
            (user_id, username, first_name, ref_code)
        )
        conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        cols = ["user_id","username","first_name","plan","plan_expires","goal","level","ref_code","referred_by","bonus_months","created_at"]
        return dict(zip(cols, row))
    return None

def set_user_plan(user_id, plan, months=1):
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    expires = (datetime.now() + timedelta(days=30*months)).strftime("%Y-%m-%d")
    c.execute("UPDATE users SET plan=?, plan_expires=? WHERE user_id=?", (plan, expires, user_id))
    conn.commit()
    conn.close()

def add_bonus_month(user_id):
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("UPDATE users SET bonus_months = bonus_months + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_referral_by_code(ref_code):
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE ref_code=?", (ref_code,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def save_referral(referrer_id, referee_id):
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("UPDATE users SET referred_by=? WHERE user_id=?", (referrer_id, referee_id))
    c.execute("INSERT INTO referrals (referrer_id, referee_id) VALUES (?,?)", (referrer_id, referee_id))
    conn.commit()
    conn.close()

def get_referral_count(user_id):
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def log_payment(user_id, plan, amount, status):
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("INSERT INTO payments (user_id, plan, amount, status) VALUES (?,?,?,?)",
              (user_id, plan, amount, status))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE plan != 'free'")
    paid_users = c.fetchone()[0]
    c.execute("SELECT SUM(amount) FROM payments WHERE status='success'")
    revenue = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM referrals")
    total_refs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE created_at >= date('now', '-7 days')")
    new_week = c.fetchone()[0]
    conn.close()
    return {
        "total_users": total_users,
        "paid_users": paid_users,
        "revenue": revenue,
        "total_refs": total_refs,
        "new_week": new_week,
    }

def get_top_referrers():
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("""
        SELECT u.first_name, u.username, COUNT(r.id) as cnt
        FROM referrals r JOIN users u ON r.referrer_id = u.user_id
        GROUP BY r.referrer_id ORDER BY cnt DESC LIMIT 10
    """)
    rows = c.fetchall()
    conn.close()
    return rows

# ══════════════════════════════════════════════════════════════
# СТАРТ
# ══════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name)

    # Обработка реферальной ссылки
    if context.args:
        ref_code = context.args[0]
        referrer_id = get_referral_by_code(ref_code)
        db_user = get_user(user.id)
        if referrer_id and referrer_id != user.id and not db_user.get("referred_by"):
            save_referral(referrer_id, user.id)
            add_bonus_month(referrer_id)
            try:
                await context.bot.send_message(
                    referrer_id,
                    "🎉 По твоей реферальной ссылке зарегистрировался новый пользователь!\n"
                    "✅ Тебе начислен *+1 месяц* бесплатно!",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    db_user = get_user(user.id)
    ref_count = get_referral_count(user.id)

    welcome_text = (
        f"👋 Привет, *{user.first_name}*!\n\n"
        "Я — *ФОРМА*, твой персональный AI-тренер и диетолог 💪\n\n"
        "Я помогу тебе:\n"
        "🏋️ Составить план тренировок под твои цели\n"
        "🥗 Разработать персональный план питания\n"
        "📊 Отслеживать прогресс каждую неделю\n"
        "🤖 Ответить на любые вопросы по здоровью 24/7\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎁 *7 дней бесплатно* — без карты, без обязательств!\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Выбери с чего начнём:"
    )
    keyboard = [
        [InlineKeyboardButton("🚀 Начать бесплатно", callback_data="free_start")],
        [InlineKeyboardButton("💰 Тарифы и цены", callback_data="show_plans")],
        [InlineKeyboardButton("👥 Реферальная программа", callback_data="referral_menu")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
    ]
    if user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔐 Админ-панель", callback_data="admin_menu")])

    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return MAIN_MENU

# ══════════════════════════════════════════════════════════════
# РЕФЕРАЛЬНАЯ СИСТЕМА
# ══════════════════════════════════════════════════════════════

async def referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    db_user = get_user(user.id)
    ref_count = get_referral_count(user.id)
    ref_code = db_user["ref_code"]
    bot_username = (await context.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={ref_code}"

    text = (
        "👥 *Реферальная программа ФОРМА*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎁 *Как это работает:*\n\n"
        "1️⃣ Поделись своей ссылкой с другом\n"
        "2️⃣ Друг регистрируется по ней\n"
        "3️⃣ *Тебе* — +1 месяц бесплатно 🎉\n"
        "4️⃣ *Другу* — скидка 20% на первую оплату\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔗 *Бонус за друга друга:*\n"
        "Если твой друг тоже приведёт друга — ты получишь ещё +7 дней!\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 Твоих рефералов: *{ref_count}*\n"
        f"🎁 Бонусных месяцев: *{db_user['bonus_months']}*\n\n"
        f"🔗 *Твоя ссылка:*\n`{ref_link}`\n\n"
        "_(нажми чтобы скопировать)_"
    )
    keyboard = [
        [InlineKeyboardButton("📤 Поделиться ссылкой", switch_inline_query=f"Присоединяйся к ФОРМА — AI-тренер в Telegram! {ref_link}")],
        [InlineKeyboardButton("← Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return MAIN_MENU

# ══════════════════════════════════════════════════════════════
# ВЫБОР ЦЕЛИ / УРОВНЯ / МЕСТА
# ══════════════════════════════════════════════════════════════

async def free_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "🎯 *Выбери свою главную цель:*\n\n"
        "От этого зависит весь план тренировок и питания"
    )
    keyboard = [
        [InlineKeyboardButton("🔥 Похудеть", callback_data="goal_похудение")],
        [InlineKeyboardButton("💪 Набрать мышечную массу", callback_data="goal_набор массы")],
        [InlineKeyboardButton("⚖️ Поддержать форму", callback_data="goal_поддержание")],
        [InlineKeyboardButton("← Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return CHOOSE_GOAL

async def choose_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    goal = query.data.replace("goal_", "")
    context.user_data["goal"] = goal
    text = (
        f"✅ Цель: *{goal.capitalize()}*\n\n"
        "💡 *Теперь укажи уровень подготовки:*"
    )
    keyboard = [
        [InlineKeyboardButton("🌱 Новичок (до 6 месяцев)", callback_data="level_beginner")],
        [InlineKeyboardButton("🔥 Средний (6 мес – 2 года)", callback_data="level_intermediate")],
        [InlineKeyboardButton("⚡ Продвинутый (2+ года)", callback_data="level_advanced")],
        [InlineKeyboardButton("← Назад", callback_data="free_start")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return CHOOSE_LEVEL

async def choose_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = query.data.replace("level_", "")
    context.user_data["level"] = level
    level_names = {"beginner": "Новичок", "intermediate": "Средний", "advanced": "Продвинутый"}
    text = (
        f"✅ Уровень: *{level_names.get(level, level)}*\n\n"
        "🏟️ *Где будешь тренироваться?*"
    )
    keyboard = [
        [InlineKeyboardButton("🏠 Дома (без оборудования)", callback_data="place_home")],
        [InlineKeyboardButton("🏋️ В зале", callback_data="place_gym")],
        [InlineKeyboardButton("🌳 На улице", callback_data="place_street")],
        [InlineKeyboardButton("← Назад", callback_data="free_start")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return CHOOSE_PLACE

async def show_workout_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    place = query.data.replace("place_", "")
    context.user_data["place"] = place
    goal = context.user_data.get("goal", "поддержание")
    level = context.user_data.get("level", "beginner")
    workouts = WORKOUTS.get(goal, WORKOUTS["поддержание"]).get(level, WORKOUTS["поддержание"]["beginner"])
    place_emoji = {"home": "🏠", "gym": "🏋️", "street": "🌳"}.get(place, "🏠")
    place_name = {"home": "Дома", "gym": "В зале", "street": "На улице"}.get(place, "Дома")
    plan_text = f"🎉 *Твой персональный план на 7 дней готов!*\n\n"
    plan_text += f"🎯 Цель: *{goal.capitalize()}* | {place_emoji} *{place_name}*\n"
    plan_text += "━━━━━━━━━━━━━━━━━━\n\n"
    for workout in workouts:
        plan_text += f"*{workout}*\n\n"
    plan_text += (
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 *Хочешь полный план питания и AI-тренера?*\n"
        "Подключи тариф *Форма* за 199 ₽/мес 🔥"
    )
    keyboard = [
        [InlineKeyboardButton("🥗 Получить план питания", callback_data="nutrition_plan")],
        [InlineKeyboardButton("💳 Подключить тариф", callback_data="show_plans")],
        [InlineKeyboardButton("🔄 Другой план", callback_data="free_start")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
    ]
    await query.edit_message_text(plan_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return SHOW_PLAN

# ══════════════════════════════════════════════════════════════
# ПИТАНИЕ
# ══════════════════════════════════════════════════════════════

async def nutrition_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    goal = context.user_data.get("goal", "похудение")
    plan = NUTRITION_PLANS.get(goal, NUTRITION_PLANS["похудение"])
    keyboard = [
        [InlineKeyboardButton("💳 Получить полный план (Прокачка)", callback_data="show_plans")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
    ]
    await query.edit_message_text(plan, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return NUTRITION_MENU

# ══════════════════════════════════════════════════════════════
# ТАРИФЫ И ОПЛАТА (ЮКАССА)
# ══════════════════════════════════════════════════════════════

async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    db_user = get_user(user.id)

    # Проверяем реферальную скидку
    has_discount = bool(db_user and db_user.get("referred_by"))
    discount_text = "\n🎁 *У тебя есть скидка 20%* на первую оплату!" if has_discount else ""

    text = (
        f"💳 *Выбери свой тариф:*{discount_text}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🆓 *Старт* — Бесплатно\n7 дней • Базовый план\n\n"
        "💪 *Форма* — 199 ₽/мес\nПерсональный план + питание\n\n"
        "🔥 *Прокачка* — 499 ₽/мес\nВсё выше + AI-тренер 24/7\n\n"
        "🏆 *Результат* — 999 ₽/мес\nМаксимум + живой куратор\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    keyboard = [
        [InlineKeyboardButton("🆓 Начать бесплатно", callback_data="plan_start")],
        [InlineKeyboardButton("💪 Форма — 199 ₽/мес", callback_data="plan_forma")],
        [InlineKeyboardButton("🔥 Прокачка — 499 ₽/мес", callback_data="plan_pro")],
        [InlineKeyboardButton("🏆 Результат — 999 ₽/мес", callback_data="plan_result")],
        [InlineKeyboardButton("← Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return SUBSCRIPTION_MENU

async def plan_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace("plan_", "")
    plan = PLANS.get(plan_key, PLANS["forma"])
    features_text = "\n".join(plan["features"])

    user = update.effective_user
    db_user = get_user(user.id)
    has_discount = bool(db_user and db_user.get("referred_by"))

    price = plan["price"]
    price_text = f"{price} ₽/месяц"
    if has_discount and price > 0:
        discounted = int(price * 0.8)
        price_text = f"~~{price}~~ → *{discounted} ₽/месяц* (скидка 20%)"
        context.user_data["discounted_price"] = discounted
    else:
        context.user_data["discounted_price"] = price

    context.user_data["selected_plan"] = plan_key

    text = (
        f"*{plan['name']}*\n"
        f"💰 {price_text}\n\n"
        f"{features_text}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Выбери этот тариф?"
    )
    keyboard = []
    if plan["price"] == 0:
        keyboard.append([InlineKeyboardButton("✅ Активировать бесплатно", callback_data="activate_free")])
    else:
        keyboard.append([InlineKeyboardButton(f"💳 Оплатить через ЮКассу", callback_data=f"pay_{plan_key}")])
    keyboard.append([InlineKeyboardButton("← К тарифам", callback_data="show_plans")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return SUBSCRIPTION_MENU

async def activate_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    set_user_plan(user.id, "free", months=0)
    text = (
        "🎉 *Тариф Старт активирован!*\n\n"
        "У тебя есть *7 дней бесплатного доступа*\n\n"
        "Что хочешь сделать первым?"
    )
    keyboard = [
        [InlineKeyboardButton("🏋️ Получить план тренировок", callback_data="free_start")],
        [InlineKeyboardButton("🥗 Посмотреть план питания", callback_data="nutrition_plan")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return MAIN_MENU

async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляем invoice через ЮКассу"""
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace("pay_", "")
    plan = PLANS.get(plan_key, PLANS["forma"])
    price = context.user_data.get("discounted_price", plan["price"])

    if not YOOKASSA_TOKEN:
        await query.edit_message_text(
            "⚠️ Платёжная система не настроена.\n"
            "Администратор должен добавить YOOKASSA_TOKEN в переменные окружения.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="show_plans")]])
        )
        return SUBSCRIPTION_MENU

    context.user_data["paying_plan"] = plan_key
    await query.message.delete()
    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title=f"Тариф {plan['name']}",
        description=plan["desc"],
        payload=f"plan_{plan_key}_{query.from_user.id}",
        provider_token=YOOKASSA_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(plan["name"], price * 100)],  # в копейках
        start_parameter="pay",
    )
    return SUBSCRIPTION_MENU

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение перед оплатой"""
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Успешная оплата — активируем тариф"""
    user = update.effective_user
    payment = update.message.successful_payment
    payload = payment.invoice_payload  # plan_forma_12345
    parts = payload.split("_")
    plan_key = parts[1] if len(parts) > 1 else "forma"
    amount = payment.total_amount // 100

    set_user_plan(user.id, plan_key, months=1)
    log_payment(user.id, plan_key, amount, "success")

    # Бонус рефереру за оплату друга
    db_user = get_user(user.id)
    if db_user and db_user.get("referred_by"):
        referrer_id = db_user["referred_by"]
        conn = sqlite3.connect("forma.db")
        c = conn.cursor()
        c.execute("SELECT bonus_given FROM referrals WHERE referrer_id=? AND referee_id=?",
                  (referrer_id, user.id))
        ref_row = c.fetchone()
        if ref_row and ref_row[0] == 0:
            c.execute("UPDATE referrals SET bonus_given=1 WHERE referrer_id=? AND referee_id=?",
                      (referrer_id, user.id))
            conn.commit()
            conn.close()
            add_bonus_month(referrer_id)
            try:
                await context.bot.send_message(
                    referrer_id,
                    f"🏆 Твой реферал оплатил подписку!\n"
                    f"✅ Тебе начислен ещё *+1 месяц* бесплатно!",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        else:
            conn.close()

    plan = PLANS.get(plan_key, PLANS["forma"])
    await update.message.reply_text(
        f"🎉 *Оплата прошла успешно!*\n\n"
        f"✅ Тариф *{plan['name']}* активирован на 1 месяц\n"
        f"💰 Списано: {amount} ₽\n\n"
        f"Наслаждайся тренировками! 💪",
        parse_mode="Markdown"
    )

# ══════════════════════════════════════════════════════════════
# ПРОФИЛЬ
# ══════════════════════════════════════════════════════════════

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    db_user = get_user(user.id)
    ref_count = get_referral_count(user.id)
    bot_username = (await context.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={db_user['ref_code']}"

    plan_names = {"free": "🆓 Старт", "forma": "💪 Форма", "pro": "🔥 Прокачка", "result": "🏆 Результат"}
    plan_display = plan_names.get(db_user["plan"], "🆓 Старт")
    expires = db_user.get("plan_expires") or "—"
    goal = db_user.get("goal") or context.user_data.get("goal", "Не выбрана")

    text = (
        f"👤 *Профиль — {user.first_name}*\n\n"
        f"🎯 Цель: *{goal.capitalize() if goal and goal != 'Не выбрана' else 'Не выбрана'}*\n"
        f"💳 Тариф: *{plan_display}*\n"
        f"📅 Действует до: *{expires}*\n"
        f"🎁 Бонусных месяцев: *{db_user['bonus_months']}*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👥 Рефералов приглашено: *{ref_count}*\n"
        f"🔗 Твоя ссылка:\n`{ref_link}`\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    keyboard = [
        [InlineKeyboardButton("🔄 Изменить цель", callback_data="free_start")],
        [InlineKeyboardButton("💳 Изменить тариф", callback_data="show_plans")],
        [InlineKeyboardButton("👥 Реферальная программа", callback_data="referral_menu")],
        [InlineKeyboardButton("← Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return PROFILE_MENU

# ══════════════════════════════════════════════════════════════
# АДМИН-ПАНЕЛЬ
# ══════════════════════════════════════════════════════════════

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in ADMIN_IDS:
        await query.answer("⛔ Нет доступа", show_alert=True)
        return MAIN_MENU

    stats = get_stats()
    text = (
        "🔐 *Админ-панель ФОРМА*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👥 Всего пользователей: *{stats['total_users']}*\n"
        f"💳 Платных подписок: *{stats['paid_users']}*\n"
        f"💰 Общая выручка: *{stats['revenue']} ₽*\n"
        f"👥 Рефералов всего: *{stats['total_refs']}*\n"
        f"🆕 Новых за 7 дней: *{stats['new_week']}*\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    keyboard = [
        [InlineKeyboardButton("📊 Статистика подробно", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Топ рефереры", callback_data="admin_referrers")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("← Главное меню", callback_data="back_main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return ADMIN_MENU

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in ADMIN_IDS:
        return ADMIN_MENU

    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("SELECT plan, COUNT(*) FROM users GROUP BY plan")
    plan_counts = c.fetchall()
    c.execute("SELECT SUM(amount), COUNT(*) FROM payments WHERE status='success'")
    pay_row = c.fetchone()
    c.execute("SELECT COUNT(*) FROM users WHERE created_at >= date('now', '-1 day')")
    new_today = c.fetchone()[0]
    conn.close()

    plan_text = ""
    for plan, cnt in plan_counts:
        plan_text += f"  • {plan}: {cnt}\n"

    text = (
        "📊 *Подробная статистика*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"*По тарифам:*\n{plan_text}\n"
        f"*Платежи:*\n"
        f"  • Сумма: {pay_row[0] or 0} ₽\n"
        f"  • Транзакций: {pay_row[1] or 0}\n\n"
        f"*Активность:*\n"
        f"  • Новых сегодня: {new_today}\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    keyboard = [[InlineKeyboardButton("← Назад", callback_data="admin_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return ADMIN_MENU

async def admin_referrers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in ADMIN_IDS:
        return ADMIN_MENU

    top = get_top_referrers()
    if top:
        lines = ""
        for i, (name, username, cnt) in enumerate(top, 1):
            uname = f"@{username}" if username else name
            lines += f"{i}. {uname} — {cnt} чел.\n"
    else:
        lines = "Пока нет данных"

    text = (
        "👥 *Топ рефереры*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{lines}"
        "━━━━━━━━━━━━━━━━━━"
    )
    keyboard = [[InlineKeyboardButton("← Назад", callback_data="admin_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return ADMIN_MENU

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in ADMIN_IDS:
        return ADMIN_MENU

    context.user_data["awaiting_broadcast"] = True
    text = (
        "📢 *Рассылка*\n\n"
        "Напиши сообщение которое хочешь отправить всем пользователям.\n"
        "Поддерживается Markdown форматирование.\n\n"
        "Для отмены напиши /cancel"
    )
    keyboard = [[InlineKeyboardButton("← Назад", callback_data="admin_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return ADMIN_MENU

# ══════════════════════════════════════════════════════════════
# ОСТАЛЬНЫЕ ХЭНДЛЕРЫ
# ══════════════════════════════════════════════════════════════

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "ℹ️ *О боте ФОРМА*\n\n"
        "🤖 AI-персональный тренер и диетолог прямо в Telegram\n\n"
        "🎯 *Что умею:*\n"
        "• Составлять планы тренировок под любую цель\n"
        "• Разрабатывать планы питания с калорийностью\n"
        "• Адаптировать программу каждую неделю\n"
        "• Отвечать на вопросы по здоровью 24/7\n\n"
        "📩 Поддержка: @FormaSupport"
    )
    keyboard = [[InlineKeyboardButton("← Назад", callback_data="back_main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return MAIN_MENU

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    text = (
        f"🏠 *Главное меню*\n\n"
        f"Привет, *{user.first_name}*! Чем займёмся сегодня?"
    )
    keyboard = [
        [InlineKeyboardButton("🚀 Мой план тренировок", callback_data="free_start")],
        [InlineKeyboardButton("🥗 План питания", callback_data="nutrition_plan")],
        [InlineKeyboardButton("💳 Тарифы", callback_data="show_plans")],
        [InlineKeyboardButton("👥 Реферальная программа", callback_data="referral_menu")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
    ]
    if user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔐 Админ-панель", callback_data="admin_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return MAIN_MENU

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    # Обработка рассылки от админа
    if context.user_data.get("awaiting_broadcast") and update.effective_user.id in ADMIN_IDS:
        context.user_data["awaiting_broadcast"] = False
        conn = sqlite3.connect("forma.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = c.fetchall()
        conn.close()
        sent, failed = 0, 0
        for (uid,) in users:
            try:
                await context.bot.send_message(uid, update.message.text, parse_mode="Markdown")
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f"📢 Рассылка завершена!\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}")
        return

    responses = {
        "белок": "💪 *Белок* — главный строительный материал для мышц.\nНорма: *1.6–2.2г на кг веса* в день.\nЛучшие источники: курица, яйца, творог, рыба, бобовые.",
        "калории": "📊 *Калорийность* зависит от цели:\n• Похудение: дефицит 300–500 ккал\n• Набор массы: профицит 300–500 ккал\n• Поддержание: баланс",
        "сколько пить воды": "💧 *Норма воды:* 30–40 мл на кг веса тела.\nПри тренировках +500–700 мл дополнительно.",
        "отжимания": "💪 *Техника отжиманий:*\n1. Руки чуть шире плеч\n2. Тело — прямая линия\n3. Грудь касается пола\n4. Выдох — вверх\n\nНачни с 3×10 и постепенно увеличивай.",
    }
    reply = None
    for key, val in responses.items():
        if key in text:
            reply = val
            break
    if not reply:
        reply = (
            "🤖 Понял твой вопрос! Для развёрнутых ответов от AI-тренера 24/7\n"
            "подключи тариф *Прокачка* (499 ₽/мес)\n\n"
            "А пока — выбери действие в меню ниже:"
        )
    keyboard = [
        [InlineKeyboardButton("🏋️ Мой план тренировок", callback_data="free_start")],
        [InlineKeyboardButton("💳 AI-тренер 24/7", callback_data="show_plans")],
    ]
    await update.message.reply_text(reply, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(free_start, pattern="^free_start$"),
                CallbackQueryHandler(show_plans, pattern="^show_plans$"),
                CallbackQueryHandler(my_profile, pattern="^my_profile$"),
                CallbackQueryHandler(about, pattern="^about$"),
                CallbackQueryHandler(back_main, pattern="^back_main$"),
                CallbackQueryHandler(activate_free, pattern="^activate_free$"),
                CallbackQueryHandler(referral_menu, pattern="^referral_menu$"),
                CallbackQueryHandler(admin_menu, pattern="^admin_menu$"),
            ],
            CHOOSE_GOAL: [
                CallbackQueryHandler(choose_goal, pattern="^goal_"),
                CallbackQueryHandler(free_start, pattern="^free_start$"),
                CallbackQueryHandler(back_main, pattern="^back_main$"),
            ],
            CHOOSE_LEVEL: [
                CallbackQueryHandler(choose_level, pattern="^level_"),
                CallbackQueryHandler(free_start, pattern="^free_start$"),
            ],
            CHOOSE_PLACE: [
                CallbackQueryHandler(show_workout_plan, pattern="^place_"),
                CallbackQueryHandler(free_start, pattern="^free_start$"),
            ],
            SHOW_PLAN: [
                CallbackQueryHandler(nutrition_plan, pattern="^nutrition_plan$"),
                CallbackQueryHandler(show_plans, pattern="^show_plans$"),
                CallbackQueryHandler(free_start, pattern="^free_start$"),
                CallbackQueryHandler(back_main, pattern="^back_main$"),
            ],
            NUTRITION_MENU: [
                CallbackQueryHandler(show_plans, pattern="^show_plans$"),
                CallbackQueryHandler(back_main, pattern="^back_main$"),
            ],
            SUBSCRIPTION_MENU: [
                CallbackQueryHandler(plan_detail, pattern="^plan_"),
                CallbackQueryHandler(activate_free, pattern="^activate_free$"),
                CallbackQueryHandler(process_payment, pattern="^pay_"),
                CallbackQueryHandler(show_plans, pattern="^show_plans$"),
                CallbackQueryHandler(back_main, pattern="^back_main$"),
            ],
            PROFILE_MENU: [
                CallbackQueryHandler(free_start, pattern="^free_start$"),
                CallbackQueryHandler(show_plans, pattern="^show_plans$"),
                CallbackQueryHandler(referral_menu, pattern="^referral_menu$"),
                CallbackQueryHandler(back_main, pattern="^back_main$"),
            ],
            ADMIN_MENU: [
                CallbackQueryHandler(admin_menu, pattern="^admin_menu$"),
                CallbackQueryHandler(admin_stats, pattern="^admin_stats$"),
                CallbackQueryHandler(admin_referrers, pattern="^admin_referrers$"),
                CallbackQueryHandler(admin_broadcast, pattern="^admin_broadcast$"),
                CallbackQueryHandler(back_main, pattern="^back_main$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🏋️ ФОРМА Bot запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
