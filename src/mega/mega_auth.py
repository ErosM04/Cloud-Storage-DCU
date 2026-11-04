import getpass
import os
import sys
from mega import Mega


def authenticate_mega():
    """
    Prompts the user for MEGA credentials in the terminal and logs in.
    Can also read MEGA_EMAIL and MEGA_PASSWORD environment variables if set.
    """
    print("\n🔐 --- MEGA Authentication ---")
    
    # Allow reading from environment variables if set
    email = os.environ.get("MEGA_EMAIL")
    password = os.environ.get("MEGA_PASSWORD")
    
    if not email:
        email = input("Enter MEGA email: ").strip()
    else:
        print(f"Using MEGA email from environment variable: {email}")

    if not password:
        password = getpass.getpass("Enter MEGA password: ").strip()
    else:
        print("Using MEGA password from environment variable.")

    if not email or not password:
        print("❌ Error: MEGA email and password cannot be empty.")
        sys.exit(1)

    print("\n⏳ Logging in to MEGA...")
    mega = Mega()
    try:
        m = mega.login(email, password)
        print("👤 MEGA Login performed successfully!\n")
        return m
    except Exception as e:
        print(f"❌ Failed to login to MEGA: {e}")
        print("Please check your email and password and try again.")
        sys.exit(1)
