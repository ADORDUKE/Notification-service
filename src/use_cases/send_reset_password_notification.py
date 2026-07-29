# src/use_cases/send_reset_password_notification.py
import logging

from motor.motor_asyncio import AsyncIOMotorClient

from src.domain.entities import ResetPasswordMessage
from src.ports.database import DatabasePort
from src.ports.email import EmailPort

logger = logging.getLogger(__name__)


class SendResetPasswordNotificationUseCase:
    def __init__(
        self, db_client: AsyncIOMotorClient, db_name: str, db_repository: DatabasePort, email_adapter: EmailPort
    ):
        self.db_client = db_client
        self.db_name = db_name
        self.repository = db_repository
        self.email_adapter = email_adapter

    async def execute(self, message: ResetPasswordMessage) -> None:
        logger.info(f"Start processing reset password for {message.email_address}")

        # Open session from long-lived client
        async with await self.db_client.start_session() as session:
            async with session.start_transaction():
                try:
                    logger.info("Saving notification draft in MongoDB...")
                    await self.repository.save_notification(session=session, message=message)

                    logger.info("Transferring control to the email adapter...")
                    await self.email_adapter.send_email(message=message)

                    logger.info("Scenario completed successfully!")

                except Exception as e:
                    logger.warning(f"Scenario failed! Error: {e}")
                    logger.info("Automatic database rollback initiated...")
                    raise e
