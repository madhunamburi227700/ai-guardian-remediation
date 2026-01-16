import os
from dotenv import load_dotenv

load_dotenv()


# Stuff from the .env file comes here
# Add more things here
class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")  # The PostgreSQL connection string
    REMEDIATION_AGENT = os.getenv("REMEDIATION_AGENT", "claude_code")
    CLAUDE_CODE_MODEL = os.getenv("CLAUDE_CODE_MODEL", "claude-sonnet-4-20250514")
    SEND_EMAIL_NOTIFICATIONS = (
        os.getenv("SEND_EMAIL_NOTIFICATIONS", "false").lower() == "true"
    )
    DB_ENABLED = os.getenv("DB_ENABLED", "false").lower() == "true"


print(f"Using Claude model: {Settings.CLAUDE_CODE_MODEL}")
print(f"Database enabled: {Settings.DB_ENABLED}")


settings = Settings()
