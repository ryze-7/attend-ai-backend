"""
Flask REST API for Classroom Attendance System
Bridges Python face recognition system with Next.js dashboard
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import threading
import time

from face_engine.database import Database
from face_engine.camera import Camera
from face_engine.recognize import FaceRecognizer
from face_engine.register import StudentRegistration

app = Flask(__name__)
CORS(app, origins=['*'])  # Allow Next.js to call this API

# Global state
recognition_thread = None
is_running = False
recognizer = None
camera = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def recognition_loop():
    """Background thread for face recognition."""
    global is_running, recognizer, camera

    last_process_time = 0
    process_interval = 3  # Process every 3 seconds

    while is_running:
        try:
            should_process, display_frame, small_frame = camera.read_frame()

            if display_frame is None:
                break

            current_time = time.time()

            if should_process and small_frame is not None:
                if (current_time - last_process_time) >= process_interval:
                    recognizer.recognize_faces(small_frame)
                    last_process_time = current_time

            time.sleep(0.1)

        except Exception as e:
            print(f"Recognition error: {e}")
            break

    is_running = False
    print("Recognition stopped")


# ============================================================
# STATUS ENDPOINTS
# ============================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status."""
    global is_running, recognizer

    db = Database()
    total_students = len(db.get_all_students())
    present_today = db.get_attendance_count_today()
    db.close()

    return jsonify({
        'success': True,
        'data': {
            'recognition_running': is_running,
            'camera_connected': is_running,
            'arduino_connected': recognizer.arduino.is_connected if recognizer else False,
            'total_students': total_students,
            'present_today': present_today,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    })


# ============================================================
# STUDENT ENDPOINTS
# ============================================================

@app.route('/api/students', methods=['GET'])
def get_students():
    """Get all registered students."""
    db = Database()
    students = db.get_all_students()
    db.close()

    student_list = []
    for student_id, name, roll_number, _ in students:
        student_list.append({
            'id': student_id,
            'name': name,
            'roll_number': roll_number
        })

    return jsonify({
        'success': True,
        'data': student_list,
        'count': len(student_list)
    })


@app.route('/api/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """Get a specific student by ID."""
    db = Database()
    result = db.get_student_by_id(student_id)
    db.close()

    if result:
        name, roll_number = result
        return jsonify({
            'success': True,
            'data': {
                'id': student_id,
                'name': name,
                'roll_number': roll_number
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Student not found'
        }), 404


@app.route('/api/students/<roll_number>', methods=['DELETE'])
def delete_student(roll_number):
    """Delete a student by roll number."""
    db = Database()
    success = db.delete_student(roll_number)
    db.close()

    if success:
        return jsonify({
            'success': True,
            'message': f'Student {roll_number} deleted successfully'
        })
    else:
        return jsonify({
            'success': False,
            'error': f'Student {roll_number} not found'
        }), 404


# ============================================================
# ATTENDANCE ENDPOINTS
# ============================================================

@app.route('/api/attendance/today', methods=['GET'])
def get_attendance_today():
    """Get today's attendance records."""
    db = Database()
    records = db.get_attendance_today()
    db.close()

    attendance_list = []
    for name, roll_number, timestamp in records:
        attendance_list.append({
            'name': name,
            'roll_number': roll_number,
            'timestamp': timestamp
        })

    return jsonify({
        'success': True,
        'data': attendance_list,
        'count': len(attendance_list),
        'date': datetime.now().strftime("%Y-%m-%d")
    })


@app.route('/api/attendance/all', methods=['GET'])
def get_all_attendance():
    """Get all attendance records."""
    db = Database()
    db.cursor.execute("""
        SELECT s.name, s.roll_number, a.timestamp
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        ORDER BY a.timestamp DESC
    """)
    records = db.cursor.fetchall()
    db.close()

    attendance_list = []
    for name, roll_number, timestamp in records:
        attendance_list.append({
            'name': name,
            'roll_number': roll_number,
            'timestamp': timestamp
        })

    return jsonify({
        'success': True,
        'data': attendance_list,
        'count': len(attendance_list)
    })


@app.route('/api/attendance/clear/today', methods=['DELETE'])
def clear_today_attendance():
    """Clear today's attendance records."""
    db = Database()
    today_start = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    ).strftime("%Y-%m-%d %H:%M:%S")

    db.cursor.execute(
        "DELETE FROM attendance WHERE timestamp >= ?",
        (today_start,)
    )
    deleted = db.cursor.rowcount
    db.conn.commit()
    db.close()

    return jsonify({
        'success': True,
        'message': f'Deleted {deleted} attendance records from today'
    })


@app.route('/api/attendance/clear/all', methods=['DELETE'])
def clear_all_attendance():
    """Clear all attendance records."""
    db = Database()
    db.cursor.execute("DELETE FROM attendance")
    deleted = db.cursor.rowcount
    db.conn.commit()
    db.close()

    return jsonify({
        'success': True,
        'message': f'Deleted {deleted} attendance records'
    })


# ============================================================
# STATS ENDPOINTS
# ============================================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get dashboard statistics."""
    db = Database()
    total_students = len(db.get_all_students())
    present_today = db.get_attendance_count_today()
    absent_today = total_students - present_today

    # Get attendance for last 7 days
    db.cursor.execute("""
        SELECT DATE(timestamp) as date, COUNT(DISTINCT student_id) as count
        FROM attendance
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        LIMIT 7
    """)
    weekly_data = db.cursor.fetchall()
    db.close()

    weekly_list = []
    for date, count in weekly_data:
        weekly_list.append({
            'date': date,
            'count': count
        })

    return jsonify({
        'success': True,
        'data': {
            'total_students': total_students,
            'present_today': present_today,
            'absent_today': absent_today,
            'attendance_rate': round((present_today / total_students * 100), 1) if total_students > 0 else 0,
            'weekly_data': weekly_list,
            'date': datetime.now().strftime("%Y-%m-%d"),
            'time': datetime.now().strftime("%H:%M:%S")
        }
    })


# ============================================================
# RECOGNITION CONTROL ENDPOINTS
# ============================================================

@app.route('/api/recognition/start', methods=['POST'])
def start_recognition():
    """Start face recognition."""
    global recognition_thread, is_running, recognizer, camera

    if is_running:
        return jsonify({
            'success': False,
            'error': 'Recognition already running'
        }), 400

    # Initialize recognizer
    recognizer = FaceRecognizer(tolerance=0.5)

    if not recognizer.start():
        return jsonify({
            'success': False,
            'error': 'No students registered'
        }), 400

    # Initialize camera
    camera = Camera(camera_index=0, scale_factor=0.25)

    if not camera.start():
        return jsonify({
            'success': False,
            'error': 'Failed to start camera'
        }), 500

    # Start recognition in background thread
    is_running = True
    recognition_thread = threading.Thread(target=recognition_loop)
    recognition_thread.daemon = True
    recognition_thread.start()

    return jsonify({
        'success': True,
        'message': 'Recognition started successfully'
    })


@app.route('/api/recognition/stop', methods=['POST'])
def stop_recognition():
    """Stop face recognition."""
    global is_running, recognizer, camera

    if not is_running:
        return jsonify({
            'success': False,
            'error': 'Recognition is not running'
        }), 400

    # Stop recognition
    is_running = False
    time.sleep(1)

    if camera:
        camera.stop()
        camera = None

    if recognizer:
        recognizer.stop()
        recognizer = None

    return jsonify({
        'success': True,
        'message': 'Recognition stopped successfully'
    })


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("\n" + "="*50)
    print("ATTENDANCE SYSTEM - FLASK API")
    print("="*50)
    print(f"Starting server on http://0.0.0.0:5000")
    print("Press Ctrl+C to stop\n")

    app.run(
        host='0.0.0.0',   # Allow external connections (from Next.js)
        port=5000,
        debug=False,
        threaded=True
    )
