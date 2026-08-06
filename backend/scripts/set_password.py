"""Prints a bcrypt hash for WEB_AUTH_PASSWORD_HASH. Run once, paste the output
into .env — there's no signup flow, this is the only account that will ever exist.

    uv run scripts/set_password.py "your password"
"""

import sys

from passlib.context import CryptContext

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: set_password.py <password>")
        sys.exit(1)
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    print(ctx.hash(sys.argv[1]))
