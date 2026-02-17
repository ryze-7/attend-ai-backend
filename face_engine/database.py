"""
Database module for managing student data and attendance records.
Handles SQLite operations for face encodings and attendance tracking.
"""

import sqlite3
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from pathlib import Path


class Database:
    """Manages SQLite database operations for attendance system."""
    
    def __init__(self, db_path: str = "attendance.db"):
        """
        Initialize database connection and create tables if needed.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()
    
    def _connect(self) -> None:
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
    
    def _create_tables(self) -> None:
        """Create students and attendance tables if they don't exist."""
        # Students table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_number TEXT UNIQUE NOT NULL,
                face_encoding BLOB NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Attendance table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)
        
        # Create index for faster attendance queries
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attendance_student_timestamp 
            ON attendance(student_id, timestamp)
        """)
        
        self.conn.commit()
    
    def add_student(self, name: str, roll_number: str, face_encoding: np.ndarray) -> bool:
        """
        Add a new student with their face encoding.
        
        Args:
            name: Student's full name
            roll_number: Unique roll number
            face_encoding: 128-dimensional face encoding from face_recognition
            
        Returns:
            True if successful, False if roll number already exists
        """
        try:
            # Serialize numpy array to BLOB
            encoding_blob = pickle.dumps(face_encoding)
            
            self.cursor.execute("""
                INSERT INTO students (name, roll_number, face_encoding)
                VALUES (?, ?, ?)
            """, (name, roll_number, encoding_blob))
            
            self.conn.commit()
            print(f"✓ Added student: {name} ({roll_number})")
            return True
            
        except sqlite3.IntegrityError:
            print(f"✗ Error: Roll number {roll_number} already exists")
            return False
        except Exception as e:
            print(f"✗ Database error: {e}")
            return False
    
    def get_all_students(self) -> List[Tuple[int, str, str, np.ndarray]]:
        """
        Retrieve all students with their face encodings.
        
        Returns:
            List of tuples: (id, name, roll_number, face_encoding)
        """
        self.cursor.execute("""
            SELECT id, name, roll_number, face_encoding
            FROM students
            ORDER BY roll_number
        """)
        
        students = []
        for row in self.cursor.fetchall():
            student_id, name, roll_number, encoding_blob = row
            # Deserialize face encoding
            face_encoding = pickle.loads(encoding_blob)
            students.append((student_id, name, roll_number, face_encoding))
        
        return students
    
    def get_student_by_id(self, student_id: int) -> Optional[Tuple[str, str]]:
        """
        Get student name and roll number by ID.
        
        Args:
            student_id: Student's database ID
            
        Returns:
            Tuple of (name, roll_number) or None if not found
        """
        self.cursor.execute("""
            SELECT name, roll_number
            FROM students
            WHERE id = ?
        """, (student_id,))
        
        result = self.cursor.fetchone()
        return result if result else None
    
    def check_recent_attendance(self, student_id: int, minutes: int = 10) -> bool:
        """
        Check if student has attendance marked in last N minutes.
        
        Args:
            student_id: Student's database ID
            minutes: Time window to check (default 10 minutes)
            
        Returns:
            True if attendance exists in time window, False otherwise
        """
        # Get the most recent attendance for this student
        self.cursor.execute("""
            SELECT timestamp
            FROM attendance
            WHERE student_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (student_id,))
        
        result = self.cursor.fetchone()
        
        if not result:
            return False  # No attendance record exists
        
        last_timestamp_str = result[0]
        
        # Parse the timestamp string from database
        try:
            # SQLite stores as: "2026-02-16 23:42:51"
            last_timestamp = datetime.strptime(last_timestamp_str, "%Y-%m-%d %H:%M:%S")
        except:
            # If parsing fails, assume it's recent to be safe
            return True
        
        # Check if last attendance was within the time window
        time_diff = datetime.now() - last_timestamp
        
        return time_diff.total_seconds() < (minutes * 60)
    
    def mark_attendance(self, student_id: int) -> bool:
        """
        Mark attendance for a student.
        
        Args:
            student_id: Student's database ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use Python's datetime instead of SQLite's CURRENT_TIMESTAMP
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.cursor.execute("""
                INSERT INTO attendance (student_id, timestamp)
                VALUES (?, ?)
            """, (student_id, timestamp))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"✗ Error marking attendance: {e}")
            return False
    
    def get_attendance_today(self) -> List[Tuple[str, str, str]]:
        """
        Get all attendance records for today.
        
        Returns:
            List of tuples: (name, roll_number, timestamp)
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_str = today_start.strftime("%Y-%m-%d %H:%M:%S")
        
        self.cursor.execute("""
            SELECT s.name, s.roll_number, a.timestamp
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.timestamp >= ?
            ORDER BY a.timestamp DESC
        """, (today_start_str,))
        
        return self.cursor.fetchall()
    
    def get_attendance_count_today(self) -> int:
        """
        Get count of unique students with attendance today.
        
        Returns:
            Number of students present today
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_str = today_start.strftime("%Y-%m-%d %H:%M:%S")
        
        self.cursor.execute("""
            SELECT COUNT(DISTINCT student_id)
            FROM attendance
            WHERE timestamp >= ?
        """, (today_start_str,))
        
        return self.cursor.fetchone()[0]
    
    def delete_student(self, roll_number: str) -> bool:
        """
        Delete a student and their attendance records.
        
        Args:
            roll_number: Student's roll number
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get student ID
            self.cursor.execute("SELECT id FROM students WHERE roll_number = ?", (roll_number,))
            result = self.cursor.fetchone()
            
            if not result:
                print(f"✗ Student {roll_number} not found")
                return False
            
            student_id = result[0]
            
            # Delete attendance records
            self.cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
            
            # Delete student
            self.cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
            
            self.conn.commit()
            print(f"✓ Deleted student: {roll_number}")
            return True
            
        except Exception as e:
            print(f"✗ Error deleting student: {e}")
            return False
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()


# Standalone utility functions
def export_attendance_csv(db_path: str = "attendance.db", output_file: str = "attendance_today.csv") -> None:
    """
    Export today's attendance to CSV file.
    
    Args:
        db_path: Path to database file
        output_file: Output CSV filename
    """
    import csv
    
    db = Database(db_path)
    records = db.get_attendance_today()
    
    if not records:
        print("No attendance records for today")
        db.close()
        return
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Roll Number', 'Timestamp'])
        writer.writerows(records)
    
    print(f"✓ Exported {len(records)} records to {output_file}")
    db.close()


def print_database_stats(db_path: str = "attendance.db") -> None:
    """
    Print database statistics.
    
    Args:
        db_path: Path to database file
    """
    db = Database(db_path)
    total_students = len(db.get_all_students())
    present_today = db.get_attendance_count_today()
    
    print(f"\n{'='*50}")
    print(f"DATABASE STATISTICS")
    print(f"{'='*50}")
    print(f"Total Registered Students: {total_students}")
    print(f"Present Today: {present_today}")
    print(f"Absent Today: {total_students - present_today}")
    print(f"{'='*50}\n")
    db.close()
