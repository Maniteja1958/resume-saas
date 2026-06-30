from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

_memory_analyses: dict[str, dict[str, Any]] = {}
_memory_events: dict[str, list[dict[str, Any]]] = {}
_mongo_client = None
_mongo_available: bool | None = None
_lock = asyncio.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_mongo_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


async def init_storage() -> None:
    """Try MongoDB; fall back to in-memory if Mongo is unavailable."""
    global _mongo_client, _mongo_available
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        _mongo_client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=1200)
        await _mongo_client.admin.command("ping")
        db = _mongo_client[settings.MONGODB_DB]
        await db.analyses.create_index("analysis_id", unique=True)
        await db.analyses.create_index([("resume_hash", 1), ("created_at", -1)])
        await db.analyses.create_index("created_at")
        await db.analysis_events.create_index([("analysis_id", 1), ("created_at", 1)])
        _mongo_available = True
        print("[storage] MongoDB connected")
    except Exception as exc:
        _mongo_available = False
        print(f"[storage] MongoDB unavailable, using in-memory store: {exc}")


def mongo_enabled() -> bool:
    return bool(_mongo_available and _mongo_client is not None)


def _db():
    if not mongo_enabled():
        return None
    return _mongo_client[settings.MONGODB_DB]


async def save_analysis(doc: dict[str, Any]) -> dict[str, Any]:
    doc = dict(doc)
    doc.setdefault("created_at", now_iso())
    doc["updated_at"] = now_iso()

    if mongo_enabled():
        await _db().analyses.replace_one({"analysis_id": doc["analysis_id"]}, doc, upsert=True)
    async with _lock:
        _memory_analyses[doc["analysis_id"]] = doc
    return doc


async def update_analysis(analysis_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    current = await get_analysis(analysis_id)
    if not current:
        return None
    current.update(patch)
    current["updated_at"] = now_iso()
    return await save_analysis(current)


async def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    if mongo_enabled():
        doc = await _db().analyses.find_one({"analysis_id": analysis_id})
        if doc:
            return _clean_mongo_doc(doc)
    async with _lock:
        doc = _memory_analyses.get(analysis_id)
        return dict(doc) if doc else None


async def list_history(limit: int = 20, offset: int = 0, resume_hash: str | None = None, top_role: str | None = None) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if resume_hash:
        query["resume_hash"] = resume_hash
    if top_role:
        query["scores.top_role"] = top_role

    if mongo_enabled():
        cursor = _db().analyses.find(query).sort("created_at", -1).skip(offset).limit(limit)
        docs = [_clean_mongo_doc(doc) async for doc in cursor]
        total = await _db().analyses.count_documents(query)
    else:
        async with _lock:
            docs = list(_memory_analyses.values())
        if resume_hash:
            docs = [d for d in docs if d.get("resume_hash") == resume_hash]
        if top_role:
            docs = [d for d in docs if d.get("scores", {}).get("top_role") == top_role]
        docs.sort(key=lambda d: d.get("created_at", ""), reverse=True)
        total = len(docs)
        docs = docs[offset : offset + limit]

    items = []
    for doc in docs:
        scores = doc.get("scores", {})
        items.append(
            {
                "analysis_id": doc.get("analysis_id"),
                "created_at": doc.get("created_at"),
                "filename": doc.get("filename"),
                "resume_hash": doc.get("resume_hash"),
                "top_role": scores.get("top_role"),
                "top_role_match": scores.get("top_role_match"),
                "ats_score": scores.get("ats_score"),
                "gap_count": scores.get("gap_count"),
                "semantic_similarity": scores.get("semantic_similarity"),
                "status": doc.get("status"),
            }
        )
    return {"items": items, "total": total}


async def save_event(analysis_id: str, event: dict[str, Any]) -> None:
    event = dict(event)
    event.setdefault("analysis_id", analysis_id)
    event.setdefault("created_at", now_iso())
    if mongo_enabled():
        await _db().analysis_events.insert_one(event)
    async with _lock:
        _memory_events.setdefault(analysis_id, []).append(event)


async def list_events(analysis_id: str) -> list[dict[str, Any]]:
    if mongo_enabled():
        cursor = _db().analysis_events.find({"analysis_id": analysis_id}).sort("created_at", 1)
        return [_clean_mongo_doc(doc) async for doc in cursor]
    async with _lock:
        return list(_memory_events.get(analysis_id, []))
