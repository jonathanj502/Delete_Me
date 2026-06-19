from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_PATH = _PROJECT_ROOT / "credentials.json"
TOKEN_PATH = _PROJECT_ROOT / "output" / "token.json"


def _handle_oauth_error(exc: Exception) -> None:
    msg = str(exc).lower()
    if "access_denied" in msg:
        raise RuntimeError(
            "OAuth authorization was denied (Error 403: access_denied).\n\n"
            "You need to add your Google account as a test user:\n"
            "  1. Go to https://console.cloud.google.com and select your project\n"
            "  2. APIs & Services → OAuth consent screen → Audience tab\n"
            "  3. Under 'Test users' → click 'Add Users'\n"
            "  4. Enter your Gmail address and click Save\n"
            "  5. Re-run the scanner\n"
        ) from exc
    if "invalid_client" in msg:
        raise RuntimeError(
            "Invalid OAuth client (Error: invalid_client).\n\n"
            "Your credentials.json may be corrupted or for the wrong project.\n"
            "  1. Go to https://console.cloud.google.com → APIs & Services → Credentials\n"
            "  2. Delete the existing OAuth client and create a new Desktop app client\n"
            "  3. Download the new credentials.json and replace the existing file\n"
        ) from exc
    raise RuntimeError(f"OAuth authorization failed: {exc}") from exc


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
            print("Stored token is corrupted — deleting and re-authenticating...")
            token_path.unlink(missing_ok=True)
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            print("Stored token has expired — re-authenticating...")
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
        try:
            creds = flow.run_local_server(port=0)
        except Exception as exc:
            _handle_oauth_error(exc)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds
