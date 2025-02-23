import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
import logging
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.thresholds = {
            'gold_usd': 1.0,    # 1% change
            'bitcoin': 2.0,     # 2% change
            'sp500': 1.0,       # 1% change
            'gbp_usd': 0.5,     # 0.5% change
            'us_10y_yield': 0.1,# 0.1 percentage point change
            'uk_inflation': 0.2,# 0.2 percentage point change
            'us_inflation': 0.2 # 0.2 percentage point change
        }

        # Email configuration
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv('NOTIFICATION_EMAIL')
        self.sender_password = os.getenv('NOTIFICATION_PASSWORD')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')

        # Track last summary sent
        self.last_summary_date = None

    def format_alert_message(self, asset, current_value, previous_value, percent_change):
        """Format the email alert message"""
        return f"""
Market Alert: Significant change detected

Asset: {asset}
Current Value: {current_value:.2f}
Previous Value: {previous_value:.2f}
Change: {percent_change:+.2f}%

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

    def send_email_alert(self, subject, message):
        """Send email alert"""
        try:
            logger.info(f"Attempting to send email: {subject}")

            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = subject

            # Add message body
            msg.attach(MIMEText(message, 'plain'))

            # Create SMTP session
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                logger.info("Establishing SMTP connection...")
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info(f"Alert email sent successfully: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
            logger.error(f"Full error details: {traceback.format_exc()}")
            return False

    def format_daily_summary(self, current_data):
        """Format the daily summary email"""
        def format_value(value, is_currency=False, is_percentage=False, currency_symbol=''):
            if value is None:
                return 'N/A'
            if is_currency:
                return f"{currency_symbol}{value:,.2f}"
            if is_percentage:
                return f"{value:.2f}%"
            return f"{value:.4f}"

        summary = f"""
Daily Market Dashboard Summary
Date: {datetime.now().strftime('%Y-%m-%d')}

Gold
USD: {format_value(current_data.get('gold_usd'), is_currency=True, currency_symbol='$')}
GBP: {format_value(current_data.get('gold_gbp'), is_currency=True, currency_symbol='£')}

Currency
GBP/USD: {format_value(current_data.get('gbp_usd'))}

Indices
S&P 500: {format_value(current_data.get('sp500'), is_currency=False)}
Bitcoin: {format_value(current_data.get('bitcoin'), is_currency=True, currency_symbol='$')}

UK Rates
Base Rate: {format_value(current_data.get('uk_base_rate'), is_percentage=True)}
Inflation: {format_value(current_data.get('uk_inflation'), is_percentage=True)}

US Rates
Federal Funds Rate: {format_value(current_data.get('us_base_rate'), is_percentage=True)}
Inflation: {format_value(current_data.get('us_inflation'), is_percentage=True)}

US Treasury Yields
2Y: {format_value(current_data.get('us_2y_yield'), is_percentage=True)}
5Y: {format_value(current_data.get('us_5y_yield'), is_percentage=True)}
10Y: {format_value(current_data.get('us_10y_yield'), is_percentage=True)}
30Y: {format_value(current_data.get('us_30y_yield'), is_percentage=True)}
"""
        return summary

    def should_send_daily_summary(self):
        """Check if we should send a daily summary"""
        now = datetime.now(timezone.utc)
        target_hour = 9  # 9:00 AM UTC
        window_minutes = 15  # Increased window to 15 minutes

        # Check if it's a new day AND it's within the target time window
        is_new_day = self.last_summary_date is None or self.last_summary_date.date() < now.date()
        is_target_time = now.hour == target_hour and now.minute < window_minutes

        logger.info(f"Daily summary check at {now} UTC")
        logger.info(f"Last summary date: {self.last_summary_date}")
        logger.info(f"Is new day: {is_new_day}, Is target time: {is_target_time}")
        logger.info(f"Current hour (UTC): {now.hour}")

        if is_new_day and is_target_time:
            self.last_summary_date = now
            logger.info(f"Daily summary scheduled for {now}")
            return True

        if not is_target_time:
            logger.info(f"Not target time. Current: {now.hour}:{now.minute}, Target: {target_hour}:00-{target_hour}:{window_minutes}")
        if not is_new_day:
            logger.info("Already sent summary today")

        return False

    def send_daily_summary(self, current_data):
        """Send daily summary email"""
        try:
            if not self.should_send_daily_summary():
                logger.debug("Not time for daily summary yet")
                return False

            if not all([self.sender_email, self.sender_password, self.recipient_email]):
                logger.error("Missing email configuration")
                return False

            logger.info("Preparing daily summary email...")
            subject = f"Daily Market Dashboard Summary - {datetime.now().strftime('%Y-%m-%d')}"
            message = self.format_daily_summary(current_data)
            success = self.send_email_alert(subject, message)

            if success:
                logger.info("Daily summary email sent successfully")
            else:
                logger.error("Failed to send daily summary email")

            return success
        except Exception as e:
            logger.error(f"Failed to send daily summary: {str(e)}")
            logger.error(f"Full error details: {traceback.format_exc()}")
            return False

    def check_and_notify(self, current_data, previous_data):
        """Check for significant changes and send notifications"""
        # Send daily summary only once per day
        self.send_daily_summary(current_data)

        # Then check for threshold alerts
        if not previous_data or not current_data:
            return

        for asset, threshold in self.thresholds.items():
            if asset not in current_data or asset not in previous_data:
                continue

            current_value = current_data[asset]
            previous_value = previous_data[asset]

            if not current_value or not previous_value:
                continue

            percent_change = ((current_value - previous_value) / previous_value) * 100

            if abs(percent_change) >= threshold:
                subject = f"Market Alert: {asset} moved by {percent_change:+.2f}%"
                message = self.format_alert_message(
                    asset, current_value, previous_value, percent_change
                )
                self.send_email_alert(subject, message)