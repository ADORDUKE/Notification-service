from abc import ABC, abstractmethod

from pymongo.client_session import ClientSession

from src.domain.entities import ResetPasswordMessage


class DatabasePort(ABC):
    @abstractmethod
    def save_notification(self, session: ClientSession, message: ResetPasswordMessage) -> None:
        """
        Saves the notification entity to the database within the current session/transaction
        """
        pass
