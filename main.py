"""
SN Fun Bot - K-pop Discord Bot
Entry point utama untuk menjalankan bot
"""
import sys
import os

# Add current directory to Python path for production
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_core import BotCore
from commands import CommandsHandler
from analytics import analytics

def main():
    """Main function untuk menjalankan Discord bot"""
    try:
        # Initialize bot core with timeout handling
        print("🚀 Initializing SN Fun Bot...")
        bot_core = BotCore()
        
        # Initialize command handlers
        print("📋 Loading command handlers...")
        commands_handler = CommandsHandler(bot_core)
        
        # Log bot startup
        print("✅ Bot ready, starting...")
        analytics.log_analytics_to_railway()
        
        # Start bot
        bot_core.run()
        
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
