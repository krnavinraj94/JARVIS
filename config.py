"""
JARVIS - Configuration
Central place for tunables so nothing is hard-coded deep inside logic files.
"""

# ---- ADB ----
# Leave as None to auto-use the only connected device.
# Set to a string like "R58M12ABCD" (from `adb devices`) if you have
# multiple devices/emulators connected at once.
ADB_DEVICE_SERIAL = None

# Path to the adb binary. "adb" works if it's on PATH; otherwise give
# the full path, e.g. r"C:\platform-tools\adb.exe"
ADB_PATH = "adb"

# ---- Voice ----
WAKE_WORD = "jarvis"          # say "jarvis, open camera"
USE_WAKE_WORD = True          # False = listen for commands continuously, no wake word
LISTEN_TIMEOUT = 5            # seconds to wait for speech to start
PHRASE_TIME_LIMIT = 6         # max seconds for a single command
MIC_INDEX = None              # None = default system mic; else int index from list_microphones()

# ---- Language ----
# Google's free speech API needs ONE language per recognition call — it can't
# reliably auto-detect Hindi vs English on the fly (it'll happily mis-transcribe
# Hindi speech using the English model instead of failing). So JARVIS starts in
# one language and you switch with a voice command:
#   "switch to hindi"  /  "हिंदी में बदलो"
#   "switch to english" /  "अंग्रेज़ी में बदलो"
RECOGNITION_LANGUAGE = "en-IN"     # starting language: "en-IN" or "hi-IN"
LANGUAGE_CODES = {
    "english": "en-IN",
    "hindi": "hi-IN",
}

# ---- TTS ----
TTS_RATE = 175
TTS_VOLUME = 1.0

# ---- App package map ----
# Map spoken app names -> Android package names. Extend as needed.
# Find a package name with: adb shell pm list packages | grep <hint>
APP_PACKAGES = {
    "whatsapp": "com.whatsapp",
    "camera": "com.android.camera",
    "chrome": "com.android.chrome",
    "youtube": "com.google.android.youtube",
    "gmail": "com.google.android.gm",
    "maps": "com.google.android.apps.maps",
    "settings": "com.android.settings",
    "phone": "com.android.dialer",
    "messages": "com.google.android.apps.messaging",
    "gallery": "com.google.android.apps.photos",
    "spotify": "com.spotify.music",
    "instagram": "com.instagram.android",
}

# Common Hindi (Devanagari) spellings of app names -> the matching key above.
# Package names are always in Latin script, so a Devanagari spoken name has to
# be translated to its English key before package lookup will work at all.
# Add more as you find gaps.
HINDI_APP_ALIASES = {
    "व्हाट्सएप": "whatsapp",
    "व्हाट्सएप्प": "whatsapp",
    "कैमरा": "camera",
    "क्रोम": "chrome",
    "यूट्यूब": "youtube",
    "जीमेल": "gmail",
    "मैप्स": "maps",
    "नक्शा": "maps",
    "सेटिंग": "settings",
    "सेटिंग्स": "settings",
    "फोन": "phone",
    "मैसेज": "messages",
    "मैसेजेस": "messages",
    "गैलरी": "gallery",
    "फोटो": "gallery",
    "स्पॉटिफाई": "spotify",
    "इंस्टाग्राम": "instagram",
}
