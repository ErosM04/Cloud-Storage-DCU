import os
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes required for downloading from Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']  # Add '.readonly' for read only permission


def get_project_root():
    """Returns the absolute path to the project root directory."""
    # src/drive/drive_auth.py -> src/drive -> src -> project root
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_credentials_file():
    """Locates credentials.json or credential.json in the project root, current directory, or src."""
    project_root = get_project_root()
    search_paths = [
        os.path.join(project_root, 'credentials.json'),
        os.path.join(project_root, 'credential.json'),
        os.path.join(os.getcwd(), 'credentials.json'),
        os.path.join(os.getcwd(), 'credential.json'),
        os.path.join(project_root, 'src', 'credentials.json'),
        os.path.join(project_root, 'src', 'credential.json'),
        os.path.join(project_root, 'src', 'drive', 'credentials.json'),
        os.path.join(project_root, 'src', 'drive', 'credential.json'),
    ]
    for path in search_paths:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    return None


def find_token_file():
    """Locates existing token.json in project root or current working directory."""
    project_root = get_project_root()
    search_paths = [
        os.path.join(project_root, 'token.json'),
        os.path.join(os.getcwd(), 'token.json'),
    ]
    for path in search_paths:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    return None


def prompt_for_credentials():
    """
    Informs the user that the credentials file is missing and prompts them to add it.
    Allows retrying once the file is placed, or exiting cleanly.
    """
    project_root = get_project_root()
    expected_path = os.path.join(project_root, 'credentials.json')

    print("\n⚠️ --- Google Drive Credentials Required ---")
    print("No 'credentials.json' (or 'credential.json') file was found in the project folder:")
    print(f"  Expected location: {expected_path}\n")
    print("How to get this file:")
    print("  1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print("  2. Enable 'Google Drive API' (APIs & Services > Library)")
    print("  3. Configure the Consent Screen (if necessary) under APIs & Services > Credentials")
    print("  4. Create an OAuth client ID (Application type: 'Desktop app') under APIs & Services > Credentials")
    print("  5. Download the JSON file, rename it to 'credentials.json', and place it in the project root folder.")
    print("  6. In the project's panel go to Google Auth Platoform > Public and add your email to the Test users.\n")

    while True:
        try:
            choice = input(f"Place 'credentials.json' in '{project_root}' and press Enter to retry (or 'q' to quit): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(1)

        if choice.lower() in ['q', 'quit', 'exit']:
            print("Operation cancelled by user.")
            sys.exit(1)

        creds_path = find_credentials_file()
        if creds_path:
            print(f"✅ Credentials file found: {os.path.basename(creds_path)}\n")
            return creds_path
        else:
            print(f"❌ File not found yet. Please ensure 'credentials.json' is saved in '{project_root}'.")


def authenticate_gdrive():
    """Handles Google Drive OAuth2 authentication."""
    creds = None
    token_path = find_token_file()

    # token.json stores the user's access and refresh tokens
    if token_path:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If there are no valid credentials, prompt the user to log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_path = find_credentials_file()
            if not creds_path:
                creds_path = prompt_for_credentials()

            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run in the project root
        project_root = get_project_root()
        save_token_path = os.path.join(project_root, 'token.json')
        with open(save_token_path, 'w', encoding='utf-8') as token_file:
            token_file.write(creds.to_json())
    
    print("\n👤 Login performed successfully")

    return creds
