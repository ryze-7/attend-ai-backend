"""
Student registration module.
Captures multiple face images and creates averaged face encoding.
"""

import face_recognition
import numpy as np
import cv2
import time
from typing import Optional, List
from .camera import Camera
from .database import Database


class StudentRegistration:
    """Handles student face registration process."""
    
    def __init__(self, num_samples: int = 15):
        """
        Initialize registration handler.
        
        Args:
            num_samples: Number of face samples to capture (default 15)
        """
        self.num_samples = num_samples
        self.camera = Camera()
        self.db = Database()
    
    def register_student(self, name: str, roll_number: str) -> bool:
        """
        Complete registration process for a student.
        
        Args:
            name: Student's full name
            roll_number: Unique roll number
            
        Returns:
            True if registration successful, False otherwise
        """
        print(f"\n{'='*50}")
        print(f"REGISTERING STUDENT: {name} ({roll_number})")
        print(f"{'='*50}")
        
        # Start camera
        if not self.camera.start():
            return False
        
        try:
            # Capture face encodings
            encodings = self._capture_encodings()
            
            if len(encodings) < 5:  # Minimum 5 valid samples
                print(f"✗ Failed: Only {len(encodings)} valid samples captured")
                print("  Need at least 5 clear face images")
                return False
            
            # Average the encodings
            averaged_encoding = np.mean(encodings, axis=0)
            
            # Save to database
            success = self.db.add_student(name, roll_number, averaged_encoding)
            
            if success:
                print(f"✓ Registration complete!")
                print(f"  Captured {len(encodings)} valid samples")
            
            return success
            
        finally:
            self.camera.stop()
    
    def _capture_encodings(self) -> List[np.ndarray]:
        """
        Capture multiple face encodings.
        
        Returns:
            List of face encodings
        """
        encodings = []
        attempts = 0
        max_attempts = self.num_samples * 3  # Allow retries
        
        print(f"\nCapturing {self.num_samples} face samples...")
        print("Please look at the camera and move your head slightly")
        print("between captures for better accuracy.\n")
        
        while len(encodings) < self.num_samples and attempts < max_attempts:
            attempts += 1
            
            # Capture frame
            frame = self.camera.capture_single_frame()
            if frame is None:
                continue
            
            # Detect faces using HOG model (faster on Raspberry Pi)
            face_locations = face_recognition.face_locations(frame, model='hog')
            
            if len(face_locations) == 0:
                print(f"  [{len(encodings)}/{self.num_samples}] No face detected, retrying...")
                time.sleep(0.3)
                continue
            
            if len(face_locations) > 1:
                print(f"  [{len(encodings)}/{self.num_samples}] Multiple faces detected, retrying...")
                time.sleep(0.3)
                continue
            
            # Generate face encoding
            face_encodings = face_recognition.face_encodings(frame, face_locations)
            
            if len(face_encodings) > 0:
                encodings.append(face_encodings[0])
                print(f"  ✓ [{len(encodings)}/{self.num_samples}] Sample captured")
                time.sleep(0.5)  # Delay between captures
        
        return encodings


def register_new_student():
    """Interactive CLI function to register a new student."""
    print("\n" + "="*50)
    print("STUDENT REGISTRATION")
    print("="*50)
    
    name = input("Enter student name: ").strip()
    roll_number = input("Enter roll number: ").strip()
    
    if not name or not roll_number:
        print("✗ Name and roll number cannot be empty")
        return
    
    registrar = StudentRegistration(num_samples=15)
    success = registrar.register_student(name, roll_number)
    
    if success:
        print("\n✓ Student registered successfully!")
    else:
        print("\n✗ Registration failed")
