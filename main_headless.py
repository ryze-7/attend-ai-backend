"""
Headless attendance recognition - no GUI display
For SSH/remote operation
"""

import time
from face_engine.camera import Camera
from face_engine.recognize import FaceRecognizer

print("\n" + "="*50)
print("HEADLESS ATTENDANCE RECOGNITION MODE")
print("="*50)
print("Running without display (for SSH)")
print("Press Ctrl+C to quit\n")

# Initialize
recognizer = FaceRecognizer(tolerance=0.5)

if not recognizer.start():
    print("✗ No students registered")
    exit(1)

camera = Camera(camera_index=0, scale_factor=0.25)

if not camera.start():
    print("✗ Failed to start camera")
    exit(1)

# Add cooldown to prevent processing same person too frequently
last_process_time = 0
process_interval = 3  # Only process faces every 3 seconds

try:
    print("✓ System running... monitoring for faces\n")
    
    while True:
        should_process, display_frame, small_frame = camera.read_frame()
        
        if display_frame is None:
            break
        
        current_time = time.time()
        
        # Only process if enough time has passed AND it's a frame we should process
        if should_process and small_frame is not None:
            if (current_time - last_process_time) >= process_interval:
                recognized_faces = recognizer.recognize_faces(small_frame)
                last_process_time = current_time
        
        time.sleep(0.1)  # Small delay

except KeyboardInterrupt:
    print("\n\nStopping...")
finally:
    camera.stop()
    recognizer.stop()
    print("✓ System stopped")
