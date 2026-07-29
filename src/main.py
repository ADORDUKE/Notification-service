# src/main.py
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from src.adapters.database.mongo_repository import MongoNotificationRepository
from src.adapters.email.aws_ses import AWSSESEmailAdapter
from src.adapters.message_broker.rabbitmq_consumer import RabbitMQConsumer
from src.config import settings
from src.use_cases.send_reset_password_notification import SendResetPasswordNotificationUseCase

# Configure logging globally
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

logger = logging.getLogger(__name__)

consumer: RabbitMQConsumer
db_client: AsyncIOMotorClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application lifecycle: connection start and soft shutdown
    """
    global consumer, db_client
    logger.info("Starting Notification-Service Worker via FastAPI...")

    # Initialize AsyncIOMotorClient
    db_client = AsyncIOMotorClient(settings.MONGO_URI, uuidRepresentation="standard")

    # 2. Instantiate Adapters
    db_repository = MongoNotificationRepository(db_client, settings.MONGO_DB)
    email_adapter = AWSSESEmailAdapter(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
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

    # ---- Starting app ---
    yield
    # ---------------------

    # 6. Graceful shutdown
    logger.info("Shutdown signal received, closing connections...")
    await consumer.close()
    db_client.close()


# Initiation FastApi
app = FastAPI(
    lifespan=lifespan,
    title="Notification-Service",
    version="1.0.0",
)


@app.get("/health", tags=["System Health"])
async def health_check():
    """
    Endpoint for health check
    """
    return {"status": "ok", "service": "Notification-Service"}


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
