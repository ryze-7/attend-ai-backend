"""
Serial communication module for Arduino interfacing.
Sends attendance status signals to Arduino.
"""

import serial
import time
from typing import Optional


class ArduinoSerial:
    """Manages serial communication with Arduino."""
    
    # Signal codes
    GREEN_SIGNAL = 'G\n'   # Match found - Green LED
    RED_SIGNAL = 'R\n'     # No match - Red LED
    
    def __init__(self, port: str = '/dev/ttyACM0', baudrate: int = 9600, timeout: float = 1.0):
        """
        Initialize serial connection to Arduino.
        
        Args:
            port: Serial port path (default /dev/ttyACM0)
            baudrate: Baud rate (default 9600)
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.is_connected = False
    
    def connect(self) -> bool:
        """
        Establish serial connection to Arduino.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            
            # Wait for Arduino to reset after serial connection
            time.sleep(2)
            
            # Flush any existing data
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            
            self.is_connected = True
            print(f"✓ Connected to Arduino on {self.port}")
            return True
            
        except serial.SerialException as e:
            print(f"✗ Error connecting to Arduino: {e}")
            self.is_connected = False
            return False
    
    def send_signal(self, code: str) -> bool:
        """
        Send a signal to Arduino.
        
        Args:
            code: Signal code ('G\n' for green, 'R\n' for red)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_connected or self.serial_conn is None:
            print("✗ Arduino not connected")
            return False
        
        try:
            self.serial_conn.write(code.encode())
            self.serial_conn.flush()
            return True
            
        except serial.SerialException as e:
            print(f"✗ Error sending signal: {e}")
            return False
    
    def send_green(self) -> bool:
        """Send green signal (attendance marked)."""
        return self.send_signal(self.GREEN_SIGNAL)
    
    def send_red(self) -> bool:
        """Send red signal (no match found)."""
        return self.send_signal(self.RED_SIGNAL)
    
    def read_line(self) -> Optional[str]:
        """
        Read a line from Arduino (if Arduino sends data back).
        
        Returns:
            Decoded string or None
        """
        if not self.is_connected or self.serial_conn is None:
            return None
        
        try:
            if self.serial_conn.in_waiting > 0:
                line = self.serial_conn.readline().decode('utf-8').strip()
                return line
        except Exception as e:
            print(f"✗ Error reading from Arduino: {e}")
        
        return None
    
    def disconnect(self) -> None:
        """Close serial connection."""
        if self.serial_conn is not None:
            self.serial_conn.close()
            self.is_connected = False
            print("✓ Disconnected from Arduino")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
