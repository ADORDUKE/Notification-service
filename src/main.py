# src/main.py
import asyncio
import logging
import signal
import sys

from motor.motor_asyncio import AsyncIOMotorClient

from src.adapters.database.mongo_repository import MongoNotificationRepository
from src.adapters.email.aws_ses import AWSSESEmailAdapter
from src.adapters.message_broker.rabbitmq_consumer import RabbitMQConsumer
from src.config import settings
from src.use_cases.send_reset_password_notification import SendResetPasswordNotificationUseCase

# Configure logging globally
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

logger = logging.getLogger(__name__)


async def main():
    """
    Main entry point for the pure async worker.
    """
    logger.info("Starting Notification-Service Async Worker...")

    # Initialize AsyncIOMotorClient
    db_client = AsyncIOMotorClient(settings.MONGO_URI, uuidRepresentation="standard")

    # 2. Instantiate Adapters
    db_repository = MongoNotificationRepository(db_client, settings.MONGO_DB)
    email_adapter = AWSSESEmailAdapter(
        aws_region=settings.AWS_REGION,
        sender_email=settings.AWS_SES_SENDER,
    )

    # 3. Instantiate Use Case
    use_case = SendResetPasswordNotificationUseCase(
        db_client=db_client, db_name=settings.MONGO_DB, db_repository=db_repository, email_adapter=email_adapter
    )

    # 4. Instantiate RabbitMQ Consumer
    amqp_url = (
        f"amqp://{settings.RABBIT_USER}:{settings.RABBIT_PASS}@{settings.RABBIT_HOST}:{int(settings.RABBIT_PORT)}/"
    )
    consumer = RabbitMQConsumer(
        amqp_url=amqp_url,
        queue_name=settings.QUEUE_NAME,
        use_case=use_case,
    )

    # 5. Start listening to RabbitMQ in the background
    await consumer.start_consuming()

    # 6. Graceful shutdown setup
    stop_event = asyncio.Event()

    def shutdown_handler(sig_name: str):
        logger.info(f"Received exit signal {sig_name}, initiating graceful shutdown...")
        stop_event.set()

    # Register sys signal (ctrl+c and Docker Stop)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: shutdown_handler(s.name))

    logger.info("Worker is running and waiting for messages. Press CTRL+C to stop.")

    # Blocking the execution of main() until stop_event.set() is called
    await stop_event.wait()

    # 7. Cleanup
    logger.info("Closing connection...")
    await consumer.close()
    db_client.close()
    logger.info("Worker stopped successfully.")


if __name__ == "__main__":
    try:
        # Start async Event loop
        asyncio.run(main())
    except KeyboardInterrupt:
        # Backup interception for correct exit in some terminals
        logger.info("Process interrupted manually.")
        sys.exit(0)
