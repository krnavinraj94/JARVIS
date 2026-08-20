"""
JARVIS - Command Parser
Turns recognized text into an (intent, args) pair, then dispatches to the
AdbController. Pattern matching is intentionally simple (regex/keywords)
so it's easy to read and extend without pulling in an NLP dependency.
"""

import re

import config
from adb_controller import AdbError


class CommandParser:
    def __init__(self, adb, speak_fn):
        """
        adb: an AdbController instance
        speak_fn: callable(str) -> None, used for spoken feedback (usually voice_engine.speak)
        """
        self.adb = adb
        self.speak = speak_fn

    def handle(self, text):
        """
        Parse `text` and execute the matching action.
        Returns False if the command means 'stop/exit the assistant', True otherwise.
        """
        if not text:
            return True

        text = text.strip().lower()

        try:
            # ---- exit ----
            if re.search(r"\b(exit|quit|stop|shut down|goodbye)\b", text):
                self.speak("Goodbye.")
                return False

            # ---- open app ----
            m = re.search(r"\bopen ([a-z0-9 ]+)", text)
            if m:
                return self._open_app(m.group(1).strip())

            # ---- close app ----
            m = re.search(r"\bclose ([a-z0-9 ]+)", text)
            if m:
                return self._close_app(m.group(1).strip())

            # ---- call ----
            m = re.search(r"\bcall ([0-9 +\-]+)", text)
            if m:
                number = m.group(1).strip()
                self.adb.make_call(number)
                self.speak(f"Calling {number}")
                return True

            if re.search(r"\bend call|hang up\b", text):
                self.adb.end_call()
                self.speak("Call ended.")
                return True

            # ---- SMS: "text 9876543210 saying I'm on my way" ----
            m = re.search(r"\btext ([0-9 +\-]+) saying (.+)", text)
            if m:
                number, message = m.group(1).strip(), m.group(2).strip()
                self.adb.send_sms(number, message)
                self.speak(f"Message ready to send to {number}")
                return True

            # ---- screenshot ----
            if "screenshot" in text or "take a screenshot" in text:
                path = self.adb.take_screenshot()
                self.speak(f"Screenshot saved to {path}")
                return True

            # ---- volume ----
            if "volume up" in text or "increase volume" in text:
                self.adb.volume_up()
                self.speak("Volume up.")
                return True
            if "volume down" in text or "decrease volume" in text:
                self.adb.volume_down()
                self.speak("Volume down.")
                return True
            if "mute" in text:
                self.adb.mute()
                self.speak("Muted.")
                return True

            # ---- media ----
            if "pause" in text or "play music" in text or "play" == text:
                self.adb.play_pause()
                self.speak("Toggled playback.")
                return True
            if "next song" in text or "next track" in text:
                self.adb.next_track()
                self.speak("Next track.")
                return True
            if "previous song" in text or "previous track" in text:
                self.adb.prev_track()
                self.speak("Previous track.")
                return True

            # ---- navigation ----
            if "go home" in text or text == "home":
                self.adb.press_home()
                self.speak("Going home.")
                return True
            if "go back" in text:
                self.adb.press_back()
                self.speak("Going back.")
                return True
            if "recent apps" in text:
                self.adb.press_recent_apps()
                self.speak("Showing recent apps.")
                return True

            # ---- lock / wake ----
            if "lock screen" in text or text == "lock":
                self.adb.lock_screen()
                self.speak("Locking screen.")
                return True
            if "wake up" in text or "wake screen" in text:
                self.adb.wake_screen()
                self.speak("Waking screen.")
                return True

            # ---- type text: "type hello there" ----
            m = re.search(r"\btype (.+)", text)
            if m:
                self.adb.type_text(m.group(1).strip())
                self.speak("Typed.")
                return True

            # ---- web search: "search for nearest coffee shop" ----
            m = re.search(r"\bsearch(?: for)? (.+)", text)
            if m:
                query = m.group(1).strip()
                self.adb.web_search(query)
                self.speak(f"Searching for {query}")
                return True

            # ---- battery ----
            if "battery" in text:
                level = self.adb.battery_level()
                if level is not None:
                    self.speak(f"Battery is at {level} percent.")
                else:
                    self.speak("Couldn't read battery level.")
                return True

            # ---- storage ----
            if "storage" in text or "how much space" in text:
                info = self.adb.storage_info()
                if info is not None:
                    used, total, percent = info
                    if percent is not None:
                        self.speak(f"You've used {used} of {total}, that's {percent} percent full.")
                    else:
                        self.speak(f"You've used {used} of {total}.")
                else:
                    self.speak("Couldn't read storage info.")
                return True

            # ---- fallback ----
            self.speak("Sorry, I didn't understand that command.")
            return True

        except AdbError as e:
            self.speak("I ran into a problem talking to the phone.")
            print(f"[command_parser] AdbError: {e}")
            return True

    # ------------------------------------------------------------------ #
    def _open_app(self, spoken_name):
        package = self._resolve_package(spoken_name)
        if not package:
            self.speak(f"I don't know the app {spoken_name}. Add it to config.APP_PACKAGES.")
            return True
        self.adb.open_app(package)
        self.speak(f"Opening {spoken_name}")
        return True

    def _close_app(self, spoken_name):
        package = self._resolve_package(spoken_name)
        if not package:
            self.speak(f"I don't know the app {spoken_name}.")
            return True
        self.adb.close_app(package)
        self.speak(f"Closing {spoken_name}")
        return True

    @staticmethod
    def _resolve_package(spoken_name):
        spoken_name = spoken_name.strip().lower()
        if spoken_name in config.APP_PACKAGES:
            return config.APP_PACKAGES[spoken_name]
        # loose match, e.g. "the camera app" -> "camera"
        for name, package in config.APP_PACKAGES.items():
            if name in spoken_name:
                return package
        return None
