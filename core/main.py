"""
SN Fun Bot - K-pop Discord Bot
Entry point utama untuk menjalankan bot
"""
import sys
import os

# Add parent directory to Python path for Railway deployment
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Also add current directory to ensure core module is found
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from core.bot_core import BotCore
except ImportError:
    from bot_core import BotCore
try:
    from core.commands import CommandsHandler
except ImportError:
    from commands import CommandsHandler
try:
    from features.analytics.analytics import BotAnalytics
except ImportError:
    try:
        from analytics.analytics import BotAnalytics
    except ImportError:
        class BotAnalytics:
            def __init__(self):
                pass
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress default logging

def start_health_server():
    """Start health check server in background"""
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    
    def run_server():
        print(f"Health check server starting on port {port}")
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return server

def main():
    """Main function untuk menjalankan Discord bot"""
    try:
        # Start health check server for Railway
        start_health_server()
        
        # Initialize bot core with timeout handling
        print("Initializing SN Fun Bot...")
        bot_core = BotCore()
        
        # Initialize command handlers
        print("Loading command handlers...")
        commands_handler = CommandsHandler(bot_core)
        
        # Log bot startup
        print("Bot ready, starting...")
        try:
            analytics = BotAnalytics()
            analytics.log_analytics_to_railway()
        except Exception as e:
            print(f"Analytics logging failed: {e}")
        
        # Start bot
        bot_core.run()
        
    except Exception as e:
        print(f"Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
