import os
import re
import logging
import smtplib
from contextlib import contextmanager
from typing import List, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ai_guardian_remediation.config import settings
from dotenv import load_dotenv


class EmailManager:
    def __init__(self, recipient_email: Union[str, List[str]], remediation_type: str):
        load_dotenv()
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SMTP_USERNAME")

        # Accept either a single email string or a list of emails
        self.recipient_email = self._normalize_recipients(recipient_email)
        self.remediation_type = remediation_type

        if settings.SEND_EMAIL_NOTIFICATIONS:
            self._validate_config()

    def _validate_config(self):
        """Ensure essential environment variables are configured."""
        missing = [
            var for var in ["SMTP_USERNAME", "SMTP_PASSWORD"] if not os.getenv(var)
        ]
        if missing:
            logging.warning(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        if not self.is_valid_email(self.sender_email):
            logging.warning(f"Invalid sender email format: {self.sender_email}")

        # Validate recipients
        for r in self.recipient_email or []:
            if not self.is_valid_email(r):
                logging.warning(f"Invalid recipient email format: {r}")

    def send_email(
        self, recipient_email: Union[str, List[str]], subject: str, body: str
    ):
        # Create message
        if not settings.SEND_EMAIL_NOTIFICATIONS:
            logging.info("Email notifications are disabled. Skipping email send.")
            return False

        if not recipient_email:
            logging.error("Recipient email is not provided. Cannot send email.")
            return False

        recipients = self._normalize_recipients(recipient_email)
        if not recipients:
            logging.error(
                "No valid recipient emails after normalization. Cannot send email."
            )
            return False

        msg = MIMEMultipart()
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        try:
            # _get_smtp_server yields (server, uses_starttls)
            with self._get_smtp_server() as (server, uses_starttls):
                server.ehlo()
                if uses_starttls:
                    # start TLS for non-SSL connections (e.g., port 587)
                    try:
                        server.starttls()
                        server.ehlo()
                    except Exception:
                        # If starttls fails, continue to attempt login which may also fail
                        logging.debug(
                            "starttls failed or not supported by server; continuing without it"
                        )

                # Login only if credentials are provided
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)

                # smtplib.sendmail accepts a list of recipient addresses
                server.sendmail(self.sender_email, recipients, msg.as_string())

            logging.info(f"Email successfully sent to {recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logging.error("SMTP authentication failed. Check credentials.")
        except smtplib.SMTPConnectError:
            logging.error("Failed to connect to SMTP server.")
        except Exception as e:
            logging.error(f"Unexpected error while sending email: {e}")

        return False

    @contextmanager
    def _get_smtp_server(self):
        """Context manager that yields an SMTP server object and a boolean indicating
        whether STARTTLS should be used. Uses SMTP_SSL for explicit SSL ports (465).
        """
        server = None
        uses_starttls = True
        try:
            # Use implicit SSL for port 465
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=60)
                uses_starttls = False
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=60)
                # keep uses_starttls True for typical submission ports like 587

            yield (server, uses_starttls)

        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    # ensure we don't raise from cleanup
                    try:
                        server.close()
                    except Exception:
                        pass

    def _normalize_recipients(
        self, recipient: Union[str, List[str], None]
    ) -> List[str]:
        """Normalize recipient input to a list of stripped email strings.

        Accepts a single string (comma or semicolon separated) or a list of strings.
        Returns a list (possibly empty) of email addresses.
        """
        if not recipient:
            return []

        if isinstance(recipient, list):
            items = recipient
        else:
            # split on common delimiters
            items = re.split(r"[;,\s]+", str(recipient))

        # strip and filter out empty entries
        normalized = [s.strip() for s in items if s and s.strip()]
        return normalized

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Basic email format validation."""
        if not email:
            return False
        # Simple regex for email validation (not exhaustive)
        pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        return re.match(pattern, email) is not None

    def send_approval_notification(self, details):
        """
        Send an email notification for approved remediation

        Args:
            recipient_email (str): Email address of the recipient
            remediation_type (str): Type of remediation (CVE/SAST)
            details (dict): Dictionary containing remediation details
        """
        subject = f"AI Guardian - {self.remediation_type} Remediation Approved - {details.get('finding', 'for SAST/SCA')}"

        # Create email content
        body = f"""
This is to inform you that the {self.remediation_type} remediation has been approved in the AI Guardian system.

Details:
Repository: {details.get("repository", "N/A")}
Branch: {details.get("branch", "N/A")}
Pull Request: {details.get("pr_url", "N/A")}
Finding: {details.get("finding", "N/A")}

Please review the Pull Request at your earliest convenience.

- AI Guardian Team
"""

        self.send_email(self.recipient_email, subject, body)
