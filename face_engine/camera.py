"""
Camera module for video capture and frame processing.
Optimized for Raspberry Pi 5 with performance considerations.
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class Camera:
    """Manages USB camera capture and frame preprocessing."""
    
    def __init__(self, camera_index: int = 0, scale_factor: float = 0.25):
        """
        Initialize camera capture.
        
        Args:
            camera_index: USB camera device index (default 0)
            scale_factor: Frame scaling factor for performance (default 0.25 = 1/4 size)
        """
        self.camera_index = camera_index
        self.scale_factor = scale_factor
        self.cap = None
        self.frame_count = 0
        self.process_every_n_frames = 5
        
    def start(self) -> bool:
        """
        Start camera capture.
        
        Returns:
            True if camera opened successfully, False otherwise
        """
        self.cap = cv2.VideoCapture(self.camera_index)
        
        if not self.cap.isOpened():
            print(f"✗ Error: Could not open camera {self.camera_index}")
            return False
        
        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        print(f"✓ Camera {self.camera_index} started successfully")
        return True
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Read and process a frame from camera.
        
        Returns:
            Tuple of (should_process, display_frame, small_frame)
            - should_process: Whether this frame should be processed (every 5th frame)
            - display_frame: Original frame for display
            - small_frame: Scaled down frame for face detection
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None, None
        
        ret, frame = self.cap.read()
        if not ret:
            return False, None, None
        
        self.frame_count += 1
        
        # Process only every Nth frame
        should_process = (self.frame_count % self.process_every_n_frames == 0)
        
        # Create small frame for face detection
        small_frame = None
        if should_process:
            small_frame = cv2.resize(frame, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
            # Convert BGR to RGB for face_recognition library
            small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        return should_process, frame, small_frame
    
    def capture_single_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame (for registration).
        
        Returns:
            RGB frame or None if capture failed
        """
        if self.cap is None or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            return None
        
        # Convert to RGB and scale down
        small_frame = cv2.resize(frame, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
        return cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    def stop(self) -> None:
        """Release camera resources."""
        if self.cap is not None:
            self.cap.release()
            print("✓ Camera stopped")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
