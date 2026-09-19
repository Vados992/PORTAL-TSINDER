"""Transactional SQLite records, content hashes, audit chain and portable bundles.

Hashes detect corruption against a retained head; they are not signatures or
protection against a database administrator rewriting the entire history.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import threading
import uuid
import zipfile
from .contracts import canonical, digest, strict_json, code_fingerprint


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.executescript((Path(__file__).parent/"data/schema.sql").read_text())

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.lock, self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def _artifact(self, db, data):
        content = canonical(data)
        sha = hashlib.sha256(content).hexdigest()
        db.execute("INSERT OR IGNORE INTO artifacts VALUES (?,?,?)", (sha, content, "application/json"))
        return sha

    def _event(self, db, kind, payload):
        previous = db.execute("SELECT sha256 FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        previous = previous[0] if previous else "0"*64
        timestamp, body = now(), canonical(payload).decode()
        sha = digest({"created_at": timestamp, "kind": kind, "payload": payload, "previous_sha": previous})
        db.execute("INSERT INTO events(created_at,kind,payload,previous_sha,sha256) VALUES (?,?,?,?,?)",
                   (timestamp, kind, body, previous, sha))
        return sha

    def event(self, kind, payload):
        with self.transaction() as db:
            return self._event(db, kind, payload)

    def save_run(self, kind, inputs, result):
        fingerprint = code_fingerprint()
        ident = uuid.uuid4().hex
        with self.transaction() as db:
            input_sha = self._artifact(db, inputs)
            result_sha = self._artifact(db, result)
            code_sha = self._artifact(db, fingerprint)
            db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?)", (ident, kind, now(), input_sha, result_sha, code_sha))
            self._event(db, "RUN_CREATED", {"run_id": ident, "input_sha": input_sha,
                                          "result_sha": result_sha, "code_sha": code_sha})
        return self.get_run(ident)

    def get_run(self, ident):
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (ident,)).fetchone()
            if row is None:
                raise KeyError(ident)
            result = dict(row)
            for name, col in [("inputs", "input_sha"), ("result", "result_sha"), ("code", "code_sha")]:
                content = db.execute("SELECT content FROM artifacts WHERE sha256=?", (row[col],)).fetchone()
                if content is None or hashlib.sha256(content[0]).hexdigest() != row[col]:
                    raise ValueError("artifact integrity failure")
                result[name] = strict_json(content[0])
            return result

    def runs(self, limit=100):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))]

    def events(self, limit=100):
        with self.connect() as db:
            return [{**dict(r), "payload": strict_json(r["payload"])} for r in
                    db.execute("SELECT * FROM events ORDER BY seq DESC LIMIT ?", (limit,))]

    def get_state(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
            return strict_json(row[0]) if row else default

    def set_state(self, key, value, event_kind):
        with self.transaction() as db:
            db.execute("INSERT INTO state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       (key, canonical(value).decode()))
            self._event(db, event_kind, {"key": key, "value": value})

    def append_telemetry(self, session_id, segment, frames):
        with self.transaction() as db:
            sha = self._artifact(db, {"session_id": session_id, "segment": segment, "frames": frames})
            db.execute("INSERT INTO telemetry_segments VALUES (?,?,?)", (session_id, segment, sha))
            self._event(db, "TELEMETRY_CHECKPOINT", {"session_id": session_id, "segment": segment, "artifact_sha": sha})

    def telemetry(self, session_id):
        frames = []
        with self.connect() as db:
            for row in db.execute("SELECT a.sha256,a.content FROM telemetry_segments t JOIN artifacts a "
                                  "ON a.sha256=t.artifact_sha WHERE session_id=? ORDER BY segment", (session_id,)):
                if hashlib.sha256(row["content"]).hexdigest() != row["sha256"]:
                    raise ValueError("telemetry integrity failure")
                frames.extend(strict_json(row["content"])["frames"])
        return frames

    def verify(self, expected_head=None):
        errors, previous, seq = [], "0"*64, 0
        # One read transaction: writers cannot change the snapshot halfway through.
        with self.connect() as db:
            db.execute("BEGIN")
            for row in db.execute("SELECT * FROM events ORDER BY seq"):
                body = {"created_at": row["created_at"], "kind": row["kind"],
                        "payload": strict_json(row["payload"]), "previous_sha": previous}
                if row["previous_sha"] != previous or digest(body) != row["sha256"] or row["seq"] != seq+1:
                    errors.append(f"audit chain mismatch at {row['seq']}")
                previous, seq = row["sha256"], row["seq"]
            for row in db.execute("SELECT * FROM artifacts"):
                if hashlib.sha256(row["content"]).hexdigest() != row["sha256"]:
                    errors.append(f"artifact mismatch {row['sha256']}")
            for row in db.execute("SELECT * FROM runs"):
                for key in ("input_sha", "result_sha", "code_sha"):
                    if not db.execute("SELECT 1 FROM artifacts WHERE sha256=?", (row[key],)).fetchone():
                        errors.append(f"missing run artifact {row['id']}:{key}")
        if expected_head is not None and previous != expected_head:
            errors.append("retained audit head does not match")
        return {"status": "PASS" if not errors else "FAIL", "errors": errors,
                "events_checked": seq, "head_sha256": previous}

    def export(self, ident):
        run = self.get_run(ident)
        files = {"run.json": canonical(run), "inputs.json": canonical(run["inputs"]),
                 "result.json": canonical(run["result"]), "code-fingerprint.json": canonical(run["code"])}
        manifest = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
            archive.writestr("manifest.json", canonical(manifest))
        return out.getvalue()


def verify_bundle(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or sum(i.file_size for i in z.infolist()) > 20_000_000:
            raise ValueError("duplicate/oversized bundle")
        manifest = strict_json(z.read("manifest.json"))
        if set(names) != set(manifest) | {"manifest.json"}:
            raise ValueError("bundle membership mismatch")
        return all(hashlib.sha256(z.read(name)).hexdigest() == sha for name, sha in manifest.items())
