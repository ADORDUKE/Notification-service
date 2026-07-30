# src/adapters/email/aws_ses.py
import logging

import aioboto3
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
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.sender_email = sender_email

        # Create async session aioboto3
        self.session = aioboto3.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region,
        )

    async def send_email(self, message: ResetPasswordMessage) -> None:
        """
        Send raw(сырое) email message via boto3
        """
        try:
            # Open async client to sending mail
            async with self.session.client("ses") as ses_client:
                # We are waiting for a response from Amazon servers without blocking the application
                response = await ses_client.send_email(
                    Source=self.sender_email,
                    Destination={"ToAddresses": [message.email_address]},
                    Message={
                        "Subject": {
                            "Data": message.subject,
                        },
                        "Body": {
                            "Text": {
                                "Data": message.body,
                            }
                        },
                    },
                )
                logger.info(f"Email sent successfully via AWS SES! MessageId: {response.get('MessageId')}")

        except ClientError as e:
            # Extract error details
            error_message = e.response["Error"]["Message"]
            logger.error(f"AWS SES Request rejected. Reason: {error_message}")

            # Raise exception to trigger database rollback
            raise RuntimeError(f"Email delivery failed via AWS SES: {error_message}") from e
