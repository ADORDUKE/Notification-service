from pymongo import MongoClient
from src.domain.entities import ResetPasswordMessage
from src.ports.database import DatabasePort
from src.ports.email import EmailPort

class ProcessResetPasswordUseCase:
    def __init__(
            self,
            db_client: MongoClient,
            db_name: str,
            db_repository: DatabasePort,
            email_adapter: EmailPort
    ):
        """
        We use Dependency Injection.
        We are passing interfaces (Ports) here, not specific implementations.
        Thanks to this, the Use Case is isolated from the outside world.
        """
        self.db_client = db_client
        self.db_name = db_name
        self.repository = db_repository
        self.email_adapter = email_adapter

    def execute(self, message: ResetPasswordMessage) -> None:
        """
        The main method that coordinates the entire business logic of the scenario
        """

        print(f"Use Case: Start processing the password reset message for {message.email_address}")

        # STEP 1: Open session in MongoDB
        # We use uuidRepresentation="standard" for db to coding UUID
        with self.db_client.start_session() as session:
            with session.start_transaction():
                try:
                    # STEP 2: We save the notification in the database beforehand (within the session)
                    print("Use Case: Making a draft entry in MongoDB...")
                    self.repository.save_notification(session=session,message=message)

                    # STEP 3: Try to send data from AWS SES
                    print("Use Case: We transfer control to the email adapter...")
                    self.email_adapter.send_email(message=message)

                    # If we got to this line, then there were no mistakes.
                    # When exiting the with block, the transaction is automatically committed.
                    print("Use Case: Transfer successfully finish! Data save to database...")
                except Exception as e:
                    # If ANY error occurred in step 2 or 3 (for example, AWS is unavailable),
                    # we log it and push it further outside.
                    print(f"Use Case: The script has failed! Mistake: {e}")
                    print("Use Case: An automatic rollback of the database has been initiated...")

                    # We send the error above (to the RabbitMQ broker) so that it knows that the message has not been processed.
                    raise e
