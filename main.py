# Telegram Game Bot using aiogram (Russian Interface)
# Author: ChatGPT + Upgraded by Daniil
# Description: Bot с /start, /stop, /help, множеством мини-игр и викторин, монеты, ставки и рейтинг

import random
import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import F
from aiogram.types import BotCommand

# ================= CONFIG =================
TOKEN = "8482698273:AAH66NnEQnEz3WNmT6MqMFl5a2-6anf4fAA"
# ==========================================

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================= DATABASE =================
conn = sqlite3.connect("users.db")
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    start_time TEXT
)
""")
conn.commit()

async def set_commands():
    commands = [
        BotCommand(command="start", description="Запустить бота и выбрать игру"),
        BotCommand(command="help", description="Показать справку"),
        BotCommand(command="stop", description="Остановить текущую игру"),
        BotCommand(command="balance", description="Показать баланс и победы"),
        BotCommand(command="leaderboard", description="Показать топ игроков")
    ]
    await bot.set_my_commands(commands)

def register_user(user: types.User):
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (user_id, username, start_time) VALUES (?, ?, ?)",
            (user.id, user.username, datetime.utcnow().isoformat())
        )
        conn.commit()

def add_balance(user_id: int, amount: int):
    cur.execute("UPDATE users SET balance = balance + ?, wins = wins + 1 WHERE user_id = ?", (amount, user_id))
    conn.commit()

def subtract_balance(user_id: int, amount: int):
    cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def get_balance(user_id: int):
    cur.execute("SELECT balance, wins, start_time FROM users WHERE user_id = ?", (user_id,))
    return cur.fetchone()

def get_leaderboard(sort_by="balance"):
    if sort_by not in ["balance", "wins", "time"]:
        sort_by = "balance"
    if sort_by == "time":
        cur.execute("SELECT username, balance, wins, start_time FROM users ORDER BY start_time ASC LIMIT 10")
    else:
        cur.execute(f"SELECT username, balance, wins, start_time FROM users ORDER BY {sort_by} DESC LIMIT 10")
    return cur.fetchall()

async def reward_win(user_id: int):
    coins = random.randint(20, 100)
    add_balance(user_id, coins)
    return coins

# ================= GAME STATES =================
user_games = {}

# ====== KEYBOARDS ======
menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎯 Угадай число"), KeyboardButton(text="✂️ КНБ")],
        [KeyboardButton(text="🧠 Викторина"), KeyboardButton(text="🎲 Кости")],
        [KeyboardButton(text="🔢 Математика"), KeyboardButton(text="😄 Правда или ложь")],
        [KeyboardButton(text="📝 Угадай слово"), KeyboardButton(text="🪙 Бросок монеты")],
        [KeyboardButton(text="❌ Остановить игру")]
    ],
    resize_keyboard=True
)

win_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="▶️ Продолжить игру")],
        [KeyboardButton(text="🎮 Выбрать другую игру")]
    ],
    resize_keyboard=True
)

# ================= COMMANDS =================

@dp.message(Command("start"))
async def start_command(message: types.Message):
    register_user(message.from_user)
    text = (
        "👋 Привет! Я игровой бот!\n\n"

        "Команды:\n\n"
        "/start — Показать игры\n"
        "/stop — Остановить игру\n"
        "/help — Помощь\n"
        "/balance — Показать баланс и статистику\n"
        "/leaderboard — Рейтинг игроков\n"
        
        "🎮 Доступные игры:\n\n"
        "🎯 Угадай число (1–20)\n"
        "✂️ Камень-Ножницы-Бумага\n"
        "🧠 Викторина\n"
        "🎲 Бросок костей\n"
        "🔢 Математическая задача\n"
        "😄 Правда или ложь\n"
        "📝 Угадай слово\n"
        "🪙 Бросок монеты\n\n"
        "👇 Выбери игру в меню ниже"
    )
    await message.answer(text, reply_markup=menu_keyboard)

@dp.message(Command("help"))
async def help_command(message: types.Message):
    text = (
        "ℹ️ Помощь\n\n"
        "/start — Показать игры\n"
        "/stop — Остановить игру\n"
        "/help — Помощь\n"
        "/balance — Показать баланс и статистику\n"
        "/leaderboard — Рейтинг игроков\n\n"
        "🎮 Просто выбери игру на клавиатуре"
    )
    await message.answer(text)

@dp.message(Command("stop"))
async def stop_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_games:
        del user_games[user_id]
        await message.answer("🛑 Игра остановлена", reply_markup=menu_keyboard)
    else:
        await message.answer("❗ У тебя нет активной игры")

@dp.message(Command("balance"))
async def balance_command(message: types.Message):
    register_user(message.from_user)
    bal = get_balance(message.from_user.id)
    if bal:
        balance, wins, start_time = bal
        start_dt = datetime.fromisoformat(start_time)
        delta = datetime.utcnow() - start_dt
        hours = delta.total_seconds() // 3600
        await message.answer(f"💰 Баланс: {balance} монет\n🏆 Побед: {wins}\n⏱ Время в боте: {int(hours)} ч")
    else:
        await message.answer("❗ Ты ещё не играл.")

@dp.message(Command("leaderboard"))
async def leaderboard_command(message: types.Message):
    text = "🏆 Рейтинг игроков (по балансу):\n"
    top = get_leaderboard("balance")
    for i, user in enumerate(top, 1):
        username, balance, wins, _ = user
        text += f"{i}. {username} — {balance} монет, {wins} побед\n"
    await message.answer(text)

# ================= AFTER WIN =================

@dp.message(F.text == "▶️ Продолжить игру")
async def continue_game(message: types.Message):
    await start_command(message)

@dp.message(F.text == "🎮 Выбрать другую игру")
async def choose_new_game(message: types.Message):
    await start_command(message)

# ================= GAMES =================

# --- УГАДАЙ ЧИСЛО ---
@dp.message(F.text == "🎯 Угадай число")
async def start_guess_game(message: types.Message):
    number = random.randint(1, 20)
    user_games[message.from_user.id] = {"game": "guess", "number": number}
    await message.answer("🎯 Я загадал число от 1 до 20. Попробуй угадать!")

async def handle_guess(message: types.Message, game_data: dict):
    try:
        guess = int(message.text)
    except:
        await message.answer("❗ Введи число")
        return
    number = game_data["number"]
    if guess == number:
        coins = await reward_win(message.from_user.id)
        await message.answer(f"🎉 Правильно! Ты выиграл! 💰 +{coins} монет", reply_markup=win_keyboard)
        del user_games[message.from_user.id]
    elif guess < number:
        await message.answer("⬆️ Слишком мало")
    else:
        await message.answer("⬇️ Слишком много")

# --- КНБ ---
@dp.message(F.text == "✂️ КНБ")
async def start_rps_game(message: types.Message):
    user_games[message.from_user.id] = {"game": "rps"}
    await message.answer("✂️ Напиши: камень, ножницы или бумага")

async def handle_rps(message: types.Message):
    text = message.text.lower()
    aliases = {
        "камень": ["камень", "рок", "stone"],
        "ножницы": ["ножницы", "нож", "scissors"],
        "бумага": ["бумага", "лист", "paper"]
    }
    user_choice = None
    for key, values in aliases.items():
        if text in values:
            user_choice = key
    if not user_choice:
        await message.answer("❗ Напиши: камень / ножницы / бумага")
        return
    choices = ["камень", "ножницы", "бумага"]
    bot_choice = random.choice(choices)
    if user_choice == bot_choice:
        result = "🤝 Ничья"
        kb = menu_keyboard
    elif (user_choice == "камень" and bot_choice == "ножницы") or \
         (user_choice == "бумага" and bot_choice == "камень") or \
         (user_choice == "ножницы" and bot_choice == "бумага"):
        coins = await reward_win(message.from_user.id)
        result = f"🎉 Победа! 💰 +{coins} монет"
        kb = win_keyboard
    else:
        result = "😢 Поражение"
        kb = menu_keyboard
    await message.answer(f"🤖 Бот: {bot_choice}\n👤 Ты: {user_choice}\n\n{result}", reply_markup=kb)
    del user_games[message.from_user.id]

# --- ВИКТОРИНА ---
quiz_questions = [  # список вопросов оставляем как есть
    {"q": "Столица Франции?", "a": "париж"},
    {"q": "5 + 5 * 2 = ?", "a": "15"},
    {"q": "В каком году появился Python?", "a": "1991"},
    {"q": "Самая большая планета?", "a": "юпитер"},
    {"q": "Кто открыл Америку?", "a": "колумб"},
    {"q": "Сколько континентов на Земле?", "a": "7"},
    {"q": "Самый высокий водопад?", "a": "ангельский"},
    {"q": "Корень из 64?", "a": "8"},
    {"q": "Кто написал 'Гарри Поттер'?", "a": "роулинг"},
    {"q": "Сколько букв в русском алфавите?", "a": "33"},
    {"q": "Самая маленькая страна?", "a": "ватикан"},
    {"q": "Столица Германии?", "a": "берлин"},
    {"q": "12 * 12 = ?", "a": "144"},
    {"q": "Кто изобрел электрическую лампу?", "a": "эдисон"},
    {"q": "Самая длинная река?", "a": "нисса"},
    {"q": "Планета, известная как 'Красная планета'?", "a": "марс"},
    {"q": "Сколько океанов на Земле?", "a": "5"},
    {"q": "Кто написал 'Войну и мир'?", "a": "толстой"},
    {"q": "Столица Италии?", "a": "рим"},
    {"q": "5 в квадрате?", "a": "25"},
    {"q": "Столица Испании?", "a": "мадрид"},
    {"q": "7 * 8 = ?", "a": "56"},
    {"q": "Кто написал 'Преступление и наказание'?", "a": "достоевский"},
    {"q": "Самая высокая гора в мире?", "a": "эверест"},
    {"q": "Какая планета самая близкая к Солнцу?", "a": "меркурий"},
    {"q": "Сколько дней в високосном году?", "a": "366"},
    {"q": "Кто открыл закон всемирного тяготения?", "a": "ньютон"},
    {"q": "Столица Японии?", "a": "токио"},
    {"q": "12 / 4 = ?", "a": "3"},
    {"q": "Какой элемент имеет символ O?", "a": "кислород"},
    {"q": "Кто написал 'Отцы и дети'?", "a": "тургенев"},
    {"q": "Самая большая страна по площади?", "a": "россия"},
    {"q": "Какой орган отвечает за фильтрацию крови?", "a": "почки"},
    {"q": "Сколько хромосом у человека?", "a": "46"},
    {"q": "Столица Канады?", "a": "оттава"},
    {"q": "5 в кубе?", "a": "125"},
    {"q": "Кто изобрел телефон?", "a": "грей"},
    {"q": "Самый быстрый сухопутный зверь?", "a": "гепард"},
    {"q": "Какая река протекает через Лондон?", "a": "темза"},
    {"q": "Столица Египта?", "a": "каир"},
    {"q": "Какой газ мы вдыхаем для дыхания?", "a": "кислород"},
    {"q": "Кто написал 'Гамлет'?", "a": "шекспир"},
    {"q": "Сколько планет в Солнечной системе?", "a": "8"},
    {"q": "Какой металл самый легкий?", "a": "литий"},
    {"q": "Самый большой океан?", "a": "тихий"},
    {"q": "Столица Австралии?", "a": "канберра"},
    {"q": "7 + 14 = ?", "a": "21"},
    {"q": "Самый большой материк?", "a": "азия"},
    {"q": "Кто написал 'Мастер и Маргарита'?", "a": "булгаков"},
    {"q": "Какая планета известна как 'Голубая планета'?", "a": "земля"},
    {"q": "Сколько минут в часе?", "a": "60"},
    {"q": "Кто создал теорию относительности?", "a": "эйнштейн"},
    {"q": "Столица Бразилии?", "a": "браcилия"},
    {"q": "9 * 9 = ?", "a": "81"},
    {"q": "Кто написал 'Анну Каренину'?", "a": "толстой"},
    {"q": "Самая глубокая точка океана?", "a": "марианская впадина"},
    {"q": "Какая страна известна своими кенгуру?", "a": "австралия"},
    {"q": "Сколько секунд в минуте?", "a": "60"},
    {"q": "Столица Индии?", "a": "нью-дели"},
    {"q": "5 * 11 = ?", "a": "55"},
    {"q": "Кто написал 'Собачье сердце'?", "a": "булгаков"},
    {"q": "Какая планета самая большая?", "a": "юпитер"},
    {"q": "Столица Китая?", "a": "пекин"},
    {"q": "Сколько дней в феврале обычного года?", "a": "28"},
    {"q": "Кто открыл Америку?", "a": "колумб"},
    {"q": "Самая длинная река в мире?", "a": "нил"},
    {"q": "Какой орган отвечает за перекачку крови?", "a": "сердце"},
    {"q": "Столица Турции?", "a": "анкара"},
    {"q": "8 * 7 = ?", "a": "56"},
    {"q": "Кто написал 'Идиот'?", "a": "достоевский"},
    {"q": "Какая планета ближе всего к Земле?", "a": "венера"},
    {"q": "Сколько континентов на Земле?", "a": "7"},
    {"q": "Столица Мексики?", "a": "мехико"},
    {"q": "7 - 3 = ?", "a": "4"},
    {"q": "Кто изобрел радио?", "a": "попов"},
    {"q": "Самая высокая гора Европы?", "a": "эльбрус"},
    {"q": "Какая страна славится пиццей?", "a": "италия"},
    {"q": "Сколько часов в сутках?", "a": "24"},
    {"q": "Кто написал 'Ромео и Джульетта'?", "a": "шекспир"},
    {"q": "Столица Франции?", "a": "париж"},
    {"q": "9 + 10 = ?", "a": "19"},
    {"q": "Кто открыл Австралию?", "a": "капитан кук"},
    {"q": "Какая планета известна как 'Венера'?", "a": "венера"},
    {"q": "Столица Южной Кореи?", "a": "сеул"},
    {"q": "6 * 6 = ?", "a": "36"},
    {"q": "Кто написал 'Дон Кихот'?", "a": "сервантес"},
    {"q": "Самая большая пустыня?", "a": "сахара"},
    {"q": "Сколько дней в неделе?", "a": "7"},
    {"q": "Столица Норвегии?", "a": "осло"},
    {"q": "5 + 7 = ?", "a": "12"},
    {"q": "Кто открыл закон тяготения?", "a": "ньютон"},
    {"q": "Какая планета известна как 'Красная планета'?", "a": "марс"},
    {"q": "Сколько стран в мире?", "a": "195"},
    {"q": "Столица Швеции?", "a": "стокгольм"},
    {"q": "12 / 3 = ?", "a": "4"},
    {"q": "Кто написал 'Вишневый сад'?", "a": "чехов"},
    {"q": "Самая длинная река России?", "a": "ленa"},
    {"q": "Какая страна известна самураями?", "a": "япония"},
    {"q": "Сколько месяцев в году?", "a": "12"},
    {"q": "Столица Польши?", "a": "варшава"},
    {"q": "8 + 9 = ?", "a": "17"},
    {"q": "Кто открыл Америку?", "a": "колумб"},
    {"q": "Какая планета вращается вокруг Солнца быстрее всех?", "a": "меркурий"},
    {"q": "Сколько костей в человеческом теле?", "a": "206"},
    {"q": "Столица Греции?", "a": "афины"},
    {"q": "7 * 5 = ?", "a": "35"},
    {"q": "Кто написал 'Мертвые души'?", "a": "гоголь"},
    {"q": "Самый большой остров в мире?", "a": "гренландия"},
    {"q": "Какая страна славится сакэ?", "a": "япония"},
    {"q": "Сколько океанов на Земле?", "a": "5"},
    {"q": "Столица Португалии?", "a": "лиссабон"},
    {"q": "6 * 9 = ?", "a": "54"},
    {"q": "Кто написал 'Братья Карамазовы'?", "a": "достоевский"},
    {"q": "Какая планета известна как 'Гигант газовый'?", "a": "юпитер"},
    {"q": "Сколько нот в музыкальной октаве?", "a": "12"},
    {"q": "Столица Финляндии?", "a": "хельсинки"},
    {"q": "5 * 8 = ?", "a": "40"},
]

@dp.message(F.text == "🧠 Викторина")
async def start_quiz_game(message: types.Message):
    question = random.choice(quiz_questions)
    user_games[message.from_user.id] = {"game": "quiz", "answer": question["a"]}
    await message.answer(f"🧠 Вопрос:\n{question['q']}")

async def handle_quiz(message: types.Message, game_data: dict):
    user_id = message.from_user.id
    if message.text.lower().strip() == game_data["answer"]:
        coins = await reward_win(user_id)
        await message.answer(f"🎉 Верно! 💰 +{coins} монет", reply_markup=win_keyboard)
    else:
        await message.answer(f"❌ Неверно. Ответ: {game_data['answer']}", reply_markup=menu_keyboard)
    del user_games[user_id]

# --- КОСТИ ---
@dp.message(F.text == "🎲 Кости")
async def start_dice(message: types.Message):
    register_user(message.from_user)
    await message.answer("🎲 Введи ставку в монетах:")
    user_games[message.from_user.id] = {"game": "dice_bet"}

async def handle_dice(message: types.Message, game_data: dict):
    try:
        bet = int(message.text)
    except:
        await message.answer("❗ Введи число")
        return
    user_id = message.from_user.id
    balance = get_balance(user_id)[0]
    if bet > balance:
        await message.answer("❌ У тебя недостаточно монет")
        return
    # Разыгрываем кости
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    if user_roll > bot_roll:
        add_balance(user_id, bet)
        result = f"🎉 Ты выиграл! 💰 +{bet} монет"
    elif user_roll < bot_roll:
        subtract_balance(user_id, bet)
        result = f"😢 Ты проиграл! 💰 -{bet} монет"
    else:
        result = "🤝 Ничья"
    await message.answer(f"🎲 Ты: {user_roll}\n🎲 Бот: {bot_roll}\n{result}", reply_markup=menu_keyboard)
    del user_games[user_id]

# --- МАТЕМАТИКА ---
@dp.message(F.text == "🔢 Математика")
async def start_math(message: types.Message):
    ops = ["+", "-", "*"]
    a = random.randint(1, 30)
    b = random.randint(1, 30)
    op = random.choice(ops)
    if op == "+": ans = a + b
    elif op == "-": ans = a - b
    else: ans = a * b
    user_games[message.from_user.id] = {"game": "math", "answer": str(ans)}
    await message.answer(f"🔢 Сколько будет: {a} {op} {b} ?")

async def handle_math(message: types.Message, game_data: dict):
    user_id = message.from_user.id
    if message.text.strip() == game_data["answer"]:
        coins = await reward_win(user_id)
        await message.answer(f"✅ Правильно! 💰 +{coins} монет", reply_markup=win_keyboard)
    else:
        await message.answer(f"❌ Неверно. Ответ: {game_data['answer']}", reply_markup=menu_keyboard)
    del user_games[user_id]

# --- ПРАВДА ИЛИ ЛОЖЬ ---
facts = [
    ("Солнце — это звезда", "да"),
    ("Человек может дышать под водой", "нет"),
    ("Python — язык программирования", "да"),
    ("Земля плоская", "нет"),
    ("У осьминога 3 сердца", "да"),
    ("Алмаз — самый твёрдый камень", "да"),
    ("Вода кипит при 100°C", "да"),
    ("Луна — планета", "нет"),
    ("Человек имеет 206 костей", "да"),
    ("Зебры — это млекопитающие", "да"),
    ("Марс — самая большая планета", "нет"),
    ("Космос полностью пустой", "нет"),
    ("Вакцины помогают бороться с болезнями", "да"),
    ("Слон — самое маленькое животное на Земле", "нет"),
    ("Кофе содержит кофеин", "да"),
    ("Электричество течёт по проводам", "да"),
    ("Чай зелёный полезнее чёрного", "да"),
    ("Африка — самый большой континент", "нет"),
    ("Гора Эверест — самая высокая на Земле", "да"),
    ("Кенгуру обитает в Австралии", "да"),
    ("Человек может прожить без воды дольше, чем без пищи", "нет"),
    ("Пчёлы производят мёд", "да"),
    ("ДНК — это молекула наследственности", "да"),
    ("Молоко коровы всегда белое", "нет"),
    ("Пингвины умеют летать", "нет"),
    ("Кислород необходим для дыхания человека", "да"),
    ("Земля вращается вокруг Солнца", "да"),
    ("Вулкан — это гора с лавой", "да"),
    ("Крокодилы — холоднокровные животные", "да"),
    ("Человек — единственный вид, который умеет говорить", "нет"),
    ("Коралл — это растение", "нет"),
    ("Гравитация действует на всё", "да"),
    ("Шоколад делают из какао", "да"),
    ("Лёд легче воды", "да"),
    ("Коты умеют видеть в темноте", "да"),
    ("Мышцы не нужны человеку для движения", "нет"),
    ("Чёрные дыры видны невооружённым глазом", "нет"),
    ("Скорость света примерно 300 000 км/с", "да"),
    ("Вулканический пепел горячий", "да"),
    ("Слоны умеют плавать", "да"),
    ("Ртуть — это жидкий металл", "да"),
    ("Планета Венера холоднее Земли", "нет"),
    ("Медузы — беспозвоночные", "да"),
    ("Человеческий мозг весит около 1.4 кг", "да"),
    ("Огурцы — это фрукты", "да"),
    ("Солнце больше Луны", "да"),
    ("Дельфины — млекопитающие", "да"),
    ("Сахар растворяется в воде", "да"),
    ("Камни могут плавать на воде", "нет"),
    ("Листья деревьев зелёные из-за хлорофилла", "да"),
]


@dp.message(F.text == "😄 Правда или ложь")
async def start_truth(message: types.Message):
    fact, answer = random.choice(facts)
    user_games[message.from_user.id] = {"game": "truth", "answer": answer}
    await message.answer(f"😄 Правда или ложь?\n{fact}\n(ответь: да / нет)")

async def handle_truth(message: types.Message, game_data: dict):
    user_id = message.from_user.id
    if message.text.lower() == game_data["answer"]:
        coins = await reward_win(user_id)
        await message.answer(f"🎉 Верно! 💰 +{coins} монет", reply_markup=win_keyboard)
    else:
        await message.answer(f"❌ Неверно. Ответ: {game_data['answer']}", reply_markup=menu_keyboard)
    del user_games[user_id]

# --- УГАДАЙ СЛОВО ---
words_list = [
    "кот", "собака", "машина", "компьютер", "телефон", "дерево", "река", "гора",
    "цветок", "солнце", "луна", "звезда", "птица", "рыба", "кошка", "мяч", "стол",
    "стул", "окно", "дверь", "книга", "ручка", "карандаш", "тетрадь", "школа", 
    "учитель", "ученик", "город", "страна", "океан", "озеро", "снег", "дождь", 
    "ветер", "облако", "музыка", "гитара", "пианино", "кино", "театр", "парк", 
    "улица", "машинист", "велосипед", "самолет", "поезд", "корабль", "пицца", 
    "яблоко", "банан", "апельсин", "морковь", "картофель", "шоколад", "конфета",
    "собрание", "праздник", "друзья", "семья", "птица", "лягушка", "заяц", "медведь",
    "лев", "тигр", "слон", "жираф", "обезьяна", "черепаха", "акула", "дельфин",
    "кит", "ракета", "планета", "звезда", "галактика", "комета", "молоко", "вода",
    "чай", "кофе", "суп", "хлеб", "масло", "сыр"
]


@dp.message(F.text == "📝 Угадай слово")
async def start_word_game(message: types.Message):
    word = random.choice(words_list)
    scrambled = "".join(random.sample(word, len(word)))
    user_games[message.from_user.id] = {"game": "word", "answer": word}
    await message.answer(f"📝 Угадай слово:\n{scrambled}")

async def handle_word(message: types.Message, game_data: dict):
    user_id = message.from_user.id
    if message.text.lower() == game_data["answer"]:
        coins = await reward_win(user_id)
        await message.answer(f"🎉 Верно! 💰 +{coins} монет", reply_markup=win_keyboard)
    else:
        await message.answer(f"❌ Неверно. Ответ: {game_data['answer']}", reply_markup=menu_keyboard)
    del user_games[user_id]

# --- БРОСОК МОНЕТЫ ---
@dp.message(F.text == "🪙 Бросок монеты")
async def start_coin_game(message: types.Message):
    coin = random.choice(["орёл", "решка"])
    user_games[message.from_user.id] = {"game": "coin", "answer": coin}
    await message.answer("🪙 Выбери: орёл или решка")

async def handle_coin(message: types.Message, game_data: dict):
    user_id = message.from_user.id
    user_choice = message.text.lower()
    if user_choice not in ["орёл", "решка"]:
        await message.answer("❗ Напиши: орёл / решка")
        return
    if user_choice == game_data["answer"]:
        coins = await reward_win(user_id)
        await message.answer(f"🎉 Выпало {game_data['answer']}! Ты выиграл! 💰 +{coins} монет", reply_markup=win_keyboard)
    else:
        await message.answer(f"❌ Выпало {game_data['answer']}! Ты проиграл.", reply_markup=menu_keyboard)
    del user_games[user_id]

# --- СТОП КНОПКА ---
@dp.message(F.text == "❌ Остановить игру")
async def stop_game_button(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_games:
        del user_games[user_id]
        await message.answer("🛑 Игра остановлена", reply_markup=menu_keyboard)
    else:
        await message.answer("❗ Нет активной игры")

# ================= MAIN HANDLER =================
@dp.message()
async def main_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_games:
        await message.answer("ℹ️ Напиши /start и выбери игру", reply_markup=menu_keyboard)
        return
    game = user_games[user_id]["game"]
    if game == "guess":
        await handle_guess(message, user_games[user_id])
    elif game == "rps":
        await handle_rps(message)
    elif game == "quiz":
        await handle_quiz(message, user_games[user_id])
    elif game == "math":
        await handle_math(message, user_games[user_id])
    elif game == "truth":
        await handle_truth(message, user_games[user_id])
    elif game == "word":
        await handle_word(message, user_games[user_id])
    elif game == "coin":
        await handle_coin(message, user_games[user_id])
    elif game == "dice_bet":
        await handle_dice(message, user_games[user_id])

# ================= START BOT =================
async def main():
    print("🤖 Бот запущен...")
    await set_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
