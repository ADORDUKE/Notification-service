import json
import logging

import aio_pika
from pydantic import ValidationError

from src.domain.entities import ResetPasswordMessage
from src.use_cases.send_reset_password_notification import SendResetPasswordNotificationUseCase

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    def __init__(
        self,
        amqp_url: str,
        queue_name: str,
        use_case: SendResetPasswordNotificationUseCase,
    ):
        """
        Setup RabbitMQ connection configuration
        """
        self.amqp_url = amqp_url
        self.queue_name = queue_name
        self.use_case = use_case
        self.connection = None

    async def start_consuming(self) -> None:
        """
        Connect to RabbitMQ and register the async consumer callback
        """

        # connect_robust automatically reconnects when the network is down
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        channel = await self.connection.channel()

        # We guarantee to process only 1 message at a time (Fair Dispatch)
        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue(self.queue_name, durable=True)

        # Starting consuming. Aio-pika don't blok Event loop
        await queue.consume(self._on_message)
        logger.info(f"RabbitMQ listening on queue [{self.queue_name}]...")

    async def _on_message(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        """
        Incoming async message callback
        """

        # Decode byte string from RabbitMQ into a readable UTF-8 text string.
        raw_body = message.body.decode("utf-8")
        logger.info(f"Received raw message payload: {raw_body}")

        try:
            # Parse payload to dictionary
            data = json.loads(raw_body)
            msg_entity = ResetPasswordMessage(**data)

            # Trigger business logic
            await self.use_case.execute(msg_entity)

            # Settle(подтверждаем) message on success
            await message.ack()
            logger.info("Message processed successfully and ACKed.")

        except ValidationError as e:
            # Reject permanently invalid payload
            logger.warning(f"Validation failed for incoming payload: {e}")
            await message.reject(requeue=False)
            logger.info("Bad message rejected with requeue=False.")

        except Exception as e:
            # Extract headers and initialize failure count
            headers = message.headers or {}

            # Extract x-death history to count previous failures
            # RabbitMQ stores retry info in the 'x-death' header array when a message is requeued
            x_death = headers.get("x-death", [])

            # Calculate total failures based on x-death count
            # If x-death exists, we sum up the 'count' values, otherwise it is the 1st failure
            failure_count = sum(d.get("count", 0) for d in x_death) + 1 if x_death else 1

            logger.error(f"Failed to process message (Attempt {failure_count}/5) due to error: {e}")

            if failure_count >= 5:
                # Reject message and route to DLQ after 5 failures
                await message.reject(requeue=False)
                logger.error("Message failed 5 times. Rejected permanently to Dead Letter Queue.")
            else:
                # Requeue message on temporary infrastructure failures
                await message.reject(requeue=True)
                logger.info(f"Message requeued with requeue=True for attempt {failure_count + 1}.")

    async def close(self) -> None:
        """
        Safely close the RabbitMQ connection
        """
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed.")
