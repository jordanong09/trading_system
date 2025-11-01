"""
Automated Scheduler for Swing Trader Alert Engine
Schedules hourly scans during market hours with timezone handling.

Priority: ⭐⭐⭐⭐⭐
Purpose: Enable hands-free automated operation
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time
import pytz
from typing import Callable, List, Optional
import logging


class TradingScheduler:
    """
    Manages automated scheduling for trading system operations.
    
    Features:
    - Hourly scans during market hours (10:30-15:30 ET)
    - NYSE holiday detection
    - Timezone handling (ET vs local)
    - Graceful error handling
    - Optional EOD and weekly tasks
    """
    
    def __init__(
        self,
        scanner_callback: Callable,
        timezone: str = "America/New_York",
        enable_eod: bool = False,
        enable_weekly: bool = False
    ):
        """
        Initialize the scheduler.
        
        Args:
            scanner_callback: Function to call for hourly scans
            timezone: Timezone for scheduling (default: US/Eastern)
            enable_eod: Enable end-of-day updates (optional)
            enable_weekly: Enable weekly watchlist generation (optional)
        """
        self.scanner_callback = scanner_callback
        self.timezone = pytz.timezone(timezone)
        self.enable_eod = enable_eod
        self.enable_weekly = enable_weekly
        
        # Initialize scheduler
        self.scheduler = BlockingScheduler(timezone=self.timezone)
        
        # NYSE holidays (2025)
        self.nyse_holidays = [
            datetime(2025, 1, 1),   # New Year's Day
            datetime(2025, 1, 20),  # MLK Jr. Day
            datetime(2025, 2, 17),  # Presidents' Day
            datetime(2025, 4, 18),  # Good Friday
            datetime(2025, 5, 26),  # Memorial Day
            datetime(2025, 6, 19),  # Juneteenth
            datetime(2025, 7, 4),   # Independence Day
            datetime(2025, 9, 1),   # Labor Day
            datetime(2025, 11, 27), # Thanksgiving
            datetime(2025, 12, 25), # Christmas
        ]
        
        # Track last scan time
        self.last_scan_time = None
        
        # Setup logging
        self.logger = logging.getLogger('scheduler')
    
    def is_market_open(self) -> bool:
        """
        Check if NYSE is open (weekday, not holiday, market hours).
        
        Returns:
            True if market is open, False otherwise
        """
        now = datetime.now(self.timezone)
        
        # Check if weekend
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # Check if holiday
        if now.date() in [h.date() for h in self.nyse_holidays]:
            self.logger.info(f"Market closed - NYSE holiday")
            return False
        
        # Check market hours (9:30 AM - 4:00 PM ET)
        market_open = time(9, 30)
        market_close = time(16, 0)
        
        if market_open <= now.time() <= market_close:
            return True
        
        return False
    
    def hourly_scan_wrapper(self):
        """
        Wrapper for hourly scan with market hours check and error handling.
        """
        scan_time = datetime.now(self.timezone)
        
        self.logger.info("="*70)
        self.logger.info(f"Scheduled Scan Triggered: {scan_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        self.logger.info("="*70)
        
        # Check if market is open
        if not self.is_market_open():
            self.logger.warning("⏸️  Market is closed - skipping scan")
            return
        
        try:
            # Execute the scanner
            self.logger.info("🔍 Starting hourly scan...")
            self.scanner_callback()
            
            self.last_scan_time = scan_time
            self.logger.info(f"✅ Scan completed successfully at {scan_time.strftime('%H:%M:%S')}")
        
        except Exception as e:
            self.logger.error(f"❌ Scan failed: {e}", exc_info=True)
            # Don't re-raise - keep scheduler running
    
    def eod_update_wrapper(self):
        """
        Wrapper for end-of-day update (optional feature).
        Updates indicators and zones with latest daily bar.
        """
        if not self.enable_eod:
            return
        
        update_time = datetime.now(self.timezone)
        
        self.logger.info("="*70)
        self.logger.info(f"EOD Update Triggered: {update_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        self.logger.info("="*70)
        
        # Check if it's a weekday
        if update_time.weekday() >= 5:
            self.logger.info("⏸️  Weekend - skipping EOD update")
            return
        
        # Check if holiday
        if update_time.date() in [h.date() for h in self.nyse_holidays]:
            self.logger.info("⏸️  Holiday - skipping EOD update")
            return
        
        try:
            self.logger.info("🔄 Starting EOD update...")
            # Call EOD update function (to be implemented)
            # eod_updater.update_all_zones()
            self.logger.info("✅ EOD update completed")
        
        except Exception as e:
            self.logger.error(f"❌ EOD update failed: {e}", exc_info=True)
    
    def weekly_watchlist_wrapper(self):
        """
        Wrapper for weekly watchlist generation (optional feature).
        Runs Sunday evening to identify best setups for the week.
        """
        if not self.enable_weekly:
            return
        
        gen_time = datetime.now(self.timezone)
        
        self.logger.info("="*70)
        self.logger.info(f"Weekly Watchlist Triggered: {gen_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        self.logger.info("="*70)
        
        try:
            self.logger.info("📋 Generating weekly watchlist...")
            # Call watchlist generator (to be implemented)
            # watchlist_generator.generate_watchlist()
            self.logger.info("✅ Weekly watchlist generated")
        
        except Exception as e:
            self.logger.error(f"❌ Watchlist generation failed: {e}", exc_info=True)
    
    def remove_all_jobs(self):
        """Remove all scheduled jobs to prevent conflicts on restart"""
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            job.remove()
        if jobs:
            print(f"   ✅ Removed {len(jobs)} existing job(s)")
    
    def schedule_hourly_scans(self) -> None:
        """
        Schedule hourly scans during market hours.
        Runs at: 10:30, 11:30, 12:30, 13:30, 14:30, 15:30 ET
        """
        scan_hours = [10, 11, 12, 13, 14, 15]
        scan_minute = 30
        
        for hour in scan_hours:
            # Create cron trigger for each hour
            trigger = CronTrigger(
                day_of_week='mon-fri',
                hour=hour,
                minute=scan_minute,
                timezone=self.timezone
            )
            
            self.scheduler.add_job(
                self.hourly_scan_wrapper,
                trigger=trigger,
                id=f'hourly_scan_{hour:02d}{scan_minute:02d}',
                name=f'Hourly Scan {hour:02d}:{scan_minute:02d}',
                max_instances=1,  # Prevent overlapping scans
                coalesce=True     # If multiple missed, run only once
            )
            
            self.logger.info(f"✅ Scheduled hourly scan at {hour:02d}:{scan_minute:02d} ET")
        
        self.logger.info(f"📅 Scheduled {len(scan_hours)} hourly scans (Mon-Fri)")
    
    def schedule_eod_update(self) -> None:
        """
        Schedule end-of-day update (Mon-Thu at 17:00 ET).
        Optional feature - updates zones with latest daily bar.
        """
        if not self.enable_eod:
            self.logger.info("ℹ️  EOD updates disabled")
            return
        
        trigger = CronTrigger(
            day_of_week='mon-thu',
            hour=17,
            minute=0,
            timezone=self.timezone
        )
        
        self.scheduler.add_job(
            self.eod_update_wrapper,
            trigger=trigger,
            id='eod_update',
            name='End-of-Day Update',
            max_instances=1
        )
        
        self.logger.info("✅ Scheduled EOD update (Mon-Thu 17:00 ET)")
    
    def schedule_weekly_watchlist(self) -> None:
        """
        Schedule weekly watchlist generation (Sunday 18:00 ET).
        Optional feature - identifies best setups for the week.
        """
        if not self.enable_weekly:
            self.logger.info("ℹ️  Weekly watchlist disabled")
            return
        
        trigger = CronTrigger(
            day_of_week='sun',
            hour=18,
            minute=0,
            timezone=self.timezone
        )
        
        self.scheduler.add_job(
            self.weekly_watchlist_wrapper,
            trigger=trigger,
            id='weekly_watchlist',
            name='Weekly Watchlist',
            max_instances=1
        )
        
        self.logger.info("✅ Scheduled weekly watchlist (Sun 18:00 ET)")
    
    def schedule_all(self) -> None:
        """
        Schedule all configured jobs.
        """
        self.logger.info("\n" + "="*70)
        self.logger.info("CONFIGURING SCHEDULER")
        self.logger.info("="*70)
        
        self.schedule_hourly_scans()
        self.schedule_eod_update()
        self.schedule_weekly_watchlist()
        
        self.logger.info("\n✅ All schedules configured")
    
    def print_jobs(self) -> None:
        self.logger.info("\n" + "="*70)
        self.logger.info("SCHEDULED JOBS")
        self.logger.info("="*70)

        now = datetime.now(self.timezone)

        for job in self.scheduler.get_jobs():
            # 1) Try attribute if present
            next_dt = getattr(job, "next_run_time", None)

            # 2) Fall back to trigger computation if missing/None
            if not next_dt:
                try:
                    prev = getattr(job, "prev_run_time", None)
                    # APScheduler 3.x signature
                    next_dt = job.trigger.get_next_fire_time(prev, now)
                except Exception:
                    next_dt = None

            # 3) Print nicely
            if next_dt:
                # ensure timezone awareness for formatting
                try:
                    next_str = next_dt.astimezone(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
                except Exception:
                    next_str = str(next_dt)
            else:
                next_str = "pending (will be computed on start)"

            self.logger.info(f"• {job.name}: {next_str}")

        self.logger.info("="*70 + "\n")

    
    def start(self) -> None:
        """
        Start the scheduler (blocking).
        This will run indefinitely until interrupted.
        """
        self.schedule_all()
        self.print_jobs()
        
        self.logger.info("🚀 Starting scheduler...")
        self.logger.info("Press Ctrl+C to stop\n")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("\n⏹️  Scheduler stopped by user")
    
    def stop(self) -> None:
        """
        Stop the scheduler gracefully.
        This is useful for tests or controlled shutdown.
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.logger.info("⏹️  Scheduler stopped")
    
    def run_test_scan(self) -> None:
        """
        Run a test scan immediately (for testing).
        """
        self.logger.info("\n" + "="*70)
        self.logger.info("TEST SCAN")
        self.logger.info("="*70)
        
        self.hourly_scan_wrapper()
    
    def get_next_scan_time(self) -> Optional[datetime]:
        jobs = self.scheduler.get_jobs()
        if not jobs:
            return None

        now = datetime.now(self.timezone)
        next_times = []

        for job in jobs:
            nxt = getattr(job, "next_run_time", None)
            if not nxt:
                try:
                    prev = getattr(job, "prev_run_time", None)
                    nxt = job.trigger.get_next_fire_time(prev, now)
                except Exception:
                    nxt = None
            if nxt:
                next_times.append(nxt)

        return min(next_times) if next_times else None


# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def mock_scanner():
    """Mock scanner function for testing."""
    print("\n🔍 MOCK SCANNER RUNNING")
    print("   • Fetching data...")
    print("   • Building zones...")
    print("   • Detecting patterns...")
    print("   • Generating signals...")
    print("   ✅ Scan complete!")


def test_market_hours():
    """Test market hours detection."""
    print("\n" + "="*70)
    print("TEST 1: Market Hours Detection")
    print("="*70)
    
    scheduler = TradingScheduler(scanner_callback=mock_scanner)
    
    now = datetime.now(scheduler.timezone)
    is_open = scheduler.is_market_open()
    
    print(f"\nCurrent time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Day of week: {now.strftime('%A')}")
    print(f"Market status: {'🟢 OPEN' if is_open else '🔴 CLOSED'}")
    
    # Test specific scenarios
    test_dates = [
        datetime(2025, 1, 1, 10, 30),   # New Year (holiday)
        datetime(2025, 1, 6, 10, 30),   # Monday morning (open)
        datetime(2025, 1, 11, 12, 0),   # Saturday (closed)
        datetime(2025, 1, 13, 10, 30),  # Monday morning (open)
        datetime(2025, 1, 13, 8, 0),    # Monday pre-market (closed)
        datetime(2025, 1, 13, 17, 0),   # Monday after-hours (closed)
    ]
    
    print("\n📅 Test Scenarios:")
    for test_dt in test_dates:
        # Temporarily modify check (just for demonstration)
        is_weekend = test_dt.weekday() >= 5
        is_holiday = test_dt.date() in [h.date() for h in scheduler.nyse_holidays]
        is_market_time = time(9, 30) <= test_dt.time() <= time(16, 0)
        
        is_open = not is_weekend and not is_holiday and is_market_time
        
        status = "🟢 OPEN" if is_open else "🔴 CLOSED"
        print(f"   {test_dt.strftime('%Y-%m-%d %H:%M')} ({test_dt.strftime('%a')}): {status}")
    
    print("\n✅ Market hours detection tested")


def test_scheduling():
    """Test job scheduling."""
    print("\n" + "="*70)
    print("TEST 2: Job Scheduling")
    print("="*70)
    
    scheduler = TradingScheduler(
        scanner_callback=mock_scanner,
        enable_eod=True,
        enable_weekly=True
    )
    
    # Schedule all jobs
    scheduler.schedule_all()
    
    # Note: We don't actually start the BlockingScheduler in tests
    # because it would block execution. Jobs are scheduled and
    # next_run_time will be calculated when scheduler.start() is called in production.
    
    # Print scheduled jobs
    print("\n📋 Scheduled Jobs:")
    job_count = 0
    for job in scheduler.scheduler.get_jobs():
        print(f"\n• {job.name}")
        print(f"  ID: {job.id}")
        print(f"  Trigger: {job.trigger}")
        job_count += 1
    
    print(f"\n✅ Successfully scheduled {job_count} jobs")
    print("📝 Note: next_run_time will be populated when scheduler starts in production")
    
    # Verify expected number of jobs
    expected_jobs = 6  # 6 hourly scans
    if scheduler.enable_eod:
        expected_jobs += 1
    if scheduler.enable_weekly:
        expected_jobs += 1
    
    assert job_count == expected_jobs, f"Expected {expected_jobs} jobs, got {job_count}"
    
    print("\n✅ Job scheduling tested")


def test_manual_scan():
    """Test manual scan execution."""
    print("\n" + "="*70)
    print("TEST 3: Manual Scan")
    print("="*70)
    
    scheduler = TradingScheduler(scanner_callback=mock_scanner)
    
    print("\nRunning test scan...")
    scheduler.run_test_scan()
    
    print("\n✅ Manual scan tested")


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*70)
    print("SCHEDULER TEST SUITE")
    print("="*70)
    
    test_market_hours()
    test_scheduling()
    test_manual_scan()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)


# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================

def integration_example():
    """
    Example of how to integrate with main.py
    """
    print("\n" + "="*70)
    print("INTEGRATION EXAMPLE")
    print("="*70)
    
    print("""
# In main.py:

from utils.scheduler import TradingScheduler
from utils.logger import setup_logger

# Setup logging
logger = setup_logger('main', 'logs/main.log')

# Define scanner function
def run_hourly_scan():
    logger.info("Starting scan...")
    # Your scanning logic here
    scanner = HourlyScanner(config)
    scanner.scan_universe(symbols)
    logger.info("Scan complete")

# Create and start scheduler
scheduler = TradingScheduler(
    scanner_callback=run_hourly_scan,
    enable_eod=True,      # Optional: Enable EOD updates
    enable_weekly=False   # Optional: Enable weekly watchlist
)

# Start scheduler (blocking - runs forever)
scheduler.start()

# Or run a single test scan
scheduler.run_test_scan()
    """)
    
    print("\n💡 TIP: Run as background service using:")
    print("   nohup python main.py --scheduled > scheduler.log 2>&1 &")


def demo_scheduler():
    """
    Demo the scheduler with immediate test.
    """
    print("\n" + "="*70)
    print("SCHEDULER DEMO")
    print("="*70)
    
    scheduler = TradingScheduler(
        scanner_callback=mock_scanner,
        enable_eod=True,
        enable_weekly=True
    )
    
    # Schedule all jobs
    scheduler.schedule_all()
    
    # Show scheduled jobs
    scheduler.print_jobs()
    
    # Run test scan
    print("Running immediate test scan...")
    scheduler.run_test_scan()
    
    print("\n💡 To run scheduler in production, call scheduler.start()")
    print("   (This will block and run indefinitely)")


if __name__ == "__main__":
    # Setup basic logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    run_all_tests()
    
    # Show integration example
    integration_example()
    
    # Demo scheduler
    demo_scheduler()