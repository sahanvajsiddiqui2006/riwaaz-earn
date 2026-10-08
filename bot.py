import os
import asyncio
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, CommandObject
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, Boolean, Numeric, DateTime, ForeignKey, select
from datetime import datetime

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./riwaaz_earn.db")

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128))
    referrer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="user", uselist=False)

class Wallet(Base):
    __tablename__ = "wallets"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True)
    available_balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00)
    pending_balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00)
    total_earned: Mapped[float] = mapped_column(Numeric(12, 2), default=0.00)
    user: Mapped["User"] = relationship("User", back_populates="wallet")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

def get_main_menu() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="💰 Earn"), KeyboardButton(text="🎯 Tasks")],
        [KeyboardButton(text="🎬 Videos"), KeyboardButton(text="👥 Refer & Earn")],
        [KeyboardButton(text="💳 Wallet"), KeyboardButton(text="💸 Withdraw")],
        [KeyboardButton(text="📊 Statistics"), KeyboardButton(text="🏆 Leaderboard")],
        [KeyboardButton(text="❓ Help")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()

        if not user:
            new_user = User(id=user_id, username=username, first_name=first_name)
            session.add(new_user)
            await session.flush()

            new_wallet = Wallet(user_id=user_id)
            session.add(new_wallet)
            await session.commit()
            
            welcome_text = f"👋 *Riwaaz Earn* में आपका स्वागत है, {first_name}!\n\nनीचे दिए गए मेनू से विकल्प चुनें:"
        else:
            welcome_text = f"वापसी पर स्वागत है, *{first_name}*!"

    await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")

@dp.message(F.text == "💳 Wallet")
async def handle_wallet(message: Message):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Wallet).where(Wallet.user_id == message.from_user.id))
        wallet = res.scalar_one_or_none()

        if not wallet:
            await message.answer("कृपया पहले /start दबाकर रजिस्टर करें।")
            return

        text = (
            "💳 *आपका Riwaaz Wallet*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Available Balance:* ₹{wallet.available_balance:.2f}\n"
            f"⏳ *Pending Balance:* ₹{wallet.pending_balance:.2f}\n"
            f"📈 *Total Earned:* ₹{wallet.total_earned:.2f}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "❓ Help")
async def handle_help(message: Message):
    text = (
        "📖 *Riwaaz Earn गाइड*\n\n"
        "• *Tasks:* प्रायोजित टास्क पूरे करें और रिवॉर्ड पाएँ।\n"
        "• *Videos:* पार्टनर वीडियो देखें।\n"
        "• *Refer & Earn:* दोस्तों को जोड़ें और कमीशन कमाएँ।\n"
        "• *Withdraw:* तय बैलेंस होने पर पैसे निकालें।"
    )
    await message.answer(text, parse_mode="Markdown")

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Riwaaz Earn Bot Started on Render!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
