import logging

from motor.motor_asyncio import AsyncIOMotorClient

from src.domain.entities import ResetPasswordMessage
from src.ports.database import DatabasePort

logger = logging.getLogger(__name__)


class MongoNotificationRepository(DatabasePort):
    def __init__(self, db_client: AsyncIOMotorClient, db_name: str):
        """
        Initialize the Mongo notification repository.
        db_client - MongoClient instance
        db_name - database name
        """
        self.db_client = db_client
        self.db = db_client[db_name]
        self.collection = self.db["notifications"]

    async def save_notification(self, session: AsyncIOMotorClient, message: ResetPasswordMessage) -> None:
        """
        Asynchronously Insert document into MongoDB within active transaction session
        """

        # Pydantic into Python dict
        # by_alias=True save fields as userId and emailAddress
        document = message.model_dump(by_alias=True)

        # session=session if operation is in inside transaction
        await self.collection.insert_one(document, session=session)
        logger.info(f"Draft notification [{message.id}] saved to MongoDB.")
