"""
API Usage Monitoring Script
Monitor dan track penggunaan API per kategori untuk optimasi
"""
import time
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import logger

class APIUsageMonitor:
    def __init__(self):
        self.usage_stats = {
            'OBROLAN': {'calls': 0, 'total_time': 0, 'errors': 0, 'api_key_usage': Counter()},
            'KPOP': {'calls': 0, 'total_time': 0, 'errors': 0, 'api_key_usage': Counter()},
            'REKOMENDASI': {'calls': 0, 'total_time': 0, 'errors': 0, 'api_key_usage': Counter()},
            'GENERAL': {'calls': 0, 'total_time': 0, 'errors': 0, 'api_key_usage': Counter()}
        }
        self.hourly_stats = defaultdict(lambda: defaultdict(int))
        self.start_time = time.time()
        
    def log_api_call(self, category, api_key_index, response_time_ms, success=True):
        """Log API call dengan kategori dan key yang digunakan"""
        if category not in self.usage_stats:
            category = 'GENERAL'
            
        stats = self.usage_stats[category]
        stats['calls'] += 1
        stats['total_time'] += response_time_ms
        stats['api_key_usage'][f'key_{api_key_index + 1}'] += 1
        
        if not success:
            stats['errors'] += 1
            
        # Log hourly stats
        current_hour = datetime.now().strftime('%H:00')
        self.hourly_stats[current_hour][category] += 1
        
        logger.logger.info(f"API Monitor: {category} call using key #{api_key_index + 1}, {response_time_ms}ms, success={success}")
    
    def get_usage_report(self):
        """Generate comprehensive usage report"""
        uptime_hours = (time.time() - self.start_time) / 3600
        
        report = f"""
=== API USAGE MONITORING REPORT ===
Uptime: {uptime_hours:.2f} hours
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CATEGORY BREAKDOWN:
"""
        
        total_calls = sum(stats['calls'] for stats in self.usage_stats.values())
        
        for category, stats in self.usage_stats.items():
            if stats['calls'] > 0:
                avg_time = stats['total_time'] / stats['calls']
                error_rate = (stats['errors'] / stats['calls']) * 100
                usage_percent = (stats['calls'] / total_calls) * 100 if total_calls > 0 else 0
                
                report += f"""
{category}:
  - Total Calls: {stats['calls']} ({usage_percent:.1f}%)
  - Average Response Time: {avg_time:.0f}ms
  - Error Rate: {error_rate:.1f}%
  - API Key Distribution:"""
                
                for key, count in stats['api_key_usage'].most_common():
                    key_percent = (count / stats['calls']) * 100
                    report += f"\n    * {key}: {count} calls ({key_percent:.1f}%)"
        
        # Hourly distribution
        if self.hourly_stats:
            report += f"\n\nHOURLY DISTRIBUTION:"
            for hour in sorted(self.hourly_stats.keys()):
                hour_total = sum(self.hourly_stats[hour].values())
                report += f"\n{hour}: {hour_total} calls"
                for category, count in self.hourly_stats[hour].items():
                    if count > 0:
                        report += f" | {category}: {count}"
        
        # Performance insights
        report += f"\n\nPERFORMANCE INSIGHTS:"
        
        # Find fastest/slowest categories
        category_speeds = {}
        for category, stats in self.usage_stats.items():
            if stats['calls'] > 0:
                category_speeds[category] = stats['total_time'] / stats['calls']
        
        if category_speeds:
            fastest = min(category_speeds, key=category_speeds.get)
            slowest = max(category_speeds, key=category_speeds.get)
            report += f"\n- Fastest Category: {fastest} ({category_speeds[fastest]:.0f}ms avg)"
            report += f"\n- Slowest Category: {slowest} ({category_speeds[slowest]:.0f}ms avg)"
        
        # API key load balancing effectiveness
        report += f"\n\nLOAD BALANCING ANALYSIS:"
        all_key_usage = Counter()
        for stats in self.usage_stats.values():
            all_key_usage.update(stats['api_key_usage'])
        
        if all_key_usage:
            total_api_calls = sum(all_key_usage.values())
            for key, count in all_key_usage.most_common():
                key_percent = (count / total_api_calls) * 100
                report += f"\n- {key}: {count} calls ({key_percent:.1f}%)"
            
            # Check if load balancing is effective (should be roughly equal)
            if len(all_key_usage) > 1:
                max_usage = max(all_key_usage.values())
                min_usage = min(all_key_usage.values())
                balance_ratio = min_usage / max_usage if max_usage > 0 else 0
                
                if balance_ratio > 0.7:
                    report += f"\n- Load Balancing: EXCELLENT (ratio: {balance_ratio:.2f})"
                elif balance_ratio > 0.5:
                    report += f"\n- Load Balancing: GOOD (ratio: {balance_ratio:.2f})"
                else:
                    report += f"\n- Load Balancing: NEEDS IMPROVEMENT (ratio: {balance_ratio:.2f})"
        
        report += f"\n\n=== END REPORT ===\n"
        return report
    
    def save_report(self, filename=None):
        """Save report to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"api_usage_report_{timestamp}.txt"
        
        report = self.get_usage_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.logger.info(f"API usage report saved to {filename}")
        return filename
    
    def reset_stats(self):
        """Reset all statistics"""
        self.__init__()
        logger.logger.info("API usage statistics reset")

# Global monitor instance
api_monitor = APIUsageMonitor()

def log_api_usage(category, api_key_index, response_time_ms, success=True):
    """Convenience function untuk logging API usage"""
    api_monitor.log_api_call(category, api_key_index, response_time_ms, success)

def get_usage_report():
    """Get current usage report"""
    return api_monitor.get_usage_report()

def save_usage_report(filename=None):
    """Save usage report to file"""
    return api_monitor.save_report(filename)

if __name__ == "__main__":
    # Test monitoring system
    print("Testing API Usage Monitor...")
    
    # Simulate some API calls
    api_monitor.log_api_call('OBROLAN', 0, 1200, True)
    api_monitor.log_api_call('KPOP', 1, 1800, True)
    api_monitor.log_api_call('REKOMENDASI', 2, 1500, True)
    api_monitor.log_api_call('OBROLAN', 0, 900, False)  # Error
    api_monitor.log_api_call('KPOP', 1, 2100, True)
    
    # Generate and print report
    print(api_monitor.get_usage_report())
    
    # Save report
    filename = api_monitor.save_report()
    print(f"Report saved to: {filename}")
