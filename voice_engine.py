"""
JARVIS - Voice Engine
Handles microphone capture -> text (speech_recognition) and
text -> speech (pyttsx3). Kept separate from command logic so you can
swap in Whisper, Vosk, etc. later without touching the rest of the app.
"""

import speech_recognition as sr
import pyttsx3

import config


class VoiceEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone(device_index=config.MIC_INDEX)

        self.tts = pyttsx3.init()
        self.tts.setProperty("rate", config.TTS_RATE)
        self.tts.setProperty("volume", config.TTS_VOLUME)

        # One-time ambient noise calibration so recognition doesn't
        # trigger on background hum.
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

    @staticmethod
    def list_microphones():
        return sr.Microphone.list_microphone_names()

    def speak(self, text):
        print(f"JARVIS: {text}")
        self.tts.say(text)
        self.tts.runAndWait()

    def listen_once(self, timeout=None, phrase_time_limit=None):
        """
        Capture one utterance from the mic and return recognized text
        (lowercase, stripped), or None if nothing was understood.
        """
        timeout = timeout or config.LISTEN_TIMEOUT
        phrase_time_limit = phrase_time_limit or config.PHRASE_TIME_LIMIT

        with self.microphone as source:
            try:
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
            except sr.WaitTimeoutError:
                return None

        try:
            text = self.recognizer.recognize_google(audio)
            return text.lower().strip()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[voice_engine] Speech recognition service error: {e}")
            return None

    def wait_for_wake_word(self, wake_word=None):
        """Block until the wake word is heard. Returns once triggered."""
        wake_word = (wake_word or config.WAKE_WORD).lower()
        print(f"Listening for wake word '{wake_word}'...")
        while True:
            heard = self.listen_once(timeout=None, phrase_time_limit=3)
            if heard and wake_word in heard:
                return
