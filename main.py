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

def main():
    """Main function untuk menjalankan Discord bot"""
    # Initialize bot core
    bot_core = BotCore()
    
    # Initialize command handlers
    commands_handler = CommandsHandler(bot_core)
    
    # Start bot
    print("🚀 Starting SN Fun Bot...")
    bot_core.run()

if __name__ == "__main__":
    main()
