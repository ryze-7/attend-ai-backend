"""
Face Engine Package
Classroom Attendance Monitoring System
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .database import Database
from .camera import Camera
from .register import StudentRegistration
from .recognize import FaceRecognizer
from .serial_comm import ArduinoSerial

__all__ = [
    'Database',
    'Camera',
    'StudentRegistration',
    'FaceRecognizer',
    'ArduinoSerial'
]
