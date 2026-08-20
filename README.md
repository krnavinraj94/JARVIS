# JARVIS — Voice-Controlled Phone Assistant (PC + ADB Edition)

Control your Android phone with your voice from your PC. You speak into
your computer's microphone; JARVIS recognizes the command and sends it
to the phone over `adb` (USB or Wi-Fi debugging) — no app needs to be
installed on the phone.

## How it works

```
Mic (PC) --> speech_recognition --> command_parser --> adb_controller --> adb shell --> Phone
                                          |
                                          v
                                   pyttsx3 (spoken feedback)
```

- `voice_engine.py` — mic capture (speech-to-text) and spoken feedback (text-to-speech)
- `command_parser.py` — turns recognized phrases into actions (regex/keyword matching)
- `adb_controller.py` — wraps every `adb` interaction (calls, apps, volume, screenshots, navigation...)
- `config.py` — all the settings you're likely to want to change
- `main.py` — wires it together and runs the listen loop
- `test_command_parser.py` — routing tests you can run without a phone/mic

## Setup

### 1. Install Android platform-tools (adb)
Download from https://developer.android.com/tools/releases/platform-tools
and add the folder to your PATH (or set `ADB_PATH` in `config.py` to the
full path of the `adb` executable).

### 2. Enable USB debugging on the phone
Settings → About phone → tap "Build number" 7 times to unlock Developer
options → Settings → Developer options → enable **USB debugging**.

### 3. Connect the phone
Plug in via USB (or set up `adb connect <ip>:5555` for wireless) and
accept the "Allow USB debugging?" RSA prompt on the phone screen.
Verify with:
```bash
adb devices
```
It should list your device as `device` (not `unauthorized` or `offline`).

### 4. Install Python dependencies
```bash
pip install -r requirements.txt
```
- **Windows**: `pip install pyaudio` usually works directly; if it fails, install the matching wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio or `pip install pipwin && pipwin install pyaudio`.
- **macOS**: `brew install portaudio` first, then `pip install pyaudio`.
- **Linux**: `sudo apt install portaudio19-dev python3-pyaudio` first.

`speech_recognition`'s default engine (`recognize_google`) uses Google's
free web API and **requires internet access**. Swap in `Vosk` or
`Whisper` in `voice_engine.py` if you need fully offline recognition.

### 5. Run it
```bash
python main.py
```
Say **"Jarvis"** to wake it up, wait for "Yes?", then give a command —
e.g. *"open whatsapp"*, *"call 9876543210"*, *"take a screenshot"*.

Set `USE_WAKE_WORD = False` in `config.py` to skip the wake word and
listen continuously instead.

## Supported commands (English + Hindi)

| Say (English) | Say (Hindi) | Action |
|---|---|---|
| "open camera" | "कैमरा खोलो" | launch an app |
| "close camera" | "कैमरा बंद करो" | force-stop an app |
| "call 9876543210" | "9876543210 को कॉल करो" | dials the number |
| "end call" / "hang up" | "कॉल काटो" | hangs up |
| "text 9876543210 saying running late" | — | opens SMS compose pre-filled |
| "take a screenshot" | "स्क्रीनशॉट लो" | saves a PNG to `./screenshots/` |
| "volume up" | "आवाज़ बढ़ाओ" | raises media volume |
| "volume down" | "आवाज़ कम करो" | lowers media volume |
| "mute" | "म्यूट करो" | mutes |
| "play" / "pause" / "play music" / "play a song" | "बजाओ" / "गाना" / "रोको" | toggles playback |
| "next track" / "skip" | "अगला गाना" | next track |
| "previous track" | "पिछला गाना" | previous track |
| "go home" | "होम जाओ" | home button |
| "go back" | "पीछे जाओ" | back button |
| "recent apps" | "हाल के ऐप" | app switcher |
| "lock screen" | "लॉक करो" | locks the screen |
| "wake up" | "स्क्रीन जगाओ" | wakes the screen |
| "type hello world" | — | types text into the focused field |
| "search for nearest coffee shop" | "कॉफी शॉप खोजो" | opens a Google search |
| "what is my battery" | "बैटरी" | reads battery percentage |
| "check my storage" / "how much space" | "स्टोरेज" / "कितनी जगह" | reads storage used/total |
| "switch to hindi" | "हिंदी में बदलो" | switches recognition language to Hindi |
| "switch to english" | "अंग्रेज़ी में बदलो" | switches recognition language to English |
| "exit" / "quit" / "stop" | "अलविदा" / "बंद हो जाओ" | shuts JARVIS down |

### Opening apps JARVIS doesn't already know about

You are **not** limited to the apps in `config.py`. "Open \<app\>" first
checks the curated `APP_PACKAGES` dict (fast, handles naming quirks —
e.g. "phone" → the dialer package), then falls back to searching every
package actually installed on your phone for a name match — so
"open telegram", "open netflix", etc. work even if you never configured
them, as long as the app's package name contains a recognizable form of
what you said. Package list is fetched once per run and cached.

For Hindi app names, spoken Devanagari has to be translated to the
English key first (package names are always Latin script) — this uses
`HINDI_APP_ALIASES` in `config.py`. It covers common apps out of the
box; add more entries there if an app you use isn't recognized in Hindi.

### Switching languages

Google's free speech API needs one language per recognition call — it
doesn't reliably auto-detect Hindi vs. English mid-sentence (it will
"transcribe" the wrong language into garbage rather than fail cleanly).
So JARVIS starts in whichever language `config.RECOGNITION_LANGUAGE` is
set to (default `"en-IN"`), and you switch by voice with
**"switch to hindi"** / **"हिंदी में बदलो"** — after that it listens in
Hindi until you switch back.

## Known limitations / things to be aware of

- **SMS auto-send**: `send_sms` opens the SMS composer pre-filled but
  does **not** tap Send automatically — this is intentional so a
  misheard command can't fire off a text. If you want auto-send, you'd
  need an accessibility-service trick or a rooted `service call` command,
  which is a bigger step and worth doing deliberately, not by default.
- **Calling requires an active SIM** and, on some OEM skins, a specific
  default dialer package — the `am start -a android.intent.action.CALL`
  intent works on stock Android/most phones but a few manufacturers
  restrict it.
- **Recognition accuracy** depends entirely on Google's web speech API;
  noisy environments or heavy accents will need `recognizer.adjust_for_ambient_noise`
  tuning (already done once at startup) or a different STT backend.
- **`input text`** can't type emoji or some special characters — this is
  an Android `adb` limitation, not something this project can work around.

## Troubleshooting

- `adb: command not found` → platform-tools isn't on PATH; set `ADB_PATH` in `config.py`.
- `No devices found` → check the USB cable/driver, confirm USB debugging is on, and accept the RSA prompt on the phone.
- Mic not detected → run `python -c "from voice_engine import VoiceEngine; print(VoiceEngine.list_microphones())"` and set `MIC_INDEX` in `config.py`.
- Commands silently do nothing → run with the phone screen on and unlocked first; many `input`/`am` commands need an unlocked screen to take effect.
