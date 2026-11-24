#!/usr/bin/env python3
import json
import time
import logging
import os
import random
import threading

# Try to import platform-specific servo libraries
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

# Constants
CONFIG_FILE = "servo_config.json"
LOG_FILE = "sassy_log.txt"

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class ServoControl:
    def __init__(self):
        self.servos = {}
        self.emotions = {}
        self.is_initialized = False
        self.lock = threading.Lock()
        
        # Load configuration
        self.load_config()
        
        # Initialize hardware if available
        if GPIO_AVAILABLE and self.servos:
            self._setup_gpio()
    
    def load_config(self):
        """Load servo configuration from config file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    self.servos = config.get("servos", {})
                    self.emotions = config.get("emotions", {})
                logging.info(f"Loaded servo configuration: {len(self.servos)} servos defined")
            except Exception as e:
                logging.error(f"Failed to load servo configuration: {str(e)}")
        else:
            # Create a default configuration file
            default_config = {
                "servos": {
                    "head": {"pin": 18, "min_angle": 0, "max_angle": 180, "default": 90},
                    "left_arm": {"pin": 23, "min_angle": 0, "max_angle": 180, "default": 90},
                    "right_arm": {"pin": 24, "min_angle": 0, "max_angle": 180, "default": 90}
                },
                "emotions": {
                    "joy": [
                        {"servo": "head", "sequence": [110, 70, 90], "speed": 0.2},
                        {"servo": "left_arm", "sequence": [45, 135, 90], "speed": 0.3},
                        {"servo": "right_arm", "sequence": [135, 45, 90], "speed": 0.3}
                    ],
                    "curiosity": [
                        {"servo": "head", "sequence": [70, 110, 90], "speed": 0.4}
                    ],
                    "alert": [
                        {"servo": "head", "sequence": [90, 140, 90], "speed": 0.1},
                        {"servo": "left_arm", "sequence": [90, 150, 90], "speed": 0.1},
                        {"servo": "right_arm", "sequence": [90, 150, 90], "speed": 0.1}
                    ]
                }
            }
            
            try:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(default_config, f, indent=2)
                self.servos = default_config["servos"]
                self.emotions = default_config["emotions"]
                logging.info("Created default servo configuration")
            except Exception as e:
                logging.error(f"Failed to create default servo configuration: {str(e)}")
    
    def _setup_gpio(self):
        """Initialize GPIO for servo control"""
        if not GPIO_AVAILABLE:
            logging.warning("GPIO library not available, servo control disabled")
            return False
        
        try:
            GPIO.setmode(GPIO.BCM)
            
            # Setup each servo
            for servo_name, servo_config in self.servos.items():
                pin = servo_config.get("pin")
                if pin is not None:
                    GPIO.setup(pin, GPIO.OUT)
                    # Create PWM instance
                    servo_config["pwm"] = GPIO.PWM(pin, 50)  # 50Hz frequency
                    servo_config["pwm"].start(0)
                    
                    # Move to default position
                    default_angle = servo_config.get("default", 90)
                    self.set_angle(servo_name, default_angle)
            
            self.is_initialized = True
            logging.info("GPIO initialized for servo control")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize GPIO: {str(e)}")
            return False
    
    def set_angle(self, servo_name, angle):
        """Set a servo to a specific angle"""
        if not self.is_initialized or not GPIO_AVAILABLE:
            logging.debug(f"Simulating servo {servo_name} movement to angle {angle}")
            return False
        
        with self.lock:
            if servo_name not in self.servos:
                logging.warning(f"Servo {servo_name} not defined in configuration")
                return False
            
            servo_config = self.servos[servo_name]
            pin = servo_config.get("pin")
            
            if pin is None:
                logging.warning(f"No pin defined for servo {servo_name}")
                return False
            
            # Ensure angle is within limits
            min_angle = servo_config.get("min_angle", 0)
            max_angle = servo_config.get("max_angle", 180)
            angle = max(min_angle, min(max_angle, angle))
            
            try:
                # Convert angle to duty cycle (typical servo range)
                # 0 degrees = 2.5% duty cycle, 180 degrees = 12.5% duty cycle
                duty_cycle = 2.5 + (angle / 180.0) * 10.0
                
                # Set the duty cycle
                servo_config["pwm"].ChangeDutyCycle(duty_cycle)
                logging.debug(f"Set servo {servo_name} to angle {angle} (duty cycle {duty_cycle:.2f})")
                
                # Give the servo time to move
                time.sleep(0.1)
                
                # Stop the PWM signal (prevents jittering)
                servo_config["pwm"].ChangeDutyCycle(0)
                return True
            except Exception as e:
                logging.error(f"Error setting servo {servo_name} angle: {str(e)}")
                return False
    
    def express_emotion(self, emotion):
        """Express an emotion through servo movements"""
        if emotion not in self.emotions:
            logging.warning(f"Emotion '{emotion}' not defined in configuration")
            return False
        
        # Execute emotion sequence in a separate thread
        threading.Thread(target=self._execute_emotion_sequence, args=(emotion,)).start()
        return True
    
    def _execute_emotion_sequence(self, emotion):
        """Execute the sequence of movements for an emotion"""
        emotion_sequences = self.emotions.get(emotion, [])
        
        # Group sequences by servo
        servo_sequences = {}
        for seq in emotion_sequences:
            servo_name = seq.get("servo")
            if servo_name:
                servo_sequences[servo_name] = seq
        
        # Execute sequences for each servo
        threads = []
        for servo_name, sequence_data in servo_sequences.items():
            t = threading.Thread(
                target=self._execute_servo_sequence,
                args=(servo_name, sequence_data)
            )
            t.start()
            threads.append(t)
        
        # Wait for all sequences to complete
        for t in threads:
            t.join()
    
    def _execute_servo_sequence(self, servo_name, sequence_data):
        """Execute a sequence of movements for a single servo"""
        sequence = sequence_data.get("sequence", [])
        speed = sequence_data.get("speed", 0.5)
        
        if not sequence:
            return
        
        for angle in sequence:
            self.set_angle(servo_name, angle)
            time.sleep(speed)
    
    def shutdown(self):
        """Clean up GPIO resources"""
        if self.is_initialized and GPIO_AVAILABLE:
            try:
                # Stop all PWM signals
                for servo_name, servo_config in self.servos.items():
                    if "pwm" in servo_config:
                        servo_config["pwm"].stop()
                
                # Clean up GPIO
                GPIO.cleanup()
                logging.info("Servo control shutdown complete")
            except Exception as e:
                logging.error(f"Error during servo shutdown: {str(e)}")

# For standalone testing
if __name__ == "__main__":
    controller = ServoControl()
    
    # Test movement if GPIO is available
    if GPIO_AVAILABLE and controller.is_initialized:
        print("Testing servo movements...")
        controller.express_emotion("joy")
        time.sleep(2)
        controller.express_emotion("curiosity")
        time.sleep(2)
        controller.express_emotion("alert")
    else:
        print("GPIO not available, running in simulation mode")
        print(f"Would express: joy, curiosity, alert")
    
    # Cleanup
    controller.shutdown() 