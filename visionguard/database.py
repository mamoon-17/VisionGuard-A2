"""A persistent prediction audit trail, shared by SQLite and PostgreSQL."""
from datetime import datetime, timezone

from sqlalchemy import (Column, DateTime, Float, Integer, MetaData, String,
                        Table, create_engine, insert, select, text)
from sqlalchemy.pool import StaticPool

metadata = MetaData()
history = Table("prediction_history", metadata,
                Column("id", Integer, primary_key=True),
                Column("created_at", DateTime(timezone=True), nullable=False),
                Column("filename", String(255), nullable=False),
                Column("content_sha256", String(64)),
                Column("label", String(32)), Column("confidence", Float),
                Column("probability_ai", Float), Column("model_version", String(255)),
                Column("latency_ms", Float), Column("status", String(32), nullable=False),
                Column("detail", String(255)))


class Database:
    def __init__(self, url):
        options = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            options["connect_args"] = {"check_same_thread": False}
            if ":memory:" in url:
                options["poolclass"] = StaticPool
        self.engine = create_engine(url, **options)
        metadata.create_all(self.engine)

    def record(self, filename, status, detail="", digest=None, result=None, latency_ms=None):
        result = result or {}
        with self.engine.begin() as connection:
            connection.execute(insert(history).values(
                created_at=datetime.now(timezone.utc), filename=filename, status=status,
                detail=detail[:255], content_sha256=digest, latency_ms=latency_ms,
                label=result.get("label"), confidence=result.get("confidence"),
                probability_ai=result.get("probability_ai"), model_version=result.get("model_version")))

    def recent(self, limit=100):
        with self.engine.connect() as connection:
            return list(connection.execute(select(history).order_by(history.c.id.desc()).limit(limit)).mappings())

    def healthy(self):
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
