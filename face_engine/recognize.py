"""
Face recognition module for attendance marking.
Detects and recognizes faces in real-time from camera feed.
"""

import face_recognition
import cv2
import numpy as np
import time
from typing import List, Tuple, Optional
from datetime import datetime
from .database import Database
from .serial_comm import ArduinoSerial


class FaceRecognizer:
    """Handles real-time face recognition and attendance marking."""
    
    def __init__(self, tolerance: float = 0.5):
        """
        Initialize face recognizer.
        
        Args:
            tolerance: Face matching tolerance (lower = stricter, default 0.5)
        """
        self.tolerance = tolerance
        self.db = Database()
        self.arduino = ArduinoSerial()
        
        # Load known faces from database
        self.known_encodings = []
        self.known_student_ids = []
        self.known_names = []
        self._load_known_faces()
        
        # In-memory cache to prevent rapid duplicate entries
        self.last_marked = {}  # {student_id: timestamp}
        self.cooldown_seconds = 600  # 10 minutes in seconds
    
    def _load_known_faces(self) -> None:
        """Load all registered students' face encodings from database."""
        print("Loading registered students...")
        
        students = self.db.get_all_students()
        
        for student_id, name, roll_number, encoding in students:
            self.known_encodings.append(encoding)
            self.known_student_ids.append(student_id)
            self.known_names.append(f"{name} ({roll_number})")
        
        print(f"✓ Loaded {len(self.known_encodings)} registered students")
    
    def recognize_faces(self, frame: np.ndarray) -> List[Tuple[str, Tuple[int, int, int, int]]]:
        """
        Detect and recognize faces in a frame.
        
        Args:
            frame: RGB image frame
            
        Returns:
            List of tuples: (name, face_location)
        """
        # Detect faces using HOG model
        face_locations = face_recognition.face_locations(frame, model='hog')
        
        if len(face_locations) == 0:
            return []
        
        # Generate encodings for detected faces
        face_encodings = face_recognition.face_encodings(frame, face_locations)
        
        recognized_faces = []
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Compare with known faces
            matches = face_recognition.compare_faces(
                self.known_encodings,
                face_encoding,
                tolerance=self.tolerance
            )
            
            name = "Unknown"
            student_id = None
            should_mark = False
            
            # Find best match
            if True in matches:
                # Calculate face distances
                face_distances = face_recognition.face_distance(
                    self.known_encodings,
                    face_encoding
                )
                
                best_match_index = np.argmin(face_distances)
                
                if matches[best_match_index]:
                    student_id = self.known_student_ids[best_match_index]
                    name = self.known_names[best_match_index]
                    
                    # Check in-memory cache first (faster than database)
                    current_time = time.time()
                    
                    if student_id not in self.last_marked or \
                       (current_time - self.last_marked[student_id]) >= self.cooldown_seconds:
                        # Mark attendance
                        if self.db.mark_attendance(student_id):
                            self.last_marked[student_id] = current_time
                            should_mark = True
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(f"✓ ATTENDANCE MARKED: {name} at {timestamp}")
            
            # Send signal to Arduino ONLY when new attendance is marked
            if should_mark:
                self.arduino.send_green()
            elif student_id is not None:
                # Known student but already marked - do nothing (no LED)
                pass
            else:
                # Unknown person
                self.arduino.send_red()
            
            recognized_faces.append((name, face_location))
        
        return recognized_faces
    
    def start(self) -> bool:
        """
        Initialize recognition system.
        
        Returns:
            True if initialization successful
        """
        # Connect to Arduino
        if not self.arduino.connect():
            print("⚠ Warning: Arduino not connected. Continuing without Arduino.")
        
        return len(self.known_encodings) > 0
    
    def stop(self) -> None:
        """Clean up resources."""
        self.arduino.disconnect()
        self.db.close()


def draw_recognition_results(frame: np.ndarray, 
                             recognized_faces: List[Tuple[str, Tuple[int, int, int, int]]],
                             scale_factor: float = 4.0) -> np.ndarray:
    """
    Draw bounding boxes and names on frame.
    
    Args:
        frame: Display frame (BGR format)
        recognized_faces: List of (name, location) tuples
        scale_factor: Scaling factor to convert small frame coords to original
        
    Returns:
        Annotated frame
    """
    for name, (top, right, bottom, left) in recognized_faces:
        # Scale up coordinates
        top = int(top * scale_factor)
        right = int(right * scale_factor)
        bottom = int(bottom * scale_factor)
        left = int(left * scale_factor)
        
        # Choose color based on recognition
        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
        
        # Draw rectangle
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        
        # Draw label background
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        
        # Draw text
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)
    
    return frame
