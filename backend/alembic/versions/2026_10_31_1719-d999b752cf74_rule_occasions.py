"""rule occasions

Every account has the rule occasions Geburtstag, Weihnachten and Ostern exactly once: rows of
the system types without a date, because their date follows a rule (#132). This migration

- adds the system type Ostern;
- lets occasion.date be NULL, but only for the three rule types;
- gives every account the three rule occasions;
- folds the occasions of the types Geburtstag and Weihnachten into the rule occasion of the
  same account and type: giftings and gift ideas move over, the old occasions go. Own
  occasions without these types stay, whatever their name.

The downgrade is best effort: one birthday occasion per person with a birthday again, a
birthday gifting with exactly one recipient who has a birthday moves to that recipient's
birthday, other giftings at a rule birthday or at Ostern lose their occasion, Weihnachten
keeps the date 24.12. of the current year, and Ostern goes.

Revision ID: d999b752cf74
Revises: da408c6d1db0
Create Date: 2026-10-31 17:19:41.492070

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d999b752cf74"
down_revision: str | Sequence[str] | None = "da408c6d1db0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The ids are part of the data, not of the code: the same values as in models/occasion.py.
BIRTHDAY_TYPE_ID = uuid.UUID("01a107a9-211b-7486-a304-d5d673618f5b")
CHRISTMAS_TYPE_ID = uuid.UUID("01a107a9-211b-7486-a304-d5d72f070565")
EASTER_TYPE_ID = uuid.UUID("01a192b1-5746-70d6-84f1-1c759ffbdf91")
RULE_NAMES = {
    BIRTHDAY_TYPE_ID: "Geburtstag",
    CHRISTMAS_TYPE_ID: "Weihnachten",
    EASTER_TYPE_ID: "Ostern",
}
PARAMS = {"birthday": BIRTHDAY_TYPE_ID, "christmas": CHRISTMAS_TYPE_ID, "easter": EASTER_TYPE_ID}

# (before, after) of every comment this migration changes.
TYPE_COMMENT = (
    (
        "Kind of occasion (F-03). owner_id NULL marks the system-wide types Geburtstag and "
        "Weihnachten, created by a migration and read-only for users."
    ),
    (
        "Kind of occasion (F-03). owner_id NULL marks the system-wide types Geburtstag, "
        "Weihnachten and Ostern, created by migrations and read-only for users."
    ),
)
OCCASION_COMMENT = (
    (
        "Occasion of an account (F-03). Stores the rule (date and recurrence); a concrete year is "
        "stored where the occasion is used. Visible only to its owner (Q-01)."
    ),
    (
        "Occasion of an account (F-03). Stores the rule (date and recurrence); a concrete year is "
        "stored where the occasion is used. Every account has the rule occasions Geburtstag, "
        "Weihnachten and Ostern exactly once, without a date. Visible only to its owner (Q-01)."
    ),
)
DATE_COMMENT = (
    "Date as a plain calendar date (Q-08). First occurrence for yearly ones.",
    (
        "Date as a plain calendar date (Q-08). First occurrence for yearly ones. NULL only for a "
        "rule occasion, whose date follows its rule."
    ),
)
GIFTING_OCCASION_COMMENT = (
    (
        "Same reasoning as gift_id: the API answers 409 when an occasion in use is deleted "
        "(directly or as a derived birthday), the cascade only runs for F-17."
    ),
    (
        "Same reasoning as gift_id: the API answers 409 when an occasion in use is deleted, the "
        "cascade only runs for F-17."
    ),
)

occasion_type = sa.table(
    "occasion_type",
    sa.column("id", sa.Uuid()),
    sa.column("owner_id", sa.Uuid()),
    sa.column("name", sa.String()),
    sa.column("default_recurrence", sa.String()),
)
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


def _set_comments(index: int) -> None:
    """Set the comments before (0) or after (1) this migration."""
    op.create_table_comment(
        "occasion_type", TYPE_COMMENT[index], existing_comment=TYPE_COMMENT[1 - index]
    )
    op.create_table_comment(
        "occasion", OCCASION_COMMENT[index], existing_comment=OCCASION_COMMENT[1 - index]
    )
    op.alter_column(
        "gifting",
        "occasion_id",
        existing_type=sa.Uuid(),
        existing_nullable=True,
        comment=GIFTING_OCCASION_COMMENT[index],
        existing_comment=GIFTING_OCCASION_COMMENT[1 - index],
    )


def upgrade() -> None:
    """Give every account the rule occasions and fold the old birthdays and Christmases in."""
    bind = op.get_bind()
    op.bulk_insert(
        occasion_type,
        [
            {
                "id": EASTER_TYPE_ID,
                "owner_id": None,
                "name": "Ostern",
                "default_recurrence": "yearly",
            }
        ],
    )
    op.alter_column(
        "occasion",
        "date",
        existing_type=sa.Date(),
        nullable=True,
        comment=DATE_COMMENT[1],
        existing_comment=DATE_COMMENT[0],
    )
    _set_comments(1)

    owner_ids = bind.execute(sa.text("SELECT id FROM user_account")).scalars().all()
    rules = [
        {
            "id": uuid.uuid7(),
            "owner_id": owner_id,
            "occasion_type_id": type_id,
            "name": name,
            "date": None,
            "recurrence": "yearly",
        }
        for owner_id in owner_ids
        for type_id, name in RULE_NAMES.items()
    ]
    if rules:
        op.bulk_insert(occasion, rules)

    # old: an occasion of the type Geburtstag or Weihnachten from before; rule: the rule
    # occasion of the same account and type that replaces it.
    bind.execute(
        sa.text(
            "UPDATE gifting SET occasion_id = rule.id FROM occasion old, occasion rule "
            "WHERE gifting.occasion_id = old.id "
            "AND old.occasion_type_id IN (:birthday, :christmas) AND old.date IS NOT NULL "
            "AND rule.owner_id = old.owner_id AND rule.occasion_type_id = old.occasion_type_id "
            "AND rule.date IS NULL"
        ),
        PARAMS,
    )
    # An idea linked to several birthdays gets one link to the rule birthday.
    bind.execute(
        sa.text(
            "INSERT INTO gift_occasion (gift_id, occasion_id) "
            "SELECT link.gift_id, rule.id FROM gift_occasion link, occasion old, occasion rule "
            "WHERE link.occasion_id = old.id "
            "AND old.occasion_type_id IN (:birthday, :christmas) AND old.date IS NOT NULL "
            "AND rule.owner_id = old.owner_id AND rule.occasion_type_id = old.occasion_type_id "
            "AND rule.date IS NULL "
            "ON CONFLICT DO NOTHING"
        ),
        PARAMS,
    )
    # Their person_occasion and gift_occasion rows go with them (ON DELETE CASCADE).
    bind.execute(
        sa.text(
            "DELETE FROM occasion "
            "WHERE occasion_type_id IN (:birthday, :christmas) AND date IS NOT NULL"
        ),
        PARAMS,
    )

    op.create_check_constraint(
        op.f("ck_occasion_date_only_null_for_rules"),
        "occasion",
        # IS NOT NULL: a NULL type would make IN NULL, which a CHECK lets pass.
        "date IS NOT NULL OR (occasion_type_id IS NOT NULL AND occasion_type_id IN "
        f"('{BIRTHDAY_TYPE_ID}', '{CHRISTMAS_TYPE_ID}', '{EASTER_TYPE_ID}'))",
    )
    op.create_index(
        "uq_occasion_owner_rule_type",
        "occasion",
        ["owner_id", "occasion_type_id"],
        unique=True,
        postgresql_where=sa.text("date IS NULL"),
    )


def downgrade() -> None:
    """Best effort: birthdays per person again, Weihnachten with a date, Ostern gone."""
    bind = op.get_bind()
    people = bind.execute(
        sa.text("SELECT id, owner_id, name, birthday FROM person WHERE birthday IS NOT NULL")
    )
    birthdays: list[dict[str, object]] = []
    links: list[dict[str, object]] = []
    for person_id, owner_id, name, birthday in people:
        occasion_id = uuid.uuid7()
        birthdays.append(
            {
                "id": occasion_id,
                "owner_id": owner_id,
                "occasion_type_id": BIRTHDAY_TYPE_ID,
                # Same rule as before this migration: the name column holds 100 characters.
                "name": f"Geburtstag {name}"[:100],
                "date": birthday,
                "recurrence": "yearly",
            }
        )
        links.append({"person_id": person_id, "occasion_id": occasion_id})
    if birthdays:
        op.bulk_insert(occasion, birthdays)
        op.bulk_insert(person_occasion, links)

    # Of the birthday occasions, only the ones created above are linked to a person.
    bind.execute(
        sa.text(
            "UPDATE gifting SET occasion_id = birthday.id "
            "FROM occasion rule, gifting_person recipient, person_occasion link, "
            "occasion birthday "
            "WHERE gifting.occasion_id = rule.id "
            "AND rule.occasion_type_id = :birthday AND rule.date IS NULL "
            "AND recipient.gifting_id = gifting.id AND link.person_id = recipient.person_id "
            "AND birthday.id = link.occasion_id AND birthday.occasion_type_id = :birthday "
            "AND (SELECT count(*) FROM gifting_person other "
            "WHERE other.gifting_id = gifting.id) = 1"
        ),
        PARAMS,
    )
    bind.execute(
        sa.text(
            "UPDATE gifting SET occasion_id = NULL FROM occasion rule "
            "WHERE gifting.occasion_id = rule.id "
            "AND rule.occasion_type_id = :birthday AND rule.date IS NULL"
        ),
        PARAMS,
    )
    # Their gift_occasion rows go with them (ON DELETE CASCADE).
    bind.execute(
        sa.text("DELETE FROM occasion WHERE occasion_type_id = :birthday AND date IS NULL"),
        PARAMS,
    )
    bind.execute(
        sa.text(
            "UPDATE occasion SET date = make_date(EXTRACT(YEAR FROM CURRENT_DATE)::int, 12, 24) "
            "WHERE occasion_type_id = :christmas AND date IS NULL"
        ),
        PARAMS,
    )
    bind.execute(
        sa.text(
            "UPDATE gifting SET occasion_id = NULL "
            "WHERE occasion_id IN (SELECT id FROM occasion WHERE occasion_type_id = :easter)"
        ),
        PARAMS,
    )
    bind.execute(sa.text("DELETE FROM occasion WHERE occasion_type_id = :easter"), PARAMS)
    bind.execute(sa.text("DELETE FROM occasion_type WHERE id = :easter"), PARAMS)

    op.drop_index(
        "uq_occasion_owner_rule_type",
        table_name="occasion",
        postgresql_where=sa.text("date IS NULL"),
    )
    op.drop_constraint(op.f("ck_occasion_date_only_null_for_rules"), "occasion", type_="check")
    _set_comments(0)
    op.alter_column(
        "occasion",
        "date",
        existing_type=sa.Date(),
        nullable=False,
        comment=DATE_COMMENT[0],
        existing_comment=DATE_COMMENT[1],
    )
