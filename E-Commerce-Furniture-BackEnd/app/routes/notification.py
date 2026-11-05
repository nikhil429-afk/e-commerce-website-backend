import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core import notify as hub
from app.core.database import get_db, LocalSession
from app.core.security import get_current_user, verify_token
from app.schema.notification import Notification
from app.schema.register import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
def list_notifications(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (db.query(Notification).filter(Notification.user_id == user.id)
            .order_by(Notification.id.desc()).limit(limit).all())
    unread = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).count()  # noqa: E712
    return {"items": [hub.to_dict(n) for n in rows], "unread": unread}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).update({"is_read": True})  # noqa: E712
    db.commit()
    return {"message": "All notifications marked as read"}


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return hub.to_dict(n)


@router.delete("")
def clear_all(db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == user.id).delete()
    db.commit()
    return {"message": "All notifications cleared"}


@router.delete("/{notification_id}")
def delete_one(notification_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(n)
    db.commit()
    return {"message": "Notification removed"}


@router.get("/stream")
async def stream(request: Request, token: Optional[str] = Query(None)):
    """Server-Sent Events. The web app sends its login token in the Authorization header; the query-string
    token is only a fallback for clients (like a plain EventSource) that cannot set headers."""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    payload = verify_token(token)
    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    def user_exists() -> bool:
        db = LocalSession()
        try:
            return db.query(User.id).filter(User.id == user_id).first() is not None
        finally:
            db.close()

    if not await asyncio.to_thread(user_exists):
        raise HTTPException(status_code=401, detail="User not found")

    queue = hub.subscribe(user_id)

    async def events():
        try:
            yield "retry: 4000\n\n"
            yield f"data: {json.dumps({'type': 'ready'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"data: {json.dumps(item)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"                 # keeps proxies from closing an idle connection
        finally:
            hub.unsubscribe(user_id, queue)

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })
