import datetime

from dataclasses import dataclass, field
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
    original_sender: Optional[str] = None
    rebloom_count: int = 0


def add_bloom(*, sender: User, content: str) -> Bloom:
    hashtags = [word[1:] for word in content.split(" ") if word.startswith("#")]

    now = datetime.datetime.now(tz=datetime.UTC)
    bloom_id = int(now.timestamp() * 1000000)
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO blooms (id, sender_id, content, send_timestamp) VALUES (%(bloom_id)s, %(sender_id)s, %(content)s, %(timestamp)s)",
            dict(
                bloom_id=bloom_id,
                sender_id=sender.id,
                content=content,
                timestamp=datetime.datetime.now(datetime.UTC),
            ),
        )
        for hashtag in hashtags:
            cur.execute(
                "INSERT INTO hashtags (hashtag, bloom_id) VALUES (%(hashtag)s, %(bloom_id)s)",
                dict(hashtag=hashtag, bloom_id=bloom_id),
            )


def add_rebloom(*, sender: User, original_bloom_id: int) -> Bloom:
    """Create a rebloom of an existing bloom."""
    original = get_bloom(original_bloom_id)
    if original is None:
        raise ValueError(f"Bloom {original_bloom_id} not found")

    now = datetime.datetime.now(tz=datetime.UTC)
    bloom_id = int(now.timestamp() * 1000000)

    with db_cursor() as cur:
        # Insert the rebloom
        cur.execute(
            """INSERT INTO blooms 
               (id, sender_id, content, send_timestamp, original_bloom_id, original_sender_id)
               VALUES (%(bloom_id)s, %(sender_id)s, %(content)s, %(timestamp)s, %(original_bloom_id)s, %(original_sender_id)s)""",
            dict(
                bloom_id=bloom_id,
                sender_id=sender.id,
                content=original.content,
                timestamp=now,
                original_bloom_id=original_bloom_id,
                original_sender_id=original.sender_id,
            ),
        )
        # Increment rebloom count on original
        cur.execute(
            "UPDATE blooms SET rebloom_count = rebloom_count + 1 WHERE id = %(id)s",
            dict(id=original_bloom_id),
        )


def get_blooms_for_user(
    username: str, *, before: Optional[int] = None, limit: Optional[int] = None
) -> List[Bloom]:
    with db_cursor() as cur:
        kwargs = {
            "sender_username": username,
        }
        if before is not None:
            before_clause = "AND blooms.send_timestamp < %(before_limit)s"
            kwargs["before_limit"] = before
        else:
            before_clause = ""

        limit_clause = make_limit_clause(limit, kwargs)

        cur.execute(
            f"""SELECT
              blooms.id, users.username, blooms.content, blooms.send_timestamp,
              blooms.original_bloom_id, original_senders.username, blooms.rebloom_count
            FROM
              blooms 
              INNER JOIN users ON users.id = blooms.sender_id
              LEFT JOIN users AS original_senders ON original_senders.id = blooms.original_sender_id
            WHERE
              users.username = %(sender_username)s
              {before_clause}
            ORDER BY blooms.send_timestamp DESC
            {limit_clause}
            """,
            kwargs,
        )
        rows = cur.fetchall()
        blooms = []
        for row in rows:
            bloom_id, sender_username, content, timestamp, original_bloom_id, original_sender, rebloom_count = row
            blooms.append(
                Bloom(
                    id=bloom_id,
                    sender=sender_username,
                    content=content,
                    sent_timestamp=timestamp,
                    original_bloom_id=original_bloom_id,
                    original_sender=original_sender,
                    rebloom_count=rebloom_count or 0,
                )
            )
    return blooms


def get_bloom(bloom_id: int) -> Optional[Bloom]:
    with db_cursor() as cur:
        cur.execute(
            """SELECT blooms.id, users.username, users.id, blooms.content, blooms.send_timestamp,
               blooms.original_bloom_id, original_senders.username, blooms.rebloom_count
               FROM blooms 
               INNER JOIN users ON users.id = blooms.sender_id
               LEFT JOIN users AS original_senders ON original_senders.id = blooms.original_sender_id
               WHERE blooms.id = %s""",
            (bloom_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        bloom_id, sender_username, sender_id, content, timestamp, original_bloom_id, original_sender, rebloom_count = row
        bloom = Bloom(
            id=bloom_id,
            sender=sender_username,
            content=content,
            sent_timestamp=timestamp,
            original_bloom_id=original_bloom_id,
            original_sender=original_sender,
            rebloom_count=rebloom_count or 0,
        )
        bloom.sender_id = sender_id
        return bloom


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
              blooms.id, users.username, blooms.content, blooms.send_timestamp,
              blooms.original_bloom_id, original_senders.username, blooms.rebloom_count
            FROM
              blooms 
              INNER JOIN hashtags ON blooms.id = hashtags.bloom_id 
              INNER JOIN users ON blooms.sender_id = users.id
              LEFT JOIN users AS original_senders ON original_senders.id = blooms.original_sender_id
            WHERE
              hashtag = %(hashtag_without_leading_hash)s
            ORDER BY blooms.send_timestamp DESC
            {limit_clause}
            """,
            kwargs,
        )
        rows = cur.fetchall()
        blooms = []
        for row in rows:
            bloom_id, sender_username, content, timestamp, original_bloom_id, original_sender, rebloom_count = row
            blooms.append(
                Bloom(
                    id=bloom_id,
                    sender=sender_username,
                    content=content,
                    sent_timestamp=timestamp,
                    original_bloom_id=original_bloom_id,
                    original_sender=original_sender,
                    rebloom_count=rebloom_count or 0,
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