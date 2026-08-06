"""Prints a bcrypt hash for WEB_AUTH_PASSWORD_HASH. Run once, paste the output
into .env — there's no signup flow, this is the only account that will ever exist.

    uv run scripts/set_password.py "your password"
"""

import sys

from app.auth import hash_secret

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: set_password.py <password>")
        sys.exit(1)
    print(hash_secret(sys.argv[1]))
