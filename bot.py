import asyncio
import logging
import json
import aiohttp
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import KeyboardButton, ReplyKeyboardRemove, WebAppInfo
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from google import genai

# 🛑 ՏՈԿԵՆՆԵՐ
API_TOKEN = '8976796625:AAFLFj7fWeewyFYITOfct7Z5iBLR2isi7Sk'
GEMINI_API_KEY = 'AIzaSyDJnVZtKtpNSyL1JdmdWtFCxz_-ZI8okR4'
WEB_APP_URL = "https://svardanyann.github.io/appa-webapp/"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

ai_client = genai.Client(api_key=GEMINI_API_KEY)

class BotStates(StatesGroup):
    waiting_for_location = State()
    waiting_for_failure_action = State()

# --- ԿՈՃԱԿՆԵՐ ---
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🚨 Վթար"), KeyboardButton(text="📝 ԱՊՊԱ"), 
                KeyboardButton(text="🚘 ԿԱՍԿՈ"), KeyboardButton(text="👤 Իմ էջը"), 
                KeyboardButton(text="🏠 Գլխավոր մենյու"))
    builder.adjust(1, 2, 2)
    return builder.as_markup(resize_keyboard=True)

def get_failure_menu():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔄 Փորձել նորից (Ուղարկել նոր նկար)"), 
                KeyboardButton(text="🏠 Գլխավոր մենյու"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# --- GEMINI ---
async def analyze_with_gemini(file_path: str):
    try:
        url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                img_bytes = await resp.read()
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[genai.types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg'),
                              "Գնահատիր մեքենայի վնասը AMD-ով։ Պատասխանիր հայերեն, կարճ և կոնկրետ:"]
                )
                return response.text
    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return None

# --- HANDLERS ---
@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Բարև ձեզ! Ընտրեք ծառայությունը:", reply_markup=get_main_menu())

@router.message(F.text == "🚨 Վթար")
async def start_crash(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.waiting_for_location)
    await message.answer("Համոզվեք, որ GPS-ը միացված է և ուղարկեք լոկացիան:", 
                         reply_markup=ReplyKeyboardBuilder().add(KeyboardButton(text="📍 Կիսվել տեղադրությամբ", request_location=True)).as_markup(resize_keyboard=True))

@router.message(BotStates.waiting_for_location, F.location)
async def handle_location(message: types.Message, state: FSMContext):
    await message.answer("Տեղադրությունը ստացվեց: Բացեք մինի-հավելվածը լուսանկարների համար:", 
                         reply_markup=ReplyKeyboardBuilder().add(KeyboardButton(text="📱 Կցել նկարներ", web_app=WebAppInfo(url=WEB_APP_URL))).as_markup(resize_keyboard=True))
    await state.clear()

@router.message(F.photo)
async def handle_photo(message: types.Message, state: FSMContext):
    status_msg = await message.answer("🤖 ԱԲ-ն ուսումնասիրում է նկարը...", reply_markup=ReplyKeyboardRemove())
    file = await bot.get_file(message.photo[-1].file_id)
    ai_result = await analyze_with_gemini(file.file_path)
    
    await status_msg.delete()
    if ai_result:
        await message.answer(f"📊 **Արդյունք:**\n\n{ai_result}", reply_markup=get_main_menu())
    else:
        await state.set_state(BotStates.waiting_for_failure_action)
        await message.answer("⚠️ Չհաջողվեց գնահատել:", reply_markup=get_failure_menu())

@router.message(BotStates.waiting_for_failure_action, F.text == "🔄 Փորձել նորից (Ուղարկել նոր նկար)")
async def retry(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Ուղարկեք նոր նկար:", reply_markup=ReplyKeyboardRemove())

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    if message.text == "🏠 Գլխավոր մենյու":
        await state.clear()
        await message.answer("Վերադարձաք գլխավոր մենյու:", reply_markup=get_main_menu())
    else:
        await message.answer("Խնդրում եմ օգտվել ներքևի կոճակներից:", reply_markup=get_main_menu())

async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())