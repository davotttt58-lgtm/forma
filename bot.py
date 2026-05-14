#!/usr/bin/env python3
"""
🏋️ ФОРМА — AI Персональный Тренер & Диетолог
Telegram Bot | @FitFormaBot
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ─── НАСТРОЙКИ ────────────────────────────────────────────────
"import os
BOT_TOKEN = os.getenv("7704620333:AAGbFgE6I05g2tkruHNCA76bQFoB_s4q3XA")"  #
PAYMENT_PROVIDER_TOKEN = "ВАШ_PAYMENT_TOKEN"  # Токен платёжной системы

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ─── СОСТОЯНИЯ ДИАЛОГА ────────────────────────────────────────
(
    MAIN_MENU, CHOOSE_GOAL, CHOOSE_LEVEL, CHOOSE_PLACE,
    SHOW_PLAN, NUTRITION_MENU, SUBSCRIPTION_MENU, PROFILE_MENU
) = range(8)

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
        "price": 299,
        "desc": "299 ₽/мес • Полный план тренировок + питание",
        "features": ["✅ Персональный план тренировок", "✅ Трекер прогресса", "✅ Базовый план питания", "✅ Еженедельная адаптация", "❌ AI-чат 24/7"],
    },
    "pro": {
        "name": "🔥 Прокачка",
        "price": 699,
        "desc": "699 ₽/мес • Полный план + AI-тренер 24/7",
        "features": ["✅ Полный план тренировок", "✅ Детальный план питания", "✅ Фото-анализ еды", "✅ AI-чат с тренером 24/7", "✅ Адаптация плана каждую неделю"],
    },
    "result": {
        "name": "🏆 Результат",
        "price": 1490,
        "desc": "1490 ₽/мес • Всё + живой куратор раз в месяц",
        "features": ["✅ Всё из тарифа Прокачка", "✅ Анализ техники по фото", "✅ Приоритетные ответы", "✅ Разбор с куратором 1×/мес", "✅ Программа под ваше событие"],
    },
}

# ─── ТРЕНИРОВКИ (примеры) ─────────────────────────────────────
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

# ─── ПРИВЕТСТВИЕ ──────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
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
        [InlineKeyboardButton("👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
    ]
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return MAIN_MENU

# ─── ВЫБОР ЦЕЛИ ───────────────────────────────────────────────
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
        [InlineKeyboardButton("🏃 Подготовка к соревнованию", callback_data="goal_спорт")],
        [InlineKeyboardButton("← Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return CHOOSE_GOAL

# ─── ВЫБОР УРОВНЯ ─────────────────────────────────────────────
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
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return CHOOSE_LEVEL

# ─── ВЫБОР МЕСТА ТРЕНИРОВОК ───────────────────────────────────
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
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return CHOOSE_PLACE

# ─── ПОКАЗ ПЛАНА ТРЕНИРОВОК ───────────────────────────────────
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
    for i, workout in enumerate(workouts, 1):
        plan_text += f"*{workout}*\n\n"
    plan_text += (
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 *Хочешь полный план питания и AI-тренера?*\n"
        "Подключи тариф *Форма* за 299 ₽/мес 🔥"
    )
    keyboard = [
        [InlineKeyboardButton("🥗 Получить план питания", callback_data="nutrition_plan")],
        [InlineKeyboardButton("💳 Подключить тариф", callback_data="show_plans")],
        [InlineKeyboardButton("🔄 Другой план", callback_data="free_start")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
    ]
    await query.edit_message_text(
        plan_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return SHOW_PLAN

# ─── ПЛАН ПИТАНИЯ ─────────────────────────────────────────────
async def nutrition_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    goal = context.user_data.get("goal", "похудение")
    plan = NUTRITION_PLANS.get(goal, NUTRITION_PLANS["похудение"])
    keyboard = [
        [InlineKeyboardButton("💳 Получить полный план (Прокачка)", callback_data="show_plans")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
    ]
    await query.edit_message_text(
        plan, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return NUTRITION_MENU

# ─── ТАРИФЫ ───────────────────────────────────────────────────
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "💳 *Выбери свой тариф:*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🆓 *Старт* — Бесплатно\n"
        "7 дней • Базовый план • 1 цель\n\n"
        "💪 *Форма* — 299 ₽/мес\n"
        "Персональный план + питание + прогресс\n\n"
        "🔥 *Прокачка* — 699 ₽/мес\n"
        "Всё выше + AI-тренер 24/7 + анализ еды\n\n"
        "🏆 *Результат* — 1 490 ₽/мес\n"
        "Максимум + живой куратор раз в месяц\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    keyboard = [
        [InlineKeyboardButton("🆓 Начать бесплатно", callback_data="plan_start")],
        [InlineKeyboardButton("💪 Форма — 299 ₽/мес", callback_data="plan_forma")],
        [InlineKeyboardButton("🔥 Прокачка — 699 ₽/мес", callback_data="plan_pro")],
        [InlineKeyboardButton("🏆 Результат — 1490 ₽/мес", callback_data="plan_result")],
        [InlineKeyboardButton("← Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return SUBSCRIPTION_MENU

# ─── ДЕТАЛИ ТАРИФА ────────────────────────────────────────────
async def plan_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace("plan_", "")
    plan = PLANS.get(plan_key, PLANS["forma"])
    features_text = "\n".join(plan["features"])
    text = (
        f"*{plan['name']}*\n"
        f"💰 *{plan['price']} ₽/месяц*\n\n"
        f"{features_text}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Выбери этот тариф?"
    )
    keyboard = []
    if plan["price"] == 0:
        keyboard.append([InlineKeyboardButton("✅ Активировать бесплатно", callback_data="activate_free")])
    else:
        keyboard.append([InlineKeyboardButton(f"💳 Оплатить {plan['price']} ₽/мес", callback_data=f"pay_{plan_key}")])
    keyboard.append([InlineKeyboardButton("← К тарифам", callback_data="show_plans")])
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return SUBSCRIPTION_MENU

# ─── АКТИВАЦИЯ БЕСПЛАТНОГО ТАРИФА ────────────────────────────
async def activate_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["plan"] = "start"
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
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return MAIN_MENU

# ─── ОПЛАТА ───────────────────────────────────────────────────
async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace("pay_", "")
    plan = PLANS.get(plan_key, PLANS["forma"])
    text = (
        f"💳 *Оплата тарифа {plan['name']}*\n\n"
        f"Сумма: *{plan['price']} ₽/месяц*\n\n"
        "Для оплаты подключите платёжную систему в настройках BotFather:\n"
        "• YooKassa\n• Robokassa\n• Stripe\n\n"
        "📌 Инструкция в файле SETUP.md"
    )
    keyboard = [[InlineKeyboardButton("← Назад", callback_data="show_plans")]]
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return SUBSCRIPTION_MENU

# ─── О БОТЕ ───────────────────────────────────────────────────
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
        "• Отвечать на вопросы по здоровью 24/7\n"
        "• Анализировать прогресс и корректировать цели\n\n"
        "📊 *Рынок:* $16.9 млрд (2025) → $65.7 млрд (2033)\n"
        "📈 *Рост:* +18.6% ежегодно\n\n"
        "🏆 *Преимущество:* Единственный полноценный\n"
        "AI-тренер в Telegram на русском языке\n\n"
        "📩 Поддержка: @FormaSupport"
    )
    keyboard = [[InlineKeyboardButton("← Назад", callback_data="back_main")]]
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return MAIN_MENU

# ─── ПРОФИЛЬ ──────────────────────────────────────────────────
async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    plan = context.user_data.get("plan", "Не активирован")
    goal = context.user_data.get("goal", "Не выбрана")
    level = context.user_data.get("level", "Не указан")
    text = (
        f"👤 *Профиль — {user.first_name}*\n\n"
        f"🎯 Цель: *{goal.capitalize() if goal != 'Не выбрана' else goal}*\n"
        f"⚡ Уровень: *{level}*\n"
        f"💳 Тариф: *{plan}*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📊 *Твой прогресс:*\n"
        "Недель в программе: 0\n"
        "Тренировок выполнено: 0\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    keyboard = [
        [InlineKeyboardButton("🔄 Изменить цель", callback_data="free_start")],
        [InlineKeyboardButton("💳 Изменить тариф", callback_data="show_plans")],
        [InlineKeyboardButton("← Назад", callback_data="back_main")],
    ]
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return PROFILE_MENU

# ─── ГЛАВНОЕ МЕНЮ (ВОЗВРАТ) ───────────────────────────────────
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
        [InlineKeyboardButton("👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")],
    ]
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return MAIN_MENU

# ─── ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ───────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
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
            "подключи тариф *Прокачка* (699 ₽/мес)\n\n"
            "А пока — выбери действие в меню ниже:"
        )
    keyboard = [
        [InlineKeyboardButton("🏋️ Мой план тренировок", callback_data="free_start")],
        [InlineKeyboardButton("💳 AI-тренер 24/7", callback_data="show_plans")],
    ]
    await update.message.reply_text(
        reply, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

# ─── MAIN ─────────────────────────────────────────────────────
def main():
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
                CallbackQueryHandler(back_main, pattern="^back_main$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🏋️ ФОРМА Bot запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
