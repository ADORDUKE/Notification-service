# src/adapters/email/aws_ses.py
import logging

import boto3
from botocore.exceptions import ClientError

from src.domain.entities import ResetPasswordMessage
from src.ports.email import EmailPort

# Initialize logger
logger = logging.getLogger(__name__)


class AWSSESEmailAdapter(EmailPort):
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, aws_region: str, sender_email: str):
        """
        Initialize AWS SES client
        """
        self.sender_email = sender_email
        self.client = boto3.client(
            "ses",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )

    def send_email(self, message: ResetPasswordMessage) -> None:
        """
        Send raw(сырое) email message via boto3
        """
        try:
            logger.info(
                f"Attempting to send email to {message.email_address} via AWS SES...")

            # Send message using standard SES payload
            self.client.send_email(
                Source=self.sender_email,
                Destination={
                    "ToAddresses": [message.email_address]
                },
                Message={
                    "Subject": {
                        "Data": message.subject,
                        "Charset": "UTF-8"
                    },
                    "Body": {
                        "Text": {
                            "Data": message.body,
                            "Charset": "UTF-8"
                        }
                    }
                }
            )
            logger.info("Email delivered successfully via AWS SES!")

        except ClientError as e:
            # Extract error details
            error_message = e.response["Error"]["Message"]
            logger.error(
                f"AWS SES Request rejected. Reason: {error_message}")

            # Raise exception to trigger database rollback
            raise RuntimeError(f"Email delivery failed via AWS SES: {error_message}") from e
