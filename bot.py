import os
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
IRAN_TIMEZONE = ZoneInfo("Asia/Tehran")
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatMemberStatus

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

# =========================
# SETTINGS
# =========================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./bot.db"
)

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@EFbVpn")

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

engine = create_async_engine(
    DATABASE_URL,
    echo=False
)

Session = async_sessionmaker(
    engine,
    expire_on_commit=False
)


# =========================
# DATABASE MODELS
# =========================

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    telegram_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True
    )

    username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    total_points: Mapped[int] = mapped_column(
        Integer,
        default=0
    )


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    home_team: Mapped[str] = mapped_column(
        String(100)
    )

    away_team: Mapped[str] = mapped_column(
        String(100)
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime
    )

    home_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    away_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_finished: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id")
    )

    home_pred: Mapped[int] = mapped_column(
        Integer
    )

    away_pred: Mapped[int] = mapped_column(
        Integer
    )

    points: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "match_id"
        ),
    )


# =========================
# DATABASE
# =========================

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_user(
    session: AsyncSession,
    message: Message
):
    result = await session.execute(
        select(User).where(
            User.telegram_id == message.from_user.id
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            total_points=0,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


# =========================
# MAIN MENU
# =========================

def main_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
    InlineKeyboardButton(
        text="📊 پیش‌بینی‌های من",
        callback_data="mine"
    )
],
[
    InlineKeyboardButton(
        text="👤 پروفایل من",
        callback_data="profile"
    )
],
            [
                InlineKeyboardButton(
                    text="🏆 جدول امتیازات",
                    callback_data="leaderboard"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 پیش‌بینی‌های من",
                    callback_data="mine"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📜 قوانین",
                    callback_data="rules"
                )
            ]
        ]
    )


# =========================
# POINT SYSTEM
# =========================

def calculate_points(
    predicted_home,
    predicted_away,
    real_home,
    real_away
):

    # Exact score
    if (
        predicted_home == real_home
        and predicted_away == real_away
    ):
        return 5

    predicted_diff = (
        predicted_home - predicted_away
    )

    real_diff = (
        real_home - real_away
    )

    # Exact goal difference
    if predicted_diff == real_diff:
        return 4

    # Correct result
    predicted_result = (
        1 if predicted_diff > 0
        else -1 if predicted_diff < 0
        else 0
    )

    real_result = (
        1 if real_diff > 0
        else -1 if real_diff < 0
        else 0
    )

    if predicted_result == real_result:
        return 3

    return 0


# =========================
# SHOW MATCHES
# =========================

async def show_matches(message: Message):

    async with Session() as session:

        result = await session.execute(
            select(Match)
            .where(
                Match.is_finished == False
            )
            .order_by(
                Match.start_time
            )
        )

        matches = result.scalars().all()

        if not matches:

            await message.answer(
                "⚽ فعلاً بازی‌ای برای پیش‌بینی وجود نداره.",
                reply_markup=main_menu()
            )

            return

        buttons = []

        for match in matches:

            locked = (
                match.is_locked
                or datetime.now(IRAN_TIMEZONE).replace(tzinfo=None) >= match.start_time
            )

            status = "🔒" if locked else "🎯"

            buttons.append(
                [
                    InlineKeyboardButton(
                        text=(
                            f"{status} "
                            f"{match.home_team} "
                            f"🆚 "
                            f"{match.away_team}"
                        ),
                        callback_data=f"match:{match.id}"
                    )
                ]
            )

        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="home"
                )
            ]
        )

        await message.answer(
            "🎯 بازی موردنظر رو انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=buttons
            )
        )


# =========================
# LEADERBOARD
# =========================

async def show_leaderboard(message: Message):

    async with Session() as session:

        result = await session.execute(
            select(User)
            .order_by(
                User.total_points.desc()
            )
            .limit(20)
        )

        users = result.scalars().all()

        if not users:

            await message.answer(
                "🏆 هنوز امتیازی ثبت نشده.",
                reply_markup=main_menu()
            )

            return

        text = "🏆 جدول امتیازات\n\n"

        medals = {
            1: "🥇",
            2: "🥈",
            3: "🥉"
        }

        for index, user in enumerate(users, start=1):

            medal = medals.get(
                index,
                f"{index}."
            )

            name = (
                user.first_name
                or user.username
                or "کاربر"
            )

            text += (
                f"{medal} {name}\n"
                f"   ⭐ {user.total_points} امتیاز\n\n"
            )

        await message.answer(
            text,
            reply_markup=main_menu()
        )


# =========================
# MY PREDICTIONS
# =========================

async def show_my_predictions(message: Message):

    async with Session() as session:

        user = await get_user(
            session,
            message
        )

        result = await session.execute(
            select(
                Prediction,
                Match
            )
            .join(
                Match,
                Prediction.match_id == Match.id
            )
            .where(
                Prediction.user_id == user.id
            )
            .order_by(
                Match.start_time.desc()
            )
            .limit(20)
        )

        rows = result.all()

        if not rows:

            await message.answer(
                "📊 هنوز هیچ پیش‌بینی‌ای ثبت نکردی.",
                reply_markup=main_menu()
            )

            return

        text = "📊 پیش‌بینی‌های من\n\n"

        for prediction, match in rows:

            text += (
                f"⚽ {match.home_team} - "
                f"{match.away_team}\n"
                f"🎯 پیش‌بینی: "
                f"{prediction.home_pred} - "
                f"{prediction.away_pred}\n"
                f"🏆 امتیاز: "
                f"{prediction.points}\n\n"
            )

        await message.answer(
            text,
            reply_markup=main_menu()
        )


# =========================
# BOT
# =========================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()
pending_match = {}
REQUIRED_CHANNEL = "@EFbVpn"
REQUIRED_GROUP = "@EFbVpn_Gp"


async def is_member(bot, user_id, chat_username):

    try:
        member = await bot.get_chat_member(
            chat_username,
            user_id
        )

        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        }

    except Exception:
        return False

# =========================
# START
# =========================

@dp.message(Command("start"))
@dp.message(Command("start"))
async def start_handler(message: Message):

    channel_member = await is_member(
        bot,
        message.from_user.id,
        REQUIRED_CHANNEL
    )

    group_member = await is_member(
        bot,
        message.from_user.id,
        REQUIRED_GROUP
    )

    if not channel_member or not group_member:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📢 عضویت در کانال",
                        url="https://t.me/EFbVpn"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👥 عضویت در گروه",
                        url="https://t.me/EFbVpn_Gp"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✅ بررسی عضویت",
                        callback_data="check_membership"
                    )
                ]
            ]
        )

        await message.answer(
            "🔐 برای استفاده از ربات باید در هر دو عضو باشی.\n\n"
            "1️⃣ وارد کانال شو\n"
            "2️⃣ وارد گروه شو\n"
            "3️⃣ سپس روی «✅ بررسی عضویت» بزن",
            reply_markup=keyboard
        )

        return

    async with Session() as session:

        await get_user(
            session,
            message
        )

    await message.answer(
        "⚽ به ربات پیش‌بینی فوتبال خوش اومدی!\n\n"
        "بازی‌ها رو انتخاب کن و نتیجه رو پیش‌بینی کن 🎯",
        reply_markup=main_menu()
    )
@dp.message(Command("matches"))
async def matches_command(message: Message):

    await show_matches(message)


# =========================
# LEADERBOARD COMMAND
# =========================

@dp.message(Command("leaderboard"))
async def leaderboard_command(message: Message):

    await show_leaderboard(message)


# =========================
# CALLBACKS
# =========================

@dp.callback_query(F.data == "home")
async def home_callback(callback):

    await callback.message.edit_text(
        "🏠 منوی اصلی:",
        reply_markup=main_menu()
    )

    await callback.answer()

@dp.callback_query(F.data == "check_membership")
async def check_membership_callback(callback):

    channel_member = await is_member(
        bot,
        callback.from_user.id,
        REQUIRED_CHANNEL
    )

    group_member = await is_member(
        bot,
        callback.from_user.id,
        REQUIRED_GROUP
    )

    if not channel_member or not group_member:

        await callback.answer(
            "❌ هنوز در هر دو عضو نشدی.",
            show_alert=True
        )

        return

    await callback.message.delete()

    async with Session() as session:

        user = await get_user(
            session,
            callback.message
        )

    await callback.message.answer(
        "✅ عضویتت تأیید شد!\n\n"
        "⚽ حالا می‌تونی از ربات استفاده کنی.",
        reply_markup=main_menu()
    )

    await callback.answer()
@dp.callback_query(F.data == "matches")
async def matches_callback(callback):

   # await callback.message.delete()

    await show_matches(
        callback.message
    )

    await callback.answer()


@dp.callback_query(F.data == "leaderboard")
async def leaderboard_callback(callback):

    await callback.message.delete()

    await show_leaderboard(
        callback.message
    )

    await callback.answer()


@dp.callback_query(F.data == "mine")
async def mine_callback(callback):

    await callback.message.delete()

    async with Session() as session:

        result = await session.execute(
            select(
                Prediction,
                Match
            )
            .join(
                Match,
                Prediction.match_id == Match.id
            )
            .join(
                User,
                Prediction.user_id == User.id
            )
            .where(
                User.telegram_id == callback.from_user.id
            )
            .order_by(
                Match.start_time.desc()
            )
            .limit(20)
        )

        rows = result.all()

        if not rows:

            await callback.message.answer(
                "📊 هنوز هیچ پیش‌بینی‌ای ثبت نکردی.",
                reply_markup=main_menu()
            )

            await callback.answer()
            return

        text = "📊 پیش‌بینی‌های من\n\n"

        for prediction, match in rows:

            text += (
                f"⚽ {match.home_team} - "
                f"{match.away_team}\n"
                f"🎯 پیش‌بینی: "
                f"{prediction.home_pred} - "
                f"{prediction.away_pred}\n"
                f"🏆 امتیاز: "
                f"{prediction.points}\n\n"
            )

        await callback.message.answer(
            text,
            reply_markup=main_menu()
        )

    await callback.answer()
    @dp.callback_query(F.data == "profile")
async def profile_callback(callback):
    async with Session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == callback.from_user.id
            )
        )

        user = result.scalar_one_or_none()

        if not user:
            await callback.answer(
                "❌ پروفایل پیدا نشد.",
                show_alert=True
            )
            return

        rank_result = await session.execute(
            select(User.telegram_id).where(
                User.total_points > user.total_points
            )
        )

        rank = len(rank_result.all()) + 1

        prediction_result = await session.execute(
            select(Prediction).where(
                Prediction.user_id == user.id
            )
        )

        predictions = prediction_result.scalars().all()

        total_predictions = len(predictions)

        text = (
            "👤 پروفایل من\n\n"
            f"👋 {user.first_name or 'کاربر'}\n\n"
            f"🏆 رتبه: {rank}\n"
            f"⭐ امتیاز: {user.total_points}\n"
            f"🎯 تعداد پیش‌بینی: {total_predictions}\n"
        )

        await callback.message.answer(
            text,
            reply_markup=main_menu()
        )

    await callback.answer()
@dp.callback_query(F.data == "rules")
async def rules_callback(callback):

    text = (
        "📜 قوانین بازی\n\n"
        "🎯 نتیجه دقیق: ۵ امتیاز\n"
        "⚽ تفاضل گل دقیق: ۴ امتیاز\n"
        "🏆 نتیجه صحیح برد/مساوی/باخت: ۳ امتیاز\n"
        "❌ پیش‌بینی اشتباه: ۰ امتیاز\n\n"
        "⏰ بعد از شروع بازی امکان ثبت پیش‌بینی وجود ندارد."
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ]
        )
    )

    await callback.answer()


# =========================
# SELECT MATCH
# =========================

@dp.callback_query(
    F.data.startswith("match:")
)
async def select_match(callback):

    match_id = int(
        callback.data.split(":")[1]
    )

    async with Session() as session:

        result = await session.execute(
            select(Match).where(
                Match.id == match_id
            )
        )

        match = result.scalar_one_or_none()

        if not match:
            await callback.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True
            )
            return

        locked = (
            match.is_locked
            or match.is_finished
            or datetime.now(IRAN_TIMEZONE).replace(tzinfo=None) >= match.start_time
        )

        if locked:
            await callback.answer(
                "🔒 زمان پیش‌بینی این بازی تمام شده.",
                show_alert=True
            )
            return

        pending_match[callback.from_user.id] = match.id

        await callback.message.answer(
            f"🎯 پیش‌بینی بازی:\n\n"
            f"⚽ {match.home_team} 🆚 {match.away_team}\n\n"
            f"نتیجه رو به این شکل بفرست:\n"
            f"مثلاً:\n"
            f"2-1"
        )

    await callback.answer()


@dp.message(F.text.regexp(r"^\d+\s*-\s*\d+$"))
async def prediction_handler(message: Message):
    try:
        parts = message.text.split("-")

        home_pred = int(parts[0].strip())
        away_pred = int(parts[1].strip())

    except Exception:
        await message.answer(
            "❌ فرمت پیش‌بینی درست نیست.\n"
            "مثال: 2-1"
        )
        return

    if home_pred > 30 or away_pred > 30:
        await message.answer(
            "❌ نتیجه واردشده معتبر نیست."
        )
        return

    user_id = message.from_user.id
    match_id = pending_match.get(user_id)

    if not match_id:
        await message.answer(
            "❌ اول یک بازی رو از بخش «🎯 پیش‌بینی بازی‌ها» انتخاب کن."
        )
        return

    async with Session() as session:

        user = await get_user(
            session,
            message
        )

        result = await session.execute(
            select(Match).where(
                Match.id == match_id
            )
        )

        match = result.scalar_one_or_none()

        if not match:
            pending_match.pop(user_id, None)

            await message.answer(
                "❌ بازی پیدا نشد.",
                reply_markup=main_menu()
            )
            return

        locked = (
            match.is_locked
            or match.is_finished
            or datetime.now(IRAN_TIMEZONE).replace(tzinfo=None) >= match.start_time
        )

        if locked:
            pending_match.pop(user_id, None)

            await message.answer(
                "🔒 زمان پیش‌بینی این بازی تمام شده.",
                reply_markup=main_menu()
            )
            return

        result = await session.execute(
            select(Prediction).where(
                Prediction.user_id == user.id,
                Prediction.match_id == match.id
            )
        )

        prediction = result.scalar_one_or_none()

        if prediction:

            prediction.home_pred = home_pred
            prediction.away_pred = away_pred

        else:

            prediction = Prediction(
                user_id=user.id,
                match_id=match.id,
                home_pred=home_pred,
                away_pred=away_pred,
                points=0
            )

            session.add(prediction)

        await session.commit()

        pending_match.pop(user_id, None)

        await message.answer(
            f"✅ پیش‌بینی ثبت شد!\n\n"
            f"⚽ {match.home_team} "
            f"{home_pred} - {away_pred} "
            f"{match.away_team}\n\n"
            f"🏆 امتیازها بعد از پایان بازی محاسبه میشن.",
            reply_markup=main_menu()
        )
        


# =========================
# ADMIN - ADD MATCH
# =========================

@dp.message(Command("addmatch"))
async def add_match(message: Message):

    if message.from_user.id not in ADMIN_IDS:

        await message.answer(
            "⛔ این دستور فقط برای ادمین است."
        )

        return

    raw = message.text.replace(
        "/addmatch",
        "",
        1
    ).strip()

    parts = raw.split("|")

    if len(parts) != 3:

        await message.answer(
            "❌ فرمت صحیح:\n\n"
            "/addmatch Barcelona|Real Madrid|2026-09-12 21:00"
        )

        return

    home_team = parts[0].strip()
    away_team = parts[1].strip()
    date_text = parts[2].strip()

    try:

        start_time = datetime.strptime(
            date_text,
            "%Y-%m-%d %H:%M"
        )

    except ValueError:

        await message.answer(
            "❌ تاریخ درست نیست.\n"
            "مثال:\n"
            "2026-09-12 21:00"
        )

        return

    async with Session() as session:

        match = Match(
            home_team=home_team,
            away_team=away_team,
            start_time=start_time,
            is_locked=False,
            is_finished=False
        )

        session.add(match)

        await session.commit()

    await message.answer(
        "✅ بازی با موفقیت اضافه شد."
    )


# =========================
# ADMIN - RESULT
# =========================

@dp.message(Command("result"))
async def result_command(message: Message):

    if message.from_user.id not in ADMIN_IDS:

        await message.answer(
            "⛔ این دستور فقط برای ادمین است."
        )

        return

    raw = message.text.replace(
        "/result",
        "",
        1
    ).strip()

    parts = raw.split()

    if len(parts) != 3:

        await message.answer(
            "❌ فرمت صحیح:\n\n"
            "/result 1 2 1"
        )

        return

    try:

        match_id = int(parts[0])
        home_score = int(parts[1])
        away_score = int(parts[2])

    except ValueError:

        await message.answer(
            "❌ اعداد واردشده صحیح نیستند."
        )

        return

    async with Session() as session:

        result = await session.execute(
            select(Match).where(
                Match.id == match_id
            )
        )

        match = result.scalar_one_or_none()

        if not match:

            await message.answer(
                "❌ بازی پیدا نشد."
            )

            return

        match.home_score = home_score
        match.away_score = away_score
        match.is_finished = True
        match.is_locked = True

        result = await session.execute(
            select(Prediction).where(
                Prediction.match_id == match.id
            )
        )

        predictions = result.scalars().all()

        for prediction in predictions:

            points = calculate_points(
                prediction.home_pred,
                prediction.away_pred,
                home_score,
                away_score
            )

            prediction.points = points

            user_result = await session.execute(
                select(User).where(
                    User.id == prediction.user_id
                )
            )

            user = user_result.scalar_one_or_none()

            if user:

                user.total_points += points

        await session.commit()

    await message.answer(
        f"✅ نتیجه ثبت شد:\n\n"
        f"⚽ {match.home_team} "
        f"{home_score} - {away_score} "
        f"{match.away_team}"
    )


# =========================
# RUN BOT
# =========================
async def auto_lock_matches():

    while True:

        async with Session() as session:

            result = await session.execute(
                select(Match).where(
                    Match.is_finished == False,
                    Match.is_locked == False,
                    Match.start_time <= datetime.now(IRAN_TIMEZONE).replace(tzinfo=None)
                )
            )

            matches = result.scalars().all()

            for match in matches:
                match.is_locked = True

            if matches:
                await session.commit()

        await asyncio.sleep(30)
async def main():

    await init_db()
    asyncio.create_task(
    auto_lock_matches()
    )

    print("Bot is running...")

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":

    asyncio.run(main())
