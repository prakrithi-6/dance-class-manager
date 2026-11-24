import os
import sqlite3

# Put the database file next to this code file
DB_PATH = os.path.join(os.path.dirname(__file__), "dance_school.db")


def get_connection():
    """Open a connection to the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # lets us read columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    """Create all tables if they don't exist yet (safe to run many times)."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS batches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            day         TEXT,
            time        TEXT,
            monthly_fee REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS students (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            phone        TEXT,
            batch_id     INTEGER,
            joining_date TEXT,
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            batch_id   INTEGER NOT NULL,
            date       TEXT NOT NULL,
            present    INTEGER NOT NULL,
            UNIQUE (student_id, batch_id, date),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            amount     REAL NOT NULL,
            paid_on    TEXT NOT NULL,
            for_month  TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        );
    """)
    conn.commit()
    conn.close()


# ---------- Batches (only a helper for now; full page comes in Step 2) ----------

def get_all_batches():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM batches ORDER BY name").fetchall()
    conn.close()
    return rows


# ---------- Students ----------

def add_student(name, phone, batch_id, joining_date):
    conn = get_connection()
    conn.execute(
        "INSERT INTO students (name, phone, batch_id, joining_date) VALUES (?, ?, ?, ?)",
        (name, phone, batch_id, joining_date),
    )
    conn.commit()
    conn.close()


def update_student(student_id, name, phone, batch_id, joining_date):
    conn = get_connection()
    conn.execute(
        "UPDATE students SET name=?, phone=?, batch_id=?, joining_date=? WHERE id=?",
        (name, phone, batch_id, joining_date, student_id),
    )
    conn.commit()
    conn.close()


def get_all_students():
    """Return every student along with their batch name."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.id, s.name, s.phone, s.batch_id,
               b.name AS batch, s.joining_date
        FROM students s
        LEFT JOIN batches b ON s.batch_id = b.id
        ORDER BY s.name
    """).fetchall()
    conn.close()
    return rows

# ---------- Batches ----------

def add_batch(name, day, time, monthly_fee):
    conn = get_connection()
    conn.execute(
        "INSERT INTO batches (name, day, time, monthly_fee) VALUES (?, ?, ?, ?)",
        (name, day, time, monthly_fee),
    )
    conn.commit()
    conn.close()


def update_batch(batch_id, name, day, time, monthly_fee):
    conn = get_connection()
    conn.execute(
        "UPDATE batches SET name=?, day=?, time=?, monthly_fee=? WHERE id=?",
        (name, day, time, monthly_fee, batch_id),
    )
    conn.commit()
    conn.close()


def get_batches_with_counts():
    """Every batch along with how many students are in it."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT b.id, b.name, b.day, b.time, b.monthly_fee,
               COUNT(s.id) AS student_count
        FROM batches b
        LEFT JOIN students s ON s.batch_id = b.id
        GROUP BY b.id
        ORDER BY b.name
    """).fetchall()
    conn.close()
    return rows

def delete_batch(batch_id):
    """Delete a batch only if it is safe. Returns (True/False, message)."""
    conn = get_connection()
    students = conn.execute(
        "SELECT COUNT(*) FROM students WHERE batch_id = ?", (batch_id,)
    ).fetchone()[0]
    records = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE batch_id = ?", (batch_id,)
    ).fetchone()[0]

    if students > 0:
        conn.close()
        return False, (f"This batch still has {students} student(s). "
                       "Move them to another batch on the Students page first.")
    if records > 0:
        conn.close()
        return False, "This batch has attendance records, so it cannot be deleted."

    conn.execute("DELETE FROM batches WHERE id = ?", (batch_id,))
    conn.commit()
    conn.close()
    return True, "Batch deleted."

# ---------- Attendance ----------

def get_students_in_batch(batch_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name FROM students WHERE batch_id = ? ORDER BY name",
        (batch_id,),
    ).fetchall()
    conn.close()
    return rows


def get_attendance(batch_id, date):
    """Return {student_id: 1 or 0} for a batch on a date (empty if not marked yet)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT student_id, present FROM attendance WHERE batch_id = ? AND date = ?",
        (batch_id, date),
    ).fetchall()
    conn.close()
    return {r["student_id"]: r["present"] for r in rows}


def save_attendance(batch_id, date, records):
    """records is a list of (student_id, present). Saves new or updates old."""
    conn = get_connection()
    for student_id, present in records:
        conn.execute(
            """INSERT INTO attendance (student_id, batch_id, date, present)
               VALUES (?, ?, ?, ?)
               ON CONFLICT (student_id, batch_id, date)
               DO UPDATE SET present = excluded.present""",
            (student_id, batch_id, date, 1 if present else 0),
        )
    conn.commit()
    conn.close()


def get_attendance_summary(batch_id):
    """For each student in a batch: classes marked and classes attended."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.id, s.name,
               COUNT(a.id) AS total,
               COALESCE(SUM(a.present), 0) AS attended
        FROM students s
        LEFT JOIN attendance a
               ON a.student_id = s.id AND a.batch_id = s.batch_id
        WHERE s.batch_id = ?
        GROUP BY s.id
        ORDER BY s.name
    """, (batch_id,)).fetchall()
    conn.close()
    return rows

# ---------- Fees ----------

def add_payment(student_id, amount, paid_on, for_month):
    conn = get_connection()
    conn.execute(
        "INSERT INTO payments (student_id, amount, paid_on, for_month) VALUES (?, ?, ?, ?)",
        (student_id, amount, paid_on, for_month),
    )
    conn.commit()
    conn.close()


def get_payments():
    """All payments, newest first, with the student's name."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.id, s.name, p.amount, p.paid_on, p.for_month
        FROM payments p
        JOIN students s ON s.id = p.student_id
        ORDER BY p.paid_on DESC, p.id DESC
    """).fetchall()
    conn.close()
    return rows


def delete_payment(payment_id):
    conn = get_connection()
    conn.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()


def get_fee_status():
    """Every student with their batch fee and the total they have paid so far."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.id, s.name, s.phone, s.joining_date,
               b.name AS batch,
               COALESCE(b.monthly_fee, 0) AS monthly_fee,
               COALESCE((SELECT SUM(p.amount) FROM payments p
                         WHERE p.student_id = s.id), 0) AS total_paid
        FROM students s
        LEFT JOIN batches b ON s.batch_id = b.id
        ORDER BY s.name
    """).fetchall()
    conn.close()
    return rows