import sqlite3
import time
import logging

print("Patching sqlite3 connections...")

# Store original connect function
original_connect = sqlite3.connect

# Create patched connect function with retry logic
def patched_connect(*args, **kwargs):
    # Set longer timeout and implement retry logic
    kwargs['timeout'] = kwargs.get('timeout', 30)
    for attempt in range(5):
        try:
            return original_connect(*args, **kwargs)
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e) and attempt < 4:
                print(f"Database locked, retrying ({attempt+1}/5)")
                time.sleep(2)  # Increased wait time between retries
            else:
                raise

# Replace the sqlite3.connect with our patched version
sqlite3.connect = patched_connect
print("Patched sqlite3.connect with retry functionality") 