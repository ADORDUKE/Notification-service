# src/main.py
from datetime import datetime, UTC
from uuid import uuid4
from pymongo import MongoClient

from src.config import settings
from src.domain.entities import ResetPasswordMessage
from src.adapters.database.mongo_repository import MongoNotificationRepository
from src.adapters.email.aws_ses import AWSSESEmailAdapter
from src.use_cases.process_reset_password import ProcessResetPasswordUseCase


def run_application():
    print("🚀 Запуск Notification-Service в режиме интеграционного теста...\n")

    # 1. Инициализируем общее подключение к MongoDB
    # Обязательно указываем uuidRepresentation для корректной работы UUID
    db_client = MongoClient(settings.MONGO_URI, uuidRepresentation="standard")

    # 2. Очищаем коллекцию перед тестом, чтобы видеть чистый результат
    db_client[settings.MONGO_DB]["notifications"].delete_many({})

    # 3. Создаем конкретные инфраструктурные адаптеры
    db_repository = MongoNotificationRepository(db_client, settings.MONGO_DB)
    email_adapter = AWSSESEmailAdapter(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_region=settings.AWS_REGION,
        sender_email=settings.AWS_SES_SENDER
    )

    # 4. Создаем Use Case и внедряем в него наши адаптеры
    use_case = ProcessResetPasswordUseCase(
        db_client=db_client,
        db_name=settings.MONGO_DB,
        db_repository=db_repository,
        email_adapter=email_adapter
    )

    # 5. Имитируем прилет валидного сообщения из RabbitMQ
    mock_data = {
        "id": str(uuid4()),
        "userId": "user_innowise_student",
        "emailAddress": "student@innowise.com",  # EmailStr сам проверит этот адрес!
        "subject": "Сброс пароля",
        "body": "Ссылка на восстановление доступа: https://example.com/reset",
        "publishedAt": datetime.now(UTC).isoformat(),
    }

    # Создаем доменную модель (если email битый — упадет прямо здесь)
    message = ResetPasswordMessage(**mock_data)

    # 6. Запускаем сценарий на выполнение
    print("🚩 Передаем сообщение в Use Case...")
    try:
        use_case.execute(message)
    except Exception as e:
        print(f"\n⚠️ Главный поток поймал ошибку сценария: {e}")

    # 7. Делаем проверку базы данных на наличие мусора
    saved_doc = db_client[settings.MONGO_DB]["notifications"].find_one({"id": message.id})
    print("\n🔍 РЕЗУЛЬТАТ ПРОВЕРКИ БАЗЫ ДАННЫХ:")
    if saved_doc:
        print("❌ ОШИБКА: Документ сохранился в базе данных! Атомарность нарушена.")
    else:
        print(
            "✅ УСПЕХ: В базе данных пусто! Настоящий адаптер AWS SES упал из-за неверных ключей, и Use Case успешно откатил транзакцию в MongoDB!")


if __name__ == "__main__":
    run_application()