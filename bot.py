import os
import asyncio
from datetime import datetime

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from sqlalchemy import (
    String, Integer, DateTime, Boolean,
    ForeignKey, UniqueConstraint, select
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./bot.db"
)

CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME",
    "@EFbVpn"
)

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv(
        "ADMIN_IDS",
        os.getenv("ADMIN_ID", "")
    ).split(",")
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
        String(255),
        nullable=True
    )

    first_name: Mapped[str | None] = mapped_column(
        String(255),
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
        String(255)
    )

    away_team: Mapped[str] = mapped_column(
        String(255)
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
            "match_id",
            name="uq_prediction"
        ),
    )
  async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_user(
    session: AsyncSession,
    tg_id: int,
    username: str | None,
    first_name: str | None
):
    result = await session.execute(
        select(User).where(User.telegram_id == tg_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=tg_id,
            username=username,
            first_name=first_name
        )

        session.add(user)
        await session.commit()

    return user


def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎯 پیش‌بینی بازی‌ها",
                    callback_data="matches"
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


def is_admin(telegram_id: int):
    return telegram_id in ADMIN_IDS


def calculate_points(
    predicted_home: int,
    predicted_away: int,
    real_home: int,
    real_away: int
):
    # نتیجه دقیق
    if (
        predicted_home == real_home
        and predicted_away == real_away
    ):
        return 5

    # تفاضل گل دقیق
    if (
        predicted_home - predicted_away
        ==
        real_home - real_away
    ):
        return 4

    predicted_result = (
        (predicted_home > predicted_away)
        -
        (predicted_home < predicted_away)
    )

    real_result = (
        (real_home > real_away)
        -
        (real_home < real_away)
    )

    # برد / مساوی / باخت درست
    if predicted_result == real_result:
        return 3

    return 0


async def show_matches(message: Message):

    async with Session() as session:

        result = await session.execute(
            select(Match)
            .where(
                Match.is_finished == False
            )
            .order_by(Match.start_time)
        )

        matches = result.scalars().all()

    if not matches:

        await message.answer(
            "⚽ فعلاً بازی‌ای برای پیش‌بینی ثبت نشده.",
            reply_markup=main_menu()
        )

        return

    buttons = []

    for match in matches:

        status = "🔒" if match.is_locked else "🎯"

        buttons.append([
            InlineKeyboardButton(
                text=(
                    f"{status} "
                    f"{match.home_team} - "
                    f"{match.away_team}"
                ),
                callback_data=f"match:{match.id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🔙 منوی اصلی",
            callback_data="home"
        )
    ])

    await message.answer(
        "🎯 بازی موردنظر را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )


async def show_leaderboard(message: Message):

    async with Session() as session:

        result = await session.execute(
            select(User)
            .order_by(User.total_points.desc())
            .limit(20)
        )

        users = result.scalars().all()

    if not users:

        await message.answer(
            "هنوز کسی امتیازی ندارد.",
            reply_markup=main_menu()
        )

        return

    text = "🏆 <b>جدول امتیازات</b>\n\n"

    for position, user in enumerate(users, 1):

        if user.username:
            name = f"@{user.username}"
        else:
            name = user.first_name or "کاربر"

        text += (
            f"{position}. "
            f"{name} — "
            f"<b>{user.total_points}</b> امتیاز\n"
        )

    await message.answer(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )
  async def show_my_predictions(message: Message):

    async with Session() as session:

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name
        )

        result = await session.execute(
            select(Prediction, Match)
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
        )

        rows = result.all()

    if not rows:

        await message.answer(
            "📊 هنوز هیچ پیش‌بینی‌ای ثبت نکردی.",
            reply_markup=main_menu()
        )

        return

    text = (
        "📊 <b>پیش‌بینی‌های من</b>\n\n"
        f"🏆 امتیاز کل: "
        f"<b>{user.total_points}</b>\n\n"
    )

    for prediction, match in rows[:20]:

        if match.is_finished:

            real_result = (
                f"{match.home_score}-"
                f"{match.away_score}"
            )

        else:

            real_result = "در انتظار نتیجه"

        text += (
            f"⚽ {match.home_team} - "
            f"{match.away_team}\n"
            f"🎯 پیش‌بینی: "
            f"{prediction.home_pred}-"
            f"{prediction.away_pred}\n"
            f"📌 نتیجه: {real_result}\n"
            f"⭐ امتیاز: {prediction.points}\n\n"
        )

    await message.answer(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


bot = Bot(BOT_TOKEN)

dp = Dispatcher()


@dp.message(Command("start"))
async def start_command(message: Message):

    async with Session() as session:

        await get_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name
        )

    await message.answer(
        "سلام 👋\n\n"
        "به ربات پیش‌بینی فوتبال خوش اومدی ⚽🔥\n\n"
        "نتیجه بازی‌ها رو پیش‌بینی کن "
        "و برای جدول امتیازات رقابت کن.",
        reply_markup=main_menu()
    )


@dp.message(Command("matches"))
async def matches_command(message: Message):

    await show_matches(message)


@dp.message(Command("leaderboard"))
async def leaderboard_command(message: Message):

    await show_leaderboard(message)


@dp.callback_query(F.data == "home")
async def home_callback(call):

    await call.answer()

    await call.message.edit_text(
        "🏠 <b>منوی اصلی</b>\n\n"
        "یکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "matches")
async def matches_callback(call):

    await call.answer()

    await show_matches(
        call.message
    )


@dp.callback_query(F.data == "leaderboard")
async def leaderboard_callback(call):

    await call.answer()

    await show_leaderboard(
        call.message
    )


@dp.callback_query(F.data == "mine")
async def mine_callback(call):

    await call.answer()

    await show_my_predictions(
        call.message
    )


@dp.callback_query(F.data == "rules")
async def rules_callback(call):

    await call.answer()

    await call.message.edit_text(

        "📜 <b>قوانین امتیازدهی</b>\n\n"

        "🔥 نتیجه دقیق: <b>۵ امتیاز</b>\n"
        "⚡ تفاضل گل دقیق: <b>۴ امتیاز</b>\n"
        "✅ برد/مساوی/باخت درست: <b>۳ امتیاز</b>\n"
        "❌ پیش‌بینی اشتباه: <b>۰ امتیاز</b>\n\n"

        "🔒 بعد از شروع بازی، "
        "امکان ثبت پیش‌بینی وجود ندارد.",

        reply_markup=main_menu(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("match:"))
async def match_callback(call):

    match_id = int(
        call.data.split(":")[1]
    )

    async with Session() as session:

        match = await session.get(
            Match,
            match_id
        )

    if not match:

        await call.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True
        )

        return

    if (
        match.is_locked
        or match.is_finished
        or datetime.now() >= match.start_time
    ):

        await call.answer(
            "🔒 زمان پیش‌بینی این بازی تمام شده.",
            show_alert=True
        )

        return

    await call.answer()

    await call.message.answer(
        f"🎯 پیش‌بینی برای:\n\n"
        f"<b>{match.home_team} - "
        f"{match.away_team}</b>\n\n"
        "نتیجه را به این شکل ارسال کن:\n"
        "<code>2-1</code>",
        parse_mode="HTML"
    )
  @dp.message(F.text.regexp(r"^\d+\s*-\s*\d+$"))
async def receive_prediction(message: Message):

    predicted_home, predicted_away = [
        int(x.strip())
        for x in message.text.split("-", 1)
    ]

    async with Session() as session:

        user = await get_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name
        )

        result = await session.execute(
            select(Match)
            .where(
                Match.is_finished == False,
                Match.is_locked == False
            )
            .order_by(Match.start_time)
        )

        matches = result.scalars().all()

        now = datetime.now()

        matches = [
            match
            for match in matches
            if match.start_time > now
        ]

        if not matches:

            await message.answer(
                "❌ فعلاً بازی فعالی برای ثبت پیش‌بینی وجود ندارد.",
                reply_markup=main_menu()
            )

            return

        match = matches[0]

        result = await session.execute(
            select(Prediction)
            .where(
                Prediction.user_id == user.id,
                Prediction.match_id == match.id
            )
        )

        prediction = result.scalar_one_or_none()

        if prediction:

            prediction.home_pred = predicted_home
            prediction.away_pred = predicted_away

            text = "✏️ پیش‌بینی‌ات ویرایش شد."

        else:

            prediction = Prediction(
                user_id=user.id,
                match_id=match.id,
                home_pred=predicted_home,
                away_pred=predicted_away
            )

            session.add(prediction)

            text = "✅ پیش‌بینی با موفقیت ثبت شد."

        await session.commit()

    await message.answer(
        f"{text}\n\n"
        f"⚽ {match.home_team} "
        f"<b>{predicted_home}-{predicted_away}</b> "
        f"{match.away_team}",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


@dp.message(Command("addmatch"))
async def add_match_command(message: Message):

    if not is_admin(message.from_user.id):
        return

    raw = message.text.replace(
        "/addmatch",
        "",
        1
    ).strip()

    try:

        home, away, date_text = [
            x.strip()
            for x in raw.split("|")
        ]

        start_time = datetime.strptime(
            date_text,
            "%Y-%m-%d %H:%M"
        )

    except Exception:

        await message.answer(
            "❌ فرمت اشتباه است.\n\n"
            "مثال:\n"
            "/addmatch Barcelona|Real Madrid|2026-09-12 21:00"
        )

        return

    async with Session() as session:

        match = Match(
            home_team=home,
            away_team=away,
            start_time=start_time
        )

        session.add(match)

        await session.commit()

        match_id = match.id

    await message.answer(
        f"✅ بازی با موفقیت اضافه شد.\n\n"
        f"🆔 شماره بازی: {match_id}\n"
        f"⚽ {home} - {away}\n"
        f"🕐 {date_text}"
    )


@dp.message(Command("result"))
async def result_command(message: Message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 3 or "-" not in parts[2]:

        await message.answer(
            "❌ فرمت درست:\n\n"
            "/result 1 3-1"
        )

        return

    try:

        match_id = int(parts[1])

        real_home, real_away = [
            int(x)
            for x in parts[2].split("-", 1)
        ]

    except Exception:

        await message.answer(
            "❌ نتیجه واردشده اشتباه است."
        )

        return

    async with Session() as session:

        match = await session.get(
            Match,
            match_id
        )

        if not match:

            await message.answer(
                "❌ بازی پیدا نشد."
            )

            return

        if match.is_finished:

            await message.answer(
                "⚠️ این بازی قبلاً نتیجه‌گذاری شده."
            )

            return

        match.home_score = real_home
        match.away_score = real_away
        match.is_locked = True
        match.is_finished = True

        result = await session.execute(
            select(Prediction)
            .where(
                Prediction.match_id == match_id
            )
        )

        predictions = result.scalars().all()

        for prediction in predictions:

            points = calculate_points(
                prediction.home_pred,
                prediction.away_pred,
                real_home,
                real_away
            )

            prediction.points = points

            user = await session.get(
                User,
                prediction.user_id
            )

            if user:

                user.total_points += points

        await session.commit()

    await message.answer(
        f"✅ نتیجه ثبت شد.\n\n"
        f"⚽ {match.home_team} "
        f"<b>{real_home}-{real_away}</b> "
        f"{match.away_team}"
    )


async def main():

    await init_db()

    print("Bot is running...")

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
