import logging

from pymongo.client_session import ClientSession

from src.domain.entities import ResetPasswordMessage
from src.ports.database import DatabasePort

logger = logging.getLogger(__name__)

class MongoNotificationRepository(DatabasePort):
    def __init__(self, db_client, db_name: str):
        """
        Initialize the Mongo notification repository.
        db_client - MongoClient instance
        db_name - database name
        """
        self.db_client = db_client
        self.db = db_client[db_name]
        self.collection = self.db["notifications"]

    def save_notification(self, session: ClientSession, message: ResetPasswordMessage) -> None:
        """
        Insert document into MongoDB within active transaction session
        """

        # Pydantic into Python dict
        # by_alias=True save fields as userId and emailAddress
        document = message.model_dump(by_alias=True)


        # session=session if operation is in inside transaction
        self.collection.insert_one(document, session=session)
        logger.info(f"Draft notification [{message.id}] saved to MongoDB.")
