import webbrowser

from google_auth_oauthlib.flow import InstalledAppFlow

from recruitment.config import get_settings


def main() -> None:
    settings = get_settings()
    if not settings.gmail_client_secret_file:
        raise RuntimeError("GMAIL_CLIENT_SECRET_FILE is not configured")
    if not settings.gmail_token_file:
        raise RuntimeError("GMAIL_TOKEN_FILE is not configured")

    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    flow = InstalledAppFlow.from_client_secrets_file(
        str(settings.gmail_client_secret_file), scopes
    )
    oauth_port = 8765
    flow.redirect_uri = f"http://localhost:{oauth_port}/"
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    url_path = settings.gmail_token_file.parent / "gmail_oauth_url.txt"
    url_path.parent.mkdir(parents=True, exist_ok=True)
    url_path.write_text(authorization_url, encoding="utf-8")
    print("\nOpen this URL in your browser to approve Gmail access:\n")
    print(authorization_url)
    print(f"\nThe same URL was written to: {url_path}\n")
    webbrowser.open(authorization_url)

    credentials = flow.run_local_server(
        port=oauth_port,
        open_browser=False,
        authorization_prompt_message="",
        success_message=(
            "Gmail approval is complete. You can close this browser tab and return to NSJ Recruitment."
        ),
    )
    settings.gmail_token_file.parent.mkdir(parents=True, exist_ok=True)
    settings.gmail_token_file.write_text(credentials.to_json(), encoding="utf-8")
    print("Gmail OAuth token is configured.")


if __name__ == "__main__":
    main()
