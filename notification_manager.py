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
            'us_10y_yield': 0.1 # 0.1 percentage point change
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

    def check_and_notify(self, current_data, previous_data):
        """Check for significant changes and send notifications"""
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
