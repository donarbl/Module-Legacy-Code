import datetime

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from data.connection import db_cursor
from data.users import User


@dataclass
class Bloom:
    id: int
    sender: User
    content: str
    sent_timestamp: datetime.datetime
    original_bloom_id: Optional[int] = None
    original_sender: Optional[User] = None
    rebloom_count: int = 0

MAX_BLOOM_LENGTH = 280 # this is to ensure the extra safety

def add_bloom(*, sender: User, content: str) -> Bloom:
    if len(content) > MAX_BLOOM_LENGTH:
        raise ValueError(f"blooms content is too long(max {MAX_BLOOM_LENGTH})")

    hashtags = [word[1:] for word in content.split(" ") if word.startswith("#")]

    now = datetime.datetime.now(tz=datetime.UTC)

    with db_cursor() as cur:
        # Let the database generate the id
        cur.execute(
            """
            INSERT INTO blooms (sender_id, content, send_timestamp)
            VALUES (%(sender_id)s, %(content)s, %(timestamp)s)
            RETURNING id
            """,
            dict(
                sender_id=sender.id,
                content=content,
                timestamp=now,
            ),
        )
        bloom_id = cur.fetchone()[0]

        for hashtag in hashtags:
            cur.execute(
                "INSERT INTO hashtags (hashtag, bloom_id) VALUES (%(hashtag)s, %(bloom_id)s)",
                dict(hashtag=hashtag, bloom_id=bloom_id),
            )

    return Bloom(
        id=bloom_id,
        sender=sender.username,
        content=content,
        sent_timestamp=now,
    )

def add_rebloom(*, rebloomer: User, original_bloom: Bloom) -> Bloom:
    now = datetime.datetime.now(tz=datetime.UTC)

    with db_cursor() as cur:
        # Insert rebloom without id, DB generates it
        cur.execute(
            """
            INSERT INTO blooms (
                sender_id, content, send_timestamp, original_bloom_id
            )
            VALUES (
                %(sender_id)s, %(content)s, %(timestamp)s, %(original_bloom_id)s
            )
            RETURNING id
            """,
            dict(
                sender_id=rebloomer.id,
                content=original_bloom.content,
                timestamp=now,
                original_bloom_id=original_bloom.id,
            ),
        )
        new_id = cur.fetchone()[0]

        # Increase rebloom_count on the original
        cur.execute(
            """
            UPDATE blooms
            SET rebloom_count = COALESCE(rebloom_count, 0) + 1
            WHERE id = %(id)s
            """,
            dict(id=original_bloom.id),
        )

    return Bloom(
        id=new_id,
        sender=rebloomer.username,
        content=original_bloom.content,
        sent_timestamp=now,
        original_bloom_id=original_bloom.id,
        original_sender=original_bloom.sender,
        rebloom_count=(original_bloom.rebloom_count or 0) + 1,
    )



def get_blooms_for_user(
    username: str, *, before: Optional[int] = None, limit: Optional[int] = None
) -> List[Bloom]:
    with db_cursor() as cur:
        kwargs = {
            "sender_username": username,
        }
        if before is not None:
            before_clause = "AND send_timestamp < %(before_limit)s"
            kwargs["before_limit"] = before
        else:
            before_clause = ""

        limit_clause = make_limit_clause(limit, kwargs)

        cur.execute(
            f"""SELECT
              blooms.id, users.username, content, send_timestamp
            FROM
              blooms INNER JOIN users ON users.id = blooms.sender_id
            WHERE
              username = %(sender_username)s
              {before_clause}
            ORDER BY send_timestamp DESC
            {limit_clause}
            """,
            kwargs,
        )
        rows = cur.fetchall()
        blooms = []
        for row in rows:
            bloom_id, sender_username, content, timestamp = row
            blooms.append(
                Bloom(
                    id=bloom_id,
                    sender=sender_username,
                    content=content,
                    sent_timestamp=timestamp,
                )
            )
    return blooms


def get_bloom(bloom_id: int) -> Optional[Bloom]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT blooms.id, users.username, content, send_timestamp FROM blooms INNER JOIN users ON users.id = blooms.sender_id WHERE blooms.id = %s",
            (bloom_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        bloom_id, sender_username, content, timestamp = row
        return Bloom(
            id=bloom_id,
            sender=sender_username,
            content=content,
            sent_timestamp=timestamp,
        )


def get_blooms_with_hashtag(
    hashtag_without_leading_hash: str, *, limit: int = None
) -> List[Bloom]:
    kwargs = {
        "hashtag_without_leading_hash": hashtag_without_leading_hash,
    }
    limit_clause = make_limit_clause(limit, kwargs)
    with db_cursor() as cur:
        cur.execute(
            f"""SELECT
              blooms.id, users.username, content, send_timestamp
            FROM
              blooms INNER JOIN hashtags ON blooms.id = hashtags.bloom_id INNER JOIN users ON blooms.sender_id = users.id
            WHERE
              hashtag = %(hashtag_without_leading_hash)s
            ORDER BY send_timestamp DESC
            {limit_clause}
            """,
            kwargs,
        )
        rows = cur.fetchall()
        blooms = []
        for row in rows:
            bloom_id, sender_username, content, timestamp = row
            blooms.append(
                Bloom(
                    id=bloom_id,
                    sender=sender_username,
                    content=content,
                    sent_timestamp=timestamp,
                )
            )
    return blooms


def make_limit_clause(limit: Optional[int], kwargs: Dict[Any, Any]) -> str:
    if limit is not None:
        limit_clause = "LIMIT %(limit)s"
        kwargs["limit"] = limit
    else:
        limit_clause = ""
    return limit_clause
