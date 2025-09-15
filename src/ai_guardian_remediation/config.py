import os
from dotenv import load_dotenv

load_dotenv()


# Stuff from the .env file comes here
# Add more things here
class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")  # The PostgreSQL connection string
    REMEDIATION_AGENT = os.getenv("REMEDIATION_AGENT", "claude_code")


settings = Settings()
