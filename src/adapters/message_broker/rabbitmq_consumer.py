
import json
import logging

import pika
from pydantic import ValidationError

from src.domain.entities import ResetPasswordMessage
from src.use_cases.process_reset_password import ProcessResetPasswordUseCase

logger = logging.getLogger(__name__)

class RabbitMQConsumer:
    def __init__(
            self,
            host: str,
            port: int,
            user: str,
            password: str,
            queue_name: str,
            use_case: ProcessResetPasswordUseCase,
    ):
        """
        Setup RabbitMQ connection configuration
        """

        self.queue_name = queue_name
        self.use_case = use_case

        # Build credentials(учетные данные) object
        # The PlainCredentials class returns the properly formatted username and password to the Connection.
        credentials = pika.PlainCredentials(user, password)
        self.connection_params = pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=credentials
        )

        self.connection = None
        self.channel = None

    def start_consuming(self) -> None:
        """
        Start listening loop
        """

        # Establish(устанавливаем) a synchronous connection to the RabbitMQ server.
        self.connection = pika.BlockingConnection(self.connection_params)
        # Open a new channel inside the established connection.
        self.channel = self.connection.channel()

        # Ensure queue exists
        self.channel.queue_declare(queue=self.queue_name, durable=True)
        # Set prefetch(предварительных) count to 1 so the worker processes only one message at a time.
        self.channel.basic_qos(prefetch_count=1)

        # Register a callback function that will be executed whenever a new message arrives.
        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self._on_message
        )

        logger.info(f"RabbitMQ listening on queue [{self.queue_name}]...")
        self.channel.start_consuming()

    def _on_message(self, ch, method, props, body):
        """
        Incoming message callback
        """

        # Decode byte string from RabbitMQ into a readable UTF-8 text string.
        raw_body = body.decode("utf-8")
        logger.info(f"Received raw message payload: {raw_body}")

        try:
            # Parse payload to dictionary
            data = json.loads(raw_body)
            message = ResetPasswordMessage(**data)

            # Trigger business logic
            self.use_case.execute(message)

            # Settle(подтверждаем) message on success
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info("Message processed successfully and ACKed.")

        except ValidationError as e:
            # Reject permanently invalid payload
            logger.warning(f"Validation failed for incoming payload: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            logger.info("Bad message rejected with requeue=False.")

        except Exception as e:
            # Extract headers and initialize failure count
            headers = props.headers or {}

            # Extract x-death history to count previous failures
            # RabbitMQ stores retry info in the 'x-death' header array when a message is requeued
            x_death = headers.get("x-death", [])

            # Calculate total failures based on x-death count
            # If x-death exists, we sum up the 'count' values, otherwise it is the 1st failure
            failure_count = sum(d.get("count",0) for d in x_death) + 1 if x_death else 1

            logger.error(f"Failed to process message (Attempt {failure_count}/5) due to error: {e}")

            if failure_count >= 5:
                # Reject message and route to DLQ after 5 failures
                # (Отклоняем сообщение и направляем в DLQ после 5 ошибок)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                logger.error("Message failed 5 times. Rejected permanently to Dead Letter Queue.")
            else:
                # Requeue message on temporary infrastructure failures
                # (Возвращаем сообщение в очередь при сбое инфраструктуры)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                logger.info(f"Message requeued with requeue=True for attempt {failure_count + 1}.")

    def close(self) -> None:
        """
        Safely close the RabbitMQ connection
        """
        if self.connection and self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ connection closed.")
