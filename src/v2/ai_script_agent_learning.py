import os
from openai import OpenAI
import pyaudio
import wave
import subprocess
import sys
import sqlite3
from typing import Optional, Tuple
from datetime import datetime
import json
import argparse

# Get API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable is not set")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

# Audio recording constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "temp.wav"

class ScriptLearningAgent:
    def __init__(self, db_path: str = "script_solutions.db", enable_verification: bool = False):
        self.db_path = db_path
        self.enable_verification = enable_verification
        self.setup_database()

    def setup_database(self):
        """Initialize SQLite database with necessary tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS solutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    applescript TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    verified_success BOOLEAN,
                    error_message TEXT,
                    feedback TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def find_successful_solution(self, command: str) -> Optional[str]:
        """Find a successful and verified solution for a similar command"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT applescript FROM solutions 
                WHERE command = ? 
                AND success = 1 
                AND (verified_success = 1 OR verified_success IS NULL)
                ORDER BY timestamp DESC LIMIT 1
            """, (command,)).fetchone()
            return result[0] if result else None

    def save_solution(self, command: str, script: str, success: bool, 
                     verified_success: Optional[bool], error_message: Optional[str] = None,
                     feedback: Optional[str] = None):
        """Save a solution attempt to the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO solutions 
                (command, applescript, success, verified_success, error_message, feedback)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (command, script, success, verified_success, error_message, feedback))

    def generate_applescript(self, command: str) -> Optional[str]:
        """Generate AppleScript using past solutions and GPT"""
        previous_solution = self.find_successful_solution(command)
        
        try:
            messages = [
                {"role": "system", "content": """You are an expert AppleScript developer. Generate ONLY the raw AppleScript code with no explanations or formatting. For Numbers app, use this exact structure:

tell application "Numbers"
    activate
    delay 1
    tell document 1
        tell sheet 1
            tell table 1
                repeat with i from 1 to (get row count)
                    set hasText to false
                    -- Check cells in the row
                    repeat with j from 1 to (get column count)
                        set cellAddress to (get name of column j) & i
                        set cellValue to value of cell cellAddress
                        if cellValue is not missing value and cellValue is not "" then
                            -- Check if the value is specifically text (not a number)
                            if class of cellValue is text then
                                set hasText to true
                                exit repeat
                            end if
                        end if
                    end repeat
                    
                    -- If row has text, color all cells in that row
                    if hasText then
                        repeat with j from 1 to (get column count)
                            set cellAddress to (get name of column j) & i
                            set background color of cell cellAddress to {0, 65535, 0}
                        end repeat
                    end if
                end repeat
            end tell
        end tell
    end tell
end tell"""}
            ]
            
            if previous_solution:
                messages.extend([
                    {"role": "system", "content": "Here's a previously successful solution for reference:"},
                    {"role": "user", "content": previous_solution}
                ])

            messages.append({"role": "user", "content": f"Generate AppleScript code to: {command}"})

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=400
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating AppleScript: {str(e)}")
            return None

    def execute_applescript(self, script: str) -> Tuple[bool, Optional[str]]:
        """Execute AppleScript and return success status and error message"""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return True, None
            else:
                error_msg = result.stderr
                if "Not authorised to send Apple events" in error_msg:
                    print("\nPermission required! To allow this script to control applications, please:")
                    print("1. Open System Settings")
                    print("2. Go to Privacy & Security > Automation")
                    print("3. Find Python or Terminal in the list")
                    print("4. Enable the checkbox for the application you want to control")
                return False, error_msg
        except Exception as e:
            return False, str(e)

    def handle_command(self, command: str) -> bool:
        """Process a command and learn from the result"""
        script = self.generate_applescript(command)
        if not script:
            return False

        print("\nGenerated AppleScript:\n")
        print(script)

        approval = input("\nExecute this script? (yes/no): ").strip().lower()
        if approval not in ["yes", "y"]:
            return False

        success, error_message = self.execute_applescript(script)
        
        verified_success = None
        feedback = None
        
        if success and self.enable_verification:
            print("\nScript executed without errors.")
            verified = input("Did this achieve what you wanted? (yes/no): ").strip().lower()
            verified_success = verified in ['yes', 'y']
            if not verified_success:
                feedback = input("What wasn't correct about the result? ").strip()

        self.save_solution(command, script, success, verified_success, error_message, feedback)

        if success:
            print("\nScript executed successfully!")
            if verified_success is False:
                print("But the result wasn't what you wanted.")
                print(f"Feedback: {feedback}")
        else:
            print(f"\nExecution failed: {error_message}")

        return success

def record_audio(duration: int = RECORD_SECONDS) -> bool:
    """Record audio from the microphone"""
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)

        print(f"Recording for {duration} seconds...")
        frames = []

        for _ in range(0, int(RATE / CHUNK * duration)):
            data = stream.read(CHUNK)
            frames.append(data)

        print("Finished recording.")

        stream.stop_stream()
        stream.close()
        p.terminate()

        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        return True
    except Exception as e:
        print(f"Error recording audio: {str(e)}")
        return False

def transcribe_audio(filename: str) -> Optional[str]:
    """Transcribe audio using Whisper"""
    try:
        with open(filename, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description='AI Script Agent with verification')
    parser.add_argument('--verify', action='store_true', help='Enable result verification')
    args = parser.parse_args()

    agent = ScriptLearningAgent(enable_verification=args.verify)
    
    while True:
        mode = input("\nType 'speak' to record audio, 'type' to enter text, or 'quit' to exit: ").strip().lower()

        if mode == "quit":
            print("Exiting.")
            break
        elif mode == "speak":
            if not record_audio():
                continue
            command = transcribe_audio(WAVE_OUTPUT_FILENAME)
            if not command:
                continue
            print(f"\nTranscribed Text: {command}")
        elif mode == "type":
            command = input("\nEnter your command: ")
        else:
            print("Invalid option.")
            continue

        agent.handle_command(command)

if __name__ == "__main__":
    main()
