# Configuration
## AWS credentials for SQS
Use `aws configure` to set access key and secret

## Environment
Required env vars:
- LOG_LEVEL (default: "INFO")
- DB_URL (default: "sqlite+aiosqlite:///adimen_test_db")
- SQS_QUEUE_URL
- USER_EMAIL - Optional. If set along with password, then user will be created on start
- USER_PASSWORD

`load_dotenv()` is used, so can create `.env` file inside `app` directory.  
Example:
```
SQS_QUEUE_URL="https://sqs.eu-central-1.amazonaws.com/1234566790/adimen_queue.fifo "
USER_EMAIL="test@api.com"
USER_PASSWORD="123"
```

# Init database
`PYTHONPATH=$(pwd)/app alembic upgrade head`

# Run
```
poetry shell
python app/main.py
```

# Test
`PYTHONPATH=$(pwd)/app pytest`