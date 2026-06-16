from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_PATH = _PROJECT_ROOT / "credentials.json"
TOKEN_PATH = _PROJECT_ROOT / "output" / "token.json"


def get_credentials(
    credentials_path: Path = CREDENTIALS_PATH,
    token_path: Path = TOKEN_PATH,
) -> Credentials:
    """Return valid Gmail read-only credentials, refreshing or re-authorizing as needed."""
    creds: Credentials | None = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            creds = None  # corrupted token — fall through to re-auth

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None
        except Exception as exc:
            raise RuntimeError(
                f"Failed to refresh credentials: {exc}\n"
                "If this persists, delete output/token.json and re-authenticate."
            ) from exc

    if not (creds and creds.valid):
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"credentials.json not found at {credentials_path}\n"
                "Run 'python setup_check.py' for setup instructions."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds
