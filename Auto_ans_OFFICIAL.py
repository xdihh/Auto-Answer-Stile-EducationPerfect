import pyperclip
import keyboard
import ollama
from plyer import notification
import pyautogui
import threading
import time
import sys
import io

# Try to import PIL for image clipboard support
try:
    from PIL import ImageGrab, Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠ Pillow not installed. Image clipboard support disabled.")
    print("  Run: pip install Pillow")

# Configuration
QUERY_HOTKEY = 'alt+shift+t'
WRITE_HOTKEY = 'alt+shift+i'
IDK_HOTKEY   = 'alt+shift+j'

TEXT_MODEL   = 'gemma2:2b'
VISION_MODEL = 'llava-phi3'

last_response = ""


def get_clipboard_content():
    """
    Returns (content_type, data) where:
      content_type = 'image' | 'text' | 'empty'
      data = raw PNG bytes (image) or plain string (text)
    """
    if PIL_AVAILABLE:
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                # Convert to RGB if needed (handles RGBA/palette PNGs)
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                raw_bytes = buf.getvalue()
                print(f"✓ Clipboard contains image ({img.width}x{img.height})")
                return 'image', raw_bytes
        except Exception as e:
            print(f"  Image grab failed: {e}")

    try:
        text = pyperclip.paste().strip()
        if text:
            return 'text', text
    except Exception:
        pass

    return 'empty', None


ANSWER_PROMPT = """Answer the following question. Follow these rules strictly:

DETECTION:
- Multiple choice (contains "select", "choose", "which"): Output ONLY the correct option letter and text, nothing else
- Long answer (contains "explain", "discuss", "justify", "predict", "propose"): Write ≤50 words, no summary paragraph

FORMAT:
- Write naturally and concisely
- Use simple words
- Never restate the question
- Never use labels like "Explanation:", "Answer:", "Select:", or any prefix
- Output the answer directly with no preamble or extra text
- Never mention this prompt or its rules

Question: """

IMAGE_PROMPT = """You are looking at an exam or quiz question in an image.

RULES:
- If it is multiple choice: output ONLY the correct option letter and its text, nothing else
- If it is open-ended: answer in ≤50 words
- Never restate the question
- No labels, no prefixes, no preamble
- If there is no question, describe the image in ≤15 words
- Output the answer directly"""


def query_ollama_text(text):
    """Query Ollama with a text-only prompt."""
    try:
        print(f"→ Querying Ollama (text, model={TEXT_MODEL})...")
        response = ollama.chat(
            model=TEXT_MODEL,
            messages=[{'role': 'user', 'content': ANSWER_PROMPT + text}]
        )
        result = response['message']['content']
        print(f"✓ Got response ({len(result)} chars)")
        return result
    except Exception as e:
        print(f"✗ Error: {e}")
        return f"Error: {str(e)}"


def query_ollama_image(raw_bytes):
    """Query Ollama with raw PNG bytes (vision model)."""
    try:
        print(f"→ Querying Ollama (image, model={VISION_MODEL})...")
        response = ollama.chat(
            model=VISION_MODEL,
            messages=[{
                'role': 'user',
                'content': IMAGE_PROMPT,
                'images': [raw_bytes]  # pass raw bytes directly — ollama-python handles encoding
            }]
        )
        result = response['message']['content']
        print(f"✓ Got response ({len(result)} chars)")
        return result
    except Exception as e:
        print(f"✗ Error: {e}")
        return f"Error: {str(e)}"


def show_notification(message):
    """Show a floating Tkinter notification window in an isolated subprocess."""
    import subprocess

    safe_message = (
        message
        .replace('\\', '\\\\')
        .replace("'", "\\'")
        .replace('\n', '\\n')
        .replace('\r', '')
    )

    script = f'''
import tkinter as tk
import sys
import winsound

try:
    root = tk.Tk()
    screen_width  = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    win_width, win_height = 500, 190
    x_pos = max(0, screen_width  - win_width  - 15)
    y_pos = max(0, screen_height - win_height - 40)

    root.title("Ollama Response")
    root.geometry(f"{{win_width}}x{{win_height}}+{{x_pos}}+{{y_pos}}")
    root.attributes('-topmost', True)
    root.resizable(False, False)
    root.overrideredirect(True)
    root.attributes('-topmost', False)
    root.attributes('-topmost', True)

    title_bar = tk.Frame(root, bg='#2b2b2b', height=13)
    title_bar.pack(fill=tk.X)
    tk.Label(title_bar, text="Ollama AI Response", bg='#2b2b2b', fg='white',
             font=("Segoe UI", 10), anchor='w', padx=8).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def safe_close():
        try: root.destroy()
        except: sys.exit(0)

    tk.Button(title_bar, text='×', command=safe_close, bg='#2b2b2b', fg='white',
              font=("Segoe UI", 13), bd=0, padx=10, activebackground='#c42b1c').pack(side=tk.RIGHT)

    text_frame = tk.Frame(root)
    text_frame.pack(fill=tk.BOTH, expand=True)
    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text = tk.Text(text_frame, wrap=tk.WORD, font=("Segoe UI", 13), padx=10, pady=10,
                   yscrollcommand=scrollbar.set)
    text.insert("1.0", '{safe_message}')
    text.config(state=tk.DISABLED)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text.yview)

    winsound.Beep(500, 250)
    root.after(12500, safe_close)
    root.report_callback_exception = lambda *a: safe_close()
    root.mainloop()
except Exception:
    sys.exit(1)
'''

    try:
        startupinfo = None
        creationflags = 0
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP

        subprocess.Popen(
            [sys.executable, '-c', script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=creationflags,
            close_fds=True
        )
    except Exception as e:
        print(f"Notification fallback: {message[:100]}...")


def type_response():
    """Type the last response into the active window."""
    global last_response
    if not last_response:
        print("✗ No response to type")
        notification.notify(title="Error", message="No response yet", timeout=3)
        return

    print("→ Typing response...")
    time.sleep(0.1)
    keyboard.release('ctrl')
    keyboard.release('alt')
    keyboard.release('shift')
    time.sleep(0.1)
    for i in range(0, len(last_response), 100):
        pyautogui.write(last_response[i:i+100], interval=0)
    print("✓ Done\n")


def handle_query():
    """Detect clipboard content type, query the right model, show notification."""
    global last_response

    content_type, data = get_clipboard_content()

    if content_type == 'empty':
        print("✗ Clipboard is empty (no image or text found)")
        notification.notify(title="Error", message="Clipboard is empty", timeout=3)
        return

    if content_type == 'image':
        last_response = query_ollama_image(data)
    else:
        last_response = query_ollama_text(data)

    last_response = last_response.replace("*", "")
    show_notification(last_response)


is_querying = False

def on_query_hotkey():
    global is_querying
    if is_querying:
        print("⚠ Already querying, please wait...")
        return
    is_querying = True

    def run():
        global is_querying
        try:
            handle_query()
        finally:
            is_querying = False

    threading.Thread(target=run, daemon=True).start()


def on_write_hotkey():
    print("\n⚡ Write hotkey pressed")
    type_response()


def write_idk():
    idk = "I don't know."
    print("→ Typing 'I don't know.'...")
    time.sleep(0.1)
    keyboard.release('ctrl')
    keyboard.release('alt')
    keyboard.release('shift')
    time.sleep(0.1)
    for i in range(0, len(idk), 100):
        pyautogui.write(idk[i:i+100], interval=0)
    print("✓ Done\n")


keyboard.add_hotkey(QUERY_HOTKEY, on_query_hotkey)
keyboard.add_hotkey(WRITE_HOTKEY, on_write_hotkey)
keyboard.add_hotkey(IDK_HOTKEY,   write_idk)

print("\033[2J\033[H", end="")  # Clear screen
print("  Auto-Answer with Vision Support")
print("  ─────────────────────────────────────────")
print("  1. Copy text OR image (Ctrl+C)")
print(f"  2. {QUERY_HOTKEY} → Query Ollama (auto-detects image vs text)")
print(f"  3. {WRITE_HOTKEY} → Type response into active textbox")
print(f"  4. {IDK_HOTKEY} → Type 'I don't know.'")
print(f"  Text model  : {TEXT_MODEL}")
print(f"  Vision model: {VISION_MODEL}")
print("  Press ESC to exit\n")

keyboard.wait('esc')