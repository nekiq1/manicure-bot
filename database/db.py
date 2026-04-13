import aiosqlite
from datetime import datetime
from typing import Optional, List, Tuple

from config import DB_PATH


class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.path)
            await self._conn.execute("PRAGMA foreign_keys = ON;")
            await self._conn.commit()
            await self._create_tables()

    async def _create_tables(self):
        # Пользователи
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                name TEXT,
                phone TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT
            )
            """
        )

        # Рабочие дни
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS work_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                is_open INTEGER DEFAULT 1
            )
            """
        )

        # Слоты времени
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_id INTEGER NOT NULL,
                time TEXT NOT NULL,
                is_available INTEGER DEFAULT 1,
                FOREIGN KEY(day_id) REFERENCES work_days(id) ON DELETE CASCADE
            )
            """
        )

        # Записи
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                slot_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT,
                appointment_dt TEXT,
                reminder_scheduled INTEGER DEFAULT 0,
                reminder_job_id TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(slot_id) REFERENCES time_slots(id) ON DELETE CASCADE
            )
            """
        )

        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def get_or_create_user(
        self,
        tg_id: int,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        is_admin: int = 0,
    ) -> int:
        cur = await self._conn.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        await cur.close()
        if row:
            user_id = row[0]
            if name or phone:
                await self._conn.execute(
                    "UPDATE users SET name = COALESCE(?, name), phone = COALESCE(?, phone) WHERE id = ?",
                    (name, phone, user_id),
                )
                await self._conn.commit()
            return user_id
        created_at = datetime.now().isoformat()
        await self._conn.execute(
            "INSERT INTO users (tg_id, name, phone, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
            (tg_id, name, phone, is_admin, created_at),
        )
        await self._conn.commit()
        cur = await self._conn.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        await cur.close()
        return row[0]

    async def has_active_booking(self, tg_id: int) -> bool:
        query = """
        SELECT b.id
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        WHERE u.tg_id = ? AND b.status = 'active'
        """
        cur = await self._conn.execute(query, (tg_id,))
        row = await cur.fetchone()
        await cur.close()
        return row is not None

    async def get_active_booking_by_tg(self, tg_id: int):
        query = """
        SELECT b.id, w.date, t.time, b.appointment_dt
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        JOIN time_slots t ON t.id = b.slot_id
        JOIN work_days w ON w.id = t.day_id
        WHERE u.tg_id = ? AND b.status = 'active'
        """
        cur = await self._conn.execute(query, (tg_id,))
        row = await cur.fetchone()
        await cur.close()
        return row

    async def add_work_day(self, date_str: str) -> int:
        await self._conn.execute(
            "INSERT OR IGNORE INTO work_days (date, is_open) VALUES (?, 1)",
            (date_str,),
        )
        await self._conn.commit()
        cur = await self._conn.execute(
            "SELECT id FROM work_days WHERE date = ?", (date_str,)
        )
        row = await cur.fetchone()
        await cur.close()
        return row[0]

    async def close_work_day(self, date_str: str):
        await self._conn.execute(
            "UPDATE work_days SET is_open = 0 WHERE date = ?", (date_str,)
        )
        await self._conn.execute(
            """
            UPDATE time_slots
            SET is_available = 0
            WHERE day_id = (SELECT id FROM work_days WHERE date = ?)
            """,
            (date_str,),
        )
        await self._conn.commit()

    async def add_time_slot(self, date_str: str, time_str: str):
        day_id = await self.add_work_day(date_str)
        await self._conn.execute(
            """
            INSERT OR IGNORE INTO time_slots (day_id, time, is_available)
            VALUES (?, ?, 1)
            """,
            (day_id, time_str),
        )
        await self._conn.commit()

    async def delete_time_slot(self, date_str: str, time_str: str) -> bool:
        query = """
        DELETE FROM time_slots
        WHERE id IN (
            SELECT t.id
            FROM time_slots t
            JOIN work_days w ON w.id = t.day_id
            WHERE w.date = ? AND t.time = ?
        )
        """
        cur = await self._conn.execute(query, (date_str, time_str))
        await self._conn.commit()
        deleted = cur.rowcount > 0
        await cur.close()
        return deleted

    async def get_available_slots_for_date(
        self, date_str: str
    ) -> List[Tuple[int, str]]:
        query = """
        SELECT t.id, t.time
        FROM time_slots t
        JOIN work_days w ON w.id = t.day_id
        WHERE w.date = ? AND w.is_open = 1 AND t.is_available = 1
        ORDER BY t.time
        """
        cur = await self._conn.execute(query, (date_str,))
        rows = await cur.fetchall()
        await cur.close()
        return rows

    async def mark_slot_unavailable(self, slot_id: int):
        await self._conn.execute(
            "UPDATE time_slots SET is_available = 0 WHERE id = ?", (slot_id,)
        )
        await self._conn.commit()

    async def mark_slot_available(self, slot_id: int):
        await self._conn.execute(
            "UPDATE time_slots SET is_available = 1 WHERE id = ?", (slot_id,)
        )
        await self._conn.commit()

    async def get_slot_info(self, slot_id: int):
        query = """
        SELECT t.id, w.date, t.time
        FROM time_slots t
        JOIN work_days w ON w.id = t.day_id
        WHERE t.id = ?
        """
        cur = await self._conn.execute(query, (slot_id,))
        row = await cur.fetchone()
        await cur.close()
        return row

    async def create_booking(
        self,
        tg_id: int,
        name: str,
        phone: str,
        slot_id: int,
        appointment_dt: datetime,
    ) -> int:
        user_id = await self.get_or_create_user(tg_id, name, phone)
        created_at = datetime.now().isoformat()
        await self._conn.execute(
            """
            INSERT INTO bookings (user_id, slot_id, status, created_at, appointment_dt, reminder_scheduled)
            VALUES (?, ?, 'active', ?, ?, 0)
            """,
            (user_id, slot_id, created_at, appointment_dt.isoformat()),
        )
        await self._conn.commit()
        cur = await self._conn.execute("SELECT last_insert_rowid()")
        row = await cur.fetchone()
        await cur.close()
        return row[0]

    async def set_booking_reminder(self, booking_id: int, job_id: Optional[str]):
        if job_id:
            await self._conn.execute(
                """
                UPDATE bookings
                SET reminder_scheduled = 1, reminder_job_id = ?
                WHERE id = ?
                """,
                (job_id, booking_id),
            )
        else:
            await self._conn.execute(
                """
                UPDATE bookings
                SET reminder_scheduled = 0, reminder_job_id = NULL
                WHERE id = ?
                """,
                (booking_id,),
            )
        await self._conn.commit()

    async def cancel_booking(self, booking_id: int):
        await self._conn.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,)
        )
        await self._conn.commit()

    async def get_booking_by_id(self, booking_id: int):
        query = """
        SELECT b.id, u.tg_id, u.name, u.phone, w.date, t.time,
               b.appointment_dt, b.reminder_scheduled, b.reminder_job_id
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        JOIN time_slots t ON t.id = b.slot_id
        JOIN work_days w ON w.id = t.day_id
        WHERE b.id = ?
        """
        cur = await self._conn.execute(query, (booking_id,))
        row = await cur.fetchone()
        await cur.close()
        return row

    async def get_future_bookings_with_reminders(self):
        query = """
        SELECT b.id, u.tg_id, b.appointment_dt, b.reminder_job_id
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        WHERE b.status = 'active'
          AND b.reminder_scheduled = 1
        """
        cur = await self._conn.execute(query)
        rows = await cur.fetchall()
        await cur.close()
        return rows

    async def get_schedule_for_date(
        self, date_str: str
    ) -> List[Tuple[str, str, str]]:
        query = """
        SELECT t.time,
               COALESCE(u.name, ''),
               b.status
        FROM time_slots t
        JOIN work_days w ON w.id = t.day_id
        LEFT JOIN bookings b ON b.slot_id = t.id AND b.status = 'active'
        LEFT JOIN users u ON u.id = b.user_id
        WHERE w.date = ?
        ORDER BY t.time
        """
        cur = await self._conn.execute(query, (date_str,))
        rows = await cur.fetchall()
        await cur.close()
        return rows


db = Database(DB_PATH)

