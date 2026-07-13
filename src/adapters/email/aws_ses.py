import boto3
from botocore.exceptions import ClientError
from src.domain.entities import ResetPasswordMessage
from src.ports.email import EmailPort

class AWSSESEmailAdapter(EmailPort):
    def __init__(
            self,
            aws_access_key_id: str,
            aws_secret_access_key: str,
            aws_region: str,
            sender_email: str
    ):
        """
        Initialization adapter.
        we are not importing the 'settings' object directly here so that the adapter remains independent.
        We will hand over all the settings to him at the start of the application (Dependency injection).
        """

        self.sender_email = sender_email

        # Create official client for working with SES
        self.client = boto3.client(
            "ses",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )

    def send_email(
            self,
            message: ResetPasswordMessage
    )-> None:
        """
        We are implementing the email sending method that our Port requires.
        Accepts a ready-made and valid domain model of the message.
        """

        try:
            print(f"Adapter AWS SES: trying to send email to {message.email_address}....")

            # Create Amazon SES message using their official standard
            self.client.send_email(
                Source=self.sender_email,
                Destination={
                    "ToAddresses": [message.email_address],
                },
                Message={
                    "Subject": {
                        "Data": message.subject,
                        "Charset": "UTF-8",
                    },
                    "Body": {
                        "Text": {
                            "Data": message.body,
                            "Charset": "UTF-8",
                        }
                    }
                }
            )
            print("Adapter AWS SES: message sent successfully to Amazon")
        except ClientError as e:
            # If Amazon reject failed, logging detail
            error_message = e.response["Error"]["Message"]
            print(f"Adapter AWS SES: Request reject, reason: {error_message}")

            # We throw the error to the top so that Use Case catches it and rolls back the MongoDB transaction!
            raise RuntimeError(f"Email delivery failed via AWS SES:{error_message}")


