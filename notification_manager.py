import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

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
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = subject

            # Add message body
            msg.attach(MIMEText(message, 'plain'))

            # Create SMTP session
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info(f"Alert email sent successfully: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
            return False

    def format_daily_summary(self, current_data):
        """Format the daily summary email"""
        summary = f"""
Daily Market Dashboard Summary
Date: {datetime.now().strftime('%Y-%m-%d')}

Gold
USD: ${current_data.get('gold_usd', 'N/A'):,.2f}
GBP: £{current_data.get('gold_gbp', 'N/A'):,.2f}

Currency
GBP/USD: {current_data.get('gbp_usd', 'N/A'):.4f}

Indices
S&P 500: {current_data.get('sp500', 'N/A'):,.2f}
Bitcoin: ${current_data.get('bitcoin', 'N/A'):,.2f}

UK Rates
Base Rate: {current_data.get('uk_base_rate', 'N/A'):.2f}%
Inflation: {current_data.get('uk_inflation', 'N/A'):.2f}%

US Rates
Federal Funds Rate: {current_data.get('us_base_rate', 'N/A'):.2f}%
Inflation: {current_data.get('us_inflation', 'N/A'):.2f}%

US Treasury Yields
2Y: {current_data.get('us_2y_yield', 'N/A'):.2f}%
5Y: {current_data.get('us_5y_yield', 'N/A'):.2f}%
10Y: {current_data.get('us_10y_yield', 'N/A'):.2f}%
30Y: {current_data.get('us_30y_yield', 'N/A'):.2f}%
"""
        return summary

    def send_daily_summary(self, current_data):
        """Send daily summary email"""
        subject = f"Daily Market Dashboard Summary - {datetime.now().strftime('%Y-%m-%d')}"
        message = self.format_daily_summary(current_data)
        self.send_email_alert(subject, message)

    def check_and_notify(self, current_data, previous_data):
        """Check for significant changes and send notifications"""
        # Send daily summary first
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