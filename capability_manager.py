#!/usr/bin/env python3
"""
SassyQueenCore Capability Manager
Detects and manages real system capabilities
"""

import os
import sys
import json
import importlib.util
import logging
from pathlib import Path
import platform
import subprocess
import tempfile
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'capabilities.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SassyQueenCore.CapabilityManager")

class CapabilityManager:
    def __init__(self):
        """Initialize the capability manager"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Base directory
        self.base_dir = Path(__file__).resolve().parent
        
        # Capability cache
        self.capabilities = {}
        self.last_check = 0
        self.cache_timeout = 60  # seconds
        
        # Hardware capability flags
        self.has_camera = False
        self.has_microphone = False
        self.has_speakers = False
        self.has_network = False
        self.has_physical_interfaces = False
        
        # Software capability flags
        self.has_llm = False
        self.has_voice_recognition = False
        self.has_text_to_speech = False
        self.has_image_processing = False
        
        # Perform initial capability check
        self.check_all_capabilities()
        
    def check_all_capabilities(self, force=False):
        """Check all system capabilities"""
        current_time = time.time()
        
        # Use cached results if recent enough
        if not force and (current_time - self.last_check) < self.cache_timeout:
            return self.capabilities
            
        logger.info("Checking system capabilities...")
        
        # Check hardware capabilities
        self.has_camera = self._check_camera()
        self.has_microphone = self._check_microphone()
        self.has_speakers = self._check_speakers()
        self.has_network = self._check_network()
        self.has_physical_interfaces = self._check_physical_interfaces()
        
        # Check software capabilities
        self.has_llm = self._check_llm()
        self.has_voice_recognition = self._check_voice_recognition()
        self.has_text_to_speech = self._check_text_to_speech()
        self.has_image_processing = self._check_image_processing()
        
        # Update capability dictionary
        self.capabilities = {
            "hardware": {
                "camera": self.has_camera,
                "microphone": self.has_microphone,
                "speakers": self.has_speakers,
                "network": self.has_network,
                "physical_interfaces": self.has_physical_interfaces
            },
            "software": {
                "llm": self.has_llm,
                "voice_recognition": self.has_voice_recognition,
                "text_to_speech": self.has_text_to_speech,
                "image_processing": self.has_image_processing
            },
            "system_info": self._get_system_info()
        }
        
        # Save capabilities to file
        self._save_capabilities()
        
        # Update last check time
        self.last_check = current_time
        
        return self.capabilities
        
    def _check_camera(self):
        """Check if camera is available"""
        try:
            # Check for camera module
            if platform.system() == "Windows":
                try:
                    import cv2
                    cap = cv2.VideoCapture(0)
                    result = cap.isOpened()
                    cap.release()
                    return result
                except (ImportError, Exception):
                    return False
            else:
                # On Linux/Mac, check for device files
                camera_paths = ["/dev/video0", "/dev/video1"]
                return any(os.path.exists(path) for path in camera_paths)
        except Exception as e:
            logger.error(f"Error checking camera: {e}")
            return False
            
    def _check_microphone(self):
        """Check if microphone is available"""
        try:
            if platform.system() == "Windows":
                try:
                    import pyaudio
                    pa = pyaudio.PyAudio()
                    mic_count = pa.get_device_count()
                    pa.terminate()
                    return mic_count > 0
                except (ImportError, Exception):
                    # Alternative check using wmic
                    try:
                        output = subprocess.check_output("wmic path Win32_SoundDevice", shell=True)
                        return b"Microphone" in output
                    except:
                        return False
            else:
                # On Linux/Mac, check for device files
                mic_paths = ["/dev/dsp", "/dev/audio"]
                return any(os.path.exists(path) for path in mic_paths)
        except Exception as e:
            logger.error(f"Error checking microphone: {e}")
            return False
            
    def _check_speakers(self):
        """Check if speakers are available"""
        try:
            if platform.system() == "Windows":
                try:
                    import winsound
                    # Create a silent sound file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
                        temp_path = temp.name
                    # Try to play it (will fail if no sound device)
                    try:
                        winsound.PlaySound(None, winsound.SND_PURGE)  # Stop any playing sound
                        return True
                    except:
                        return False
                    finally:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                except ImportError:
                    # Alternative: assume speakers exist if Windows
                    return True
            else:
                # On Linux/Mac, check for device files
                speaker_paths = ["/dev/dsp", "/dev/audio"]
                return any(os.path.exists(path) for path in speaker_paths)
        except Exception as e:
            logger.error(f"Error checking speakers: {e}")
            return False
            
    def _check_network(self):
        """Check if network is available"""
        try:
            # Ping a reliable server
            if platform.system() == "Windows":
                ping_cmd = ["ping", "-n", "1", "-w", "1000", "8.8.8.8"]
            else:
                ping_cmd = ["ping", "-c", "1", "-W", "1", "8.8.8.8"]
                
            result = subprocess.run(ping_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking network: {e}")
            return False
            
    def _check_physical_interfaces(self):
        """Check for physical interface capabilities"""
        try:
            # Check for physical directory
            physical_dir = self.base_dir / "physical"
            has_dir = physical_dir.exists()
            
            # Check for specific hardware integration files
            has_integration_files = False
            if has_dir:
                integration_files = list(physical_dir.glob("*_interface.py"))
                has_integration_files = len(integration_files) > 0
                
            return has_dir and has_integration_files
        except Exception as e:
            logger.error(f"Error checking physical interfaces: {e}")
            return False
            
    def _check_llm(self):
        """Check if LLM integration is available"""
        try:
            # Check for LLM integration
            scripts_dir = self.base_dir / "scripts"
            llm_path = scripts_dir / "llm_integration.py"
            
            return llm_path.exists()
        except Exception as e:
            logger.error(f"Error checking LLM: {e}")
            return False
            
    def _check_voice_recognition(self):
        """Check if voice recognition is available"""
        try:
            # Check if we have microphone first
            if not self._check_microphone():
                return False
                
            # Check for voice recognition modules
            try:
                import speech_recognition
                return True
            except ImportError:
                pass
                
            # Check for whisper.cpp bindings
            whisper_path = self.base_dir / "scripts" / "whisper_integration.py"
            return whisper_path.exists()
        except Exception as e:
            logger.error(f"Error checking voice recognition: {e}")
            return False
            
    def _check_text_to_speech(self):
        """Check if text-to-speech is available"""
        try:
            # Check if we have speakers first
            if not self._check_speakers():
                return False
                
            # Check for TTS modules
            try:
                import pyttsx3
                return True
            except ImportError:
                pass
                
            # Check for other TTS implementations
            tts_paths = [
                self.base_dir / "scripts" / "tts_integration.py",
                self.base_dir / "scripts" / "elevenlabs_integration.py"
            ]
            return any(path.exists() for path in tts_paths)
        except Exception as e:
            logger.error(f"Error checking text-to-speech: {e}")
            return False
            
    def _check_image_processing(self):
        """Check if image processing is available"""
        try:
            # Check if we have camera first
            if not self._check_camera():
                return False
                
            # Check for OpenCV
            try:
                import cv2
                return True
            except ImportError:
                pass
                
            # Check for PIL
            try:
                from PIL import Image
                return True
            except ImportError:
                return False
        except Exception as e:
            logger.error(f"Error checking image processing: {e}")
            return False
            
    def _get_system_info(self):
        """Get basic system information"""
        return {
            "os": platform.system(),
            "version": platform.version(),
            "processor": platform.processor(),
            "python": platform.python_version()
        }
        
    def _save_capabilities(self):
        """Save capabilities to a JSON file"""
        try:
            capability_file = self.base_dir / "config" / "capabilities.json"
            
            # Create config directory if it doesn't exist
            os.makedirs(self.base_dir / "config", exist_ok=True)
            
            with open(capability_file, 'w', encoding='utf-8') as f:
                json.dump(self.capabilities, f, indent=2)
                
            logger.info(f"Capabilities saved to {capability_file}")
        except Exception as e:
            logger.error(f"Error saving capabilities: {e}")
            
    def get_capability_summary(self):
        """Get a human-readable summary of capabilities"""
        self.check_all_capabilities()
        
        summary = []
        summary.append("SassyQueenCore Capability Summary")
        summary.append("="*40)
        
        # Hardware
        summary.append("\nHardware Capabilities:")
        for name, status in self.capabilities["hardware"].items():
            summary.append(f"  {'✅' if status else '❌'} {name.replace('_', ' ').title()}")
            
        # Software
        summary.append("\nSoftware Capabilities:")
        for name, status in self.capabilities["software"].items():
            summary.append(f"  {'✅' if status else '❌'} {name.replace('_', ' ').title()}")
            
        # System Info
        summary.append("\nSystem Information:")
        for name, value in self.capabilities["system_info"].items():
            summary.append(f"  {name.title()}: {value}")
            
        return "\n".join(summary)
        
    def can_perform_action(self, action_type):
        """
        Check if system can perform a specific action
        
        action_type can be:
        - "speech_input": Can accept speech input
        - "speech_output": Can output speech
        - "vision_input": Can accept visual input
        - "physical_action": Can perform physical actions
        - "network_action": Can perform network operations
        - "llm_processing": Can process using LLM
        """
        self.check_all_capabilities()
        
        if action_type == "speech_input":
            return self.has_microphone and self.has_voice_recognition
            
        elif action_type == "speech_output":
            return self.has_speakers and self.has_text_to_speech
            
        elif action_type == "vision_input":
            return self.has_camera and self.has_image_processing
            
        elif action_type == "physical_action":
            return self.has_physical_interfaces
            
        elif action_type == "network_action":
            return self.has_network
            
        elif action_type == "llm_processing":
            return self.has_llm
            
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return False

# Singleton instance
_capability_manager = None

def get_capability_manager():
    """Get the singleton capability manager instance"""
    global _capability_manager
    if _capability_manager is None:
        _capability_manager = CapabilityManager()
    return _capability_manager

# Direct execution example
if __name__ == "__main__":
    # Check all capabilities and print summary
    manager = get_capability_manager()
    print(manager.get_capability_summary()) 