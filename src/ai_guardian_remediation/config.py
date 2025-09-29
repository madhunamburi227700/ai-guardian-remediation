import os
from dotenv import load_dotenv

load_dotenv()


# Stuff from the .env file comes here
# Add more things here
class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")  # The PostgreSQL connection string
    REMEDIATION_AGENT = os.getenv("REMEDIATION_AGENT", "claude_code")
    CLAUDE_CODE_MODEL = os.getenv("CLAUDE_CODE_MODEL", "claude")


print(f"Using Claude model: {Settings.CLAUDE_CODE_MODEL}")


settings = Settings()
