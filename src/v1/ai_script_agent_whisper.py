import os
from openai import OpenAI
import pyaudio
import wave
import subprocess
import sys
from typing import Optional

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

def record_audio(duration: int = RECORD_SECONDS) -> bool:
    """
    Record audio from the microphone for specified duration.
    Returns True if successful, False otherwise.
    """
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
    """
    Transcribe audio file using OpenAI's Whisper model.
    Returns transcribed text or None if transcription fails.
    """
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

def generate_applescript(user_command: str) -> Optional[str]:
    """
    Generate AppleScript from natural language command using GPT-3.5-turbo.
    Returns generated AppleScript or None if generation fails.
    """
    try:
        prompt = (
            "You are an assistant that translates natural language commands into AppleScript code. "
            "Only provide the AppleScript code and nothing else. "
            "Do NOT wrap the code in markdown code blocks (```) or any other formatting. "
            "Focus on common macOS automation tasks like:\n"
            "- Opening applications\n"
            "- Controlling system settings\n"
            "- Managing windows\n"
            "- Basic file operations\n"
            "- System notifications\n"
            "- Controlling applications like Numbers, Safari, Finder, etc.\n\n"
            "Important:\n"
            "1. Generate only the AppleScript code, no explanations\n"
            "2. Use proper AppleScript syntax and structure\n"
            "3. Include necessary delays and activation commands\n"
            "4. Handle application-specific requirements (like Numbers' table structure)\n\n"
            f"Command: {user_command}\n\nAppleScript Code:"
        )
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert AppleScript developer. Generate clean, working AppleScript code for any macOS automation task. Handle application-specific requirements and proper object hierarchies automatically."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )
        
        # Clean up the response to remove any markdown formatting
        code = response.choices[0].message.content.strip()
        # Remove any markdown code block markers
        code = code.replace("```applescript", "").replace("```", "").strip()
        return code
    except Exception as e:
        print(f"Error generating AppleScript: {str(e)}")
        return None

def execute_applescript(script: str) -> bool:
    """
    Execute AppleScript code and return True if successful.
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("\nScript executed successfully. Output:")
            print(result.stdout)
            return True
        else:
            error_msg = result.stderr
            if "Not authorised to send Apple events" in error_msg:
                print("\nPermission required! To allow this script to control applications, please:")
                print("1. Open System Settings")
                print("2. Go to Privacy & Security > Automation")
                print("3. Find Python or Terminal in the list")
                print("4. Enable the checkbox for the application you want to control (e.g., Numbers)")
                print("\nAfter granting permission, try running the command again.")
                return False
            else:
                print("\nError executing script:")
                print(error_msg)
                return False
    except Exception as e:
        print(f"\nError executing script: {str(e)}")
        return False

def main():
    while True:
        mode = input("\nType 'speak' to record audio, 'type' to enter text, or 'quit' to exit: ").strip().lower()

        if mode == "quit":
            print("Exiting.")
            break
        elif mode == "speak":
            if not record_audio():
                continue
            user_command = transcribe_audio(WAVE_OUTPUT_FILENAME)
            if not user_command:
                continue
            print(f"\nTranscribed Text: {user_command}")
        elif mode == "type":
            user_command = input("\nEnter your command: ")
        else:
            print("Invalid option.")
            continue

        # Generate AppleScript from user_command
        applescript_code = generate_applescript(user_command)
        if not applescript_code:
            continue
            
        print("\nGenerated AppleScript:\n")
        print(applescript_code)

        # Confirm & execute
        approval = input("\nExecute this script? (yes/no): ").strip().lower()
        if approval in ["yes", "y"]:
            execute_applescript(applescript_code)
        else:
            print("Execution cancelled.")

if __name__ == "__main__":
    main()
