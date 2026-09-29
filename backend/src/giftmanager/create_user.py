"""Create an account from the command line, also while registration is closed.

Usage: ``python -m giftmanager.create_user --email anna@example.org --display-name Anna``,
locally via ``mise run create-user -- ...``, on a server via
``docker compose exec api python -m giftmanager.create_user ...``. The password is
prompted for, so it never ends up in the shell history or the process list.
"""

import argparse
import asyncio
import getpass
import sys

from pydantic import ValidationError

from giftmanager.core.db import get_engine, get_sessionmaker
from giftmanager.core.errors import ConflictError
from giftmanager.models import User
from giftmanager.schemas.auth import RegisterIn
from giftmanager.services import auth as auth_service


async def _create(data: RegisterIn) -> User:
    try:
        async with get_sessionmaker()() as session, session.begin():
            return await auth_service.register(
                session, email=data.email, password=data.password, display_name=data.display_name
            )
    finally:
        await get_engine().dispose()


def main(argv: list[str] | None = None) -> int:
    """Prompt for the password, create the account and return the exit code."""
    parser = argparse.ArgumentParser(prog="python -m giftmanager.create_user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args(argv)

    password = getpass.getpass("Password: ")
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    try:
        data = RegisterIn(email=args.email, password=password, display_name=args.display_name)
    except ValidationError as exc:
        for error in exc.errors():
            print(f"{error['loc'][0]}: {error['msg']}", file=sys.stderr)
        return 1

    try:
        user = asyncio.run(_create(data))
    except ConflictError as exc:
        print(f"{exc.detail}.", file=sys.stderr)
        return 1
    print(f"Created account {user.email} ({user.id}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
