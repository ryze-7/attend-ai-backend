from face_engine.database import Database
from datetime import datetime

db = Database()

# Check if check_recent_attendance is working
student_id = 1

print("Testing check_recent_attendance function:")
print(f"Student ID: {student_id}")

# Get last attendance
db.cursor.execute("""
    SELECT timestamp
    FROM attendance
    WHERE student_id = ?
    ORDER BY timestamp DESC
    LIMIT 1
""", (student_id,))

result = db.cursor.fetchone()

if result:
    print(f"Last timestamp in DB: {result[0]}")
    print(f"Type: {type(result[0])}")
    
    # Try to parse it
    try:
        last_timestamp = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        print(f"Parsed timestamp: {last_timestamp}")
        
        time_diff = datetime.now() - last_timestamp
        print(f"Time difference: {time_diff.total_seconds()} seconds")
        print(f"Minutes ago: {time_diff.total_seconds() / 60}")
        
        is_recent = time_diff.total_seconds() < (10 * 60)
        print(f"Is within 10 minutes? {is_recent}")
        
    except Exception as e:
        print(f"Error parsing: {e}")
else:
    print("No attendance records found")

print("\n" + "="*50)
print("Now testing the actual function:")
result = db.check_recent_attendance(student_id, minutes=10)
print(f"check_recent_attendance returned: {result}")

db.close()
