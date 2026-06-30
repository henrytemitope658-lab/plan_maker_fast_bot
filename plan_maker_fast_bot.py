"""
📅 Plan Maker Fast Bot - Professional Calendar & Planner Generator
Create monthly, yearly, and custom calendars with events and reminders
"""

import os
import io
import re
import logging
import calendar
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ Pillow not installed. Calendar images will be basic.")

# ==================== LOGGING ====================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

# Try multiple possible token variable names
BOT_TOKEN = (
    os.environ.get("TELEGRAM_TOKEN") or
    os.environ.get("TELEGRAM_BOT_TOKEN") or
    os.environ.get("BOT_TOKEN")
)

# If token is not set, try reading from .env file
if not BOT_TOKEN:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        BOT_TOKEN = (
            os.environ.get("TELEGRAM_TOKEN") or
            os.environ.get("TELEGRAM_BOT_TOKEN") or
            os.environ.get("BOT_TOKEN")
        )
    except:
        pass

# If still no token, show error
if not BOT_TOKEN:
    logger.error("=" * 60)
    logger.error("❌ ERROR: No Telegram Bot Token found!")
    logger.error("=" * 60)
    raise ValueError("❌ No Telegram Bot Token found in environment variables!")

BOT_NAME = "Plan Maker Fast Bot"
BOT_USERNAME = "plan_maker_fast_bot"
BOT_VERSION = "1.0.0"

# ==================== CONSTANTS ====================

# Month names
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# Short month names
MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Day names
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Day names short
DAYS_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ==================== USER DATA ====================

user_data: Dict[int, Dict] = {}

def get_user_data(user_id: int) -> Dict:
    """Get or create user data"""
    if user_id not in user_data:
        user_data[user_id] = {
            "events": {},
            "reminders": {},
            "total_calendars": 0,
            "current_year": datetime.now().year,
            "current_month": datetime.now().month,
            "last_calendar": None,
            "custom_events": []
        }
    return user_data[user_id]

# ==================== KEYBOARDS ====================

def get_main_keyboard():
    """Create main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("📅 Monthly Calendar", callback_data="monthly")],
        [InlineKeyboardButton("📆 Yearly Calendar", callback_data="yearly")],
        [InlineKeyboardButton("📋 Custom Calendar", callback_data="custom")],
        [InlineKeyboardButton("➕ Add Event", callback_data="add_event")],
        [InlineKeyboardButton("📌 My Events", callback_data="my_events")],
        [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_month_navigation_keyboard(year: int, month: int):
    """Create month navigation keyboard"""
    keyboard = [
        [InlineKeyboardButton("◀️ Prev", callback_data=f"month_{year}_{month-1}"),
         InlineKeyboardButton(f"{MONTHS[month-1]} {year}", callback_data="noop"),
         InlineKeyboardButton("Next ▶️", callback_data=f"month_{year}_{month+1}")],
        [InlineKeyboardButton("📆 Year View", callback_data=f"year_{year}")],
        [InlineKeyboardButton("➕ Add Event", callback_data=f"add_event_{year}_{month}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_year_navigation_keyboard(year: int):
    """Create year navigation keyboard"""
    keyboard = [
        [InlineKeyboardButton("◀️ Prev Year", callback_data=f"year_{year-1}"),
         InlineKeyboardButton(f"{year}", callback_data="noop"),
         InlineKeyboardButton("Next Year ▶️", callback_data=f"year_{year+1}")],
        [InlineKeyboardButton("📅 Month View", callback_data=f"month_{year}_{datetime.now().month}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_event_type_keyboard():
    """Create event type selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("📅 Personal", callback_data="event_personal")],
        [InlineKeyboardButton("💼 Work", callback_data="event_work")],
        [InlineKeyboardButton("🎉 Celebration", callback_data="event_celebration")],
        [InlineKeyboardButton("📝 Reminder", callback_data="event_reminder")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== CALENDAR FUNCTIONS ====================

def generate_month_calendar(year: int, month: int, events: Dict = None) -> Tuple[str, bytes]:
    """
    Generate a month calendar with events
    Returns: (text representation, image bytes)
    """
    if events is None:
        events = {}
    
    # Create calendar text
    cal_text = f"📅 **{MONTHS[month-1]} {year}**\n\n"
    cal_text += "Mon Tue Wed Thu Fri Sat Sun\n"
    
    # Get calendar data
    cal = calendar.monthcalendar(year, month)
    
    for week in cal:
        week_str = ""
        for day in week:
            if day == 0:
                week_str += "    "
            else:
                date_key = f"{year}-{month:02d}-{day:02d}"
                if date_key in events:
                    week_str += f" **{day:2d}**"
                else:
                    week_str += f"  {day:2d} "
        cal_text += week_str + "\n"
    
    # Add events
    if events:
        cal_text += "\n📌 **Events:**\n"
        for date_key, event_list in events.items():
            if date_key.startswith(f"{year}-{month:02d}"):
                day = int(date_key.split("-")[2])
                for event in event_list:
                    cal_text += f"• {day:02d}: {event}\n"
    
    # Generate image
    img_data = None
    if PIL_AVAILABLE:
        img_data = create_calendar_image(year, month, events)
    
    return cal_text, img_data

def generate_year_calendar(year: int) -> Tuple[str, bytes]:
    """
    Generate a year calendar
    Returns: (text representation, image bytes)
    """
    cal_text = f"📆 **Year {year}**\n\n"
    
    # Create 3x4 grid of months
    for row in range(4):
        for col in range(3):
            month = row * 3 + col + 1
            if month <= 12:
                cal_text += f"**{MONTHS_SHORT[month-1]}**".ljust(8)
        cal_text += "\n"
        
        # Days header
        for col in range(3):
            month = row * 3 + col + 1
            if month <= 12:
                cal_text += "Mo Tu We Th Fr Sa Su".ljust(22)
        cal_text += "\n"
        
        # Calendar grid
        for week in range(6):
            for col in range(3):
                month = row * 3 + col + 1
                if month <= 12:
                    week_data = calendar.monthcalendar(year, month)
                    if week < len(week_data):
                        week_str = ""
                        for day in week_data[week]:
                            if day == 0:
                                week_str += "   "
                            else:
                                week_str += f"{day:2d} "
                        cal_text += week_str.ljust(22)
                    else:
                        cal_text += " " * 22
            cal_text += "\n"
        cal_text += "\n"
    
    # Generate image
    img_data = None
    if PIL_AVAILABLE:
        img_data = create_year_calendar_image(year)
    
    return cal_text, img_data

def create_calendar_image(year: int, month: int, events: Dict = None) -> Optional[bytes]:
    """Create a visual calendar image using Pillow"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create image
        width, height = 800, 600
        img = Image.new('RGB', (width, height), color='#FFFFFF')
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            day_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            date_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            day_font = ImageFont.load_default()
            date_font = ImageFont.load_default()
        
        # Draw title
        draw.text((width//2 - 100, 20), f"{MONTHS[month-1]} {year}", 
                 fill=(50, 50, 150), font=title_font)
        
        # Draw day headers
        start_x = 60
        start_y = 80
        cell_width = 90
        cell_height = 60
        
        for i, day in enumerate(DAYS_SHORT):
            x = start_x + i * cell_width
            draw.text((x + 20, start_y), day, fill=(100, 100, 100), font=day_font)
        
        # Draw calendar grid
        cal = calendar.monthcalendar(year, month)
        y_offset = start_y + 30
        
        for week in cal:
            x_offset = start_x
            for day in week:
                if day != 0:
                    date_key = f"{year}-{month:02d}-{day:02d}"
                    # Draw date
                    draw.text((x_offset + 10, y_offset + 10), str(day), 
                             fill=(50, 50, 50), font=date_font)
                    
                    # Check for events
                    if events and date_key in events:
                        draw.rectangle([x_offset, y_offset, x_offset + cell_width - 5, y_offset + cell_height - 5],
                                      outline=(255, 100, 100), width=3)
                x_offset += cell_width
            y_offset += cell_height
        
        # Draw footer
        draw.text((20, height - 30), f"Generated by {BOT_NAME}", 
                 fill=(200, 200, 200), font=day_font)
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
        
    except Exception as e:
        logger.error(f"Calendar image error: {e}")
        return None

def create_year_calendar_image(year: int) -> Optional[bytes]:
    """Create a visual year calendar image"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        width, height = 1200, 900
        img = Image.new('RGB', (width, height), color='#FFFFFF')
        draw = ImageDraw.Draw(img)
        
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            month_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            day_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            title_font = ImageFont.load_default()
            month_font = ImageFont.load_default()
            day_font = ImageFont.load_default()
        
        # Draw title
        draw.text((width//2 - 80, 20), f"Year {year}", 
                 fill=(50, 50, 150), font=title_font)
        
        # Draw months in 3x4 grid
        month_positions = []
        for row in range(4):
            for col in range(3):
                month = row * 3 + col + 1
                if month <= 12:
                    x = 80 + col * 360
                    y = 80 + row * 190
                    month_positions.append((x, y, month))
        
        for x, y, month in month_positions:
            # Month name
            draw.text((x + 40, y), MONTHS_SHORT[month-1], 
                     fill=(80, 80, 80), font=month_font)
            
            # Day headers
            for i, day in enumerate(['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']):
                draw.text((x + i * 42 + 8, y + 25), day, 
                         fill=(150, 150, 150), font=day_font)
            
            # Calendar grid
            cal = calendar.monthcalendar(year, month)
            for week_idx, week in enumerate(cal):
                for day_idx, day in enumerate(week):
                    if day != 0:
                        draw.text((x + day_idx * 42 + 10, y + 45 + week_idx * 22), 
                                 str(day), fill=(50, 50, 50), font=day_font)
        
        # Draw footer
        draw.text((20, height - 30), f"Generated by {BOT_NAME}", 
                 fill=(200, 200, 200), font=day_font)
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
        
    except Exception as e:
        logger.error(f"Year calendar image error: {e}")
        return None

def parse_date_input(text: str) -> Optional[Tuple[int, int, int]]:
    """Parse date input in various formats"""
    # Try YYYY-MM-DD
    match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    
    # Try MM/DD/YYYY
    match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
    if match:
        return (int(match.group(3)), int(match.group(1)), int(match.group(2)))
    
    # Try DD/MM/YYYY
    match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
    if match:
        # If month > 12, assume DD/MM/YYYY
        if int(match.group(2)) > 12:
            return (int(match.group(3)), int(match.group(2)), int(match.group(1)))
    
    return None

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = str(user.id)
    data = get_user_data(user_id)
    
    welcome = (
        f"📅 **Welcome to {BOT_NAME}!**\n\n"
        f"👋 Hello @{user.username or user.first_name}!\n\n"
        f"Your professional calendar and planner assistant.\n\n"
        f"✨ **Features:**\n"
        f"• 📅 Monthly Calendar Generator\n"
        f"• 📆 Yearly Calendar Generator\n"
        f"• 📋 Custom Calendar Creator\n"
        f"• ➕ Add Events & Reminders\n"
        f"• 📌 View Your Events\n"
        f"• 📊 Usage Statistics\n\n"
        f"📊 **Your Stats:**\n"
        f"• Total calendars: {data['total_calendars']}\n"
        f"• Total events: {len(data['events'])}\n\n"
        f"⬇️ Use the buttons below to get started!"
    )
    
    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        f"📖 **{BOT_NAME} User Guide**\n\n"
        "**📅 Calendar Types:**\n"
        "• Monthly Calendar - View any month\n"
        "• Yearly Calendar - View any year\n"
        "• Custom Calendar - Create custom range\n\n"
        "**➕ Add Event:**\n"
        "• Choose event type\n"
        "• Enter date (YYYY-MM-DD)\n"
        "• Enter event description\n\n"
        "**📌 Commands:**\n"
        "/start - Main menu\n"
        "/help - This help\n"
        "/stats - Your statistics\n"
        "/calendar - Generate calendar"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    user_id = str(update.effective_user.id)
    data = get_user_data(user_id)
    
    events = data.get("events", {})
    total_events = sum(len(e) for e in events.values())
    
    stats_text = (
        f"📊 **Your Statistics**\n\n"
        f"📅 Total calendars generated: {data['total_calendars']}\n"
        f"📌 Total events: {total_events}\n"
        f"📋 Custom calendars: {len(data.get('custom_events', []))}\n"
        f"📅 Account active since: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"🔢 Events by month:\n"
    )
    
    # Events by month
    month_counts = defaultdict(int)
    for date_key in events.keys():
        if len(date_key) >= 7:
            month_key = date_key[:7]  # YYYY-MM
            month_counts[month_key] += len(events[date_key])
    
    for month_key, count in sorted(month_counts.items()):
        stats_text += f"• {month_key}: {count}\n"
    
    await update.message.reply_text(
        stats_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /calendar command"""
    await update.message.reply_text(
        "📅 **Choose calendar type:**\n\n"
        "Use the buttons below to generate a calendar.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# ==================== CALLBACK HANDLERS ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    data = get_user_data(user_id)
    action = query.data
    
    # ===== MAIN ACTIONS =====
    
    if action == "monthly":
        now = datetime.now()
        year = data.get("current_year", now.year)
        month = data.get("current_month", now.month)
        
        events = data.get("events", {})
        cal_text, img_data = generate_month_calendar(year, month, events)
        
        if img_data:
            await query.message.reply_photo(
                photo=io.BytesIO(img_data),
                caption=cal_text,
                parse_mode="Markdown",
                reply_markup=get_month_navigation_keyboard(year, month)
            )
        else:
            await query.message.reply_text(
                cal_text,
                parse_mode="Markdown",
                reply_markup=get_month_navigation_keyboard(year, month)
            )
        
        data["total_calendars"] += 1
        
    elif action == "yearly":
        year = data.get("current_year", datetime.now().year)
        cal_text, img_data = generate_year_calendar(year)
        
        if img_data:
            await query.message.reply_photo(
                photo=io.BytesIO(img_data),
                caption=cal_text,
                parse_mode="Markdown",
                reply_markup=get_year_navigation_keyboard(year)
            )
        else:
            await query.message.reply_text(
                cal_text,
                parse_mode="Markdown",
                reply_markup=get_year_navigation_keyboard(year)
            )
        
        data["total_calendars"] += 1
        
    elif action == "custom":
        await query.edit_message_text(
            "📋 **Custom Calendar**\n\n"
            "Send me a date range in this format:\n"
            "• `YYYY-MM-DD to YYYY-MM-DD`\n"
            "• Example: `2024-01-01 to 2024-12-31`\n\n"
            "Or send a single month: `2024-01`",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["action"] = "custom_calendar"
        
    elif action == "add_event":
        await query.edit_message_text(
            "➕ **Add Event**\n\n"
            "Select event type:",
            parse_mode="Markdown",
            reply_markup=get_event_type_keyboard()
        )
        
    elif action == "my_events":
        events = data.get("events", {})
        if not events:
            await query.edit_message_text(
                "📌 **My Events**\n\n"
                "You have no events yet. Add one with the 'Add Event' button!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        event_text = "📌 **My Events**\n\n"
        for date_key, event_list in sorted(events.items()):
            event_text += f"**{date_key}:**\n"
            for event in event_list:
                event_text += f"• {event}\n"
            event_text += "\n"
        
        # Truncate if too long
        if len(event_text) > 4000:
            event_text = event_text[:3900] + "\n\n... and more"
        
        await query.edit_message_text(
            event_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Clear All Events", callback_data="clear_events")],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )
        
    elif action == "clear_events":
        data["events"] = {}
        await query.edit_message_text(
            "✅ **All events cleared!**",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    elif action == "stats":
        events = data.get("events", {})
        total_events = sum(len(e) for e in events.values())
        
        stats_text = (
            f"📊 **Your Statistics**\n\n"
            f"📅 Total calendars generated: {data['total_calendars']}\n"
            f"📌 Total events: {total_events}\n"
            f"📋 Custom calendars: {len(data.get('custom_events', []))}\n"
            f"📅 Account active since: {datetime.now().strftime('%Y-%m-%d')}"
        )
        
        await query.edit_message_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    elif action == "help":
        help_text = (
            f"📖 **{BOT_NAME} User Guide**\n\n"
            "**📅 Calendar Types:**\n"
            "• Monthly Calendar - View any month\n"
            "• Yearly Calendar - View any year\n"
            "• Custom Calendar - Create custom range\n\n"
            "**➕ Add Event:**\n"
            "• Choose event type\n"
            "• Enter date (YYYY-MM-DD)\n"
            "• Enter event description\n\n"
            "**📌 Commands:**\n"
            "/start - Main menu\n"
            "/help - This help\n"
            "/stats - Your statistics"
        )
        await query.edit_message_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    elif action == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to do?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["action"] = None
        
    elif action == "noop":
        await query.answer("Just a label")
        
    # ===== MONTH NAVIGATION =====
    
    elif action.startswith("month_"):
        parts = action.split("_")
        if len(parts) == 3:
            year = int(parts[1])
            month = int(parts[2])
            
            # Handle wrap-around
            if month > 12:
                month = 1
                year += 1
            elif month < 1:
                month = 12
                year -= 1
            
            data["current_year"] = year
            data["current_month"] = month
            
            events = data.get("events", {})
            cal_text, img_data = generate_month_calendar(year, month, events)
            
            if img_data:
                await query.message.reply_photo(
                    photo=io.BytesIO(img_data),
                    caption=cal_text,
                    parse_mode="Markdown",
                    reply_markup=get_month_navigation_keyboard(year, month)
                )
            else:
                await query.message.reply_text(
                    cal_text,
                    parse_mode="Markdown",
                    reply_markup=get_month_navigation_keyboard(year, month)
                )
    
    # ===== YEAR NAVIGATION =====
    
    elif action.startswith("year_"):
        year = int(action.replace("year_", ""))
        data["current_year"] = year
        
        cal_text, img_data = generate_year_calendar(year)
        
        if img_data:
            await query.message.reply_photo(
                photo=io.BytesIO(img_data),
                caption=cal_text,
                parse_mode="Markdown",
                reply_markup=get_year_navigation_keyboard(year)
            )
        else:
            await query.message.reply_text(
                cal_text,
                parse_mode="Markdown",
                reply_markup=get_year_navigation_keyboard(year)
            )
    
    # ===== EVENT TYPES =====
    
    elif action.startswith("event_"):
        event_type = action.replace("event_", "")
        context.user_data["event_type"] = event_type
        context.user_data["action"] = "event_date"
        
        type_names = {
            "personal": "📅 Personal",
            "work": "💼 Work",
            "celebration": "🎉 Celebration",
            "reminder": "📝 Reminder"
        }
        
        await query.edit_message_text(
            f"✅ **Selected:** {type_names.get(event_type, event_type)}\n\n"
            "📅 Enter the date in this format:\n"
            "• `YYYY-MM-DD` (e.g., 2024-12-25)\n\n"
            "You can also use:\n"
            "• `tomorrow` for tomorrow\n"
            "• `next week` for next week\n"
            "• `next month` for next month\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== MESSAGE HANDLERS ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = str(update.effective_user.id)
    data = get_user_data(user_id)
    text = update.message.text.strip()
    action = context.user_data.get("action", "")
    
    # ===== CANCEL =====
    
    if text.lower() == "/cancel":
        context.user_data["action"] = None
        await update.message.reply_text(
            "✅ Cancelled!",
            reply_markup=get_main_keyboard()
        )
        return
    
    # ===== CUSTOM CALENDAR =====
    
    if action == "custom_calendar":
        # Parse date range
        if " to " in text:
            parts = text.split(" to ")
            start_date = parse_date_input(parts[0].strip())
            end_date = parse_date_input(parts[1].strip())
        else:
            start_date = parse_date_input(text)
            end_date = start_date
        
        if start_date and end_date:
            year, month, day = start_date
            end_year, end_month, end_day = end_date
            
            # Generate calendar for the range
            cal_text = f"📋 **Custom Calendar**\n\n"
            cal_text += f"From: {year}-{month:02d}-{day:02d}\n"
            cal_text += f"To: {end_year}-{end_month:02d}-{end_day:02d}\n\n"
            
            # Generate monthly calendars in range
            current = datetime(year, month, day)
            end = datetime(end_year, end_month, end_day)
            
            while current <= end:
                y, m = current.year, current.month
                events = data.get("events", {})
                month_text, img_data = generate_month_calendar(y, m, events)
                cal_text += month_text + "\n"
                
                # Move to next month
                if m == 12:
                    current = datetime(y + 1, 1, 1)
                else:
                    current = datetime(y, m + 1, 1)
            
            data["total_calendars"] += 1
            
            await update.message.reply_text(
                cal_text[:4000],
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            context.user_data["action"] = None
        else:
            await update.message.reply_text(
                "❌ Invalid date format.\n\n"
                "Use: `YYYY-MM-DD to YYYY-MM-DD`\n"
                "Example: `2024-01-01 to 2024-12-31`",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        return
    
    # ===== EVENT DATE =====
    
    if action == "event_date":
        # Parse date
        if text.lower() == "tomorrow":
            target_date = datetime.now() + timedelta(days=1)
        elif text.lower() == "next week":
            target_date = datetime.now() + timedelta(days=7)
        elif text.lower() == "next month":
            target_date = datetime.now() + timedelta(days=30)
        else:
            parsed = parse_date_input(text)
            if parsed:
                target_date = datetime(parsed[0], parsed[1], parsed[2])
            else:
                await update.message.reply_text(
                    "❌ Invalid date format.\n\n"
                    "Use: `YYYY-MM-DD` (e.g., 2024-12-25)\n"
                    "Or: `tomorrow`, `next week`, `next month`",
                    parse_mode="Markdown"
                )
                return
        
        context.user_data["event_date"] = target_date.strftime("%Y-%m-%d")
        context.user_data["action"] = "event_description"
        
        await update.message.reply_text(
            f"📅 **Date:** {target_date.strftime('%Y-%m-%d')}\n\n"
            "📝 Now send me the event description:\n"
            "• Example: 'Team meeting at 3 PM'\n"
            "• Be descriptive!\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown"
        )
        return
    
    # ===== EVENT DESCRIPTION =====
    
    if action == "event_description":
        event_type = context.user_data.get("event_type", "personal")
        event_date = context.user_data.get("event_date")
        event_desc = text
        
        if not event_date:
            await update.message.reply_text(
                "❌ Date not set. Please start over.",
                reply_markup=get_main_keyboard()
            )
            context.user_data["action"] = None
            return
        
        # Save event
        if "events" not in data:
            data["events"] = {}
        
        if event_date not in data["events"]:
            data["events"][event_date] = []
        
        emoji_map = {
            "personal": "📅",
            "work": "💼",
            "celebration": "🎉",
            "reminder": "📝"
        }
        
        event_entry = f"{emoji_map.get(event_type, '📌')} {event_desc}"
        data["events"][event_date].append(event_entry)
        
        await update.message.reply_text(
            f"✅ **Event Added!**\n\n"
            f"📅 Date: {event_date}\n"
            f"📌 Event: {event_entry}\n\n"
            f"View your events with 'My Events'",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
        context.user_data["action"] = None
        context.user_data["event_type"] = None
        context.user_data["event_date"] = None

# ==================== MAIN ====================

async def post_init(application):
    """Post initialization"""
    logger.info("=" * 60)
    logger.info(f"📅 {BOT_NAME} Started Successfully!")
    logger.info(f"🤖 Username: @{BOT_USERNAME}")
    logger.info(f"📦 Version: {BOT_VERSION}")
    logger.info(f"📸 Image Support: {'Enabled' if PIL_AVAILABLE else 'Disabled'}")
    logger.info("=" * 60)
    logger.info("✅ Bot is ready to create calendars!")
    logger.info("=" * 60)

def main():
    """Main entry point"""
    logger.info(f"🚀 Starting {BOT_NAME}...")
    logger.info(f"📡 Using token: {BOT_TOKEN[:15]}...{BOT_TOKEN[-5:]}")
    
    if not PIL_AVAILABLE:
        logger.warning("⚠️ Pillow not installed! Install with: pip install Pillow")
    
    application = ApplicationBuilder() \
        .token(BOT_TOKEN) \
        .post_init(post_init) \
        .build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("calendar", calendar_command))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("✅ Bot is polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
