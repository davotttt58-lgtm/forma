#!/usr/bin/env python3
"""
🏋️ ФОРМА — AI Персональный Тренер & Диетолог
Полная версия: оплата + рефералы + админка + AI-чат + пуши + фото-анализ еды
"""

import os
import json
import base64
import logging
import sqlite3
import hashlib
import httpx
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
Application, CommandHandler, CallbackQueryHandler,
MessageHandler, filters, ContextTypes, ConversationHandler,
PreCheckoutQueryHandler
)

# ══════════════════════════════════════════════════════════════

# НАСТРОЙКИ

# ══════════════════════════════════════════════════════════════

BOT_TOKEN         = os.getenv(“BOT_TOKEN”)
ANTHROPIC_API_KEY = os.getenv(“ANTHROPIC_API_KEY”)  # ключ Claude API
ADMIN_IDS         = [int(x) for x in os.getenv(“ADMIN_IDS”, “0”).split(”,”) if x]

# ── ЮКасса ────────────────────────────────────────────────────

# YOOKASSA_TOKEN получаешь в BotFather:

# /mybots → выбери бота → Bot Settings → Payments → ЮKassa

# Вставь полученный токен в переменную окружения YOOKASSA_TOKEN

# на Railway/Heroku или пропиши напрямую ниже (только для теста!)

YOOKASSA_TOKEN    = os.getenv(“YOOKASSA_TOKEN”)

# Данные магазина ЮКасса (для прямых API-запросов если нужно)

YOOKASSA_SHOP_ID  = “1357057”
YOOKASSA_SECRET   = “live_NDbfKU3p8jsiLkzTN46KziIqQ78-v-9eSrpQa5cdPSM”

logging.basicConfig(
format=”%(asctime)s - %(name)s - %(levelname)s - %(message)s”,
level=logging.INFO
)
logger = logging.getLogger(**name**)

# ══════════════════════════════════════════════════════════════

# СОСТОЯНИЯ ДИАЛОГА

# ══════════════════════════════════════════════════════════════

(
MAIN_MENU, CHOOSE_GOAL, CHOOSE_LEVEL, CHOOSE_PLACE,
SHOW_PLAN, NUTRITION_MENU, SUBSCRIPTION_MENU, PROFILE_MENU,
ADMIN_MENU
) = range(9)

# ══════════════════════════════════════════════════════════════

# ТАРИФЫ

# ══════════════════════════════════════════════════════════════

PLANS = {
“start”: {
“name”: “🆓 Старт”, “price”: 0,
“desc”: “7 дней бесплатно • Базовый план”,
“features”: [“✅ 7-дневный план тренировок”, “✅ Базовые советы по питанию”,
“✅ Трекер прогресса”, “❌ AI-чат с тренером”, “❌ Фото-анализ еды”],
},
“forma”: {
“name”: “💪 Форма”, “price”: 199,
“desc”: “199 ₽/мес • Полный план тренировок + питание”,
“features”: [“✅ Персональный план тренировок”, “✅ Трекер прогресса”,
“✅ Базовый план питания”, “✅ Умные уведомления”, “❌ AI-чат 24/7”, “❌ Фото-анализ еды”],
},
“pro”: {
“name”: “🔥 Прокачка”, “price”: 499,
“desc”: “499 ₽/мес • Полный план + AI-тренер 24/7 + фото-анализ еды”,
“features”: [“✅ Полный план тренировок”, “✅ Детальный план питания”,
“✅ 📸 Фото-анализ еды”, “✅ 🤖 AI-чат с тренером 24/7”,
“✅ Умные уведомления”, “✅ Адаптация плана каждую неделю”],
},
“result”: {
“name”: “🏆 Результат”, “price”: 999,
“desc”: “999 ₽/мес • Всё + живой куратор раз в месяц”,
“features”: [“✅ Всё из тарифа Прокачка”, “✅ Анализ техники по фото”,
“✅ Приоритетные ответы AI”, “✅ Разбор с куратором 1×/мес”],
},
}

# ══════════════════════════════════════════════════════════════

# ТРЕНИРОВКИ И ПИТАНИЕ

# ══════════════════════════════════════════════════════════════

WORKOUTS = {
“похудение”: {
“beginner”: [
“День 1: 🏃 Кардио 30 мин + Приседания 3×15 + Планка 3×30 сек”,
“День 2: 🧘 Активное восстановление — растяжка 20 мин”,
“День 3: 🔥 Берпи 3×10 + Выпады 3×12 + Скакалка 15 мин”,
“День 4: 😴 Отдых”,
“День 5: 🏃 Интервальный бег 25 мин + Пресс 3×20”,
“День 6: 💪 Отжимания 3×10 + Приседания 3×20 + Планка 3×45 сек”,
“День 7: 🧘 Йога 30 мин”,
],
“intermediate”: [
“День 1: 🔥 HIIT 40 мин + Присед с весом 4×15”,
“День 2: 🏃 Бег 5 км + Планка 4×1 мин”,
“День 3: 💪 Круговая тренировка: 5 упр × 4 подхода”,
“День 4: 😴 Активный отдых — плавание или велосипед”,
“День 5: 🔥 Табата 30 мин + Выпады 4×15”,
“День 6: 🏃 Кардио 45 мин + Пресс комплекс”,
“День 7: 🧘 Растяжка и МФР”,
],
},
“набор массы”: {
“beginner”: [
“День 1: 💪 Грудь/Трицепс — Жим лёжа 3×8, Отжимания 3×12, Разводка 3×10”,
“День 2: 🦵 Ноги — Приседания 3×10, Жим ногами 3×12, Выпады 3×10”,
“День 3: 😴 Отдых”,
“День 4: 🔙 Спина/Бицепс — Тяга 3×8, Подтягивания 3×max, Сгибания 3×12”,
“День 5: 🏋️ Плечи — Жим стоя 3×10, Разводки 3×12, Шраги 3×15”,
“День 6: 💪 Руки + Пресс — Суперсеты 4 упр × 3 подхода”,
“День 7: 😴 Отдых”,
],
},
“поддержание”: {
“beginner”: [
“День 1: 🏃 Кардио 30 мин + Силовой комплекс 3×12”,
“День 2: 🧘 Йога или пилатес 45 мин”,
“День 3: 💪 Функциональный тренинг 40 мин”,
“День 4: 😴 Отдых”,
“День 5: 🔥 Круговая тренировка 35 мин”,
“День 6: 🏊 Плавание или велосипед 45 мин”,
“День 7: 🧘 Растяжка 30 мин”,
],
},
}

NUTRITION_PLANS = {
“похудение”: “”“🥗 *План питания — Похудение*

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
💡 *Совет:* Ужин не позже 19:00. Голод вечером — норма!”””,

```
"набор массы": """🥩 *План питания — Набор массы*
```

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
💡 *Совет:* Главное — профицит калорий 300–500 ккал/день”””,
}

# ══════════════════════════════════════════════════════════════

# БАЗА ДАННЫХ

# ══════════════════════════════════════════════════════════════

def init_db():
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(”””
CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY,
username TEXT,
first_name TEXT,
plan TEXT DEFAULT ‘free’,
plan_expires TEXT,
goal TEXT,
level TEXT,
ref_code TEXT UNIQUE,
referred_by INTEGER,
bonus_months INTEGER DEFAULT 0,
notify_time TEXT DEFAULT NULL,
calorie_goal INTEGER DEFAULT 1800,
created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
“””)
# Миграция для старых БД
for col, defn in [(“notify_time”, “TEXT DEFAULT NULL”), (“calorie_goal”, “INTEGER DEFAULT 1800”)]:
try:
c.execute(f”ALTER TABLE users ADD COLUMN {col} {defn}”)
except Exception:
pass
c.execute(”””
CREATE TABLE IF NOT EXISTS payments (
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER, plan TEXT, amount INTEGER, status TEXT,
created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
“””)
c.execute(”””
CREATE TABLE IF NOT EXISTS referrals (
id INTEGER PRIMARY KEY AUTOINCREMENT,
referrer_id INTEGER, referee_id INTEGER, bonus_given INTEGER DEFAULT 0,
created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
“””)
# AI-чат с памятью
c.execute(”””
CREATE TABLE IF NOT EXISTS ai_chat_history (
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER, role TEXT, content TEXT,
created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
“””)
# Дневник питания
c.execute(”””
CREATE TABLE IF NOT EXISTS food_diary (
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER, food_name TEXT,
calories INTEGER, protein REAL, fat REAL, carbs REAL,
date TEXT DEFAULT (date(‘now’)),
created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
“””)
conn.commit()
conn.close()

# ─── Хелперы БД ───────────────────────────────────────────────

def get_or_create_user(user_id, username, first_name):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“SELECT user_id FROM users WHERE user_id=?”, (user_id,))
if not c.fetchone():
ref_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8]
c.execute(“INSERT INTO users (user_id, username, first_name, ref_code) VALUES (?,?,?,?)”,
(user_id, username, first_name, ref_code))
conn.commit()
conn.close()

def get_user(user_id):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“SELECT * FROM users WHERE user_id=?”, (user_id,))
row = c.fetchone()
conn.close()
if not row:
return None
cols = [“user_id”,“username”,“first_name”,“plan”,“plan_expires”,“goal”,“level”,
“ref_code”,“referred_by”,“bonus_months”,“notify_time”,“calorie_goal”,“created_at”]
return dict(zip(cols, row))

def set_user_plan(user_id, plan, months=1):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
expires = (datetime.now() + timedelta(days=30*months)).strftime(”%Y-%m-%d”)
c.execute(“UPDATE users SET plan=?, plan_expires=? WHERE user_id=?”, (plan, expires, user_id))
conn.commit()
conn.close()

def set_notify_time(user_id, notify_time):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“UPDATE users SET notify_time=? WHERE user_id=?”, (notify_time, user_id))
conn.commit()
conn.close()

def add_bonus_month(user_id):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“UPDATE users SET bonus_months = bonus_months + 1 WHERE user_id=?”, (user_id,))
conn.commit()
conn.close()

def get_referral_by_code(ref_code):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“SELECT user_id FROM users WHERE ref_code=?”, (ref_code,))
row = c.fetchone()
conn.close()
return row[0] if row else None

def save_referral(referrer_id, referee_id):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“UPDATE users SET referred_by=? WHERE user_id=?”, (referrer_id, referee_id))
c.execute(“INSERT INTO referrals (referrer_id, referee_id) VALUES (?,?)”, (referrer_id, referee_id))
conn.commit()
conn.close()

def get_referral_count(user_id):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“SELECT COUNT(*) FROM referrals WHERE referrer_id=?”, (user_id,))
count = c.fetchone()[0]
conn.close()
return count

def log_payment(user_id, plan, amount, status):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“INSERT INTO payments (user_id, plan, amount, status) VALUES (?,?,?,?)”,
(user_id, plan, amount, status))
conn.commit()
conn.close()

def has_ai_access(plan):
return plan in (“pro”, “result”)

def get_ai_history(user_id, limit=10):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“SELECT role, content FROM ai_chat_history WHERE user_id=? ORDER BY id DESC LIMIT ?”,
(user_id, limit))
rows = c.fetchall()
conn.close()
return list(reversed(rows))

def save_ai_message(user_id, role, content):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“INSERT INTO ai_chat_history (user_id, role, content) VALUES (?,?,?)”,
(user_id, role, content))
c.execute(””“DELETE FROM ai_chat_history WHERE user_id=? AND id NOT IN
(SELECT id FROM ai_chat_history WHERE user_id=? ORDER BY id DESC LIMIT 20)”””,
(user_id, user_id))
conn.commit()
conn.close()

def clear_ai_history(user_id):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“DELETE FROM ai_chat_history WHERE user_id=?”, (user_id,))
conn.commit()
conn.close()

def save_food_entry(user_id, food_name, calories, protein, fat, carbs):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“INSERT INTO food_diary (user_id, food_name, calories, protein, fat, carbs) VALUES (?,?,?,?,?,?)”,
(user_id, food_name, int(calories), float(protein), float(fat), float(carbs)))
conn.commit()
conn.close()

def get_today_food(user_id):
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“SELECT food_name, calories, protein, fat, carbs FROM food_diary WHERE user_id=? AND date=date(‘now’)”,
(user_id,))
rows = c.fetchall()
conn.close()
return rows

def get_stats():
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“SELECT COUNT(*) FROM users”);               total_users = c.fetchone()[0]
c.execute(“SELECT COUNT(*) FROM users WHERE plan NOT IN (‘free’,‘start’)”); paid_users = c.fetchone()[0]
c.execute(“SELECT SUM(amount) FROM payments WHERE status=‘success’”); revenue = c.fetchone()[0] or 0
c.execute(“SELECT COUNT(*) FROM referrals”);           total_refs = c.fetchone()[0]
c.execute(“SELECT COUNT(*) FROM users WHERE created_at >= date(‘now’, ‘-7 days’)”); new_week = c.fetchone()[0]
c.execute(“SELECT COUNT(*) FROM ai_chat_history”);     ai_msgs = c.fetchone()[0]
c.execute(“SELECT COUNT(*) FROM food_diary”);          food_entries = c.fetchone()[0]
conn.close()
return dict(total_users=total_users, paid_users=paid_users, revenue=revenue,
total_refs=total_refs, new_week=new_week, ai_msgs=ai_msgs, food_entries=food_entries)

def get_top_referrers():
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(””“SELECT u.first_name, u.username, COUNT(r.id) as cnt
FROM referrals r JOIN users u ON r.referrer_id = u.user_id
GROUP BY r.referrer_id ORDER BY cnt DESC LIMIT 10”””)
rows = c.fetchall()
conn.close()
return rows

def get_all_users_with_notify():
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“SELECT user_id, first_name, notify_time, goal FROM users WHERE notify_time IS NOT NULL”)
rows = c.fetchall()
conn.close()
return rows

# ══════════════════════════════════════════════════════════════

# CLAUDE API

# ══════════════════════════════════════════════════════════════

async def call_claude(messages: list, system: str = “”, max_tokens: int = 800) -> str:
if not ANTHROPIC_API_KEY:
return “⚠️ AI-тренер временно недоступен. Администратор должен добавить ANTHROPIC_API_KEY.”
try:
async with httpx.AsyncClient(timeout=30) as client:
payload = {“model”: “claude-sonnet-4-20250514”, “max_tokens”: max_tokens, “messages”: messages}
if system:
payload[“system”] = system
resp = await client.post(
“https://api.anthropic.com/v1/messages”,
headers={“x-api-key”: ANTHROPIC_API_KEY, “anthropic-version”: “2023-06-01”,
“content-type”: “application/json”},
json=payload,
)
data = resp.json()
return data[“content”][0][“text”]
except Exception as e:
logger.error(f”Claude API error: {e}”)
return “⚠️ Не удалось получить ответ от AI. Попробуй чуть позже.”

async def call_claude_vision(image_bytes: bytes, prompt: str) -> str:
if not ANTHROPIC_API_KEY:
return “⚠️ AI-анализ недоступен. Нужен ANTHROPIC_API_KEY.”
try:
b64 = base64.standard_b64encode(image_bytes).decode(“utf-8”)
async with httpx.AsyncClient(timeout=40) as client:
resp = await client.post(
“https://api.anthropic.com/v1/messages”,
headers={“x-api-key”: ANTHROPIC_API_KEY, “anthropic-version”: “2023-06-01”,
“content-type”: “application/json”},
json={
“model”: “claude-sonnet-4-20250514”, “max_tokens”: 600,
“messages”: [{“role”: “user”, “content”: [
{“type”: “image”, “source”: {“type”: “base64”, “media_type”: “image/jpeg”, “data”: b64}},
{“type”: “text”, “text”: prompt},
]}]
}
)
data = resp.json()
return data[“content”][0][“text”]
except Exception as e:
logger.error(f”Claude Vision error: {e}”)
return “⚠️ Не удалось проанализировать фото. Попробуй ещё раз.”

# ══════════════════════════════════════════════════════════════

# СТАРТ

# ══════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
get_or_create_user(user.id, user.username, user.first_name)

```
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

welcome_text = (
    f"👋 Привет, *{user.first_name}*!\n\n"
    "Я — *ФОРМА*, твой персональный AI-тренер и диетолог 💪\n\n"
    "🏋️ Персональные планы тренировок\n"
    "🥗 Планы питания с калорийностью\n"
    "🤖 AI-чат с памятью о твоём прогрессе\n"
    "📸 Анализ еды по фото — КЖБУ за секунду\n"
    "⏰ Умные напоминания о тренировках\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "🎁 *7 дней бесплатно* — без карты!\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "Выбери с чего начнём:"
)
keyboard = [
    [InlineKeyboardButton("🚀 Начать бесплатно", callback_data="free_start")],
    [InlineKeyboardButton("🤖 AI-тренер", callback_data="ai_chat_info"),
     InlineKeyboardButton("📸 Анализ еды", callback_data="food_diary_menu")],
    [InlineKeyboardButton("⏰ Уведомления", callback_data="notify_menu"),
     InlineKeyboardButton("💰 Тарифы", callback_data="show_plans")],
    [InlineKeyboardButton("👥 Рефералы", callback_data="referral_menu"),
     InlineKeyboardButton("👤 Профиль", callback_data="my_profile")],
    [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
]
if user.id in ADMIN_IDS:
    keyboard.append([InlineKeyboardButton("🔐 Админ-панель", callback_data="admin_menu")])

await update.message.reply_text(
    welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
)
return MAIN_MENU
```

# ══════════════════════════════════════════════════════════════

# 🤖 AI-ЧАТ С ПАМЯТЬЮ

# ══════════════════════════════════════════════════════════════

async def ai_chat_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
user = update.effective_user
db_user = get_user(user.id)

```
if not has_ai_access(db_user.get("plan", "free")):
    text = (
        "🤖 *AI-тренер с памятью*\n\n"
        "Персональный тренер который:\n"
        "• Помнит твои цели и весь прогресс\n"
        "• Отвечает в контексте твоей программы\n"
        "• Видит что ты ел сегодня и корректирует советы\n"
        "• Доступен 24/7 — пиши в любое время\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔒 Доступно на тарифе *Прокачка* за 499 ₽/мес"
    )
    keyboard = [
        [InlineKeyboardButton("🔥 Подключить Прокачку", callback_data="plan_pro")],
        [InlineKeyboardButton("← Назад", callback_data="back_main")],
    ]
else:
    history_count = len(get_ai_history(user.id))
    text = (
        "🤖 *AI-тренер ФОРМА*\n\n"
        f"💬 Сообщений в памяти: *{history_count}*\n\n"
        "Просто напиши любой вопрос — я отвечу с учётом твоих целей и истории!\n\n"
        "*Примеры:*\n"
        "• Болит колено, что делать с тренировкой?\n"
        "• Можно ли есть углеводы после 18:00?\n"
        "• Составь мне план питания на завтра\n"
        "• Как ускорить восстановление?\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Напиши свой вопрос прямо сейчас 👇"
    )
    keyboard = [
        [InlineKeyboardButton("🗑 Очистить историю", callback_data="ai_clear_history")],
        [InlineKeyboardButton("← Назад", callback_data="back_main")],
    ]
    context.user_data["ai_mode"] = True

await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
return MAIN_MENU
```

async def ai_clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
clear_ai_history(update.effective_user.id)
context.user_data.pop(“ai_mode”, None)
await query.edit_message_text(
“🗑 История AI-чата очищена. Начнём с чистого листа!”,
reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(“← Назад”, callback_data=“ai_chat_info”)]])
)
return MAIN_MENU

async def process_ai_message(user_id: int, user_text: str, db_user: dict) -> str:
goal  = db_user.get(“goal”) or “не указана”
level = db_user.get(“level”) or “не указан”
plan  = db_user.get(“plan”) or “free”

```
# Контекст питания за сегодня
today_food = get_today_food(user_id)
food_context = ""
if today_food:
    total_cal = sum(f[1] for f in today_food)
    names = ", ".join(f[0] for f in today_food)
    food_context = f"\nСегодня пользователь съел: {names} (итого {total_cal} ккал)."

system_prompt = (
    "Ты персональный AI-тренер и диетолог приложения ФОРМА. "
    "Общайся на русском, дружелюбно и конкретно.\n\n"
    f"Данные пользователя:\n"
    f"- Имя: {db_user.get('first_name', 'друг')}\n"
    f"- Цель: {goal}\n"
    f"- Уровень: {level}\n"
    f"- Тариф: {plan}{food_context}\n\n"
    "Правила:\n"
    "1. Давай конкретные советы с учётом цели и уровня\n"
    "2. При травмах советуй обратиться к врачу\n"
    "3. Отвечай кратко (3-6 предложений), используй эмодзи\n"
    "4. Помни контекст всего диалога"
)

history = get_ai_history(user_id)
messages = [{"role": r, "content": c} for r, c in history]
messages.append({"role": "user", "content": user_text})

save_ai_message(user_id, "user", user_text)
response = await call_claude(messages, system=system_prompt)
save_ai_message(user_id, "assistant", response)
return response
```

# ══════════════════════════════════════════════════════════════

# ⏰ УМНЫЕ PUSH-УВЕДОМЛЕНИЯ

# ══════════════════════════════════════════════════════════════

async def notify_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
db_user = get_user(update.effective_user.id)
current = db_user.get(“notify_time”)
labels = {“morning”: “☀️ Утро (8:00)”, “afternoon”: “🌤 День (13:00)”, “evening”: “🌙 Вечер (19:00)”}
current_text = labels.get(current, “не настроены”)

```
text = (
    "⏰ *Умные уведомления о тренировках*\n\n"
    f"Сейчас: *{current_text}*\n\n"
    "Каждый день в выбранное время бот напомнит о тренировке.\n"
    "Если не отметишь выполнение — пришлёт вечернее напоминание.\n\n"
    "Выбери удобное время:"
)
keyboard = [
    [InlineKeyboardButton("☀️ Утро (8:00)", callback_data="notify_morning")],
    [InlineKeyboardButton("🌤 День (13:00)", callback_data="notify_afternoon")],
    [InlineKeyboardButton("🌙 Вечер (19:00)", callback_data="notify_evening")],
    [InlineKeyboardButton("🔕 Отключить напоминания", callback_data="notify_off")],
    [InlineKeyboardButton("← Назад", callback_data="back_main")],
]
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
return MAIN_MENU
```

async def set_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
action = query.data
time_map = {
“notify_morning”:   (“morning”,   “☀️ Утро (8:00)”),
“notify_afternoon”: (“afternoon”, “🌤 День (13:00)”),
“notify_evening”:   (“evening”,   “🌙 Вечер (19:00)”),
“notify_off”:       (None,        “отключены”),
}
notify_key, label = time_map.get(action, (None, “отключены”))
set_notify_time(update.effective_user.id, notify_key)

```
text = (
    f"✅ *Уведомления настроены!*\n\nВремя: *{label}*\n\n"
    "Каждый день я буду напоминать тебе о тренировке 💪"
    if notify_key else "🔕 Уведомления отключены."
)
keyboard = [[InlineKeyboardButton("← Назад", callback_data="notify_menu")]]
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
return MAIN_MENU
```

async def mark_workout_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer(“✅ Тренировка засчитана!”)
await query.edit_message_text(
“🎉 *Отлично! Тренировка засчитана!*\n\n”
“💪 Ты молодец! Постоянство — ключ к результату.\n”
“Увидимся завтра!”,
parse_mode=“Markdown”
)
return MAIN_MENU

async def send_morning_reminders(app):
for user_id, first_name, notify_time, goal in get_all_users_with_notify():
if notify_time != “morning”:
continue
try:
await app.bot.send_message(
user_id,
f”☀️ Доброе утро, *{first_name}*!\n\n”
f”Сегодня тебя ждёт тренировка — *{goal or ‘по твоей программе’}*.\n”
“Отметь когда выполнишь 👇”,
reply_markup=InlineKeyboardMarkup([[
InlineKeyboardButton(“✅ Тренировка выполнена!”, callback_data=“workout_done”)
]]),
parse_mode=“Markdown”
)
except Exception:
pass

async def send_afternoon_reminders(app):
for user_id, first_name, notify_time, goal in get_all_users_with_notify():
if notify_time != “afternoon”:
continue
try:
await app.bot.send_message(
user_id,
f”🌤 Привет, *{first_name}*!\n\n”
“Середина дня — лучшее время для тренировки.\n”
“Всего 30–45 минут — и результат будет! 💪”,
reply_markup=InlineKeyboardMarkup([[
InlineKeyboardButton(“✅ Тренировка выполнена!”, callback_data=“workout_done”)
]]),
parse_mode=“Markdown”
)
except Exception:
pass

async def send_evening_reminders(app):
for user_id, first_name, notify_time, goal in get_all_users_with_notify():
if notify_time != “evening”:
continue
try:
await app.bot.send_message(
user_id,
f”🌙 *{first_name}*, вечер — отличное время!\n\n”
“После работы тренировка снимает стресс и заряжает на завтра 🔥”,
reply_markup=InlineKeyboardMarkup([[
InlineKeyboardButton(“✅ Тренировка выполнена!”, callback_data=“workout_done”)
]]),
parse_mode=“Markdown”
)
except Exception:
pass

async def send_late_reminders(app):
“”“21:00 — напоминание тем кто ещё не отметил тренировку.”””
for user_id, first_name, notify_time, goal in get_all_users_with_notify():
if not notify_time:
continue
try:
await app.bot.send_message(
user_id,
f”😴 *{first_name}*, ещё не поздно!\n\n”
“Даже 20 минут лёгкой тренировки — это лучше, чем ничего 💙”,
reply_markup=InlineKeyboardMarkup([
[InlineKeyboardButton(“✅ Сделал тренировку!”, callback_data=“workout_done”)],
[InlineKeyboardButton(“⏭ Пропустить сегодня”, callback_data=“back_main”)],
]),
parse_mode=“Markdown”
)
except Exception:
pass

# ══════════════════════════════════════════════════════════════

# 📸 ФОТО-АНАЛИЗ ЕДЫ

# ══════════════════════════════════════════════════════════════

async def food_diary_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
user = update.effective_user
db_user = get_user(user.id)

```
if not has_ai_access(db_user.get("plan", "free")):
    text = (
        "📸 *Фото-анализ еды*\n\n"
        "Сфотографируй тарелку — AI за секунду определит:\n"
        "🍽 Название блюда\n"
        "🔥 Калории\n"
        "💪 Белки / Жиры / Углеводы\n"
        "📊 Сводку питания за день\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔒 Доступно на тарифе *Прокачка* за 499 ₽/мес"
    )
    keyboard = [
        [InlineKeyboardButton("🔥 Подключить Прокачку", callback_data="plan_pro")],
        [InlineKeyboardButton("← Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return MAIN_MENU

today_food = get_today_food(user.id)
calorie_goal = db_user.get("calorie_goal") or 1800

if today_food:
    total_cal = sum(f[1] for f in today_food)
    total_p = sum(f[2] for f in today_food)
    total_f = sum(f[3] for f in today_food)
    total_c = sum(f[4] for f in today_food)
    remaining = calorie_goal - total_cal
    status = "🟢" if remaining >= 0 else "🔴"
    diary_lines = "\n".join(f"• {f[0]}: {f[1]} ккал" for f in today_food)
    diary_text = (
        f"\n*Съедено сегодня:*\n{diary_lines}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{status} Итого: *{total_cal}* / {calorie_goal} ккал\n"
        f"💪 Б: {total_p:.0f}г | 🧈 Ж: {total_f:.0f}г | 🍚 У: {total_c:.0f}г"
    )
else:
    diary_text = "\n_Сегодня записей нет. Сфотографируй первое блюдо!_"

text = (
    f"📸 *Дневник питания*{diary_text}\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "Отправь фото блюда — AI сразу посчитает КЖБУ 👇"
)
keyboard = [[InlineKeyboardButton("← Назад", callback_data="back_main")]]
context.user_data["food_photo_mode"] = True
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
return MAIN_MENU
```

async def handle_food_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
db_user = get_user(user.id)
if not db_user:
get_or_create_user(user.id, user.username, user.first_name)
db_user = get_user(user.id)

```
if not has_ai_access(db_user.get("plan", "free")):
    await update.message.reply_text(
        "📸 Фото-анализ еды доступен на тарифе *Прокачка* (499 ₽/мес)\n\nХочешь подключить?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Подключить", callback_data="plan_pro")]
        ]),
        parse_mode="Markdown"
    )
    return

msg = await update.message.reply_text("🔍 Анализирую блюдо... секунду!")

try:
    photo = update.message.photo[-1]
    tg_file = await context.bot.get_file(photo.file_id)
    image_bytes = bytes(await tg_file.download_as_bytearray())

    prompt = (
        "Проанализируй блюдо на фото. Ответь СТРОГО в этом формате (без лишнего текста):\n\n"
        "БЛЮДО: [название на русском]\n"
        "КАЛОРИИ: [число]\n"
        "БЕЛКИ: [число]г\n"
        "ЖИРЫ: [число]г\n"
        "УГЛЕВОДЫ: [число]г\n"
        "КОММЕНТАРИЙ: [1 предложение о пользе/вреде для фитнеса]\n\n"
        "Если на фото не еда — напиши только: НЕ_ЕДА"
    )
    result = await call_claude_vision(image_bytes, prompt)

    if "НЕ_ЕДА" in result:
        await msg.edit_text("🤔 Не вижу еду на фото. Попробуй сфотографировать блюдо крупнее!")
        return

    # Парсинг ответа
    food_data = {}
    for line in result.strip().split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            food_data[k.strip()] = v.strip()

    def parse_num(s):
        return ''.join(c for c in s if c.isdigit() or c == '.')

    food_name = food_data.get("БЛЮДО", "Блюдо")
    calories  = int(parse_num(food_data.get("КАЛОРИИ", "0")) or 0)
    protein   = float(parse_num(food_data.get("БЕЛКИ", "0")) or 0)
    fat       = float(parse_num(food_data.get("ЖИРЫ", "0")) or 0)
    carbs     = float(parse_num(food_data.get("УГЛЕВОДЫ", "0")) or 0)
    comment   = food_data.get("КОММЕНТАРИЙ", "")

    save_food_entry(user.id, food_name, calories, protein, fat, carbs)

    today_food    = get_today_food(user.id)
    total_cal     = sum(f[1] for f in today_food)
    calorie_goal  = db_user.get("calorie_goal") or 1800
    remaining     = calorie_goal - total_cal
    day_status    = "🟢 В норме" if remaining >= 0 else "🔴 Превышение"

    response_text = (
        f"✅ *{food_name}*\n\n"
        f"🔥 Калории: *{calories} ккал*\n"
        f"💪 Белки: *{protein:.0f}г*\n"
        f"🧈 Жиры: *{fat:.0f}г*\n"
        f"🍚 Углеводы: *{carbs:.0f}г*\n\n"
        f"💬 _{comment}_\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Итог дня:* {total_cal} / {calorie_goal} ккал\n"
        f"{day_status} | Остаток: {abs(remaining)} ккал"
    )
    keyboard = [
        [InlineKeyboardButton("📊 Весь дневник", callback_data="food_diary_menu")],
        [InlineKeyboardButton("🤖 Спросить AI-тренера", callback_data="ai_chat_info")],
        [InlineKeyboardButton("🏠 Меню", callback_data="back_main")],
    ]
    await msg.edit_text(response_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

except Exception as e:
    logger.error(f"Food photo error: {e}")
    await msg.edit_text("⚠️ Не удалось проанализировать фото. Попробуй ещё раз.")
```

# ══════════════════════════════════════════════════════════════

# ТРЕНИРОВКИ / ПИТАНИЕ

# ══════════════════════════════════════════════════════════════

async def free_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
text = “🎯 *Выбери свою главную цель:*\n\nОт этого зависит весь план тренировок и питания”
keyboard = [
[InlineKeyboardButton(“🔥 Похудеть”, callback_data=“goal_похудение”)],
[InlineKeyboardButton(“💪 Набрать мышечную массу”, callback_data=“goal_набор массы”)],
[InlineKeyboardButton(“⚖️ Поддержать форму”, callback_data=“goal_поддержание”)],
[InlineKeyboardButton(“← Назад”, callback_data=“back_main”)],
]
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”)
return CHOOSE_GOAL

async def choose_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
goal = query.data.replace(“goal_”, “”)
context.user_data[“goal”] = goal
keyboard = [
[InlineKeyboardButton(“🌱 Новичок (до 6 месяцев)”, callback_data=“level_beginner”)],
[InlineKeyboardButton(“🔥 Средний (6 мес – 2 года)”, callback_data=“level_intermediate”)],
[InlineKeyboardButton(“⚡ Продвинутый (2+ года)”, callback_data=“level_advanced”)],
[InlineKeyboardButton(“← Назад”, callback_data=“free_start”)],
]
await query.edit_message_text(
f”✅ Цель: *{goal.capitalize()}*\n\n💡 *Теперь укажи уровень подготовки:*”,
reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”
)
return CHOOSE_LEVEL

async def choose_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
level = query.data.replace(“level_”, “”)
context.user_data[“level”] = level
level_names = {“beginner”: “Новичок”, “intermediate”: “Средний”, “advanced”: “Продвинутый”}
keyboard = [
[InlineKeyboardButton(“🏠 Дома (без оборудования)”, callback_data=“place_home”)],
[InlineKeyboardButton(“🏋️ В зале”, callback_data=“place_gym”)],
[InlineKeyboardButton(“🌳 На улице”, callback_data=“place_street”)],
[InlineKeyboardButton(“← Назад”, callback_data=“free_start”)],
]
await query.edit_message_text(
f”✅ Уровень: *{level_names.get(level, level)}*\n\n🏟️ *Где будешь тренироваться?*”,
reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”
)
return CHOOSE_PLACE

async def show_workout_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
place = query.data.replace(“place_”, “”)
goal  = context.user_data.get(“goal”, “поддержание”)
level = context.user_data.get(“level”, “beginner”)
workouts = WORKOUTS.get(goal, WORKOUTS[“поддержание”]).get(level, WORKOUTS[“поддержание”][“beginner”])
place_emoji = {“home”: “🏠”, “gym”: “🏋️”, “street”: “🌳”}.get(place, “🏠”)
place_name  = {“home”: “Дома”, “gym”: “В зале”, “street”: “На улице”}.get(place, “Дома”)

```
plan_text = (
    f"🎉 *Твой персональный план на 7 дней готов!*\n\n"
    f"🎯 Цель: *{goal.capitalize()}* | {place_emoji} *{place_name}*\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
)
plan_text += "\n\n".join(f"*{w}*" for w in workouts)
plan_text += (
    "\n\n━━━━━━━━━━━━━━━━━━\n"
    "💡 Хочешь AI-тренера который ответит на любой вопрос?\n"
    "Подключи *Прокачку* за 499 ₽/мес 🔥"
)
keyboard = [
    [InlineKeyboardButton("🥗 План питания", callback_data="nutrition_plan"),
     InlineKeyboardButton("🤖 AI-тренер", callback_data="ai_chat_info")],
    [InlineKeyboardButton("⏰ Настроить уведомления", callback_data="notify_menu")],
    [InlineKeyboardButton("💳 Подключить тариф", callback_data="show_plans")],
    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
]
await query.edit_message_text(plan_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
return SHOW_PLAN
```

async def nutrition_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
goal = context.user_data.get(“goal”, “похудение”)
plan = NUTRITION_PLANS.get(goal, NUTRITION_PLANS[“похудение”])
keyboard = [
[InlineKeyboardButton(“📸 Анализ фото еды”, callback_data=“food_diary_menu”)],
[InlineKeyboardButton(“💳 Полный план (Прокачка)”, callback_data=“show_plans”)],
[InlineKeyboardButton(“🏠 Главное меню”, callback_data=“back_main”)],
]
await query.edit_message_text(plan, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”)
return NUTRITION_MENU

# ══════════════════════════════════════════════════════════════

# ТАРИФЫ И ОПЛАТА

# ══════════════════════════════════════════════════════════════

async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
db_user = get_user(update.effective_user.id)
has_discount = bool(db_user and db_user.get(“referred_by”))
discount_text = “\n🎁 *У тебя есть скидка 20%* на первую оплату!” if has_discount else “”

```
text = (
    f"💳 *Выбери свой тариф:*{discount_text}\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "🆓 *Старт* — Бесплатно\n7 дней • Базовый план\n\n"
    "💪 *Форма* — 199 ₽/мес\nПланы + питание + уведомления\n\n"
    "🔥 *Прокачка* — 499 ₽/мес\n🤖 AI-чат + 📸 Фото-анализ + всё выше\n\n"
    "🏆 *Результат* — 999 ₽/мес\nВсё + живой куратор раз в месяц\n"
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
```

async def plan_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
plan_key = query.data.replace(“plan_”, “”)
plan = PLANS.get(plan_key, PLANS[“forma”])
db_user = get_user(update.effective_user.id)
has_discount = bool(db_user and db_user.get(“referred_by”))
price = plan[“price”]
if has_discount and price > 0:
discounted = int(price * 0.8)
price_text = f”~{price}~ → *{discounted} ₽/месяц* (скидка 20%)”
context.user_data[“discounted_price”] = discounted
else:
price_text = f”*{price} ₽/месяц*” if price > 0 else “*Бесплатно*”
context.user_data[“discounted_price”] = price
context.user_data[“selected_plan”] = plan_key

```
features_text = "\n".join(plan["features"])
text = f"*{plan['name']}*\n💰 {price_text}\n\n{features_text}\n\n━━━━━━━━━━━━━━━━━━\nВыбери этот тариф?"
keyboard = []
if plan["price"] == 0:
    keyboard.append([InlineKeyboardButton("✅ Активировать бесплатно", callback_data="activate_free")])
else:
    keyboard.append([InlineKeyboardButton("💳 Оплатить через ЮКассу", callback_data=f"pay_{plan_key}")])
keyboard.append([InlineKeyboardButton("← К тарифам", callback_data="show_plans")])
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
return SUBSCRIPTION_MENU
```

async def activate_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
set_user_plan(update.effective_user.id, “free”, months=0)
keyboard = [
[InlineKeyboardButton(“🏋️ Получить план”, callback_data=“free_start”)],
[InlineKeyboardButton(“⏰ Настроить уведомления”, callback_data=“notify_menu”)],
[InlineKeyboardButton(“🏠 Главное меню”, callback_data=“back_main”)],
]
await query.edit_message_text(
“🎉 *Тариф Старт активирован!*\n\nУ тебя есть *7 дней бесплатного доступа*\n\nС чего начнём?”,
reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”
)
return MAIN_MENU

async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
plan_key = query.data.replace(“pay_”, “”)
plan     = PLANS.get(plan_key, PLANS[“forma”])
price    = context.user_data.get(“discounted_price”, plan[“price”])

```
# ── Проверка токена ────────────────────────────────────────
if not YOOKASSA_TOKEN:
    await query.edit_message_text(
        "⚠️ *Платёжная система не настроена*\n\n"
        "Администратор должен:\n"
        "1. Зайти в @BotFather\n"
        "2. /mybots → выбрать бота\n"
        "3. Bot Settings → Payments → ЮKassa\n"
        "4. Добавить токен в переменные как YOOKASSA_TOKEN\n\n"
        "Напиши @FormaSupport если нужна помощь",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="show_plans")]]),
        parse_mode="Markdown"
    )
    return SUBSCRIPTION_MENU

# ── Удаляем старое сообщение и отправляем счёт ────────────
try:
    await query.message.delete()
except Exception:
    pass

try:
    await context.bot.send_invoice(
        chat_id    = query.from_user.id,
        title      = f"ФОРМА — {plan['name']}",
        description= plan["desc"],
        payload    = f"plan_{plan_key}_{query.from_user.id}",
        provider_token = YOOKASSA_TOKEN,
        currency   = "RUB",
        prices     = [LabeledPrice(plan["name"], price * 100)],
        start_parameter = "pay",
        # Защита от дублей: пользователь видит кнопку "Оплатить"
        need_name          = False,
        need_phone_number  = False,
        need_email         = False,
        need_shipping_address = False,
        is_flexible        = False,
    )
except Exception as e:
    logger.error(f"send_invoice error: {e}")
    await context.bot.send_message(
        chat_id = query.from_user.id,
        text    = "⚠️ Не удалось создать счёт. Попробуй позже или напиши @FormaSupport",
    )
return SUBSCRIPTION_MENU
```

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
user    = update.effective_user
payment = update.message.successful_payment
parts   = payment.invoice_payload.split(”_”)
plan_key = parts[1] if len(parts) > 1 else “forma”
amount   = payment.total_amount // 100

```
# Активируем тариф
set_user_plan(user.id, plan_key, months=1)
log_payment(user.id, plan_key, amount, "success")

# Бонус рефереру
db_user = get_user(user.id)
if db_user and db_user.get("referred_by"):
    referrer_id = db_user["referred_by"]
    conn = sqlite3.connect("forma.db")
    c    = conn.cursor()
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
                "🏆 *Твой реферал оплатил подписку!*\n"
                "✅ Тебе начислен *+1 месяц* бесплатно!",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    else:
        conn.close()

plan  = PLANS.get(plan_key, PLANS["forma"])
extra = "\n\n🤖 *AI-тренер* и 📸 *фото-анализ еды* теперь доступны!" if plan_key in ("pro", "result") else ""

keyboard = [
    [InlineKeyboardButton("🏋️ Мой план тренировок", callback_data="free_start")],
    [InlineKeyboardButton("🤖 AI-тренер", callback_data="ai_chat_info"),
     InlineKeyboardButton("📸 Анализ еды", callback_data="food_diary_menu")],
    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
]
await update.message.reply_text(
    f"🎉 *Оплата прошла успешно!*\n\n"
    f"✅ Тариф *{plan['name']}* активирован на 30 дней\n"
    f"💰 Списано: *{amount} ₽*\n"
    f"🔄 Следующее списание: через 30 дней{extra}",
    reply_markup=InlineKeyboardMarkup(keyboard),
    parse_mode="Markdown"
)
```

# ══════════════════════════════════════════════════════════════

# РЕФЕРАЛЫ / ПРОФИЛЬ / О БОТЕ / МЕНЮ

# ══════════════════════════════════════════════════════════════

async def referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
user = update.effective_user
db_user = get_user(user.id)
ref_count = get_referral_count(user.id)
bot_username = (await context.bot.get_me()).username
ref_link = f”https://t.me/{bot_username}?start={db_user[‘ref_code’]}”

```
text = (
    "👥 *Реферальная программа ФОРМА*\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "1️⃣ Поделись ссылкой с другом\n"
    "2️⃣ Друг регистрируется по ней\n"
    "3️⃣ *Тебе* — +1 месяц бесплатно 🎉\n"
    "4️⃣ *Другу* — скидка 20% на первую оплату\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    f"👤 Твоих рефералов: *{ref_count}*\n"
    f"🎁 Бонусных месяцев: *{db_user['bonus_months']}*\n\n"
    f"🔗 *Твоя ссылка:*\n`{ref_link}`"
)
keyboard = [
    [InlineKeyboardButton("📤 Поделиться", switch_inline_query=f"Присоединяйся к ФОРМА! {ref_link}")],
    [InlineKeyboardButton("← Назад", callback_data="back_main")],
]
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
return MAIN_MENU
```

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
user = update.effective_user
db_user = get_user(user.id)
ref_count = get_referral_count(user.id)
bot_username = (await context.bot.get_me()).username
ref_link = f”https://t.me/{bot_username}?start={db_user[‘ref_code’]}”

```
plan_names   = {"free":"🆓 Старт","start":"🆓 Старт","forma":"💪 Форма","pro":"🔥 Прокачка","result":"🏆 Результат"}
notify_names = {"morning":"☀️ 8:00","afternoon":"🌤 13:00","evening":"🌙 19:00",None:"не настроены"}
today_food   = get_today_food(user.id)
ai_msgs      = len(get_ai_history(user.id))

text = (
    f"👤 *Профиль — {user.first_name}*\n\n"
    f"🎯 Цель: *{(db_user.get('goal') or 'не выбрана').capitalize()}*\n"
    f"💳 Тариф: *{plan_names.get(db_user.get('plan'), '🆓 Старт')}*\n"
    f"📅 Действует до: *{db_user.get('plan_expires') or '—'}*\n"
    f"⏰ Уведомления: *{notify_names.get(db_user.get('notify_time'))}*\n"
    f"🤖 AI-диалог: *{ai_msgs} сообщений*\n"
    f"📸 Питание сегодня: *{len(today_food)} блюд*\n"
    f"🎁 Бонусных месяцев: *{db_user['bonus_months']}*\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    f"👥 Рефералов: *{ref_count}*\n"
    f"🔗 `{ref_link}`"
)
keyboard = [
    [InlineKeyboardButton("🔄 Изменить цель", callback_data="free_start"),
     InlineKeyboardButton("⏰ Уведомления", callback_data="notify_menu")],
    [InlineKeyboardButton("🤖 AI-тренер", callback_data="ai_chat_info"),
     InlineKeyboardButton("📸 Дневник еды", callback_data="food_diary_menu")],
    [InlineKeyboardButton("💳 Изменить тариф", callback_data="show_plans")],
    [InlineKeyboardButton("👥 Рефералы", callback_data="referral_menu")],
    [InlineKeyboardButton("← Назад", callback_data="back_main")],
]
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
return PROFILE_MENU
```

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
text = (
“ℹ️ *О боте ФОРМА*\n\n”
“🤖 AI-персональный тренер и диетолог в Telegram\n\n”
“🎯 *Что умею:*\n”
“• 🏋️ Планы тренировок под любую цель\n”
“• 🥗 Планы питания с калорийностью\n”
“• 🤖 AI-чат с памятью — отвечаю в контексте прогресса\n”
“• 📸 Фото-анализ еды — КЖБУ за секунду\n”
“• ⏰ Умные напоминания о тренировках\n\n”
“📩 Поддержка: @FormaSupport”
)
keyboard = [[InlineKeyboardButton(“← Назад”, callback_data=“back_main”)]]
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”)
return MAIN_MENU

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
context.user_data.pop(“food_photo_mode”, None)
context.user_data.pop(“ai_mode”, None)
user = update.effective_user
text = f”🏠 *Главное меню*\n\nПривет, *{user.first_name}*! Чем займёмся сегодня?”
keyboard = [
[InlineKeyboardButton(“🚀 Мой план тренировок”, callback_data=“free_start”)],
[InlineKeyboardButton(“🤖 AI-тренер”, callback_data=“ai_chat_info”),
InlineKeyboardButton(“📸 Анализ еды”, callback_data=“food_diary_menu”)],
[InlineKeyboardButton(“⏰ Уведомления”, callback_data=“notify_menu”),
InlineKeyboardButton(“💳 Тарифы”, callback_data=“show_plans”)],
[InlineKeyboardButton(“👥 Рефералы”, callback_data=“referral_menu”),
InlineKeyboardButton(“👤 Профиль”, callback_data=“my_profile”)],
]
if user.id in ADMIN_IDS:
keyboard.append([InlineKeyboardButton(“🔐 Админ-панель”, callback_data=“admin_menu”)])
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”)
return MAIN_MENU

# ══════════════════════════════════════════════════════════════

# АДМИН-ПАНЕЛЬ

# ══════════════════════════════════════════════════════════════

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
if update.effective_user.id not in ADMIN_IDS:
await query.answer(“⛔ Нет доступа”, show_alert=True)
return MAIN_MENU
stats = get_stats()
text = (
“🔐 *Админ-панель ФОРМА*\n\n”
“━━━━━━━━━━━━━━━━━━\n”
f”👥 Пользователей: *{stats[‘total_users’]}*\n”
f”💳 Платных: *{stats[‘paid_users’]}*\n”
f”💰 Выручка: *{stats[‘revenue’]} ₽*\n”
f”🤖 AI-сообщений: *{stats[‘ai_msgs’]}*\n”
f”📸 Записей питания: *{stats[‘food_entries’]}*\n”
f”👥 Рефералов: *{stats[‘total_refs’]}*\n”
f”🆕 Новых за 7 дней: *{stats[‘new_week’]}*\n”
“━━━━━━━━━━━━━━━━━━”
)
keyboard = [
[InlineKeyboardButton(“📊 Статистика”, callback_data=“admin_stats”),
InlineKeyboardButton(“👥 Топ рефереры”, callback_data=“admin_referrers”)],
[InlineKeyboardButton(“📢 Рассылка”, callback_data=“admin_broadcast”)],
[InlineKeyboardButton(“← Главное меню”, callback_data=“back_main”)],
]
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”)
return ADMIN_MENU

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
if update.effective_user.id not in ADMIN_IDS:
return ADMIN_MENU
conn = sqlite3.connect(“forma.db”)
c = conn.cursor()
c.execute(“SELECT plan, COUNT(*) FROM users GROUP BY plan”); plan_counts = c.fetchall()
c.execute(“SELECT SUM(amount), COUNT(*) FROM payments WHERE status=‘success’”); pay_row = c.fetchone()
c.execute(“SELECT COUNT(*) FROM users WHERE created_at >= date(‘now’, ‘-1 day’)”); new_today = c.fetchone()[0]
conn.close()
plan_text = “”.join(f”  • {p}: {cnt}\n” for p, cnt in plan_counts)
text = (
“📊 *Подробная статистика*\n\n”
“━━━━━━━━━━━━━━━━━━\n”
f”*По тарифам:*\n{plan_text}\n”
f”*Платежи:*\n  • Сумма: {pay_row[0] or 0} ₽\n  • Транзакций: {pay_row[1] or 0}\n\n”
f”*Активность:*\n  • Новых сегодня: {new_today}\n”
“━━━━━━━━━━━━━━━━━━”
)
keyboard = [[InlineKeyboardButton(“← Назад”, callback_data=“admin_menu”)]]
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”)
return ADMIN_MENU

async def admin_referrers(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
if update.effective_user.id not in ADMIN_IDS:
return ADMIN_MENU
top = get_top_referrers()
lines = “”.join(f”{i}. {’@’+u if u else n} — {cnt}\n” for i,(n,u,cnt) in enumerate(top,1)) if top else “Нет данных”
text = f”👥 *Топ рефереры*\n\n━━━━━━━━━━━━━━━━━━\n{lines}━━━━━━━━━━━━━━━━━━”
keyboard = [[InlineKeyboardButton(“← Назад”, callback_data=“admin_menu”)]]
await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”)
return ADMIN_MENU

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
if update.effective_user.id not in ADMIN_IDS:
return ADMIN_MENU
context.user_data[“awaiting_broadcast”] = True
keyboard = [[InlineKeyboardButton(“← Назад”, callback_data=“admin_menu”)]]
await query.edit_message_text(
“📢 *Рассылка*\n\nНапиши сообщение для всех пользователей.\nДля отмены — /cancel”,
reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”
)
return ADMIN_MENU

# ══════════════════════════════════════════════════════════════

# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ

# ══════════════════════════════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
text = update.message.text

```
# Рассылка от админа
if context.user_data.get("awaiting_broadcast") and user.id in ADMIN_IDS:
    context.user_data["awaiting_broadcast"] = False
    conn = sqlite3.connect("forma.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    sent, failed = 0, 0
    for (uid,) in users:
        try:
            await context.bot.send_message(uid, text, parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"📢 Рассылка завершена!\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}")
    return

db_user = get_user(user.id)
if not db_user:
    get_or_create_user(user.id, user.username, user.first_name)
    db_user = get_user(user.id)

# ── AI-чат для платных тарифов ────────────────────────────
if has_ai_access(db_user.get("plan", "free")):
    thinking = await update.message.reply_text("🤖 Думаю...")
    response = await process_ai_message(user.id, text, db_user)
    keyboard = [
        [InlineKeyboardButton("📸 Анализ еды", callback_data="food_diary_menu"),
         InlineKeyboardButton("🏠 Меню", callback_data="back_main")],
    ]
    await thinking.edit_text(response, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return

# ── Статические ответы для бесплатных ────────────────────
text_lower = text.lower()
static = {
    "белок":  "💪 *Белок* — строительный материал для мышц.\nНорма: *1.6–2.2г на кг веса* в день.\nЛучшие источники: курица, яйца, творог, рыба.",
    "калори": "📊 *Калорийность* зависит от цели:\n• Похудение: дефицит 300–500 ккал\n• Набор массы: профицит 300–500 ккал",
    "вода":   "💧 *Норма воды:* 30–40 мл на кг веса.\nПри тренировках +500–700 мл дополнительно.",
    "отжим":  "💪 *Техника отжиманий:*\n1. Руки чуть шире плеч\n2. Тело — прямая линия\n3. Грудь касается пола\n4. Выдох — вверх",
}
reply = next((v for k, v in static.items() if k in text_lower), None)
if not reply:
    reply = (
        "🤖 Отличный вопрос! Для развёрнутых ответов с учётом *твоих целей и прогресса* "
        "подключи тариф *Прокачка* — AI-тренер с памятью за 499 ₽/мес 🔥"
    )
keyboard = [
    [InlineKeyboardButton("🤖 Подключить AI-тренера", callback_data="ai_chat_info")],
    [InlineKeyboardButton("🏋️ Мой план тренировок", callback_data="free_start")],
]
await update.message.reply_text(reply, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
```

# ══════════════════════════════════════════════════════════════

# MAIN

# ══════════════════════════════════════════════════════════════

def main():
init_db()
app = Application.builder().token(BOT_TOKEN).build()

```
# Планировщик уведомлений (МСК timezone)
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
scheduler.add_job(send_morning_reminders,   "cron", hour=8,  minute=0,  args=[app])
scheduler.add_job(send_afternoon_reminders, "cron", hour=13, minute=0,  args=[app])
scheduler.add_job(send_evening_reminders,   "cron", hour=19, minute=0,  args=[app])
scheduler.add_job(send_late_reminders,      "cron", hour=21, minute=0,  args=[app])
scheduler.start()

# Единый список колбэков для всех состояний
cbs = [
    CallbackQueryHandler(free_start,        pattern="^free_start$"),
    CallbackQueryHandler(show_plans,        pattern="^show_plans$"),
    CallbackQueryHandler(my_profile,        pattern="^my_profile$"),
    CallbackQueryHandler(about,             pattern="^about$"),
    CallbackQueryHandler(back_main,         pattern="^back_main$"),
    CallbackQueryHandler(activate_free,     pattern="^activate_free$"),
    CallbackQueryHandler(referral_menu,     pattern="^referral_menu$"),
    CallbackQueryHandler(admin_menu,        pattern="^admin_menu$"),
    CallbackQueryHandler(admin_stats,       pattern="^admin_stats$"),
    CallbackQueryHandler(admin_referrers,   pattern="^admin_referrers$"),
    CallbackQueryHandler(admin_broadcast,   pattern="^admin_broadcast$"),
    CallbackQueryHandler(ai_chat_info,      pattern="^ai_chat_info$"),
    CallbackQueryHandler(ai_clear_history,  pattern="^ai_clear_history$"),
    CallbackQueryHandler(food_diary_menu,   pattern="^food_diary_menu$"),
    CallbackQueryHandler(notify_menu,       pattern="^notify_menu$"),
    CallbackQueryHandler(set_notify,        pattern="^notify_(morning|afternoon|evening|off)$"),
    CallbackQueryHandler(mark_workout_done, pattern="^workout_done$"),
    CallbackQueryHandler(plan_detail,       pattern="^plan_"),
    CallbackQueryHandler(process_payment,   pattern="^pay_"),
    CallbackQueryHandler(nutrition_plan,    pattern="^nutrition_plan$"),
]

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        MAIN_MENU:         cbs,
        CHOOSE_GOAL:       cbs + [CallbackQueryHandler(choose_goal,        pattern="^goal_")],
        CHOOSE_LEVEL:      cbs + [CallbackQueryHandler(choose_level,       pattern="^level_")],
        CHOOSE_PLACE:      cbs + [CallbackQueryHandler(show_workout_plan,  pattern="^place_")],
        SHOW_PLAN:         cbs,
        NUTRITION_MENU:    cbs,
        SUBSCRIPTION_MENU: cbs,
        PROFILE_MENU:      cbs,
        ADMIN_MENU:        cbs,
    },
    fallbacks=[CommandHandler("start", start)],
)

app.add_handler(conv)
app.add_handler(PreCheckoutQueryHandler(pre_checkout))
app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
app.add_handler(MessageHandler(filters.PHOTO, handle_food_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🏋️ ФОРМА Bot запущен! AI-чат + умные пуши + фото-анализ еды активны.")
app.run_polling(allowed_updates=Update.ALL_TYPES)
```

if **name** == “**main**”:
main()
