import logging
import nsepython as nse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from nse_utils import (
    INDICES_LIST,
    INDICES,
    get_expiries,
    get_option_chain,
    format_option_chain_message,
    format_most_active,
    format_preopen_movers,
    format_fiidii,
    format_block_deals,
    format_bulk_deals,
    format_indiavix,
    format_top_gainers,
    format_top_losers,

)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_TYPE = 1
CHOOSING_INDEX = 2
CHOOSING_STOCK = 3
CHOOSING_EXPIRY = 4
SHOW_CHAIN = 5

# Store user states
user_states = {}


# ========= Helpers to format nsepython outputs ========= #



# ========= Telegram handlers ========= #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the bot and show main menu."""
    user_id = update.effective_user.id
    user_states[user_id] = {}  # ← This clears user state (restart effect)

    keyboard = [
        [InlineKeyboardButton("📊 Option Chain", callback_data="option_chain")],
        [InlineKeyboardButton("📈 Market Data", callback_data="market_menu")],
        [InlineKeyboardButton("🔄 Restart", callback_data="restart")],  # ← New!
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Welcome to NSE Option Chain Bot!\n\n"
        "Choose an option below:",
        reply_markup=reply_markup,
    )

    return CHOOSING_TYPE

async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Restart button - clears state and shows main menu."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer("🔄 Restarting...")

    # Clear user state completely
    user_states[user_id] = {}

    # Show fresh main menu
    keyboard = [
        [InlineKeyboardButton("📊 Option Chain", callback_data="option_chain")],
        [InlineKeyboardButton("📈 Market Data", callback_data="market_menu")],
        [InlineKeyboardButton("🔄 Restart", callback_data="restart")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "✅ Bot restarted! Choose an option:",
        reply_markup=reply_markup,
    )

    return CHOOSING_TYPE


# ----- Option Chain existing flow (unchanged except start menu) ----- #

async def option_chain_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📈 Index Options", callback_data="index_options")],
        [InlineKeyboardButton("📉 Stock Options", callback_data="stock_options")],
        [InlineKeyboardButton("🧮 Market Data", callback_data="market_menu")],
        [InlineKeyboardButton("🏠 Home", callback_data="back_to_start")],
        [InlineKeyboardButton("🔄 Restart", callback_data="restart")],

    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Choose option type:",
        reply_markup=reply_markup,
    )

    return CHOOSING_TYPE


async def index_options_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    user_states[user_id]["option_type"] = "indices"

    keyboard = []
    for idx in INDICES_LIST:
        keyboard.append(
            [InlineKeyboardButton(INDICES[idx], callback_data=f"idx_{idx}")]
        )

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="option_chain")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Select an Index:",
        reply_markup=reply_markup,
    )

    return CHOOSING_INDEX


async def stock_options_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    user_states[user_id]["option_type"] = "equities"

    await query.edit_message_text(
        "📝 Enter stock symbol (e.g., RELIANCE, TCS, INFY):\n\n"
        "(Type /cancel to go back)"
    )

    return CHOOSING_STOCK


async def handle_stock_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    symbol = update.message.text.strip().upper()

    if symbol == "/CANCEL":
        # fake callback to reuse option_chain_menu
        class DummyQuery:
            data = "option_chain"

            async def answer(self): ...
            async def edit_message_text(self, *a, **k): ...

        update.callback_query = DummyQuery()
        return await option_chain_menu(update, context)

    if len(symbol) < 2 or len(symbol) > 10:
        await update.message.reply_text(
            "❌ Invalid symbol. Please enter a valid stock symbol (e.g., RELIANCE)"
        )
        return CHOOSING_STOCK

    user_states[user_id]["symbol"] = symbol

    await update.message.reply_text("⏳ Fetching expiry dates...")

    expiries = get_expiries(symbol, "equities")

    if not expiries:
        await update.message.reply_text(
            f"❌ Could not fetch expiries for {symbol}. "
            "Please check the symbol and try again."
        )
        return CHOOSING_STOCK

    await show_expiry_menu(update, context, symbol, expiries)

    return CHOOSING_EXPIRY


async def handle_index_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    symbol = query.data.split("_")[1]
    user_states[user_id]["symbol"] = symbol

    await query.edit_message_text("⏳ Fetching expiry dates...")

    expiries = get_expiries(symbol, "indices")

    if not expiries:
        await query.edit_message_text(
            f"❌ Could not fetch expiries for {symbol}. Please try again."
        )
        return CHOOSING_INDEX

    await show_expiry_menu(update, context, symbol, expiries)

    return CHOOSING_EXPIRY


async def show_expiry_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    symbol: str,
    expiries: list,
) -> None:
    expiries_to_show = expiries[:5]

    keyboard = []
    for expiry in expiries_to_show:
        keyboard.append(
            [InlineKeyboardButton(expiry, callback_data=f"exp_{expiry}")]
        )

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="option_chain")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            f"Select Expiry for {symbol}:",
            reply_markup=reply_markup,
        )
    else:
        await update.message.reply_text(
            f"Select Expiry for {symbol}:",
            reply_markup=reply_markup,
        )


async def handle_expiry_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    expiry = query.data.split("exp_")[1]
    symbol = user_states[user_id]["symbol"]
    option_type = user_states[user_id]["option_type"]

    await query.edit_message_text(
        "⏳ Fetching option chain data...\n"
        "(This may take a few seconds)"
    )

    try:
        option_chain_data = get_option_chain(symbol, expiry, option_type)

        message = format_option_chain_message(
            option_chain_data,
            symbol,
            expiry,
            option_type,
        )

        keyboard = [
            [InlineKeyboardButton("📊 New Query", callback_data="option_chain")],
            [InlineKeyboardButton("📈 Market Data", callback_data="market_menu")],
            [InlineKeyboardButton("🏠 Home", callback_data="back_to_start")],
            [InlineKeyboardButton("🔄 Restart", callback_data="restart")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error fetching option chain: {str(e)}")
        await query.edit_message_text(
            f"❌ Error fetching option chain: {str(e)}\n\nPlease try again."
        )

    return SHOW_CHAIN


# ----- Market Data menu and handlers ----- #

async def market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show market data menu."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔥 Most Active", callback_data="most_active")],
        [InlineKeyboardButton("🕒 Preopen Movers", callback_data="preopen_movers")],
        [InlineKeyboardButton("🏦 FII / DII", callback_data="fiidii")],
        [InlineKeyboardButton("📦 Block Deals", callback_data="block_deals")],
        [InlineKeyboardButton("📊 Bulk Deals", callback_data="bulk_deals")],
        [InlineKeyboardButton("⚡ India VIX", callback_data="indiavix")],
        [InlineKeyboardButton("📈 Top Gainers", callback_data="top_gainers")],
        [InlineKeyboardButton("📉 Top Losers", callback_data="top_losers")],
        [InlineKeyboardButton("🏠 Home", callback_data="back_to_start")],
        [InlineKeyboardButton("🔄 Restart", callback_data="restart")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Select Market Data:",
        reply_markup=reply_markup,
    )

    return CHOOSING_TYPE


async def handle_market_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle all market data callbacks."""
    query = update.callback_query
    data = query.data
    await query.answer()

    await query.edit_message_text("⏳ Fetching data...")

    try:
        if data == "most_active":
            text = format_most_active()
        elif data == "preopen_movers":
            text = format_preopen_movers()
        elif data == "fiidii":
            text = format_fiidii()
        elif data == "block_deals":
            text = format_block_deals()
        elif data == "bulk_deals":
            text = format_bulk_deals()
        elif data == "indiavix":
            text = format_indiavix()
        elif data == "top_gainers":
            text = format_top_gainers()
        elif data == "top_losers":
            text = format_top_losers()
        else:
            text = "❌ Unknown selection."

        keyboard = [
            [InlineKeyboardButton("🔁 Market Menu", callback_data="market_menu")],
            [InlineKeyboardButton("📊 Option Chain", callback_data="option_chain")],
            [InlineKeyboardButton("🏠 Home", callback_data="back_to_start")],
            [InlineKeyboardButton("🔄 Restart", callback_data="restart")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error in market data callback: {str(e)}")
        await query.edit_message_text(
            f"❌ Error fetching data: {str(e)}\n\nPlease try again."
        )

    return CHOOSING_TYPE


# ----- Common navigation ----- #

async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Go back to main menu."""
    if update.callback_query:
        await update.callback_query.answer()
        # simulate /start
        msg = update.callback_query.message
        return await start(msg, context)  # type: ignore[arg-type]
    else:
        return await start(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("👋 Cancelled. Type /start to begin again.")
    return ConversationHandler.END


def main() -> None:
    TOKEN = "8230069689:AAG-80w1aVXL9uihe8ZPTaZTNNRnZzHvFPc"
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(restart_bot, pattern="^restart$"))
    application.add_handler(CallbackQueryHandler(option_chain_menu, pattern="^option_chain$"))
    application.add_handler(CallbackQueryHandler(index_options_menu, pattern="^index_options$"))
    application.add_handler(CallbackQueryHandler(stock_options_menu, pattern="^stock_options$"))
    application.add_handler(CallbackQueryHandler(handle_index_selection, pattern="^idx_"))
    application.add_handler(CallbackQueryHandler(handle_expiry_selection, pattern="^exp_"))
    application.add_handler(CallbackQueryHandler(back_to_start, pattern="^back_to_start$"))

    application.add_handler(CallbackQueryHandler(market_menu, pattern="^market_menu$"))
    application.add_handler(CallbackQueryHandler(handle_market_callback,
                                                 pattern="^(most_active|preopen_movers|fiidii|block_deals|bulk_deals|indiavix|top_gainers|top_losers)$"))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock_symbol)
    )

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
