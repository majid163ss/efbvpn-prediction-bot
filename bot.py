import os
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
IRAN_TIMEZONE = ZoneInfo("Asia/Tehran")
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.enums import ChatMemberStatus

from sqlalchemy import (
text,
    String,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    func,
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

class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    telegram_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True
    )
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
    level: Mapped[int] = mapped_column(
        Integer,
        default=1
    )

    current_streak: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    best_streak: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    medals: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
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
    is_published: Mapped[bool] = mapped_column(
    Boolean,
    default=False
    )
    is_special: Mapped[bool] = mapped_column(
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
    created_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.utcnow
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
class WeeklyWinner(Base):
    __tablename__ = "weekly_winners"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    week_start: Mapped[datetime] = mapped_column(
        DateTime,
        unique=True
    )

    points: Mapped[int] = mapped_column(
        Integer
    )


class WeeklyPrize(Base):
    __tablename__ = "weekly_prizes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    week_start: Mapped[datetime] = mapped_column(
        DateTime,
        index=True
    )

    prize_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    prize_content: Mapped[str | None] = mapped_column(
        String(5000),
        nullable=True
    )

    winner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )

    is_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    is_announced: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
class GalleryImage(Base):
    __tablename__ = "gallery_images"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    file_id: Mapped[str] = mapped_column(
        String(255)
    )

    player_name: Mapped[str] = mapped_column(
        String(100),
        index=True
    )

    caption: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )
class EfootballSection(Base):
    __tablename__ = "efootball_sections"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
class EfootballContent(Base):
    __tablename__ = "efootball_contents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    section_id: Mapped[int] = mapped_column(
        ForeignKey("efootball_sections.id"),
        index=True
    )

    content_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True
    )

    content: Mapped[str | None] = mapped_column(
        String(5000),
        nullable=True
    )

    file_id: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
    


# =========================
# DATABASE
# =========================

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # ستون‌های جدید سیستم امتیازات
        try:
            await conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN level INTEGER DEFAULT 1"
                )
            )
        except Exception:
            pass

        try:
            await conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN current_streak INTEGER DEFAULT 0"
                )
            )
        except Exception:
            pass

        try:
            await conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN best_streak INTEGER DEFAULT 0"
                )
            )
        except Exception:
            pass

        try:
            await conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN medals VARCHAR(1000)"
                )
            )
        except Exception:
            pass

        try:
            await conn.execute(
                text(
                    "ALTER TABLE matches "
                    "ADD COLUMN is_special BOOLEAN DEFAULT 0"
                )
            )
        except Exception:
            pass
        # ثبت سوپر ادمین‌ها در دیتابیس
        for admin_id in SUPER_ADMIN_IDS:
            await conn.execute(
                text(
                    "INSERT OR IGNORE INTO admins (telegram_id) VALUES (:telegram_id)"
                ),
                {"telegram_id": admin_id}
            )

        try:
            await conn.execute(
                text(
                    "ALTER TABLE predictions "
                    "ADD COLUMN created_at DATETIME"
                )
            )
        except Exception:
            pass
    try:
        await conn.execute(
            text(
            "ALTER TABLE matches "
            "ADD COLUMN is_published BOOLEAN DEFAULT 0"
        )
    )
    except Exception:
       pass


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
                    text="🎯 پیش‌بینی نتایج",
                    callback_data="prediction_menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎮 ای فوتبال",
                    callback_data="efootball"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ پنل مدیریت",
                    callback_data="admin_panel"
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
def get_level(points):
    if points >= 200:
        return 5
    if points >= 100:
        return 4
    if points >= 50:
        return 3
    if points >= 20:
        return 2
    return 1


def get_medal(level):
    medals = {
        1: "🥉",
        2: "🥈",
        3: "🥇",
        4: "🏆",
        5: "👑"
    }

    return medals.get(level, "🥉")


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

        for index, user in enumerate(
            users,
            start=1
        ):

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
@dp.callback_query(F.data.startswith("ef_section:"))
async def ef_section_callback(callback):

    section_id = int(callback.data.split(":")[1])

    async with Session() as session:
        result = await session.execute(
            select(EfootballContent)
            .where(
                EfootballContent.section_id == section_id,
                EfootballContent.is_active == True
            )
            .order_by(EfootballContent.sort_order.asc())
        )

        contents = result.scalars().all()

    if not contents:
        await callback.answer(
            "📭 این بخش هنوز محتوایی نداره.",
            show_alert=True
        )
        return

    for item in contents:

        if item.content_type == "text":
            await callback.message.answer(
                item.content or ""
            )

        elif item.content_type == "photo" and item.file_id:
            await callback.message.answer_photo(
                photo=item.file_id,
                caption=item.content or ""
            )

        elif item.content_type == "video" and item.file_id:
            await callback.message.answer_video(
                video=item.file_id,
                caption=item.content or ""
            )

    await callback.answer()
@dp.callback_query(F.data == "efootball")
async def efootball_callback(callback):

    async with Session() as session:

        result = await session.execute(
            select(EfootballSection)
            .where(
                EfootballSection.is_active == True
            )
            .order_by(
                EfootballSection.sort_order.asc()
            )
        )

        sections = result.scalars().all()

    keyboard = []

    keyboard.append([
        InlineKeyboardButton(
            text="🎮 مکس‌های eFootball",
            callback_data="gallery"
        )
    ])

    for section in sections:
        keyboard.append([
            InlineKeyboardButton(
                text=section.title,
                callback_data=f"ef_section:{section.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data="home"
        )
    ])

    await callback.message.edit_text(
        "🎮 ای فوتبال\n\n"
        "یکی از بخش‌ها رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )

    await callback.answer()
@dp.message(F.text == "☰ منوی اصلی")
async def persistent_menu_handler(message: Message):
    await message.answer(
        "🏠 منوی اصلی",
        reply_markup=main_menu()
    )


SUPER_ADMIN_IDS = {
    6833441844,
    1116170821
}

ADMIN_IDS = set(SUPER_ADMIN_IDS)


def is_admin(user_id):
    return user_id in ADMIN_IDS


def is_super_admin(user_id):
    return user_id in SUPER_ADMIN_IDS


pending_match = {}

REQUIRED_CHANNEL = "@EFbVpn"
REQUIRED_GROUP = "@EFbVpn_Gp"


async def is_member(bot, user_id, chat_username):

    try:

        member = await bot.get_chat_member(
            chat_username,
            user_id
        )

        print(
            f"👤 Membership check | "
            f"user={user_id} | "
            f"chat={chat_username} | "
            f"status={member.status}"
        )

        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        }

    except Exception as e:

        print(
            f"❌ Membership error | "
            f"user={user_id} | "
            f"chat={chat_username} | "
            f"error={e}"
        )

        return False

# =========================
# START
# =========================

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

    # بررسی لینک مستقیم یک بازی
    start_param = None

    if message.text:
        parts = message.text.split(maxsplit=1)

        if len(parts) == 2:
            start_param = parts[1].strip()

    if start_param and start_param.startswith("match_"):

        try:
            match_id = int(
                start_param.replace("match_", "", 1)
            )
        except ValueError:
            match_id = None

        if match_id is not None:

            async with Session() as session:

                result = await session.execute(
                    select(Match).where(
                        Match.id == match_id
                    )
                )

                match = result.scalar_one_or_none()

            if not match:

                await message.answer(
                    "❌ این بازی پیدا نشد."
                )
                return

            locked = (
                match.is_locked
                or match.is_finished
                or datetime.now(
                    IRAN_TIMEZONE
                ).replace(tzinfo=None) >= match.start_time
            )

            if locked:

                await message.answer(
                    "🔒 زمان پیش‌بینی این بازی تمام شده."
                )
                return

            pending_match[
                message.from_user.id
            ] = match.id

            await message.answer(
                f"🎯 پیش‌بینی بازی:\n\n"
                f"⚽ {match.home_team} 🆚 {match.away_team}\n\n"
                f"نتیجه رو به این شکل بفرست:\n"
                f"مثلاً:\n"
                f"2-1"
            )

            return

    # ورود معمولی به ربات
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

    await message.answer(
        "☰ برای باز کردن منوی اصلی، از دکمه پایین استفاده کن.",
        reply_markup=persistent_menu()
    )


# =========================
# LEADERBOARD COMMAND
# =========================

@dp.message(Command("leaderboard"))
async def leaderboard_command(message: Message):

    await show_leaderboard(message)

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    keyboard_buttons = [
        [
            InlineKeyboardButton(
                text="➕ افزودن بازی",
                callback_data="admin_add_match"
            )
        ],
        [
            InlineKeyboardButton(
                text="📢 انتشار بازی‌ها در کانال",
                callback_data="admin_publish_matches"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎮 افزودن مکس eFootball",
                callback_data="admin_add_gallery"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎮 مدیریت eFootball",
                callback_data="admin_efootball"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 مدیریت بازی‌ها",
                callback_data="admin_matches"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏁 ثبت نتیجه",
                callback_data="admin_result"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 آمار کاربران",
                callback_data="admin_stats"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎁 مدیریت جایزه هفتگی",
                callback_data="admin_weekly_prize"
            )
        ]
    ]

    if is_super_admin(callback.from_user.id):
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="👑 مدیریت ادمین‌ها",
                callback_data="admin_manage"
            )
        ])

    keyboard_buttons.append([
        InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data="home"
        )
    ])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=keyboard_buttons
    )

    await callback.message.edit_text(
        "⚙️ پنل مدیریت\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=keyboard
    )

    await callback.answer()
    # =========================
# ADMIN MANAGEMENT
# =========================

pending_admin_action = {}


def admin_management_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ افزودن ادمین",
                    callback_data="admin_add"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ حذف ادمین",
                    callback_data="admin_delete"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 لیست ادمین‌ها",
                    callback_data="admin_list"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="admin_panel"
                )
            ]
        ]
    )


@dp.callback_query(F.data == "admin_manage")
async def admin_manage_callback(callback):

    if not is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ فقط سوپرادمین‌ها دسترسی دارند.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "👑 مدیریت ادمین‌ها\n\n"
        "یکی از گزینه‌ها را انتخاب کن:",
        reply_markup=admin_management_menu()
    )

    await callback.answer()
@dp.callback_query(F.data == "admin_weekly_prize")
async def admin_weekly_prize_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎁 تعیین جایزه این هفته",
                    callback_data="weekly_prize_set"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 انتخاب برنده هفته",
                    callback_data="weekly_prize_winner"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 اعلام برنده در کانال",
                    callback_data="weekly_prize_announce"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="admin_panel"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "🎁 مدیریت جایزه هفتگی\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=keyboard
    )

    await callback.answer()


# =========================
# ADD ADMIN
# =========================

@dp.callback_query(F.data == "admin_add")
async def admin_add_callback(callback):

    if not is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ فقط سوپرادمین‌ها دسترسی دارند.",
            show_alert=True
        )
        return

    pending_admin_action[callback.from_user.id] = "add"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data="admin_manage"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "➕ افزودن ادمین\n\n"
        "آیدی عددی تلگرام شخص را ارسال کن.\n\n"
        "مثال:\n"
        "123456789",
        reply_markup=keyboard
    )

    await callback.answer()


# =========================
# DELETE ADMIN
# =========================

@dp.callback_query(F.data == "admin_delete")
async def admin_delete_callback(callback):

    if not is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ فقط سوپرادمین‌ها دسترسی دارند.",
            show_alert=True
        )
        return

    pending_admin_action[callback.from_user.id] = "delete"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data="admin_manage"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "❌ حذف ادمین\n\n"
        "آیدی عددی ادمینی که می‌خواهی حذف شود را ارسال کن.\n\n"
        "⚠️ سوپرادمین‌ها قابل حذف نیستند.",
        reply_markup=keyboard
    )

    await callback.answer()


# =========================
# ADMIN LIST
# =========================

@dp.callback_query(F.data == "admin_list")
async def admin_list_callback(callback):

    if not is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ فقط سوپرادمین‌ها دسترسی دارند.",
            show_alert=True
        )
        return

    async with Session() as session:

        result = await session.execute(
            select(Admin).order_by(Admin.id)
        )

        admins = result.scalars().all()

    if not admins:
        text_message = "📋 هیچ ادمینی ثبت نشده است."
    else:
        lines = ["📋 لیست ادمین‌ها\n"]

        for number, admin in enumerate(admins, start=1):

            if admin.telegram_id in SUPER_ADMIN_IDS:
                role = "👑 سوپرادمین"
            else:
                role = "🛡 ادمین"

            lines.append(
                f"{number}. `{admin.telegram_id}` — {role}"
            )

        text_message = "\n".join(lines)

    await callback.message.edit_text(
        text_message,
        parse_mode="Markdown",
        reply_markup=admin_management_menu()
    )

    await callback.answer()


# =========================
# RECEIVE ADMIN ID
# =========================

@dp.message(F.text.regexp(r"^\d+$"))
async def admin_id_input_handler(message: Message):

    user_id = message.from_user.id

    if not is_super_admin(user_id):
        return

    action = pending_admin_action.get(user_id)

    if not action:
        return

    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ آیدی وارد شده معتبر نیست."
        )
        return

    # =========================
    # ADD
    # =========================

    if action == "add":

        async with Session() as session:

            result = await session.execute(
                select(Admin).where(
                    Admin.telegram_id == target_id
                )
            )

            existing_admin = result.scalar_one_or_none()

            if existing_admin:
                pending_admin_action.pop(user_id, None)

                await message.answer(
                    "⚠️ این شخص از قبل ادمین است."
                )
                return

            new_admin = Admin(
                telegram_id=target_id
            )

            session.add(new_admin)
            await session.commit()

        ADMIN_IDS.add(target_id)

        pending_admin_action.pop(user_id, None)

        await message.answer(
            "✅ ادمین با موفقیت اضافه شد.\n\n"
            f"🆔 `{target_id}`",
            parse_mode="Markdown",
            reply_markup=admin_management_menu()
        )

        return

    # =========================
    # DELETE
    # =========================

    if action == "delete":

        if target_id in SUPER_ADMIN_IDS:

            pending_admin_action.pop(user_id, None)

            await message.answer(
                "⛔ سوپرادمین قابل حذف نیست."
            )
            return

        async with Session() as session:

            result = await session.execute(
                select(Admin).where(
                    Admin.telegram_id == target_id
                )
            )

            admin = result.scalar_one_or_none()

            if not admin:

                pending_admin_action.pop(user_id, None)

                await message.answer(
                    "⚠️ این آیدی در لیست ادمین‌ها وجود ندارد."
                )
                return

            await session.delete(admin)
            await session.commit()

        ADMIN_IDS.discard(target_id)

        pending_admin_action.pop(user_id, None)

        await message.answer(
            "✅ ادمین با موفقیت حذف شد.\n\n"
            f"🆔 `{target_id}`",
            parse_mode="Markdown",
            reply_markup=admin_management_menu()
        )

        return
@dp.callback_query(F.data == "admin_efootball")
async def admin_efootball_callback(callback):
    print("🔥 NEW EFOOTBALL ADMIN MENU")

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📂 مدیریت بخش‌ها",
                    callback_data="ef_manage_sections"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📄 مدیریت محتوا",
                    callback_data="ef_manage_content"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="admin_panel"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "🎮 مدیریت eFootball\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=keyboard
    )

    await callback.answer()
@dp.callback_query(F.data == "ef_manage_sections")
async def ef_manage_sections_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ افزودن بخش",
                    callback_data="ef_add_section"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ ویرایش بخش",
                    callback_data="ef_edit_section"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ حذف بخش",
                    callback_data="ef_delete_section"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 لیست بخش‌ها",
                    callback_data="ef_list_sections"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="admin_efootball"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "📂 مدیریت بخش‌های eFootball\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=keyboard
    )

    await callback.answer()
    # =========================
# لیست بخش‌های eFootball
# =========================

@dp.callback_query(F.data == "ef_list_sections")
async def ef_list_sections_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    async with Session() as session:

        result = await session.execute(
            select(EfootballSection)
            .order_by(EfootballSection.sort_order.asc())
        )

        sections = result.scalars().all()

    if not sections:
        text = "📭 هنوز هیچ بخشی ساخته نشده."
    else:
        text = "📋 لیست بخش‌های eFootball\n\n"

        for i, section in enumerate(sections, 1):
            text += (
                f"{i}. {section.title}\n"
                f"🆔 ID: {section.id}\n\n"
            )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="ef_manage_sections"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )

    await callback.answer()


# =========================
# انتخاب بخش برای ویرایش
# =========================

@dp.callback_query(F.data == "ef_edit_section")
async def ef_edit_section_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    async with Session() as session:

        result = await session.execute(
            select(EfootballSection)
            .order_by(EfootballSection.sort_order.asc())
        )

        sections = result.scalars().all()

    if not sections:
        await callback.answer(
            "📭 هنوز هیچ بخشی وجود ندارد.",
            show_alert=True
        )
        return

    keyboard = []

    for section in sections:
        keyboard.append([
            InlineKeyboardButton(
                text=f"✏️ {section.title}",
                callback_data=f"ef_edit_select:{section.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data="ef_manage_sections"
        )
    ])

    await callback.message.edit_text(
        "✏️ بخشی که می‌خوای ویرایش کنی رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )

    await callback.answer()


# =========================
# انتخاب بخش برای حذف
# =========================

@dp.callback_query(F.data == "ef_delete_section")
async def ef_delete_section_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    async with Session() as session:

        result = await session.execute(
            select(EfootballSection)
            .order_by(EfootballSection.sort_order.asc())
        )

        sections = result.scalars().all()

    if not sections:
        await callback.answer(
            "📭 هنوز هیچ بخشی وجود ندارد.",
            show_alert=True
        )
        return

    keyboard = []

    for section in sections:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🗑️ {section.title}",
                callback_data=f"ef_delete_select:{section.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data="ef_manage_sections"
        )
    ])

    await callback.message.edit_text(
        "🗑️ بخشی که می‌خوای حذف کنی رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )

    await callback.answer()


# =========================
# انتخاب بخش برای ویرایش
# =========================

@dp.callback_query(F.data.startswith("ef_edit_select:"))
async def ef_edit_select_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    section_id = int(callback.data.split(":")[1])

    async with Session() as session:

        result = await session.execute(
            select(EfootballSection).where(
                EfootballSection.id == section_id
            )
        )

        section = result.scalar_one_or_none()

    if not section:
        await callback.answer(
            "❌ بخش پیدا نشد.",
            show_alert=True
        )
        return

    user_id = callback.from_user.id

    pending_match[user_id] = "ef_edit_section"
    pending_match[f"{user_id}_edit_section"] = section_id

    await callback.message.answer(
        f"✏️ ویرایش بخش\n\n"
        f"بخش فعلی: {section.title}\n\n"
        f"اسم جدید بخش رو بفرست:"
    )

    await callback.answer()


# =========================
# انتخاب بخش برای حذف
# =========================

@dp.callback_query(F.data.startswith("ef_delete_select:"))
async def ef_delete_select_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    section_id = int(callback.data.split(":")[1])

    async with Session() as session:

        result = await session.execute(
            select(EfootballSection).where(
                EfootballSection.id == section_id
            )
        )

        section = result.scalar_one_or_none()

    if not section:
        await callback.answer(
            "❌ بخش پیدا نشد.",
            show_alert=True
        )
        return

    user_id = callback.from_user.id

    pending_match[user_id] = "ef_delete_section"
    pending_match[f"{user_id}_delete_section"] = section_id

    await callback.message.answer(
        f"🗑️ حذف بخش\n\n"
        f"بخش انتخاب‌شده: {section.title}\n\n"
        f"برای حذف، کلمه «حذف» را بفرست."
    )

    await callback.answer()
@dp.callback_query(F.data == "ef_add_section")
async def ef_add_section_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    pending_match[callback.from_user.id] = "ef_add_section"

    await callback.message.answer(
        "➕ افزودن بخش eFootball\n\n"
        "اسم بخش رو بفرست.\n\n"
        "مثال:\n"
        "🧠 سبک‌های بازی"
    )

    await callback.answer()
@dp.callback_query(F.data == "admin_add_gallery")
async def admin_add_gallery_callback(callback):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    pending_match[callback.from_user.id] = "admin_gallery_player"

    await callback.message.answer(
        "🎮 افزودن مکس eFootball\n\n"
        "اسم بازیکن رو بفرست.\n\n"
        "مثال:\n"
        "Messi"
    )

    await callback.answer()
@dp.callback_query(F.data == "admin_result")
async def admin_result_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    async with Session() as session:

        result = await session.execute(
            select(Match).where(
                Match.is_finished == False
            ).order_by(Match.start_time)
        )

        matches = result.scalars().all()

    if not matches:
        await callback.answer(
            "❌ هیچ بازی فعالی وجود ندارد.",
            show_alert=True
        )
        return

    buttons = []

    for match in matches:

        buttons.append([
            InlineKeyboardButton(
                text=f"⚽ {match.home_team} 🆚 {match.away_team}",
                callback_data=f"result_match:{match.id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data="admin_panel"
        )
    ])

    await callback.message.edit_text(
        "🏁 ثبت نتیجه\n\n"
        "بازی موردنظر را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()
@dp.callback_query(F.data == "admin_add_match")
async def admin_add_match_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    pending_match[callback.from_user.id] = "admin_add_match"

    await callback.message.answer(
        "➕ افزودن بازی\n\n"
        "فرمت ارسال:\n\n"
        "Barcelona|Real Madrid|2026-09-13 21:00\n\n"
        "مثال:\n"
        "Inter|Milan|2026-09-13 22:30"
    )

    await callback.answer()

@dp.message(F.text.contains("|"))
async def admin_add_match_message(message: Message):

    if not is_admin(message.from_user.id):
        return

    if pending_match.get(message.from_user.id) != "admin_add_match":
        return

    parts = message.text.split("|")

    if len(parts) != 3:
        await message.answer(
            "❌ فرمت اشتباه است.\n\n"
            "مثال:\n"
            "Barcelona|Real Madrid|2026-09-13 21:00"
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
            "❌ تاریخ درست نیست.\n\n"
            "مثال:\n"
            "2026-09-13 21:00"
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
        await session.refresh(match)

    pending_match.pop(message.from_user.id, None)

    await message.answer(
        f"✅ بازی با موفقیت اضافه شد.\n\n"
        f"⚽ {home_team} 🆚 {away_team}\n"
        f"🆔 شماره بازی: {match.id}\n"
        f"⏰ {date_text}"
    )
@dp.callback_query(F.data == "admin_matches")
async def admin_matches_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    async with Session() as session:

        result = await session.execute(
            select(Match)
            .where(Match.is_finished == False)
            .order_by(Match.start_time)
        )

        matches = result.scalars().all()

    if not matches:
        await callback.message.edit_text(
            "📋 هیچ بازی فعالی وجود ندارد.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 بازگشت",
                            callback_data="admin_panel"
                        )
                    ]
                ]
            )
        )
        await callback.answer()
        return

    buttons = []

    for match in matches:

        status = "🔒" if match.is_locked else "🟢"

        buttons.append([
            InlineKeyboardButton(
                text=f"{status} {match.home_team} 🆚 {match.away_team}",
                callback_data=f"admin_match:{match.id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data="admin_panel"
        )
    ])

    await callback.message.edit_text(
        "📋 مدیریت بازی‌ها\n\n"
        "بازی موردنظر رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()
@dp.callback_query(F.data.startswith("admin_match:"))
async def admin_match_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    print("RESULT CALLBACK DATA:", callback.data)

    match_id = int(
        callback.data.split(":")[-1]
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

    status = (
        "🔒 قفل شده"
        if match.is_locked
        else "🟢 باز"
    )

    special_status = (
        "🎯 بازی ویژه ×۲"
        if match.is_special
        else "⚪ بازی معمولی"
    )

    special_button_text = (
        "❌ غیرفعال کردن بازی ویژه"
        if match.is_special
        else "🎯 فعال کردن بازی ویژه ×۲"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔒 قفل بازی",
                    callback_data=f"lock_match:{match.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔓 باز کردن بازی",
                    callback_data=f"unlock_match:{match.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=special_button_text,
                    callback_data=f"toggle_special:{match.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏁 ثبت نتیجه",
                    callback_data=f"result_match:{match.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 حذف بازی",
                    callback_data=f"delete_match:{match.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="admin_matches"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        f"⚽ {match.home_team} 🆚 {match.away_team}\n\n"
        f"⏰ {match.start_time}\n"
        f"📌 وضعیت: {status}\n"
        f"🎯 وضعیت ویژه: {special_status}\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=keyboard
    )

    await callback.answer()
@dp.callback_query(F.data.startswith("toggle_special:"))
async def toggle_special_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    match_id = int(
        callback.data.split(":")[-1]
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

        match.is_special = not match.is_special

        await session.commit()

        status = (
            "🎯 بازی ویژه ×۲ فعال شد."
            if match.is_special
            else "⚪ بازی ویژه غیرفعال شد."
        )

    await callback.answer(
        status,
        show_alert=True
    )

    # باز کردن دوباره صفحه مدیریت همین بازی
    await admin_match_callback(callback)
@dp.callback_query(F.data.startswith("lock_match:"))
async def lock_match_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    match_id = int(callback.data.split(":")[1])

    async with Session() as session:

        result = await session.execute(
            select(Match).where(Match.id == match_id)
        )

        match = result.scalar_one_or_none()

        if not match:
            await callback.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True
            )
            return

        match.is_locked = True
        await session.commit()

    await callback.answer(
        "🔒 بازی قفل شد.",
        show_alert=True
    )
@dp.callback_query(F.data.startswith("unlock_match:"))
async def unlock_match_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    match_id = int(callback.data.split(":")[1])

    async with Session() as session:

        result = await session.execute(
            select(Match).where(Match.id == match_id)
        )

        match = result.scalar_one_or_none()

        if not match:
            await callback.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True
            )
            return

        if match.is_finished:
            await callback.answer(
                "⚠️ این بازی تمام شده و قابل باز کردن نیست.",
                show_alert=True
            )
            return

        match.is_locked = False
        await session.commit()

    await callback.answer(
        "🔓 بازی باز شد.",
        show_alert=True
    )
    # =========================
# ADMIN - DELETE MATCH
# =========================

@dp.callback_query(F.data.startswith("delete_match:"))
async def delete_match_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    match_id = int(callback.data.split(":")[1])

    async with Session() as session:
        result = await session.execute(
            select(Match).where(Match.id == match_id)
        )
        match = result.scalar_one_or_none()

        if not match:
            await callback.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True
            )
            return

        result = await session.execute(
            select(Prediction).where(
                Prediction.match_id == match_id
            )
        )
        predictions = result.scalars().all()

        for prediction in predictions:
            await session.delete(prediction)

        await session.delete(match)
        await session.commit()

    await callback.message.edit_text(
        "✅ بازی با موفقیت حذف شد.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 مدیریت بازی‌ها",
                        callback_data="admin_matches"
                    )
                ]
            ]
        )
    )

    await callback.answer("🗑 بازی حذف شد.")


# =========================
# ADMIN - RESULT
# =========================

@dp.callback_query(F.data.startswith("result_match:"))
async def result_match_callback(callback):
    print("🔥 RESULT HANDLER:", callback.data)

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    match_id = int(callback.data.split(":")[1])

    async with Session() as session:

        result = await session.execute(
            select(Match)
        )

        all_matches = result.scalars().all()

        match = next(
            (m for m in all_matches if m.id == match_id),
            None
        )

        if not match:
            await callback.answer(
                f"❌ بازی پیدا نشد.\n"
                f"ID: {match_id}\n"
                f"IDs موجود: {[m.id for m in all_matches]}",
                show_alert=True
            )
            return

        home_team = match.home_team
        away_team = match.away_team

    pending_match[callback.from_user.id] = f"admin_result:{match_id}"

    await callback.message.answer(
        f"🏁 ثبت نتیجه\n\n"
        f"⚽ {home_team} 🆚 {away_team}\n\n"
        f"نتیجه نهایی رو بفرست:\n\n"
        f"مثال: 2-1"
    )

    await callback.answer()

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
@dp.callback_query(F.data == "prediction_menu")
async def prediction_menu_callback(callback):

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚽️ پیش‌بینی بازی‌ها",
                    callback_data="matches"
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
                    text="🏆 جدول امتیازات",
                    callback_data="leaderboard"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 لیگ این هفته",
                    callback_data="weekly"
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
                    text="🔙 بازگشت",
                    callback_data="home"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "🎯 پیش‌بینی نتایج\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=keyboard
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
    
async def save_weekly_winner():
    now = datetime.now(IRAN_TIMEZONE).replace(tzinfo=None)

    days_since_saturday = (now.weekday() + 2) % 7

    current_week_start = (
        now - timedelta(days=days_since_saturday)
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    previous_week_start = current_week_start - timedelta(days=7)
    previous_week_end = current_week_start

    async with Session() as session:

        existing = await session.execute(
            select(WeeklyWinner).where(
                WeeklyWinner.week_start == previous_week_start
            )
        )

        if existing.scalar_one_or_none():
            return

        result = await session.execute(
            select(
                User,
                func.sum(Prediction.points).label("weekly_points")
            )
            .join(
                Prediction,
                Prediction.user_id == User.id
            )
            .join(
                Match,
                Match.id == Prediction.match_id
            )
            .where(
                Match.start_time >= previous_week_start,
                Match.start_time < previous_week_end,
                Match.is_finished == True
            )
            .group_by(User.id)
            .order_by(
                func.sum(Prediction.points).desc(),
                User.id.asc()
            )
            .limit(1)
        )

        winner = result.first()

        if not winner:
            return

        user, weekly_points = winner

        session.add(
            WeeklyWinner(
                user_id=user.id,
                week_start=previous_week_start,
                points=weekly_points
            )
        )

        await session.commit()
@dp.callback_query(F.data == "weekly")
async def weekly_callback(callback):

    now = datetime.now(IRAN_TIMEZONE).replace(tzinfo=None)

    days_since_saturday = (now.weekday() + 2) % 7

    start_of_week = (
        now
        - timedelta(days=days_since_saturday)
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    end_of_week = start_of_week + timedelta(days=7)

    async with Session() as session:

        result = await session.execute(
            select(
                User,
                func.coalesce(
                    func.sum(Prediction.points),
                    0
                ).label("weekly_points")
            )
            .join(
                Prediction,
                Prediction.user_id == User.id
            )
            .join(
                Match,
                Match.id == Prediction.match_id
            )
            .where(
                Match.start_time >= start_of_week,
                Match.start_time < end_of_week,
                Match.is_finished == True
            )
            .group_by(User.id)
            .order_by(
                func.sum(Prediction.points).desc()
            )
            .limit(20)
        )

        rows = result.all()

    await callback.message.delete()

    if not rows:

        await callback.message.answer(
            "🏆 لیگ این هفته\n\n"
            "هنوز امتیازی برای این هفته ثبت نشده.",
            reply_markup=main_menu()
        )

        await callback.answer()
        return

    text = "🏆 لیگ این هفته\n\n"

    text += "👑 برندگان این هفته\n\n"

    winner_medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }

    for index, (user, weekly_points) in enumerate(
        rows[:3],
        start=1
    ):

        name = (
            user.first_name
            or user.username
            or "کاربر"
        )

        text += (
            f"{winner_medals[index]} {name} — "
            f"⭐ {weekly_points} امتیاز\n"
        )

    text += "\n━━━━━━━━━━━━━━\n\n"
    text += "📊 جدول لیگ\n\n"

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }

    for index, (user, weekly_points) in enumerate(
        rows,
        start=1
    ):

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
            f"   ⭐ {weekly_points} امتیاز\n\n"
        )

    await callback.message.answer(
        text,
        reply_markup=main_menu()
    )

    await callback.answer()
@dp.callback_query(F.data == "mine")
async def mine_callback(callback):

    user_id = callback.from_user.id

    async with Session() as session:

        user_result = await session.execute(
            select(User).where(
                User.telegram_id == user_id
            )
        )

        user = user_result.scalar_one_or_none()

        if not user:
            await callback.message.delete()

            await callback.message.answer(
                "❌ هنوز اطلاعاتی از شما ثبت نشده.",
                reply_markup=main_menu()
            )

            await callback.answer()
            return

        result = await session.execute(
            select(
                Prediction,
                Match
            )
            .join(
                Match,
                Match.id == Prediction.match_id
            )
            .where(
                Prediction.user_id == user.id
            )
            .order_by(
                Match.start_time.desc()
            )
        )

        rows = result.all()

    await callback.message.delete()

    if not rows:

        await callback.message.answer(
            "📊 پیش‌بینی‌های من\n\n"
            "هنوز هیچ پیش‌بینی‌ای ثبت نکردی.",
            reply_markup=main_menu()
        )

        await callback.answer()
        return

    text = "📊 پیش‌بینی‌های من\n\n"

    for prediction, match in rows:

        if match.is_finished:
            result_text = (
                f"{match.home_score} - "
                f"{match.away_score}"
            )

            status = (
                f"🏁 نتیجه: {result_text}\n"
                f"⭐ امتیاز شما: {prediction.points}"
            )

        elif match.is_locked:
            status = "🔒 بازی شروع شده — در انتظار نتیجه"

        else:
            status = "🟢 پیش‌بینی ثبت شده"

        text += (
            f"⚽ {match.home_team} 🆚 {match.away_team}\n"
            f"🎯 پیش‌بینی شما: "
            f"{prediction.home_pred} - "
            f"{prediction.away_pred}\n"
            f"{status}\n\n"
            f"━━━━━━━━━━━━━━\n\n"
        )

    await callback.message.answer(
        text,
        reply_markup=main_menu()
    )

    await callback.answer()

        


@dp.callback_query(F.data == "profile")
async def profile_callback(callback):

    async with Session() as session:

        # پیدا کردن کاربر
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

        # رتبه کاربر بر اساس امتیاز کل
        rank_result = await session.execute(
            select(func.count(User.id)).where(
                User.total_points > user.total_points
            )
        )

        rank = rank_result.scalar_one() + 1

        # تمام پیش‌بینی‌های کاربر + اطلاعات بازی
        prediction_result = await session.execute(
            select(
                Prediction,
                Match
            )
            .join(
                Match,
                Match.id == Prediction.match_id
            )
            .where(
                Prediction.user_id == user.id
            )
        )

        rows = prediction_result.all()

        # فقط بازی‌هایی که نتیجه‌شان ثبت شده
        finished_predictions = [
            (prediction, match)
            for prediction, match in rows
            if match.is_finished
        ]

        total_predictions = len(rows)
        finished_count = len(finished_predictions)

        # پیش‌بینی موفق = حداقل 3 امتیاز
        correct_predictions = sum(
            1
            for prediction, match in finished_predictions
            if prediction.points >= 3
        )

        # نتیجه کاملاً دقیق
        exact_predictions = sum(
            1
            for prediction, match in finished_predictions
            if prediction.points == 5
        )

        # درصد موفقیت
        success_rate = (
            round(
                (correct_predictions / finished_count) * 100
            )
            if finished_count > 0
            else 0
        )

        name = (
            user.first_name
            or user.username
            or "کاربر"
        )

        text = (
            "👤 پروفایل من\n\n"
            f"👋 {name}\n\n"
            "━━━━━━━━━━━━━━\n\n"
            f"🏆 رتبه کلی: {rank}\n"
            f"⭐ مجموع امتیاز: {user.total_points}\n"
            f"🔥 رکورد پیاپی: {user.current_streak}\n"
            f"🏅 بهترین رکورد پیاپی: {user.best_streak}\n\n"
            f"🎯 کل پیش‌بینی‌ها: {total_predictions}\n"
            f"🏁 بازی‌های تمام‌شده: {finished_count}\n"
            f"✅ پیش‌بینی‌های موفق: {correct_predictions}\n"
            f"🎯 نتایج دقیق: {exact_predictions}\n"
            f"📈 درصد موفقیت: {success_rate}%\n\n"
            "━━━━━━━━━━━━━━"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ]
        )

        await callback.message.edit_text(
            text,
            reply_markup=keyboard
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
@dp.callback_query(F.data == "gallery")
async def gallery_callback(callback):

    pending_match[callback.from_user.id] = "gallery_search"

    await callback.message.answer(
        "🎮 جستجوی مکس eFootball\n\n"
        "اسم بازیکن رو بفرست:\n\n"
        "مثال:\n"
        "Messi"
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

        await bot.send_message(
    chat_id=callback.from_user.id,
    text=(
        f"🎯 پیش‌بینی بازی:\n\n"
        f"⚽ {match.home_team} 🆚 {match.away_team}\n\n"
        f"نتیجه رو به این شکل بفرست:\n"
        f"مثلاً:\n"
        f"2-1"
    )
        )

    await callback.answer()
@dp.message(
    F.text,
    lambda message: pending_match.get(message.from_user.id) in (
        "admin_gallery_player",
        "gallery_search",
        "ef_add_section",
        "ef_edit_section",
        "ef_delete_section"
    )
)
async def gallery_player_name_handler(message: Message):

    user_id = message.from_user.id
    pending = pending_match.get(user_id)

    # =========================
    # افزودن بخش eFootball
    # =========================
    if is_admin(user_id) and pending == "ef_add_section":

        title = message.text.strip()

        if not title:
            await message.answer(
                "❌ اسم بخش نمی‌تونه خالی باشه."
            )
            return

        async with Session() as session:

            result = await session.execute(
                select(EfootballSection).order_by(
                    EfootballSection.sort_order.desc()
                )
            )

            last_section = result.scalars().first()

            next_order = (
                last_section.sort_order + 1
                if last_section
                else 1
            )

            section = EfootballSection(
                title=title,
                sort_order=next_order,
                is_active=True
            )

            session.add(section)
            await session.commit()

        pending_match.pop(user_id, None)

        await message.answer(
            f"✅ بخش «{title}» با موفقیت اضافه شد! 🎮🔥"
        )

        return

    # =========================
    # ویرایش بخش eFootball
    # =========================
    if is_admin(user_id) and pending == "ef_edit_section":

        new_title = message.text.strip()

        if not new_title:
            await message.answer(
                "❌ اسم بخش نمی‌تونه خالی باشه."
            )
            return

        section_id = pending_match.get(
            f"{user_id}_edit_section"
        )

        if not section_id:
            pending_match.pop(user_id, None)
            await message.answer(
                "❌ بخش پیدا نشد. دوباره امتحان کن."
            )
            return

        async with Session() as session:

            result = await session.execute(
                select(EfootballSection).where(
                    EfootballSection.id == section_id
                )
            )

            section = result.scalar_one_or_none()

            if not section:
                pending_match.pop(user_id, None)
                pending_match.pop(
                    f"{user_id}_edit_section",
                    None
                )

                await message.answer(
                    "❌ بخش پیدا نشد."
                )
                return

            old_title = section.title
            section.title = new_title

            await session.commit()

        pending_match.pop(user_id, None)
        pending_match.pop(
            f"{user_id}_edit_section",
            None
        )

        await message.answer(
            f"✅ بخش با موفقیت ویرایش شد! 🎮\n\n"
            f"قبل: {old_title}\n"
            f"بعد: {new_title}"
        )

        return

    # =========================
    # حذف بخش eFootball
    # =========================
    if is_admin(user_id) and pending == "ef_delete_section":

        section_id = pending_match.get(
            f"{user_id}_delete_section"
        )

        if not section_id:
            pending_match.pop(user_id, None)

            await message.answer(
                "❌ بخش پیدا نشد. دوباره امتحان کن."
            )
            return

        async with Session() as session:

            result = await session.execute(
                select(EfootballSection).where(
                    EfootballSection.id == section_id
                )
            )

            section = result.scalar_one_or_none()

            if not section:
                pending_match.pop(user_id, None)
                pending_match.pop(
                    f"{user_id}_delete_section",
                    None
                )

                await message.answer(
                    "❌ بخش پیدا نشد."
                )
                return

            title = section.title

            await session.delete(section)
            await session.commit()

        pending_match.pop(user_id, None)
        pending_match.pop(
            f"{user_id}_delete_section",
            None
        )

        await message.answer(
            f"🗑️ بخش «{title}» با موفقیت حذف شد."
        )

        return

    # =========================
    # افزودن مکس توسط ادمین
    # =========================
    if is_admin(user_id) and pending == "admin_gallery_player":

        player_name = message.text.strip()

        if not player_name:
            await message.answer(
                "❌ اسم بازیکن نمی‌تونه خالی باشه."
            )
            return

        pending_match[user_id] = (
            f"admin_gallery_player:{player_name}"
        )

        await message.answer(
            f"✅ بازیکن: {player_name}\n\n"
            "حالا عکس مکس این بازیکن رو بفرست 📷"
        )

        return

    # =========================
    # جستجوی مکس توسط کاربر
    # =========================
    if pending == "gallery_search":

        player_name = message.text.strip()

        if not player_name:
            await message.answer(
                "❌ اسم بازیکن رو وارد کن."
            )
            return

        async with Session() as session:

            result = await session.execute(
                select(GalleryImage).where(
                    GalleryImage.player_name.ilike(
                        f"%{player_name}%"
                    )
                ).order_by(
                    GalleryImage.id.desc()
                )
            )

            images = result.scalars().all()

        pending_match.pop(user_id, None)

        if not images:
            await message.answer(
                f"❌ مکی برای «{player_name}» پیدا نشد.",
                reply_markup=main_menu()
            )
            return

        await message.answer(
            f"🎮 مکس‌های {player_name}\n\n"
            f"📸 {len(images)} مکس پیدا شد:"
        )

        for image in images:

            await message.answer_photo(
                photo=image.file_id,
                caption=image.caption
            )

        return

                
@dp.message(F.photo)
@dp.message(F.photo)
async def gallery_photo_handler(message: Message):

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    pending = pending_match.get(user_id)

    if not isinstance(pending, str):
        return

    if not pending.startswith("admin_gallery_player:"):
        return

    player_name = pending.split(":", 1)[1].strip()

    if not player_name:
        return

    photo = message.photo[-1]

    caption = message.caption

    async with Session() as session:

        image = GalleryImage(
            file_id=photo.file_id,
            player_name=player_name,
            caption=caption
        )

        session.add(image)
        await session.commit()

    pending_match.pop(user_id, None)

    await message.answer(
        f"✅ مکس {player_name} با موفقیت ذخیره شد! 🎮🔥\n\n"
        "کاربران می‌تونن با جستجوی اسم بازیکن پیداش کنن."
    )
@dp.message(F.text)
async def weekly_prize_message_handler(message: Message):

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    pending = pending_prize.get(user_id)

    if not pending:
        return

    text = message.text.strip()

    if not text:
        return

    # مرحله اول: دریافت نام جایزه
    if pending.get("step") == "name":

        pending["prize_name"] = text
        pending["step"] = "content"

        await message.answer(
            "🔑 حالا کد یا متن جایزه رو وارد کن:\n\n"
            "مثلاً:\n"
            "ABC123XYZ\n\n"
            "اگر جایزه کد ندارد، می‌تونی توضیحات جایزه رو بنویسی."
        )

        return

    # مرحله دوم: دریافت کد یا متن جایزه
    if pending.get("step") == "content":

        prize_name = pending.get("prize_name")

        if not prize_name:
            pending_prize.pop(user_id, None)

            await message.answer(
                "❌ اطلاعات جایزه ناقص بود. دوباره تلاش کن."
            )

            return

        now = datetime.now(
            IRAN_TIMEZONE
        ).replace(tzinfo=None)

        days_since_saturday = (
            now.weekday() + 2
        ) % 7

        start_of_week = (
            now - timedelta(
                days=days_since_saturday
            )
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        async with Session() as session:

            prize = WeeklyPrize(
                week_start=start_of_week,
                prize_name=prize_name,
                prize_content=text
            )

            session.add(prize)

            await session.commit()

        pending_prize.pop(user_id, None)

        await message.answer(
            "✅ جایزه با موفقیت ثبت شد.\n\n"
            f"🎁 جایزه: {prize_name}\n"
            f"🔑 محتوا: {text}\n\n"
            "📅 مربوط به لیگ این هفته است."
        )
@dp.message(F.text.regexp(r"^\d+\s*-\s*\d+$"))
async def prediction_handler(message: Message):

    try:
        parts = message.text.split("-")
        home_score = int(parts[0].strip())
        away_score = int(parts[1].strip())
    except Exception:
        await message.answer(
            "❌ فرمت نتیجه درست نیست.\n"
            "مثال: 2-1"
        )
        return

    if home_score > 30 or away_score > 30:
        await message.answer(
            "❌ نتیجه واردشده معتبر نیست."
        )
        return

    user_id = message.from_user.id
    pending = pending_match.get(user_id)

    if not pending:
        await message.answer(
            "❌ اول یک بازی رو انتخاب کن."
        )
        return

    # =========================
    # ثبت نتیجه توسط ادمین
    # =========================

    if (
        is_admin(user_id)
        and isinstance(pending, str)
        and pending.startswith("admin_result:")
    ):

        match_id = int(
            pending.split(":")[1]
        )

        async with Session() as session:

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

            match.home_score = home_score
            match.away_score = away_score
            match.is_finished = True
            match.is_locked = True

            # =========================
            # محاسبه امتیاز پیش‌بینی‌ها
            # =========================

            result = await session.execute(
                select(Prediction).where(
                    Prediction.match_id == match.id
                )
            )

            predictions = result.scalars().all()

            game_winners = []

            for prediction in predictions:

                points = calculate_points(
                    prediction.home_pred,
                    prediction.away_pred,
                    home_score,
                    away_score
                )

                # 🎯 بازی ویژه = امتیاز ×۲
                if match.is_special:
                    points *= 2

                prediction.points = points

                user_result = await session.execute(
                    select(User).where(
                        User.id == prediction.user_id
                    )
                )

                user = user_result.scalar_one_or_none()

                if user:

                    user.total_points += points

                    # 🎖️ سطح
                    user.level = get_level(
                        user.total_points
                    )

                    # 🏅 مدال
                    user.medals = get_medal(
                        user.level
                    )

                    # 🔥 رکورد پیاپی
                    if points >= 3:

                        user.current_streak += 1

                        if (
                            user.current_streak
                            > user.best_streak
                        ):
                            user.best_streak = (
                                user.current_streak
                            )

                    else:

                        user.current_streak = 0

                    # ذخیره برای جدول برترین‌های همین بازی
                    game_winners.append(
                        (
                            user,
                            prediction,
                            points
                        )
                    )

            await session.commit()

            # =========================
            # 🏆 مرتب‌سازی برترین‌های بازی
            # =========================

            game_winners.sort(
                key=lambda x: x[2],
                reverse=True
            )

            # =========================
            # 🏆 جدول کلی امتیازات
            # =========================

            leaderboard_result = await session.execute(
                select(User)
                .order_by(
                    User.total_points.desc()
                )
                .limit(5)
            )

            leaderboard_users = (
                leaderboard_result.scalars().all()
            )

        # =========================
        # 📢 ساخت پیام نتیجه کانال
        # =========================

        special_text = (
            "\n🎯 این بازی ویژه بود و امتیازها ×۲ محاسبه شد."
            if match.is_special
            else ""
        )

        channel_text = (
            "🏁 <b>نتیجه نهایی</b>\n\n"
            f"⚽ <b>{match.home_team}</b> "
            f"{home_score} - {away_score} "
            f"<b>{match.away_team}</b>\n"
            f"{special_text}\n\n"
            "━━━━━━━━━━━━━━\n\n"
            "🏅 <b>برترین‌های این بازی</b>\n\n"
        )

        if game_winners:

            medals = ["🥇", "🥈", "🥉"]

            for index, (
                user,
                prediction,
                points
            ) in enumerate(
                game_winners[:3]
            ):

                name = (
                    f"@{user.username}"
                    if user.username
                    else user.first_name
                    or "کاربر"
                )

                medal = medals[index]

                channel_text += (
                    f"{medal} {name} — "
                    f"<b>{points} امتیاز</b>\n"
                    f"   🎯 پیش‌بینی: "
                    f"{prediction.home_pred}-"
                    f"{prediction.away_pred}\n"
                )

        else:

            channel_text += (
                "❌ کسی برای این بازی پیش‌بینی ثبت نکرده.\n"
            )

        channel_text += (
            "\n━━━━━━━━━━━━━━\n\n"
            "🏆 <b>جدول امتیازات</b>\n\n"
        )

        if leaderboard_users:

            rank_icons = [
                "🥇",
                "🥈",
                "🥉",
                "4️⃣",
                "5️⃣"
            ]

            for index, user in enumerate(
                leaderboard_users
            ):

                name = (
                    f"@{user.username}"
                    if user.username
                    else user.first_name
                    or "کاربر"
                )

                channel_text += (
                    f"{rank_icons[index]} "
                    f"{name} — "
                    f"<b>{user.total_points} امتیاز</b>\n"
                )

        else:

            channel_text += (
                "هنوز جدول امتیازات تشکیل نشده.\n"
            )

        channel_text += (
            "\n━━━━━━━━━━━━━━\n"
            "🎯 برای شرکت در پیش‌بینی‌های بعدی، "
            "بازی‌های کانال را دنبال کنید."
        )

        # =========================
        # 📢 ارسال نتیجه به کانال
        # =========================

        try:

            await bot.send_message(
                CHANNEL_USERNAME,
                channel_text,
                parse_mode="HTML"
            )

        except Exception as e:

            print(
                "❌ خطا در ارسال نتیجه به کانال:",
                e
            )

        # =========================
        # پایان ثبت نتیجه برای ادمین
        # =========================

        pending_match.pop(
            user_id,
            None
        )

        await message.answer(
            f"✅ نتیجه با موفقیت ثبت شد!\n\n"
            f"⚽ {match.home_team} "
            f"{home_score} - {away_score} "
            f"{match.away_team}\n\n"
            "📢 نتیجه و جدول امتیازات در کانال منتشر شد."
        )

        return

    # =========================
    # ثبت پیش‌بینی کاربر
    # =========================

    if not isinstance(pending, int):
        await message.answer(
            "❌ درخواست نامعتبر است."
        )
        return

    match_id = pending

    async with Session() as session:

        result = await session.execute(
            select(User).where(
                User.telegram_id == user_id
            )
        )

        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name
            )

            session.add(user)
            await session.flush()

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
            or datetime.now(
                IRAN_TIMEZONE
            ).replace(tzinfo=None) >= match.start_time
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

            prediction.home_pred = home_score
            prediction.away_pred = away_score

        else:

            prediction = Prediction(
                user_id=user.id,
                match_id=match.id,
                home_pred=home_score,
                away_pred=away_score,
                points=0,
                created_at=datetime.now(
                    IRAN_TIMEZONE
                ).replace(tzinfo=None)
            )

            session.add(prediction)

        await session.commit()

        pending_match.pop(user_id, None)

        await message.answer(
            f"✅ پیش‌بینی ثبت شد!\n\n"
            f"⚽ {match.home_team} "
            f"{home_score} - {away_score} "
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
        
        await save_weekly_winner()

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
        # =========================================================
# مدیریت کامل محتوای eFootball
# =========================================================

@dp.callback_query(F.data == "ef_manage_content")
async def ef_manage_content_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ افزودن محتوا",
                    callback_data="ef_content_add"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ ویرایش محتوا",
                    callback_data="ef_content_edit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ حذف محتوا",
                    callback_data="ef_content_delete"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 لیست محتوا",
                    callback_data="ef_content_list"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="admin_efootball"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "📄 مدیریت محتوای eFootball\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=keyboard
    )

    await callback.answer()


# =========================================================
# انتخاب بخش برای افزودن محتوا
# =========================================================

@dp.callback_query(F.data == "ef_content_add")
async def ef_content_add_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    async with Session() as session:

        result = await session.execute(
            select(EfootballSection)
            .where(EfootballSection.is_active == True)
            .order_by(EfootballSection.sort_order.asc())
        )

        sections = result.scalars().all()

    if not sections:
        await callback.answer(
            "📭 اول حداقل یک بخش بساز.",
            show_alert=True
        )
        return

    keyboard = []

    for section in sections:

        keyboard.append([
            InlineKeyboardButton(
                text=f"📂 {section.title}",
                callback_data=f"ef_content_add_section:{section.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data="ef_manage_content"
        )
    ])

    await callback.message.edit_text(
        "📂 محتوا رو در کدوم بخش می‌خوای اضافه کنی؟",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )

    await callback.answer()


# =========================================================
# انتخاب نوع محتوا
# =========================================================

@dp.callback_query(F.data.startswith("ef_content_add_section:"))
async def ef_content_add_section_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    section_id = int(callback.data.split(":")[1])

    pending_match[callback.from_user.id] = (
        f"ef_content_type:{section_id}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 متن",
                    callback_data=f"ef_content_type:text:{section_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼️ عکس",
                    callback_data=f"ef_content_type:photo:{section_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎬 ویدیو",
                    callback_data=f"ef_content_type:video:{section_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="ef_content_add"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "📄 نوع محتوا رو انتخاب کن:",
        reply_markup=keyboard
    )

    await callback.answer()


# =========================================================
# انتخاب نوع و شروع دریافت محتوا
# =========================================================

@dp.callback_query(F.data.startswith("ef_content_type:"))
async def ef_content_type_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    parts = callback.data.split(":")

    content_type = parts[1]
    section_id = int(parts[2])

    user_id = callback.from_user.id

    pending_match[user_id] = (
        f"ef_add_content:{content_type}:{section_id}"
    )

    if content_type == "text":

        await callback.message.answer(
            "📝 محتوای متنی رو بفرست.\n\n"
            "مثال:\n"
            "بهترین تنظیمات بازی..."
        )

    elif content_type == "photo":

        await callback.message.answer(
            "🖼️ عکس رو بفرست.\n\n"
            "می‌تونی کپشن هم براش بنویسی."
        )

    elif content_type == "video":

        await callback.message.answer(
            "🎬 ویدیو رو بفرست.\n\n"
            "می‌تونی کپشن هم براش بنویسی."
        )

    await callback.answer()


# =========================================================
# دریافت متن محتوا
# =========================================================

@dp.message(
    F.text,
    lambda message:
        isinstance(
            pending_match.get(message.from_user.id),
            str
        )
        and pending_match.get(
            message.from_user.id
        ).startswith("ef_add_content:text:")
)
async def ef_add_text_handler(message: Message):

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    pending = pending_match.get(user_id)

    section_id = int(
        pending.split(":")[2]
    )

    content_text = message.text.strip()

    if not content_text:
        await message.answer(
            "❌ متن نمی‌تونه خالی باشه."
        )
        return

    async with Session() as session:

        item = EfootballContent(
            section_id=section_id,
            content_type="text",
            title=None,
            content=content_text,
            file_id=None,
            sort_order=0,
            is_active=True
        )

        session.add(item)
        await session.commit()

    pending_match.pop(user_id, None)

    await message.answer(
        "✅ محتوای متنی با موفقیت اضافه شد! 🎮🔥"
    )


# =========================================================
# دریافت عکس محتوا
# =========================================================

@dp.message(
    F.photo,
    lambda message:
        isinstance(
            pending_match.get(message.from_user.id),
            str
        )
        and pending_match.get(
            message.from_user.id
        ).startswith("ef_add_content:photo:")
)
async def ef_add_photo_content_handler(message: Message):

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    pending = pending_match.get(user_id)

    section_id = int(
        pending.split(":")[2]
    )

    photo = message.photo[-1]

    async with Session() as session:

        item = EfootballContent(
            section_id=section_id,
            content_type="photo",
            title=None,
            content=message.caption,
            file_id=photo.file_id,
            sort_order=0,
            is_active=True
        )

        session.add(item)
        await session.commit()

    pending_match.pop(user_id, None)

    await message.answer(
        "✅ عکس با موفقیت به بخش eFootball اضافه شد! 🖼️🔥"
    )


# =========================================================
# دریافت ویدیو محتوا
# =========================================================

@dp.message(
    F.video,
    lambda message:
        isinstance(
            pending_match.get(message.from_user.id),
            str
        )
        and pending_match.get(
            message.from_user.id
        ).startswith("ef_add_content:video:")
)
async def ef_add_video_content_handler(message: Message):

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    pending = pending_match.get(user_id)

    section_id = int(
        pending.split(":")[2]
    )

    video = message.video

    async with Session() as session:

        item = EfootballContent(
            section_id=section_id,
            content_type="video",
            title=None,
            content=message.caption,
            file_id=video.file_id,
            sort_order=0,
            is_active=True
        )

        session.add(item)
        await session.commit()

    pending_match.pop(user_id, None)

    await message.answer(
        "✅ ویدیو با موفقیت به بخش eFootball اضافه شد! 🎬🔥"
    )


# =========================================================
# لیست محتوا
# =========================================================

@dp.callback_query(F.data == "ef_content_list")
async def ef_content_list_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    async with Session() as session:

        result = await session.execute(
            select(
                EfootballContent,
                EfootballSection
            )
            .join(
                EfootballSection,
                EfootballContent.section_id
                == EfootballSection.id
            )
            .order_by(
                EfootballSection.sort_order.asc(),
                EfootballContent.id.asc()
            )
        )

        rows = result.all()

    if not rows:

        await callback.message.edit_text(
            "📭 هنوز هیچ محتوایی اضافه نشده.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 بازگشت",
                            callback_data="ef_manage_content"
                        )
                    ]
                ]
            )
        )

        await callback.answer()
        return

    text = "📋 لیست محتوای eFootball\n\n"

    for i, (item, section) in enumerate(rows, 1):

        if item.content_type == "text":
            icon = "📝"
        elif item.content_type == "photo":
            icon = "🖼️"
        else:
            icon = "🎬"

        preview = item.content or ""

        if len(preview) > 80:
            preview = preview[:80] + "..."

        text += (
            f"{i}. {icon} {section.title}\n"
            f"🆔 محتوا: {item.id}\n"
            f"📄 نوع: {item.content_type}\n"
            f"📝 {preview}\n\n"
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="ef_manage_content"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )

    await callback.answer()


# =========================================================
# انتخاب محتوا برای حذف
# =========================================================

@dp.callback_query(F.data == "ef_content_delete")
async def ef_content_delete_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    async with Session() as session:

        result = await session.execute(
            select(
                EfootballContent,
                EfootballSection
            )
            .join(
                EfootballSection,
                EfootballContent.section_id
                == EfootballSection.id
            )
            .order_by(EfootballContent.id.asc())
        )

        rows = result.all()

    if not rows:

        await callback.answer(
            "📭 هنوز محتوایی وجود ندارد.",
            show_alert=True
        )
        return

    keyboard = []

    for item, section in rows:

        if item.content_type == "text":
            icon = "📝"
        elif item.content_type == "photo":
            icon = "🖼️"
        else:
            icon = "🎬"

        keyboard.append([
            InlineKeyboardButton(
                text=f"{icon} {section.title} | #{item.id}",
                callback_data=f"ef_content_delete_select:{item.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data="ef_manage_content"
        )
    ])

    await callback.message.edit_text(
        "🗑️ محتوایی که می‌خوای حذف کنی رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )

    await callback.answer()


# =========================================================
# حذف محتوا
# =========================================================

@dp.callback_query(F.data.startswith("ef_content_delete_select:"))
async def ef_content_delete_select_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    content_id = int(
        callback.data.split(":")[1]
    )

    async with Session() as session:

        result = await session.execute(
            select(EfootballContent).where(
                EfootballContent.id == content_id
            )
        )

        item = result.scalar_one_or_none()

        if not item:

            await callback.answer(
                "❌ محتوا پیدا نشد.",
                show_alert=True
            )
            return

        await session.delete(item)
        await session.commit()

    await callback.message.edit_text(
        "🗑️ محتوا با موفقیت حذف شد.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 مدیریت محتوا",
                        callback_data="ef_manage_content"
                    )
                ]
            ]
        )
    )

    await callback.answer()


# =========================================================
# انتخاب محتوا برای ویرایش
# =========================================================

@dp.callback_query(F.data == "ef_content_edit")
async def ef_content_edit_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    async with Session() as session:

        result = await session.execute(
            select(
                EfootballContent,
                EfootballSection
            )
            .join(
                EfootballSection,
                EfootballContent.section_id
                == EfootballSection.id
            )
            .order_by(EfootballContent.id.asc())
        )

        rows = result.all()

    if not rows:

        await callback.answer(
            "📭 هنوز محتوایی وجود ندارد.",
            show_alert=True
        )
        return

    keyboard = []

    for item, section in rows:

        if item.content_type == "text":
            icon = "📝"
        elif item.content_type == "photo":
            icon = "🖼️"
        else:
            icon = "🎬"

        keyboard.append([
            InlineKeyboardButton(
                text=f"{icon} {section.title} | #{item.id}",
                callback_data=f"ef_content_edit_select:{item.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data="ef_manage_content"
        )
    ])

    await callback.message.edit_text(
        "✏️ محتوایی که می‌خوای ویرایش کنی رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )

    await callback.answer()


# =========================================================
# انتخاب نوع ویرایش
# =========================================================

@dp.callback_query(F.data.startswith("ef_content_edit_select:"))
async def ef_content_edit_select_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    content_id = int(
        callback.data.split(":")[1]
    )

    async with Session() as session:

        result = await session.execute(
            select(EfootballContent).where(
                EfootballContent.id == content_id
            )
        )

        item = result.scalar_one_or_none()

    if not item:

        await callback.answer(
            "❌ محتوا پیدا نشد.",
            show_alert=True
        )
        return

    user_id = callback.from_user.id

    pending_match[user_id] = (
        f"ef_edit_content:{content_id}"
    )

    if item.content_type == "text":

        await callback.message.answer(
            "✏️ متن جدید این محتوا رو بفرست:"
        )

    else:

        await callback.message.answer(
            "✏️ برای این محتوا یک فایل جدید بفرست:\n\n"
            "🖼️ برای عکس: عکس بفرست\n"
            "🎬 برای ویدیو: ویدیو بفرست\n\n"
            "اگر کپشن هم می‌خوای تغییر کنه، همراه فایل کپشن بفرست."
        )

    await callback.answer()


# =========================================================
# ویرایش متن
# =========================================================

@dp.message(
    F.text,
    lambda message:
        isinstance(
            pending_match.get(message.from_user.id),
            str
        )
        and pending_match.get(
            message.from_user.id
        ).startswith("ef_edit_content:")
)
async def ef_edit_content_text_handler(message: Message):

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    pending = pending_match.get(user_id)

    content_id = int(
        pending.split(":")[1]
    )

    async with Session() as session:

        result = await session.execute(
            select(EfootballContent).where(
                EfootballContent.id == content_id
            )
        )

        item = result.scalar_one_or_none()

        if not item:
            pending_match.pop(user_id, None)

            await message.answer(
                "❌ محتوا پیدا نشد."
            )
            return

        if item.content_type != "text":
            await message.answer(
                "❌ این محتوا متنی نیست. فایل مناسبش رو بفرست."
            )
            return

        item.content = message.text.strip()

        await session.commit()

    pending_match.pop(user_id, None)

    await message.answer(
        "✅ متن با موفقیت ویرایش شد! ✏️🔥"
    )


# =========================================================
# ویرایش عکس
# =========================================================

@dp.message(
    F.photo,
    lambda message:
        isinstance(
            pending_match.get(message.from_user.id),
            str
        )
        and pending_match.get(
            message.from_user.id
        ).startswith("ef_edit_content:")
)
async def ef_edit_content_photo_handler(message: Message):

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    pending = pending_match.get(user_id)

    content_id = int(
        pending.split(":")[1]
    )

    photo = message.photo[-1]

    async with Session() as session:

        result = await session.execute(
            select(EfootballContent).where(
                EfootballContent.id == content_id
            )
        )

        item = result.scalar_one_or_none()

        if not item:
            pending_match.pop(user_id, None)

            await message.answer(
                "❌ محتوا پیدا نشد."
            )
            return

        if item.content_type != "photo":
            await message.answer(
                "❌ این محتوا عکس نیست."
            )
            return

        item.file_id = photo.file_id

        if message.caption is not None:
            item.content = message.caption

        await session.commit()

    pending_match.pop(user_id, None)

    await message.answer(
        "✅ عکس و کپشن با موفقیت ویرایش شد! 🖼️🔥"
    )


# =========================================================
# ویرایش ویدیو
# =========================================================

@dp.message(
    F.video,
    lambda message:
        isinstance(
            pending_match.get(message.from_user.id),
            str
        )
        and pending_match.get(
            message.from_user.id
        ).startswith("ef_edit_content:")
)
async def ef_edit_content_video_handler(message: Message):

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    pending = pending_match.get(user_id)

    content_id = int(
        pending.split(":")[1]
    )

    video = message.video

    async with Session() as session:

        result = await session.execute(
            select(EfootballContent).where(
                EfootballContent.id == content_id
            )
        )

        item = result.scalar_one_or_none()

        if not item:
            pending_match.pop(user_id, None)

            await message.answer(
                "❌ محتوا پیدا نشد."
            )
            return

        if item.content_type != "video":
            await message.answer(
                "❌ این محتوا ویدیو نیست."
            )
            return

        item.file_id = video.file_id

        if message.caption is not None:
            item.content = message.caption

        await session.commit()

    pending_match.pop(user_id, None)

    await message.answer(
        "✅ ویدیو و کپشن با موفقیت ویرایش شد! 🎬🔥"
    )
    async def load_admins():
        ADMIN_IDS.clear()

    async with Session() as session:
        result = await session.execute(
            select(Admin.telegram_id)
        )

        admin_ids = result.scalars().all()

    ADMIN_IDS.update(admin_ids)
    ADMIN_IDS.update(SUPER_ADMIN_IDS)
@dp.callback_query(F.data == "admin_weekly_prize")
async def admin_weekly_prize_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎁 افزودن جایزه",
                    callback_data="weekly_prize_set"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 جوایز این هفته",
                    callback_data="weekly_prizes_list"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏆 انتخاب برنده هفته",
                    callback_data="weekly_prize_winner"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📩 ارسال خصوصی جایزه",
                    callback_data="weekly_prize_send"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 اعلام برنده‌ها",
                    callback_data="weekly_prize_announce"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📜 تاریخچه",
                    callback_data="weekly_prize_history"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="admin_panel"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "🎁 مدیریت جایزه هفتگی\n\n"
        "می‌تونی برای هر هفته صفر، یک یا چند جایزه ثبت کنی.",
        reply_markup=keyboard
    )

    await callback.answer()

@dp.callback_query(F.data == "weekly_prize_set")
async def weekly_prize_set_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    pending_prize[callback.from_user.id] = {
        "step": "name"
    }

    await callback.message.answer(
        "🎁 افزودن جایزه\n\n"
        "اسم جایزه رو وارد کن:\n\n"
        "مثلاً:\n"
        "🎫 اشتراک یک ماهه فیلترشکن"
    )

    await callback.answer()
@dp.callback_query(F.data == "weekly_prizes_list")
async def weekly_prizes_list_callback(callback):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی نداری.",
            show_alert=True
        )
        return

    now = datetime.now(
        IRAN_TIMEZONE
    ).replace(tzinfo=None)

    days_since_saturday = (
        now.weekday() + 2
    ) % 7

    start_of_week = (
        now - timedelta(
            days=days_since_saturday
        )
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    async with Session() as session:

        result = await session.execute(
            select(WeeklyPrize)
            .where(
                WeeklyPrize.week_start == start_of_week
            )
            .order_by(
                WeeklyPrize.id.asc()
            )
        )

        prizes = result.scalars().all()

    if not prizes:

        text = (
            "📋 جوایز این هفته\n\n"
            "❌ هنوز هیچ جایزه‌ای ثبت نشده."
        )

    else:

        text = (
            "📋 جوایز این هفته\n\n"
            f"🎁 تعداد جوایز: {len(prizes)}\n\n"
        )

        for index, prize in enumerate(
            prizes,
            start=1
        ):

            status = (
                "📩 ارسال شده"
                if prize.is_sent
                else "⏳ ارسال نشده"
            )

            text += (
                f"{index}. 🎁 {prize.prize_name}\n"
                f"   {status}\n\n"
            )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="admin_weekly_prize"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )

    await callback.answer()
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
