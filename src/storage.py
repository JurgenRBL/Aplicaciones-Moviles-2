"""SQLite y evidencias privadas, sin servicios externos."""
import math
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

CATEGORIES = ("Mascota perdida", "Mascota encontrada", "Avistamiento", "Animal en riesgo", "Otro")
PRIORITIES = ("Baja", "Media", "Alta")


class Storage:
    def __init__(self, root):
        self.root = Path(root)
        self.media = self.root / "evidencias"
        self.media.mkdir(parents=True, exist_ok=True)
        self.database = self.root / "incidentes.sqlite3"
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY, category TEXT NOT NULL, description TEXT NOT NULL,
                created TEXT NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL,
                priority TEXT NOT NULL, photo TEXT, video TEXT, audio TEXT)""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(incidents)")}
            for column in ("pet_name", "species", "landmark"):
                if column not in columns:
                    db.execute(f"ALTER TABLE incidents ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def attach(self, source, kind):
        source = Path(source)
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError("La captura no generó un archivo válido.")
        target = self.media / (uuid.uuid4().hex + (source.suffix or {"photo": ".jpg", "video": ".mp4", "audio": ".m4a"}[kind]))
        shutil.copyfile(source, target)
        return str(target)

    def save(self, category, description, coordinates, priority, evidence, pet_name="", species="", landmark=""):
        if category not in CATEGORIES or priority not in PRIORITIES:
            raise ValueError("Selecciona categoría y prioridad válidas.")
        if not description.strip() or len(description.strip()) > 2000:
            raise ValueError("Escribe una descripción de 1 a 2000 caracteres.")
        if coordinates is None:
            raise ValueError("Obtén tu ubicación o selecciona un punto en el mapa.")
        lat, lon = coordinates
        if not all(math.isfinite(n) for n in (lat, lon)) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Coordenadas inválidas.")
        for path in evidence.values():
            if path and (not Path(path).is_file() or not Path(path).is_relative_to(self.media)):
                raise ValueError("La evidencia no está disponible en el almacenamiento local.")
        identifier = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("""INSERT INTO incidents
                (id,category,description,created,latitude,longitude,priority,photo,video,audio,pet_name,species,landmark)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                identifier, category, description.strip(), datetime.now().astimezone().isoformat(timespec="seconds"),
                lat, lon, priority, evidence.get("photo"), evidence.get("video"), evidence.get("audio"),
                pet_name.strip()[:100], species.strip()[:40], landmark.strip()[:200]))
        return identifier

    def all(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM incidents ORDER BY created DESC, rowid DESC")]
