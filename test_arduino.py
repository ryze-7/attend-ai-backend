import serial
import time

try:
    print("Attempting to connect to Arduino...")
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
    time.sleep(2)  # Wait for Arduino to reset
    
    print("✓ Connected successfully!")
    print(f"Port: {ser.port}")
    print(f"Baudrate: {ser.baudrate}")
    
    # Try to read any startup message
    if ser.in_waiting > 0:
        msg = ser.readline().decode('utf-8').strip()
        print(f"Arduino says: {msg}")
    
    # Send test commands
    print("\nSending 'G' (Green)...")
    ser.write(b'G\n')
    time.sleep(2)
    
    print("Sending 'R' (Red)...")
    ser.write(b'R\n')
    time.sleep(2)
    
    ser.close()
    print("\n✓ Test complete!")
    
except serial.SerialException as e:
    print(f"✗ Error: {e}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
