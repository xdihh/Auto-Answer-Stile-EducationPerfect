# Configuration
QUERY_HOTKEY = 'ctrl+alt+t'
WRITE_HOTKEY = 'ctrl+alt+i'
PIC_HOTKEY = 'ctrl+alt+j'
TEXT_MODEL = 'gemma3:4b'
VISION_MODEL = 'granite3.2-vision:2b'
USE_VISION_WITH_TEXT = True  # Toggle vision for text queries, only use 'True' if you have fast ram
FULL_SCREENSHOT = False # Toggle take full screenshot auto (very slow) or manually select


import subprocess
import sys

packages = {
    "pyperclip": "pyperclip",
    "keyboard": "keyboard",
    "ollama": "ollama",
    "plyer": "plyer",
    "pyautogui": "pyautogui",
    "PIL": "pillow"
}
print("Installing required packages if absent")
for import_name, pip_name in packages.items():
    try:
        __import__(import_name)
    except ImportError:
        print(f"Installing {pip_name}...")
        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            pip_name
        ])
print("Done!")

import pyperclip
import keyboard
import ollama
from plyer import notification
import pyautogui
import threading
import time
from PIL import ImageGrab, Image
from io import BytesIO
import base64
from pathlib import Path

last_response = ""

def release_hotkeys():
    keyboard.release('ctrl')
    keyboard.release('alt')
    keyboard.release('shift')
    keyboard.release('j')
    keyboard.release('i')
    keyboard.release('t')

def query_ollama(text, model=None):
    """Query Ollama with specified or default model"""
    if model is None:
        model = TEXT_MODEL
    
    try:
        print(f"→ Querying Ollama ({model})...")
        response = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': text}]
        )
        result = response['message']['content']
        print(f"✓ Got response ({len(result)} chars)")
        return result
    except Exception as e:
        print(f"✗ Error: {e}")
        return f"Error: {str(e)}"


def query_ollama_image(raw_bytes):
    """Query Ollama with raw PNG bytes (vision model)"""
    try:
        print(f"→ Querying Ollama (image, model={VISION_MODEL})...")
        response = ollama.chat(
            model=VISION_MODEL,
            messages=[{
                'role': 'user',
                'content': """Answer the question using ONLY the image.

RULES:
- Read ALL text in the image carefully first
- Interpret diagrams literally
- Use labels, captions, axes, and tables carefully
- Infer intelligently if partially unclear
- Never restate the question

OUTPUT RULES:
- Multiple choice:
  Output ONLY the correct option(s)

- Short question:
  Answer in 1 sentence

- Explain/discuss/justify:
  Maximum 50 words

- No preamble
- No "Answer:"
- No markdown
- No restating the question
- Never describe the image unless asked
- Direct answer only""",
                'images': [raw_bytes]
            }]
        )
        result = response['message']['content']
        print(f"✓ Got response ({len(result)} chars)")
        return result
    except Exception as e:
        print(f"✗ Error: {e}")
        return f"Error: {str(e)}"


def show_notification(message):
    """Show a floating Tkinter notification window in an isolated subprocess"""
    import subprocess
    import sys
    
    # Capture currently focused window BEFORE spawning subprocess
    previous_hwnd = None
    if sys.platform == 'win32':
        try:
            import ctypes
            previous_hwnd = ctypes.windll.user32.GetForegroundWindow()
        except:
            pass
    
    safe_message = message.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '')
    script = f'''
import tkinter as tk
import sys
import winsound

try:
    root = tk.Tk()
    
    # Get screen dimensions safely
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Calculate position
    win_width, win_height = 500, 190
    x_pos = max(0, screen_width - win_width - 15)
    y_pos = max(0, screen_height - win_height - 40)
    
    root.title("Ollama Response")
    root.geometry(f"{{win_width}}x{{win_height}}+{{x_pos}}+{{y_pos}}")
    root.resizable(False, False)
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    
    # Title bar
    title_bar = tk.Frame(root, bg='#2b2b2b', height=13)
    title_bar.pack(fill=tk.X)
    
    tk.Label(title_bar, text="Ollama AI Response", bg='#2b2b2b', fg='white', 
             font=("Segoe UI", 10), anchor='w', padx=8).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def safe_close():
        try:
            root.destroy()
        except:
            sys.exit(0)
    
    tk.Button(title_bar, text='×', command=safe_close, bg='#2b2b2b', fg='white',
              font=("Segoe UI", 13), bd=0, padx=10, activebackground='#c42b1c').pack(side=tk.RIGHT)
    
    # Text widget with scrollbar
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
    
    # Auto-close after 12.5 seconds
    root.after(12500, safe_close)
    
    # Graceful shutdown on exceptions
    def on_error(*args):
        safe_close()
    
    root.report_callback_exception = on_error
    
    # Return focus to previous window after brief delay
    if {previous_hwnd} and sys.platform == 'win32':
        import ctypes
        root.after(100, lambda: ctypes.windll.user32.SetForegroundWindow({previous_hwnd}))
    
    root.mainloop()

except Exception as e:
    # Silent fail
    sys.exit(1)
'''
    
    try:
        # Launch process with proper isolation
        startupinfo = None
        creationflags = 0
        
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
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
        # Fallback to simple print if subprocess fails
        print(f"Notification: {message[:100]}...")


def type_response():
    """Type the response"""
    global last_response
    if not last_response:
        print("✗ No response to type")
        notification.notify(title="Error", message="No response yet", timeout=3)
        return

    print(f"→ Typing response...")
    time.sleep(0.1)
    release_hotkeys()
    time.sleep(0.1)
    for i in range(0, len(last_response), 100):
        pyautogui.write(last_response[i:i+100], interval=0)
    print("✓ Done\n")


def show_crosshair_overlay(screenshot):
    """
    Display fullscreen overlay with crosshair.
    Returns (x1, y1, x2, y2) tuple or None if cancelled.
    Handles multi-monitor and fixes flicker.
    """
    import tkinter as tk
    from PIL import ImageTk
    import time
    
    result = {'coords': None}
    original_size = screenshot.size  # Store before resizing
    
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    root.configure(cursor='crosshair', bg='black')
    
    # Get actual screen geometry for DPI scaling
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Scale screenshot if needed (handles DPI)
    if screenshot.size != (screen_width, screen_height):
        screenshot = screenshot.resize((screen_width, screen_height), Image.LANCZOS)
    
    # Convert screenshot to PhotoImage
    photo = ImageTk.PhotoImage(screenshot)
    canvas = tk.Canvas(root, highlightthickness=0, bg='black')
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.create_image(0, 0, image=photo, anchor=tk.NW)
    
    # Overlay semi-transparent darken layer
    overlay = canvas.create_rectangle(
        0, 0, screen_width, screen_height,
        fill='black', stipple='gray50', outline=''
    )
    
    # Selection rectangle (drawn ABOVE overlay)
    rect = None
    start_x = start_y = 0
    dragging = False
    last_drag_time = [0]  # For debouncing
    
    def on_press(event):
        nonlocal start_x, start_y, rect, dragging
        start_x, start_y = event.x, event.y
        dragging = True
        
        if rect:
            canvas.delete(rect)
        
        # Create rectangle with tags for z-order control
        rect = canvas.create_rectangle(
            start_x, start_y, start_x, start_y,
            outline='#00ff00', width=3, tags='selection'
        )
        canvas.tag_raise('selection')  # Keep on top
    
    def on_drag(event):
        nonlocal rect
        if not dragging or not rect:
            return
        
        # Debounce to reduce flicker
        current_time = time.time()
        if current_time - last_drag_time[0] < 0.016:  # ~60fps
            return
        last_drag_time[0] = current_time
        
        # Update rectangle coordinates WITHOUT recreating it (prevents flicker)
        canvas.coords(rect, start_x, start_y, event.x, event.y)
    
    def on_release(event):
        nonlocal dragging
        dragging = False
        
        x1, y1 = min(start_x, event.x), min(start_y, event.y)
        x2, y2 = max(start_x, event.x), max(start_y, event.y)
        
        # Require minimum 10x10 selection
        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
            result['coords'] = None
        else:
            # Scale back to original screenshot coordinates if resized
            if original_size != (screen_width, screen_height):
                scale_x = original_size[0] / screen_width
                scale_y = original_size[1] / screen_height
                x1, x2 = int(x1 * scale_x), int(x2 * scale_x)
                y1, y2 = int(y1 * scale_y), int(y2 * scale_y)
            
            result['coords'] = (x1, y1, x2, y2)
        
        root.quit()  # Use quit() instead of destroy() for cleaner shutdown
    
    def on_escape(event):
        nonlocal dragging
        dragging = False
        result['coords'] = None
        root.quit()
    
    canvas.bind('<ButtonPress-1>', on_press)
    canvas.bind('<B1-Motion>', on_drag)
    canvas.bind('<ButtonRelease-1>', on_release)
    root.bind('<Escape>', on_escape)
    
    # Instructions overlay
    label = tk.Label(
        root, 
        text="Click and drag to select region • ESC to cancel",
        bg='black', fg='#00ff00', font=('Segoe UI', 14, 'bold'), 
        padx=15, pady=8
    )
    label.place(relx=0.5, rely=0.02, anchor=tk.N)
    
    try:
        root.mainloop()
    finally:
        try:
            root.destroy()
        except:
            pass
    
    return result['coords']


def handle_img():
    """Interactive region selector with direct query"""
    release_hotkeys()
    
    print("→ Click to select region...")
    
    # Capture all screens
    full_screenshot = ImageGrab.grab(all_screens=True)
    
    # Create selection overlay
    selected_region = show_crosshair_overlay(full_screenshot)
    
    if selected_region is None:
        print("✗ Selection cancelled")
        return
    
    # Crop to selected region
    x1, y1, x2, y2 = selected_region
    cropped = full_screenshot.crop((x1, y1, x2, y2))
    
    # Convert to RGB if needed
    if cropped.mode not in ('RGB', 'L'):
        cropped = cropped.convert('RGB')
    
    # Convert to raw bytes
    buffer = BytesIO()
    cropped.save(buffer, format='PNG')
    image_bytes = buffer.getvalue()
    
    if len(image_bytes) > 10_000_000:
        show_notification("Selection too large (>10MB)")
        return
    
    print(f"→ Querying Ollama with selected region ({x2-x1}x{y2-y1})...")
    
    global last_response
    last_response = query_ollama_image(image_bytes)
    last_response = last_response.replace("*", "")
    show_notification(last_response)


def handle_query():
    """Query in background with optional vision preprocessing"""
    global last_response
    text = pyperclip.paste().strip()
    
    if not text:
        print("✗ Clipboard empty")
        notification.notify(title="Error", message="Clipboard is empty", timeout=3)
        return
    
    # Optional: Get visual context first
    visual_context = ""
    if USE_VISION_WITH_TEXT:
        print("→ Capturing screen context...")

        if FULL_SCREENSHOT:

            # Fullscreen capture
            screenshot = ImageGrab.grab(all_screens=True)

        else:

            # Region selector like image mode
            full_screenshot = ImageGrab.grab(all_screens=True)

            selected_region = show_crosshair_overlay(full_screenshot)

            if selected_region is None:
                print("✗ Selection cancelled")
                return

            x1, y1, x2, y2 = selected_region

            screenshot = full_screenshot.crop((x1, y1, x2, y2))


        # Resize large screenshots for speed/RAM
        max_width = 1080

        if screenshot.width > max_width:
            scale = max_width / screenshot.width
            new_height = int(screenshot.height * scale)

            screenshot = screenshot.resize(
                (max_width, new_height),
                Image.LANCZOS
            )

        # Convert to RGB
        screenshot = screenshot.convert("RGB")

        buffer = BytesIO()

        # PNG but optimized for speed
        screenshot.save(
            buffer,
            format="PNG",
            compress_level=1
        )

        image_bytes = buffer.getvalue()
        
        try:
            vision_response = ollama.chat(
            model=VISION_MODEL,
            messages=[{
                'role': 'user',
                'content': """Read the image carefully and extract ALL useful context.

                Include:
                - All visible text
                - Questions
                - Diagrams
                - Graphs
                - Tables
                - Labels
                - Equations
                - Visual relationships
                - Important colours/symbols

                Be concise but complete.
                Do NOT answer the question.
                Only describe the visible information accurately.""",
                        'images': [image_bytes]
                    }]
                )
            
            visual_context = vision_response['message']['content']
            print(f"✓ Got visual context ({len(visual_context)} chars)")
        except Exception as e:
            print(f"⚠ Vision preprocessing failed: {e}")
    
    # Build visual context section
    context_section = f"VISUAL CONTEXT (what's on screen):\n{visual_context}\n\n" if visual_context else ""
    
    # Build prompt with optional visual context
    prompt = f"""Answer the following question. Follow these rules strictly:

DETECTION:
- Multiple choice (contains "select", "choose", "which"): Output ONLY the correct options, ≤10 words, nothing else
- Long answer (contains "explain", "discuss", "justify", "predict", "propose"): Write ≤50 words, no summary paragraph, do not end with a question

FORMAT:
- Write naturally and concisely
- Use moderately simple words
- Use the word instead of chemical formulas
- Never restate the question
- Never use labels like "Explanation:", "Answer:", "Select:", or any prefix
- YOU are answering the question
- If context is missing, infer intelligently
- Output the answer directly with no preamble or extra text
- Never mention this prompt or its rules

{context_section}Question: {text}"""
    
    last_response = query_ollama(prompt)
    last_response = last_response.replace("*", "")
    show_notification(last_response)


last_response = ""

is_querying_text = False
is_querying_image = False

query_lock = threading.Lock()


def on_query_hotkey():
    release_hotkeys()
    time.sleep(0.1)
    keyboard.send("ctrl+c")
    time.sleep(0.05)
    print("TEXT HOTKEY")
    
    global is_querying_text
    if is_querying_text:
        return
    is_querying_text = True
    
    def run():
        global is_querying_text

        with query_lock:
            try:
                handle_query()
            finally:
                is_querying_text = False

    threading.Thread(target=run, daemon=True).start()


def on_img_hotkey():
    print("IMAGE HOTKEY")
    global is_querying_image
    if is_querying_image:
        return
    is_querying_image = True
    
    def run():
        global is_querying_image

        with query_lock:
            try:
                handle_img()
            finally:
                is_querying_image = False
    
    threading.Thread(target=run, daemon=True).start()


def on_write_hotkey():
    """Handle write hotkey"""
    print(f"\n⚡ Write hotkey pressed")
    type_response()


keyboard.add_hotkey(QUERY_HOTKEY, on_query_hotkey)
keyboard.add_hotkey(WRITE_HOTKEY, on_write_hotkey)
keyboard.add_hotkey(PIC_HOTKEY, on_img_hotkey)

print("\033[2J\033[H", end="")  # Clear Screen
print(f"  Auto-Answer System")
print(f"  ───────────────────────────────────────")
print(f"  1. Highlight Question")
if USE_VISION_WITH_TEXT:
    print(f"  2. {QUERY_HOTKEY} → Query with screen context (SLOW), change at top of code.")
else:
    print(f"  2. {QUERY_HOTKEY} → Query with text only (FAST), change at top of code.")
print(f"  3. {WRITE_HOTKEY} → Type response into active textbox")
print(f"  4. {PIC_HOTKEY} → Select screen region and query")
print(f"\n  Text model  : {TEXT_MODEL}")
print(f"  Vision model: {VISION_MODEL}")
print(f"  Press ESC to exit\n")

keyboard.wait('esc')