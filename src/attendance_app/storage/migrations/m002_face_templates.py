VERSION = 2
NAME = 'face_templates'
STATEMENTS = (
    """CREATE TABLE face_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
        embedding BLOB NOT NULL CHECK(length(embedding)=512),
        dimensions INTEGER NOT NULL CHECK(dimensions=128),
        dtype TEXT NOT NULL CHECK(dtype='<f4'),
        model_id TEXT NOT NULL CHECK(length(model_id)>0),
        alignment_id TEXT NOT NULL CHECK(length(alignment_id)>0),
        created_at TEXT NOT NULL
    )""",
    'CREATE INDEX idx_face_templates_person ON face_templates(person_id)',
)
