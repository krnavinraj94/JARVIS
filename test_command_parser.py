"""
Quick logic test for CommandParser using a mock AdbController.
Doesn't need a real phone, mic, or adb install — just verifies that
spoken text routes to the right method calls.
Run: python3 test_command_parser.py
"""

from command_parser import CommandParser


class MockAdb:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def recorder(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "take_screenshot":
                return "screenshots/fake.png"
            if name == "battery_level":
                return "77"
            return None
        return recorder


def run_case(text, expect_method, expect_args=None):
    mock = MockAdb()
    spoken = []
    parser = CommandParser(mock, speak_fn=lambda s: spoken.append(s))
    result = parser.handle(text)

    methods_called = [c[0] for c in mock.calls]
    ok = expect_method in methods_called
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] '{text}' -> expected {expect_method}, got {methods_called}")
    if expect_args is not None:
        for call in mock.calls:
            if call[0] == expect_method:
                args_ok = call[1] == expect_args
                print(f"    args {'match' if args_ok else 'MISMATCH'}: {call[1]} vs expected {expect_args}")
    return ok, result


cases = [
    ("open whatsapp", "open_app"),
    ("close camera", "close_app"),
    ("call 987 654 3210", "make_call"),
    ("end call", "end_call"),
    ("text 9876543210 saying I am on my way", "send_sms"),
    ("take a screenshot", "take_screenshot"),
    ("volume up", "volume_up"),
    ("volume down", "volume_down"),
    ("mute", "mute"),
    ("next track", "next_track"),
    ("go home", "press_home"),
    ("go back", "press_back"),
    ("lock screen", "lock_screen"),
    ("wake up", "wake_screen"),
    ("type hello world", "type_text"),
    ("search for nearest coffee shop", "web_search"),
    ("what is my battery", "battery_level"),
]

all_pass = True
for text, method in cases:
    ok, _ = run_case(text, method)
    all_pass = all_pass and ok

_, keep_running = run_case("jarvis please exit now", "___never_called___")
print(f"\n'exit' command returns running=False as expected: {keep_running is False}")

print("\nALL PASS" if all_pass else "\nSOME FAILED")
