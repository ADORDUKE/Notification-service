from abc import ABC, abstractmethod
from src.domain.entities import ResetPasswordMessage

class EmailPort(ABC):
    """
    An abstract port (interface) for sending Email notifications.
    The core of our system knows only about this class.
    """
    @abstractmethod
    def send_email(self, message: ResetPasswordMessage):
        """
        Every adapter that wants to work as an email sender
        (AWS SES, SMTP, Mailgun), IS REQUIRED to implement this method with the same signature.
        """
        pass