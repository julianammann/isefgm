"""Foreign-access check (Q-01) that every account-bound resource reuses.

README rule 5: an endpoint is not done without a test "account B accesses a resource of
account A -> 404".
"""

from httpx import AsyncClient, Cookies
from sqlalchemy.ext.asyncio import AsyncSession

from tests.accounts import log_in_new_user

# Methods on an item URL. Parametrize foreign-access tests with them, so every endpoint is
# its own test case (QZ-06: authorization tests per endpoint). Pass a subset for resources
# that do not offer all of them.
ITEM_METHODS = ("GET", "PUT", "DELETE")


async def assert_invisible_to_other_account(
    client: AsyncClient,
    session: AsyncSession,
    *,
    method: str,
    collection: str,
    item_id: str,
    replacement: dict[str, object],
) -> None:
    """Assert that another account gets 404 for `method` on the item and cannot list it."""
    url = f"{collection}/{item_id}"
    snapshot = await client.get(url)
    assert snapshot.status_code == 200

    owner_cookies = Cookies(client.cookies)

    await log_in_new_user(client, session, "peter@example.com")

    r = await client.request(method, url, json=replacement if method == "PUT" else None)
    assert r.status_code == 404
    assert r.json()["title"] == "Not Found"

    listed = (await client.get(collection)).json()
    assert item_id not in [item["id"] for item in listed["items"]]
    assert listed["total"] == len(listed["items"])

    # Back as the owner: the stranger's request changed nothing.
    client.cookies = owner_cookies
    after = await client.get(url)
    assert after.status_code == 200
    assert after.json() == snapshot.json()
