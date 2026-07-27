# src/main.py
import logging
import signal
import sys

from pymongo import MongoClient

from src.adapters.database.mongo_repository import MongoNotificationRepository
from src.adapters.email.aws_ses import AWSSESEmailAdapter
from src.adapters.message_broker.rabbitmq_consumer import RabbitMQConsumer
from src.config import settings
from src.use_cases.send_reset_password_notification import SendResetPasswordNotificationUseCase

# Configure logging globally
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)

def run_application():
    logger.info("Starting Notification-Service Worker...")

    # 1. Initialize long-lived MongoClient
    db_client = MongoClient(settings.MONGO_URI, uuidRepresentation="standard")

    # 2. Instantiate Adapters
    db_repository = MongoNotificationRepository(db_client, settings.MONGO_DB)
    email_adapter = AWSSESEmailAdapter(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_region=settings.AWS_REGION,
        sender_email=settings.AWS_SES_SENDER
    )

    # 3. Instantiate Use Case
    use_case = SendResetPasswordNotificationUseCase(
        db_client=db_client,
        db_name=settings.MONGO_DB,
        db_repository=db_repository,
        email_adapter=email_adapter
    )

    # 4. Instantiate Consumer
    consumer = RabbitMQConsumer(
        host=settings.RABBIT_HOST,
        port=int(settings.RABBIT_PORT),
        user=settings.RABBIT_USER,
        password=settings.RABBIT_PASS,
        queue_name=settings.QUEUE_NAME,
        use_case=use_case
    )

    # Graceful shutdown handler
    def handle_shutdown(signum, frame):
        logger.info("Shutdown signal received, closing connections...")
        consumer.close()
        db_client.close()
        sys.exit(0)

    # Register OS signals for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # 5. Start infinite consuming loop
    try:
        consumer.start_consuming()
    except Exception as e:
        logger.critical(f"Unhandled worker error: {e}")
    finally:
        # Close connections on exit
        logger.info("Closing connections in finally block...")
        consumer.close()
        db_client.close()

if __name__ == "__main__":
    run_application()
