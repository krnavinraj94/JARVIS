"""
JARVIS - Voice-Controlled Phone Assistant (PC + ADB Edition)
Entry point. Wires together voice input, command parsing, and the
ADB-controlled phone.

Usage:
    python main.py
"""

import sys

import config
from adb_controller import AdbController, AdbError
from voice_engine import VoiceEngine
from command_parser import CommandParser


def main():
    print("Starting JARVIS...")

    # 1. Connect to phone first — fail fast with a clear message if not ready.
    try:
        adb = AdbController()
        devices = adb.ensure_device_connected()
        print(f"Connected device(s): {devices}")
    except AdbError as e:
        print(f"[FATAL] {e}")
        sys.exit(1)

    # 2. Set up voice I/O.
    try:
        voice = VoiceEngine()
    except OSError as e:
        print(f"[FATAL] Could not access microphone: {e}")
        sys.exit(1)

    parser = CommandParser(adb, speak_fn=voice.speak)

    voice.speak("JARVIS online.")

    # 3. Main loop.
    running = True
    while running:
        try:
            if config.USE_WAKE_WORD:
                voice.wait_for_wake_word()
                voice.speak("Yes?")

            text = voice.listen_once()
            if text is None:
                continue  # nothing understood, keep listening

            print(f"You said: {text}")
            running = parser.handle(text)

        except KeyboardInterrupt:
            voice.speak("Shutting down.")
            break


if __name__ == "__main__":
    main()
