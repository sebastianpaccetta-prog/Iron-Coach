"""Central configuration for Iron Coach. Tweak race date and paths here."""
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RACE_DATE = date(2027, 2, 1)
RACE_NAME = "Half Ironman 70.3"
ATHLETE_NAME = "Sebastian"

DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "normalized.db"

# Export folders. The loader tolerates dated folder names (strava_export_9.15.2025 etc.)
# by scanning these candidates in order and picking the first that exists.
STRAVA_DIR_CANDIDATES = [DATA_DIR / "strava"] + sorted(ROOT.glob("strava_export_*"))
APPLE_HEALTH_DIR_CANDIDATES = [DATA_DIR / "apple_health"] + sorted(ROOT.glob("apple_health_export_*"))

SITE_DATA_PATH = ROOT / "site" / "public" / "data.json"
PLAN_OUTPUT_PATH = DATA_DIR / "plan.json"

GOOGLE_CREDENTIALS_PATH = ROOT / "credentials.json"
GOOGLE_TOKEN_PATH = ROOT / "token.json"
CALENDAR_NAME = "Iron Coach"


def find_dir(candidates):
    for c in candidates:
        if c.is_dir():
            return c
    return None
