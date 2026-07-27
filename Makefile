# Load environment variables
-include .env
export

# Phony targets definition
.PHONY: up down lint format fix db-init test

# Start docker services
up:
	docker compose up -d

# Stop docker services
down:
	docker compose down

# Run Ruff linter via uv
lint:
	uv run ruff check .

# Format code style via uv
format:
	uv run ruff format .

# Auto-fix code style issues via uv
fix:
	uv run ruff check . --fix

# Initialize MongoDB replica set
db-init:
	-docker exec -it notification_mongodb mongosh -u $(MONGO_ROOT_USER) -p $(MONGO_ROOT_PASSWORD) --authenticationDatabase admin --eval 'rs.initiate({_id: "rs0", members: [{_id: 0, host: "localhost:27017"}]})'

# Run integration tests worker via uv
test:
	uv run python -m src.main