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

## Supported commands (examples)

| Say | Action |
|---|---|
| "open camera" / "close camera" | launch / force-stop an app |
| "call 9876543210" | dials the number |
| "end call" | hangs up |
| "text 9876543210 saying running late" | opens SMS compose pre-filled |
| "take a screenshot" | saves a PNG to `./screenshots/` |
| "volume up" / "volume down" / "mute" | media volume |
| "next track" / "previous track" / "pause" | media playback |
| "go home" / "go back" / "recent apps" | navigation keys |
| "lock screen" / "wake up" | power key |
| "type hello world" | types text into the focused field |
| "search for nearest coffee shop" | opens a Google search in the browser |
| "what is my battery" | reads battery percentage |
| "exit" / "quit" / "stop" | shuts JARVIS down |

Add more apps by editing `APP_PACKAGES` in `config.py`. Find a package
name with:
```bash
adb shell pm list packages | grep <hint>
```

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
