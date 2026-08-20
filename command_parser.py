"""
JARVIS - Command Parser
Turns recognized text into an (intent, args) pair, then dispatches to the
AdbController. Supports English and Hindi trigger phrases for every command.
Language itself is switched via voice ("switch to hindi") — see voice_engine.py;
this file just needs to recognize the switch command and the two phrasings.

App resolution: checks the curated config.APP_PACKAGES dict first (fast,
handles naming quirks), then falls back to a live search of every package
installed on the phone (fetched once via adb and cached), so JARVIS can open
apps you never explicitly configured.
"""

import re

import config
from adb_controller import AdbError


class CommandParser:
    def __init__(self, adb, speak_fn, set_language_fn=None):
        """
        adb: an AdbController instance
        speak_fn: callable(str) -> None, spoken feedback (usually voice_engine.speak)
        set_language_fn: callable(str) -> None, switches STT language (usually voice_engine.set_language)
        """
        self.adb = adb
        self.speak = speak_fn
        self.set_language = set_language_fn
        self._installed_packages_cache = None

    def handle(self, text):
        """
        Parse `text` and execute the matching action.
        Returns False if the command means 'stop/exit the assistant', True otherwise.
        """
        if not text:
            return True

        text = text.strip().lower()

        try:
            # ---- language switch ----
            if self._match(text, [r"\bswitch to hindi\b", "हिंदी में बदलो", "हिंदी में बात करो"]):
                if self.set_language:
                    self.set_language(config.LANGUAGE_CODES["hindi"])
                self.speak("अब मैं हिंदी में सुन रहा हूँ।")
                return True
            if self._match(text, [r"\bswitch to english\b", "अंग्रेज़ी में बदलो", "इंग्लिश में बात करो"]):
                if self.set_language:
                    self.set_language(config.LANGUAGE_CODES["english"])
                self.speak("Now listening in English.")
                return True

            # ---- exit ----
            if self._match(text, [r"\b(exit|quit|stop|shut down|goodbye)\b", "बंद हो जाओ", "अलविदा", "बाय जार्विस"]):
                self.speak("Goodbye.")
                return False

            # ---- open app ----
            # English: "open <app>"   Hindi: "<app> खोलो" / "<app> खोल दो"
            m = re.search(r"\bopen ([a-z0-9 ]+)", text)
            if m:
                return self._open_app(m.group(1).strip())
            m = re.search(r"^(.+?)\s*(?:खोलो|खोल दो)\s*$", text)
            if m:
                return self._open_app(m.group(1).strip())

            # ---- close app ----
            # English: "close <app>"   Hindi: "<app> बंद करो"
            m = re.search(r"\bclose ([a-z0-9 ]+)", text)
            if m:
                return self._close_app(m.group(1).strip())
            m = re.search(r"^(.+?)\s*बंद करो\s*$", text)
            if m:
                return self._close_app(m.group(1).strip())

            # ---- call ----
            m = re.search(r"\bcall ([0-9 +\-]+)", text) or re.search(r"([0-9 +\-]{6,})\s*(?:को कॉल करो|पर कॉल करो)", text)
            if m:
                number = m.group(1).strip()
                self.adb.make_call(number)
                self.speak(f"Calling {number}")
                return True

            if self._match(text, [r"\bend call\b", r"\bhang up\b", "कॉल काटो", "कॉल बंद करो"]):
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
            if self._match(text, ["screenshot", "स्क्रीनशॉट"]):
                path = self.adb.take_screenshot()
                self.speak(f"Screenshot saved to {path}")
                return True

            # ---- volume ----
            if self._match(text, ["volume up", "increase volume", "आवाज़ बढ़ाओ", "आवाज बढ़ाओ"]):
                self.adb.volume_up()
                self.speak("Volume up.")
                return True
            if self._match(text, ["volume down", "decrease volume", "आवाज़ कम करो", "आवाज कम करो"]):
                self.adb.volume_down()
                self.speak("Volume down.")
                return True
            if self._match(text, ["mute", "म्यूट करो", "आवाज़ बंद करो"]):
                self.adb.mute()
                self.speak("Muted.")
                return True

            # ---- media ----
            # Broadened: any mention of playing/pausing/music/song toggles play-pause,
            # since a single ADB keyevent can't distinguish "play X" from "resume".
            if self._match(text, [r"\bplay\b", r"\bpause\b", "song", "music",
                                    "बजाओ", "गाना", "प्ले करो", "रोको", "पॉज़ करो"]):
                self.adb.play_pause()
                self.speak("Toggled playback.")
                return True
            if self._match(text, ["next song", "next track", "skip", "अगला गाना", "अगला गीत"]):
                self.adb.next_track()
                self.speak("Next track.")
                return True
            if self._match(text, ["previous song", "previous track", "पिछला गाना", "पिछला गीत"]):
                self.adb.prev_track()
                self.speak("Previous track.")
                return True

            # ---- navigation ----
            if self._match(text, [r"\bgo home\b", r"^home$", "होम जाओ", "होम स्क्रीन"]):
                self.adb.press_home()
                self.speak("Going home.")
                return True
            if self._match(text, [r"\bgo back\b", "पीछे जाओ", "बैक करो"]):
                self.adb.press_back()
                self.speak("Going back.")
                return True
            if self._match(text, ["recent apps", "हाल के ऐप"]):
                self.adb.press_recent_apps()
                self.speak("Showing recent apps.")
                return True

            # ---- lock / wake ----
            if self._match(text, [r"\block screen\b", r"^lock$", "स्क्रीन लॉक करो", "लॉक करो"]):
                self.adb.lock_screen()
                self.speak("Locking screen.")
                return True
            if self._match(text, [r"\bwake up\b", r"\bwake screen\b", "स्क्रीन जगाओ", "जगाओ"]):
                self.adb.wake_screen()
                self.speak("Waking screen.")
                return True

            # ---- type text: "type hello there" ----
            m = re.search(r"\btype (.+)", text)
            if m:
                self.adb.type_text(m.group(1).strip())
                self.speak("Typed.")
                return True

            # ---- storage ----
            if self._match(text, ["storage", "how much space", "स्टोरेज", "कितनी जगह"]):
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

            # ---- battery ---- (checked before generic "search" so it doesn't get swallowed)
            if self._match(text, ["battery", "बैटरी"]):
                level = self.adb.battery_level()
                if level is not None:
                    self.speak(f"Battery is at {level} percent.")
                else:
                    self.speak("Couldn't read battery level.")
                return True

            # ---- web search: "search for nearest coffee shop" ----
            m = re.search(r"\bsearch(?: for)? (.+)", text) or re.search(r"^(.+?) खोजो$", text)
            if m:
                query = m.group(1).strip()
                self.adb.web_search(query)
                self.speak(f"Searching for {query}")
                return True

            # ---- fallback ----
            self.speak("Sorry, I didn't understand that command.")
            return True

        except AdbError as e:
            self.speak("I ran into a problem talking to the phone.")
            print(f"[command_parser] AdbError: {e}")
            return True

    # ------------------------------------------------------------------ #
    @staticmethod
    def _match(text, patterns):
        """True if any pattern matches. Plain substrings (incl. Hindi) are
        checked with `in`; anything containing regex metacharacters (\\b, ^, $,
        etc.) is matched with re.search."""
        for p in patterns:
            if any(ch in p for ch in ("\\", "^", "$", "(", ")", "[", "]", "|")):
                if re.search(p, text):
                    return True
            elif p in text:
                return True
        return False

    def _open_app(self, spoken_name):
        package = self._resolve_package(spoken_name)
        if not package:
            self.speak(f"I couldn't find an app called {spoken_name} on your phone.")
            return True
        self.adb.open_app(package)
        self.speak(f"Opening {spoken_name}")
        return True

    def _close_app(self, spoken_name):
        package = self._resolve_package(spoken_name)
        if not package:
            self.speak(f"I couldn't find an app called {spoken_name}.")
            return True
        self.adb.close_app(package)
        self.speak(f"Closing {spoken_name}")
        return True

    # ------------------------------------------------------------------ #
    def _get_installed_packages(self):
        """Fetch and cache the phone's installed package list (fetched once per run)."""
        if self._installed_packages_cache is None:
            try:
                self._installed_packages_cache = self.adb.list_installed_packages()
            except AdbError:
                self._installed_packages_cache = []
        return self._installed_packages_cache

    def _resolve_package(self, spoken_name):
        """
        Resolve a spoken app name to a package name.
        1. Exact match in config.APP_PACKAGES (curated, handles naming quirks)
        2. Loose substring match in config.APP_PACKAGES
        3. Dynamic substring search across every package actually installed
           on the phone, so unlisted apps still work.
        """
        spoken_name = spoken_name.strip().lower()

        # Devanagari spoken name -> translate to the English key first.
        for hindi_name, english_key in config.HINDI_APP_ALIASES.items():
            if hindi_name in spoken_name:
                spoken_name = english_key
                break

        if spoken_name in config.APP_PACKAGES:
            return config.APP_PACKAGES[spoken_name]
        for name, package in config.APP_PACKAGES.items():
            if name in spoken_name:
                return package

        normalized = re.sub(r"[^a-z0-9]", "", spoken_name)
        if not normalized:
            return None

        packages = self._get_installed_packages()
        candidates = [
            p for p in packages
            if normalized in p.lower().replace(".", "").replace("_", "")
        ]
        if not candidates:
            return None
        # Prefer the shortest matching package name — usually the most specific
        # (e.g. "com.whatsapp" over "com.whatsapp.w4b" for "whatsapp").
        candidates.sort(key=len)
        return candidates[0]
