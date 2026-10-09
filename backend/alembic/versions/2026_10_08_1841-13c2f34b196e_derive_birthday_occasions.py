"""derive birthday occasions

From now on person.birthday is the only source of a birthday, and the service keeps one
occasion of the type Geburtstag per person in line with it (F-03, F-04). This migration does
the same for the rows that exist already:

- every person with a birthday gets the birthday occasion, linked to the person;
- occasions of the type Geburtstag made by hand lose the type, so they stay editable.

The downgrade deletes the derived occasions. It cannot tell which occasions had the type
before, so those keep no type.

Revision ID: 13c2f34b196e
Revises: cbd3c5c4acbd
Create Date: 2026-10-08 18:41:54.604953

"""

import uuid
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "13c2f34b196e"
down_revision: str | Sequence[str] | None = "cbd3c5c4acbd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The ids are part of the data, not of the code: copied from the migration that created them.
BIRTHDAY_TYPE_ID = uuid.UUID("01a107a9-211b-7486-a304-d5d673618f5b")

occasion = sa.table(
    "occasion",
    sa.column("id", sa.Uuid()),
    sa.column("owner_id", sa.Uuid()),
    sa.column("occasion_type_id", sa.Uuid()),
    sa.column("name", sa.String()),
    sa.column("date", sa.Date()),
    sa.column("recurrence", sa.String()),
)
person_occasion = sa.table(
    "person_occasion",
    sa.column("person_id", sa.Uuid()),
    sa.column("occasion_id", sa.Uuid()),
)


def upgrade() -> None:
    """Derive the birthday occasions of existing people."""
    op.execute(
        occasion.update()
        .where(occasion.c.occasion_type_id == BIRTHDAY_TYPE_ID)
        .values(occasion_type_id=None)
    )
    people = op.get_bind().execute(
        sa.text("SELECT id, owner_id, name, birthday FROM person WHERE birthday IS NOT NULL")
    )
    occasions: list[dict[str, object]] = []
    links: list[dict[str, object]] = []
    for person_id, owner_id, name, birthday in people:
        occasion_id = uuid.uuid7()
        occasions.append(
            {
                "id": occasion_id,
                "owner_id": owner_id,
                "occasion_type_id": BIRTHDAY_TYPE_ID,
                # Same rule as services/occasion.py: the name column holds 100 characters.
                "name": f"Geburtstag {name}"[:100],
                "date": birthday,
                "recurrence": "yearly",
            }
        )
        links.append({"person_id": person_id, "occasion_id": occasion_id})
    if occasions:
        op.bulk_insert(occasion, occasions)
        op.bulk_insert(person_occasion, links)


def downgrade() -> None:
    """Delete the derived birthday occasions; their links go with them (ON DELETE CASCADE)."""
    op.execute(occasion.delete().where(occasion.c.occasion_type_id == BIRTHDAY_TYPE_ID))
