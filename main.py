"""
Main application entry point for Classroom Attendance System.
Provides CLI interface for registration and recognition modes.
"""

import cv2
import sys
from face_engine.camera import Camera
from face_engine.database import Database, print_database_stats
from face_engine.register import register_new_student
from face_engine.recognize import FaceRecognizer, draw_recognition_results


def recognition_mode():
    """Run attendance recognition mode."""
    print("\n" + "="*50)
    print("ATTENDANCE RECOGNITION MODE")
    print("="*50)
    print("Press 'q' to quit\n")
    
    # Initialize components
    recognizer = FaceRecognizer(tolerance=0.5)
    
    if not recognizer.start():
        print("✗ No students registered. Please register students first.")
        return
    
    camera = Camera(camera_index=0, scale_factor=0.25)
    
    if not camera.start():
        print("✗ Failed to start camera")
        return
    
    try:
        while True:
            # Read frame
            should_process, display_frame, small_frame = camera.read_frame()
            
            if display_frame is None:
                break
            
            # Process every 5th frame
            if should_process and small_frame is not None:
                # Recognize faces
                recognized_faces = recognizer.recognize_faces(small_frame)
                
                # Draw results on display frame
                if recognized_faces:
                    display_frame = draw_recognition_results(
                        display_frame,
                        recognized_faces,
                        scale_factor=4.0
                    )
            
            # Display frame
            cv2.imshow('Attendance System', display_frame)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        camera.stop()
        recognizer.stop()
        cv2.destroyAllWindows()


def registration_mode():
    """Run student registration mode."""
    while True:
        print("\n" + "="*50)
        print("REGISTRATION MENU")
        print("="*50)
        print("1. Register new student")
        print("2. View registered students")
        print("3. Back to main menu")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == '1':
            register_new_student()
        elif choice == '2':
            view_registered_students()
        elif choice == '3':
            break
        else:
            print("Invalid choice")


def view_registered_students():
    """Display all registered students."""
    db = Database()
    students = db.get_all_students()
    
    print("\n" + "="*50)
    print("REGISTERED STUDENTS")
    print("="*50)
    
    if not students:
        print("No students registered yet")
    else:
        for student_id, name, roll_number, _ in students:
            print(f"{roll_number:15s} - {name}")
    
    print("="*50)
    db.close()


def view_attendance():
    """Display today's attendance records."""
    from datetime import datetime
    
    db = Database()
    records = db.get_attendance_today()
    
    print("\n" + "="*50)
    print("TODAY'S ATTENDANCE")
    print("="*50)
    
    if not records:
        print("No attendance records for today")
    else:
        for name, roll_number, timestamp in records:
            # Handle both string and datetime objects
            if isinstance(timestamp, str):
                # Parse string timestamp
                dt = datetime.fromisoformat(timestamp.replace(' ', 'T'))
                time_str = dt.strftime("%H:%M:%S")
            else:
                time_str = timestamp.strftime("%H:%M:%S")
            
            print(f"{time_str} - {name} ({roll_number})")
    
    print("="*50)
    db.close()

def main():
    """Main application loop."""
    print("\n" + "="*60)
    print(" "*15 + "CLASSROOM ATTENDANCE SYSTEM")
    print(" "*20 + "Raspberry Pi 5")
    print("="*60)
    
    while True:
        print("\nMAIN MENU")
        print("1. Start Attendance Recognition")
        print("2. Register Students")
        print("3. View Registered Students")
        print("4. View Today's Attendance")
        print("5. Database Statistics")
        print("6. Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == '1':
            recognition_mode()
        elif choice == '2':
            registration_mode()
        elif choice == '3':
            view_registered_students()
        elif choice == '4':
            view_attendance()
        elif choice == '5':
            print_database_stats()
        elif choice == '6':
            print("\nGoodbye!")
            sys.exit(0)
        else:
            print("Invalid choice, please try again")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
