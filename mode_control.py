#!/usr/bin/env python3
"""
SassyQueenCore Mode Control
Allows easy switching between operational modes with verification
"""

import os
import sys
import argparse
from pathlib import Path
import json
import time

# Add parent directory to path if needed
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import the mode_switcher
try:
    from mode_switcher import ModeSwitcher, get_mode_info
except ImportError:
    print("Error: Could not import ModeSwitcher. Make sure mode_switcher.py is in the same directory.")
    sys.exit(1)

def print_mode_info(mode_info):
    """Print information about the current mode"""
    print("\n" + "="*50)
    print(f"🔹 SassyQueenCore Mode: {mode_info['current_mode'].upper()}")
    print("="*50)
    print(f"📝 Description: {mode_info['description']}")
    
    # Print capabilities
    print("\n🧠 Current Capabilities:")
    for cap, status in mode_info['capabilities'].items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {cap.replace('_', ' ').title()}")
    
    # Print safety protocols if any
    if mode_info.get('safety_protocols'):
        print("\n🔒 Safety Protocols:")
        for protocol in mode_info['safety_protocols']:
            print(f"  ✓ {protocol}")
    
    print("\n" + "-"*50)

def interactive_mode():
    """Interactive mode selector"""
    switcher = ModeSwitcher()
    mode_info = switcher.get_mode_info()
    
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("\n🌟 SassyQueenCore Mode Control 🌟\n")
    print_mode_info(mode_info)
    
    while True:
        print("\nChoose an option:")
        print("1. Switch to Manual Mode")
        print("2. Switch to Copilot Mode")
        print("3. Switch to Autopilot Mode")
        print("4. Refresh Mode Info")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == '1':
            success, message = switcher.set_mode('manual')
            print(message)
            if success:
                mode_info = switcher.get_mode_info()
                print_mode_info(mode_info)
                
        elif choice == '2':
            success, message = switcher.set_mode('copilot')
            print(message)
            if success:
                mode_info = switcher.get_mode_info()
                print_mode_info(mode_info)
                
        elif choice == '3':
            print("\n🔐 Autopilot Mode Confirmation 🔐")
            print("In Autopilot mode, SassyQueenCore can take actions without explicit confirmation")
            print("within the boundaries of safety protocols.")
            
            confirm = input("\nAre you sure you want to enable Autopilot mode? (yes/no): ")
            if confirm.lower() in ['yes', 'y']:
                success, message = switcher.set_mode('autopilot')
                print(message)
                if success:
                    mode_info = switcher.get_mode_info()
                    print_mode_info(mode_info)
                else:
                    print(f"Could not switch to Autopilot: {message}")
            else:
                print("Autopilot mode activation cancelled.")
                
        elif choice == '4':
            mode_info = switcher.get_mode_info()
            print_mode_info(mode_info)
            
        elif choice == '5':
            print("\nExiting Mode Control. SassyQueenCore continues in current mode.")
            break
            
        else:
            print("Invalid choice. Please try again.")

def main():
    """Main function for the mode control script"""
    parser = argparse.ArgumentParser(description="SassyQueenCore Mode Control")
    parser.add_argument('mode', nargs='?', choices=['manual', 'copilot', 'autopilot', 'info'],
                        help="Mode to switch to, or 'info' to show current mode")
    parser.add_argument('--interactive', '-i', action='store_true', 
                        help="Start interactive mode control")
    parser.add_argument('--force', '-f', action='store_true', 
                        help="Force mode switch without confirmation")
    
    args = parser.parse_args()
    
    # Create the switcher
    switcher = ModeSwitcher()
    
    # Interactive mode
    if args.interactive or not args.mode:
        interactive_mode()
        return
        
    # Info mode
    if args.mode == 'info':
        mode_info = switcher.get_mode_info()
        print_mode_info(mode_info)
        return
        
    # Switching mode
    if args.mode == 'autopilot' and not args.force:
        print("\n🔐 Autopilot Mode Confirmation 🔐")
        print("In Autopilot mode, SassyQueenCore can take actions without explicit confirmation")
        print("within the boundaries of safety protocols.")
        
        confirm = input("\nAre you sure you want to enable Autopilot mode? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("Autopilot mode activation cancelled.")
            return
            
    success, message = switcher.set_mode(args.mode)
    print(message)
    
    if success:
        mode_info = switcher.get_mode_info()
        print_mode_info(mode_info)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMode control interrupted. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 