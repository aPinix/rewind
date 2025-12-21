import sqlite3
from collections import namedtuple
import numpy as np
import json
from typing import Any, List, Optional, Tuple

from openrelife.config import db_path

# Define the structure of a database entry using namedtuple
Entry = namedtuple("Entry", ["id", "app", "title", "text", "timestamp", "embedding", "words_coords", "ai_text", "ai_words_coords"])


def create_db() -> None:
    """
    Creates the SQLite database and the 'entries' table if they don't exist.

    The table schema includes columns for an auto-incrementing ID, application name,
    window title, extracted text, timestamp, and text embedding.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS entries (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       app TEXT,
                       title TEXT,
                       text TEXT,
                       timestamp INTEGER UNIQUE,
                       embedding BLOB,
                       words_coords TEXT,
                       ai_text TEXT,
                       ai_words_coords TEXT
                   )"""
            )
            # Add index on timestamp for faster lookups
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON entries (timestamp)"
            )
            
            # Migration: Add words_coords column if it doesn't exist
            cursor.execute("PRAGMA table_info(entries)")
            columns = [column[1] for column in cursor.fetchall()]
            if "words_coords" not in columns:
                cursor.execute("ALTER TABLE entries ADD COLUMN words_coords TEXT DEFAULT '[]'")
            if "ai_text" not in columns:
                cursor.execute("ALTER TABLE entries ADD COLUMN ai_text TEXT")
            if "ai_words_coords" not in columns:
                cursor.execute("ALTER TABLE entries ADD COLUMN ai_words_coords TEXT")
            
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error during table creation: {e}")


def get_all_entries() -> List[Entry]:
    """
    Retrieves all entries from the database.

    Returns:
        List[Entry]: A list of all entries as Entry namedtuples.
                     Returns an empty list if the table is empty or an error occurs.
    """
    entries: List[Entry] = []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
            cursor = conn.cursor()
            cursor.execute("SELECT id, app, title, text, timestamp, embedding, words_coords, ai_text, ai_words_coords FROM entries ORDER BY timestamp DESC")
            results = cursor.fetchall()
            for row in results:
                # Deserialize the embedding blob back into a NumPy array
                embedding = np.frombuffer(row["embedding"], dtype=np.float32)
                words_coords_str = row["words_coords"] if row["words_coords"] else "[]"
                try:
                    words_coords = json.loads(words_coords_str)
                except (json.JSONDecodeError, TypeError):
                    words_coords = []
                
                ai_words_coords_str = row["ai_words_coords"] if row["ai_words_coords"] else "[]"
                try:
                    ai_words_coords = json.loads(ai_words_coords_str)
                except (json.JSONDecodeError, TypeError):
                    ai_words_coords = []
                    
                entries.append(
                    Entry(
                        id=row["id"],
                        app=row["app"],
                        title=row["title"],
                        text=row["text"],
                        timestamp=row["timestamp"],
                        embedding=embedding,
                        words_coords=words_coords,
                        ai_text=row["ai_text"],
                        ai_words_coords=ai_words_coords,
                    )
                )
    except sqlite3.Error as e:
        print(f"Database error while fetching all entries: {e}")
    return entries


def get_timestamps() -> List[int]:
    """
    Retrieves all timestamps from the database, ordered descending.

    Returns:
        List[int]: A list of all timestamps.
                   Returns an empty list if the table is empty or an error occurs.
    """
    timestamps: List[int] = []
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Use the index for potentially faster retrieval
            cursor.execute("SELECT timestamp FROM entries ORDER BY timestamp DESC")
            results = cursor.fetchall()
            timestamps = [result[0] for result in results]
    except sqlite3.Error as e:
        print(f"Database error while fetching timestamps: {e}")
    return timestamps


def update_ai_ocr(timestamp: int, ai_text: str, ai_words_coords: List) -> bool:
    """
    Updates AI OCR data for an existing entry.
    
    Args:
        timestamp (int): The Unix timestamp of the screenshot.
        ai_text (str): The AI-extracted text.
        ai_words_coords (List): List of word coordinates from AI OCR.
    
    Returns:
        bool: True if update was successful, False otherwise.
    """
    ai_words_coords_json: str = json.dumps(ai_words_coords) if ai_words_coords else "[]"
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE entries 
                   SET ai_text = ?, ai_words_coords = ?
                   WHERE timestamp = ?""",
                (ai_text, ai_words_coords_json, timestamp),
            )
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error during AI OCR update: {e}")
        return False


def insert_entry(
    text: str, timestamp: int, embedding: np.ndarray, app: str, title: str, words_coords: List = None
) -> Optional[int]:
    """
    Inserts a new entry into the database.

    Args:
        text (str): The extracted text content.
        timestamp (int): The Unix timestamp of the screenshot.
        embedding (np.ndarray): The embedding vector for the text.
        app (str): The name of the active application.
        title (str): The title of the active window.
        words_coords (List): List of word coordinates from OCR.

    Returns:
        Optional[int]: The ID of the newly inserted row, or None if insertion fails.
                       Prints an error message to stderr on failure.
    """
    embedding_bytes: bytes = embedding.astype(np.float32).tobytes() # Ensure consistent dtype
    words_coords_json: str = json.dumps(words_coords) if words_coords else "[]"
    last_row_id: Optional[int] = None
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO entries (text, timestamp, embedding, app, title, words_coords)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(timestamp) DO NOTHING""", # Avoid duplicates based on timestamp
                (text, timestamp, embedding_bytes, app, title, words_coords_json),
            )
            conn.commit()
            if cursor.rowcount > 0: # Check if insert actually happened
                last_row_id = cursor.lastrowid
            # else:
                # Optionally log that a duplicate timestamp was encountered
                # print(f"Skipped inserting entry with duplicate timestamp: {timestamp}")

    except sqlite3.Error as e:
        # More specific error handling can be added (e.g., IntegrityError for UNIQUE constraint)
        print(f"Database error during insertion: {e}")
    return last_row_id


def delete_entries(timestamps: List[int]) -> int:
    """
    Deletes entries with the specified timestamps from the database.
    
    Args:
        timestamps (List[int]): List of timestamps to delete.
        
    Returns:
        int: Number of deleted entries.
    """
    deleted_count = 0
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(timestamps))
            sql = f"DELETE FROM entries WHERE timestamp IN ({placeholders})"
            cursor.execute(sql, timestamps)
            conn.commit()
            deleted_count = cursor.rowcount
    except sqlite3.Error as e:
        print(f"Database error during deletion: {e}")
    return deleted_count
