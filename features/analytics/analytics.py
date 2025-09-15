"""
Analytics dan Monitoring Module untuk K-pop Bot
Tracking success rate, response time, dan user behavior
"""
import time
import json
import os
from datetime import datetime
# import logging - removed to avoid conflicts

class BotAnalytics:
    def __init__(self):
        self.analytics_file = "data/analytics_data.json"
        self.data = self._load_analytics()
    
    def _load_analytics(self):
        """Load existing analytics data"""
        if os.path.exists(self.analytics_file):
            try:
                with open(self.analytics_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading analytics: {e}")
        
        # Default structure
        return {
            "query_stats": {
                "enhanced_success": 0,
                "enhanced_failed": 0,
                "simple_success": 0,
                "simple_failed": 0,
                "total_queries": 0
            },
            "response_times": {
                "scraping": [],
                "ai_generation": [],
                "total_response": []
            },
            "popular_queries": {},
            "source_performance": {
                "soompi": {"success": 0, "failed": 0, "avg_time": 0},
                "allkpop": {"success": 0, "failed": 0, "avg_time": 0},
                "dbkpop": {"success": 0, "failed": 0, "avg_time": 0},
                "kprofiles": {"success": 0, "failed": 0, "avg_time": 0},
                "wikipedia": {"success": 0, "failed": 0, "avg_time": 0},
                "namu_wiki": {"success": 0, "failed": 0, "avg_time": 0},
                "naver": {"success": 0, "failed": 0, "avg_time": 0},
                "google_cse": {"success": 0, "failed": 0, "avg_time": 0},
                "newsapi": {"success": 0, "failed": 0, "avg_time": 0}
            },
            "daily_stats": {}
        }
    
    def _save_analytics(self):
        """Save analytics data to file"""
        try:
            with open(self.analytics_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving analytics: {e}")
    
    def track_query_success(self, query_type, success, detected_name):
        """Track query success rate"""
        self.data["query_stats"]["total_queries"] += 1
        
        if query_type == "enhanced":
            if success:
                self.data["query_stats"]["enhanced_success"] += 1
            else:
                self.data["query_stats"]["enhanced_failed"] += 1
        elif query_type == "simple":
            if success:
                self.data["query_stats"]["simple_success"] += 1
            else:
                self.data["query_stats"]["simple_failed"] += 1
        
        # Track popular queries
        if detected_name:
            if detected_name not in self.data["popular_queries"]:
                self.data["popular_queries"][detected_name] = 0
            self.data["popular_queries"][detected_name] += 1
        
        self._save_analytics()
    
    def track_response_time(self, operation, duration):
        """Track response times"""
        if operation in self.data["response_times"]:
            self.data["response_times"][operation].append(duration)
            # Keep only last 100 entries
            if len(self.data["response_times"][operation]) > 100:
                self.data["response_times"][operation] = self.data["response_times"][operation][-100:]
        
        self._save_analytics()
    
    def track_source_performance(self, source, success, duration):
        """Track individual source performance"""
        if source in self.data["source_performance"]:
            if success:
                self.data["source_performance"][source]["success"] += 1
            else:
                self.data["source_performance"][source]["failed"] += 1
            
            # Update average time
            current_avg = self.data["source_performance"][source]["avg_time"]
            total_requests = (self.data["source_performance"][source]["success"] + 
                            self.data["source_performance"][source]["failed"])
            
            new_avg = ((current_avg * (total_requests - 1)) + duration) / total_requests
            self.data["source_performance"][source]["avg_time"] = round(new_avg, 2)
        
        self._save_analytics()
    
    def track_daily_usage(self):
        """Track daily usage statistics"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in self.data["daily_stats"]:
            self.data["daily_stats"][today] = 0
        
        self.data["daily_stats"][today] += 1
        self._save_analytics()
    
    def get_analytics_summary(self):
        """Get formatted analytics summary"""
        stats = self.data["query_stats"]
        
        # Calculate success rates
        enhanced_total = stats["enhanced_success"] + stats["enhanced_failed"]
        simple_total = stats["simple_success"] + stats["simple_failed"]
        
        enhanced_rate = (stats["enhanced_success"] / enhanced_total * 100) if enhanced_total > 0 else 0
        simple_rate = (stats["simple_success"] / simple_total * 100) if simple_total > 0 else 0
        
        # Get top queries
        top_queries = sorted(self.data["popular_queries"].items(), 
                           key=lambda x: x[1], reverse=True)[:5]
        
        # Calculate average response times
        avg_scraping = sum(self.data["response_times"]["scraping"]) / len(self.data["response_times"]["scraping"]) if self.data["response_times"]["scraping"] else 0
        avg_ai = sum(self.data["response_times"]["ai_generation"]) / len(self.data["response_times"]["ai_generation"]) if self.data["response_times"]["ai_generation"] else 0
        avg_total = sum(self.data["response_times"]["total_response"]) / len(self.data["response_times"]["total_response"]) if self.data["response_times"]["total_response"] else 0
        
        summary = f"""
📊 **ANALYTICS SUMMARY**

**Query Success Rate:**
• Enhanced Query: {enhanced_rate:.1f}% ({stats['enhanced_success']}/{enhanced_total})
• Simple Query: {simple_rate:.1f}% ({stats['simple_success']}/{simple_total})
• Total Queries: {stats['total_queries']}

**Average Response Times:**
• Scraping: {avg_scraping:.2f}s
• AI Generation: {avg_ai:.2f}s
• Total Response: {avg_total:.2f}s

**Top 5 Popular Queries:**
"""
        
        for i, (query, count) in enumerate(top_queries, 1):
            summary += f"{i}. {query}: {count} requests\n"
        
        summary += "\n**Source Performance:**\n"
        for source, perf in self.data["source_performance"].items():
            total = perf["success"] + perf["failed"]
            if total > 0:
                success_rate = perf["success"] / total * 100
                summary += f"• {source}: {success_rate:.1f}% success, {perf['avg_time']:.2f}s avg\n"
        
        return summary
    
    def log_error(self, error_type, error_message, user_input=None):
        """Log error untuk monitoring"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if "errors" not in self.data:
            self.data["errors"] = {}
        
        if today not in self.data["errors"]:
            self.data["errors"][today] = []
        
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": str(error_message),
            "user_input": user_input
        }
        
        self.data["errors"][today].append(error_entry)
        
        # Keep only last 7 days of errors
        if len(self.data["errors"]) > 7:
            oldest_date = min(self.data["errors"].keys())
            del self.data["errors"][oldest_date]
        
        self._save_analytics()
        print(f"Analytics logged error: {error_type} - {error_message}")
    
    def log_analytics_to_railway(self):
        """Log analytics summary to Railway logs - only if there's meaningful data"""
        # Only log if there are actual queries to report
        if self.data["query_stats"]["total_queries"] > 0:
            summary = self.get_analytics_summary()
            print(f"📊 DAILY ANALYTICS REPORT:\n{summary}")
        else:
            # Silent - no spam logs for empty analytics
            pass

# Global analytics instance
analytics = BotAnalytics()
