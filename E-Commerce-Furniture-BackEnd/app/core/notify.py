"""Real-time notifications.

`notify()` stores a notification for one user and immediately pushes it to every browser tab that user
has open (Server-Sent Events, see routes/notification.py). Pushing is in-memory, so it works when the API
runs as one process (the Render default); with several workers the front end's periodic refresh still
delivers the notification within a few seconds.
"""
import asyncio
import logging
from collections import defaultdict
from typing import Dict, Optional, Set

from sqlalchemy.orm import Session

from app.schema.notification import Notification

log = logging.getLogger("notify")

_subscribers: Dict[int, Set[asyncio.Queue]] = defaultdict(set)
_loop: Optional[asyncio.AbstractEventLoop] = None


def bind_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def subscribe(user_id: int) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers[user_id].add(q)
    return q


def unsubscribe(user_id: int, q: asyncio.Queue) -> None:
    _subscribers[user_id].discard(q)
    if not _subscribers[user_id]:
        _subscribers.pop(user_id, None)


def to_dict(n: Notification) -> dict:
    return {
        "id": n.id,
        "kind": n.kind,
        "title": n.title,
        "message": n.message,
        "link": n.link,
        "is_read": bool(n.is_read),
        "created_at": n.created_at.isoformat() + "Z" if n.created_at else None,
    }


def _push(user_id: int, payload: dict) -> None:
    queues = list(_subscribers.get(user_id, ()))
    if not queues or _loop is None:
        return
    for q in queues:
        def put(q=q):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass
        _loop.call_soon_threadsafe(put)           # route handlers run in a worker thread


def notify(db: Session, user_id: Optional[int], kind: str, title: str, message: str, link: Optional[str] = None) -> Optional[Notification]:
    """Save + push. Never raises: a notification problem must not undo the owner's action."""
    if not user_id:
        return None
    try:
        n = Notification(user_id=user_id, kind=kind, title=title[:150], message=message[:500], link=link)
        db.add(n)
        db.commit()
        db.refresh(n)
        _push(user_id, {"type": "notification", "notification": to_dict(n)})
        return n
    except Exception:
        db.rollback()
        log.exception("Could not create a notification for user %s", user_id)
        return None
