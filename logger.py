import logging
import sys
import os
from datetime import datetime

# ---- Logger setup ----
logger = logging.getLogger("sn_fun_bot")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Deteksi environment untuk format yang tepat
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None
USE_EMOJI = IS_RAILWAY or os.getenv('PYTHONIOENCODING') == 'utf-8'

# Format log yang lebih rapi dan terstruktur
class ColoredFormatter(logging.Formatter):
    """Custom formatter dengan warna dan format yang lebih rapi"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Format timestamp yang lebih compact
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Pilih warna berdasarkan level
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format level dengan padding yang konsisten
        level = f"{record.levelname:<8}"
        
        # Format pesan dengan indentasi yang rapi
        message = record.getMessage()
        
        # Format final yang rapi - emoji untuk Railway, ASCII untuk Windows
        separator = "│" if USE_EMOJI else "|"
        return f"{color}[{timestamp}] {level}{reset} {separator} {message}"

formatter = ColoredFormatter()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ---- CSV Loader ----
def log_csv_loaded(df):
    if df.empty:
        icon = "❌" if USE_EMOJI else "[X]"
        sep = "│" if USE_EMOJI else "|"
        logger.error(f"{icon} DATABASE {sep} CSV K-pop gagal dimuat atau kosong")
    else:
        groups = df['Group'].nunique()
        members = len(df)
        icon = "📊" if USE_EMOJI else "[+]"
        sep = "│" if USE_EMOJI else "|"
        logger.info(f"{icon} DATABASE {sep} CSV K-pop dimuat: {members:,} entries | {groups} groups | {members} members")

# ---- Redis Cache ----
def log_cache_set(category, name):
    icon = "💾" if USE_EMOJI else "[C]"
    sep = "│" if USE_EMOJI else "|"
    logger.info(f"{icon} CACHE {sep} Saved {category}:{name}")

def log_cache_hit(category, name):
    icon = "⚡" if USE_EMOJI else "[H]"
    sep = "│" if USE_EMOJI else "|"
    logger.info(f"{icon} CACHE {sep} Retrieved {category}:{name}")

def log_cache_miss(category, name):
    icon = "🔍" if USE_EMOJI else "[M]"
    sep = "│" if USE_EMOJI else "|"
    logger.info(f"{icon} CACHE {sep} Miss {category}:{name} - generating new")

# ---- Detection System ----
def log_detection(user_input, category, detected_name=None, confidence=None):
    sep = "│" if USE_EMOJI else "|"
    arrow = "→" if USE_EMOJI else "->"
    
    if category in ["GROUP", "MEMBER", "MEMBER_GROUP"]:
        conf_str = f" ({confidence:.1f}%)" if confidence else ""
        icon = "🎯" if USE_EMOJI else "[D]"
        logger.info(f"{icon} DETECT {sep} '{user_input}' {arrow} {category}:{detected_name}{conf_str}")
    elif category == "MULTIPLE":
        icon = "🤔" if USE_EMOJI else "[D]"
        logger.info(f"{icon} DETECT {sep} '{user_input}' {arrow} {category} (multiple matches)")
    elif category == "REKOMENDASI":
        icon = "💡" if USE_EMOJI else "[D]"
        logger.info(f"{icon} DETECT {sep} '{user_input}' {arrow} {category}")
    elif category == "OBROLAN":
        icon = "💬" if USE_EMOJI else "[D]"
        logger.info(f"{icon} DETECT {sep} '{user_input}' {arrow} {category}")
    else:
        icon = "🔍" if USE_EMOJI else "[D]"
        logger.info(f"{icon} DETECT {sep} '{user_input}' {arrow} {category}")

# ---- Command Processing ----
def log_sn_command(user, input_text, category, detected_name=None):
    user_display = str(user)[:20] + "..." if len(str(user)) > 20 else str(user)
    icon = "🤖" if USE_EMOJI else "[B]"
    sep = "│" if USE_EMOJI else "|"
    arrow = "→" if USE_EMOJI else "->"
    
    if category in ["GROUP", "MEMBER", "MEMBER_GROUP"]:
        logger.info(f"{icon} COMMAND {sep} {user_display} {arrow} !sn '{input_text}' {arrow} {category}:{detected_name}")
    elif category == "MULTIPLE":
        logger.info(f"{icon} COMMAND {sep} {user_display} {arrow} !sn '{input_text}' {arrow} {category}")
    elif category in ["OBROLAN", "REKOMENDASI"]:
        logger.info(f"{icon} COMMAND {sep} {user_display} {arrow} !sn '{input_text}' {arrow} {category}")
    else:
        logger.info(f"{icon} COMMAND {sep} {user_display} {arrow} !sn '{input_text}' {arrow} {category}")

# ---- AI Processing ----
def log_ai_request(category, prompt_length):
    icon = "🧠" if USE_EMOJI else "[A]"
    sep = "│" if USE_EMOJI else "|"
    logger.info(f"{icon} AI {sep} Request {category} (prompt: {prompt_length} chars)")

def log_ai_response(category, response_length, duration_ms):
    icon = "✨" if USE_EMOJI else "[A]"
    sep = "│" if USE_EMOJI else "|"
    logger.info(f"{icon} AI {sep} Response {category} ({response_length} chars, {duration_ms}ms)")

def log_ai_error(category, error_msg):
    icon = "❌" if USE_EMOJI else "[X]"
    sep = "│" if USE_EMOJI else "|"
    logger.error(f"{icon} AI {sep} Error {category}: {error_msg}")

# ---- Transition Detection ----
def log_transition(context, user_input, result_category):
    context_short = context[:30] + "..." if len(context) > 30 else context
    icon = "🔄" if USE_EMOJI else "[T]"
    sep = "│" if USE_EMOJI else "|"
    arrow = "→" if USE_EMOJI else "->"
    logger.info(f"{icon} TRANSIT {sep} '{context_short}' + '{user_input}' {arrow} {result_category}")

# ---- Performance Monitoring ----
def log_performance(operation, duration_ms, details=None):
    sep = "│" if USE_EMOJI else "|"
    details_str = f" {sep} {details}" if details else ""
    
    if duration_ms < 1000:
        icon = "⚡" if USE_EMOJI else "[P]"
        logger.info(f"{icon} PERF {sep} {operation}: {duration_ms}ms{details_str}")
    elif duration_ms < 5000:
        icon = "🐌" if USE_EMOJI else "[S]"
        logger.warning(f"{icon} PERF {sep} {operation}: {duration_ms}ms (slow){details_str}")
    else:
        icon = "🚨" if USE_EMOJI else "[!]"
        logger.error(f"{icon} PERF {sep} {operation}: {duration_ms}ms (very slow){details_str}")

# ---- Error Handling ----
def log_error(component, error_msg, user_input=None):
    sep = "│" if USE_EMOJI else "|"
    input_str = f" {sep} Input: '{user_input}'" if user_input else ""
    icon = "💥" if USE_EMOJI else "[X]"
    logger.error(f"{icon} ERROR {sep} {component}: {error_msg}{input_str}")

def log_warning(component, warning_msg):
    icon = "⚠️" if USE_EMOJI else "[W]"
    sep = "│" if USE_EMOJI else "|"
    logger.warning(f"{icon} WARNING {sep} {component}: {warning_msg}")
