import mss
import numpy as np
import cv2
import threading
import time
from collections import deque
from tkinter import Tk, Button, messagebox
from datetime import datetime, timedelta
import sys
import os
import json
import requests
import platform

# ==================== Configuration ====================
CONFIG_FILE = "config.json"

# Load configuration
def load_config():
    default_config = {
        "FRAME_RATE": 60,  # Frames per second
        "BUFFER_SECONDS": 30,  # Seconds to keep in buffer
        "SCREEN_MONITOR": 1,  # Primary monitor
        "OUTPUT_DIR": "./replays/",  # Directory to save replay videos
        "DONATION_URL": "https://your-donation-endpoint.com/upload",  # URL to upload donation image
        "REMINDER_INTERVALS": [7, 30, 365, 1825, 5475, 10950, 21900, 43800, 87600, 175200, 350400, 700800],
        # Days after which to remind: 7 days, 30, 365 (1 year), 5 years, 15, 30, 60, 120, 240, 480, 960, 1920
    }

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config
    else:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)

config = load_config()

FRAME_RATE = config["FRAME_RATE"]
BUFFER_SECONDS = config["BUFFER_SECONDS"]
SCREEN_MONITOR = config["SCREEN_MONITOR"]
OUTPUT_DIR = config["OUTPUT_DIR"]
DONATION_URL = config["DONATION_URL"]
REMINDER_INTERVALS = config["REMINDER_INTERVALS"]

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# License file
LICENSE_FILE = "license.json"

def is_perpetual_license():
    if os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, 'r') as f:
            license_data = json.load(f)
            return license_data.get("perpetual", False)
    return False

def grant_perpetual_license():
    with open(LICENSE_FILE, 'w') as f:
        json.dump({"perpetual": True}, f)

def get_installation_date():
    INSTALL_FILE = "install.json"
    if not os.path.exists(INSTALL_FILE):
        with open(INSTALL_FILE, 'w') as f:
            json.dump({"install_date": datetime.now().isoformat(), "reminder_index": 0}, f)
        return datetime.now()
    else:
        with open(INSTALL_FILE, 'r') as f:
            data = json.load(f)
            return datetime.fromisoformat(data["install_date"]), data.get("reminder_index", 0)

def update_reminder_index(index):
    INSTALL_FILE = "install.json"
    if os.path.exists(INSTALL_FILE):
        with open(INSTALL_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {}
    data["reminder_index"] = index
    with open(INSTALL_FILE, 'w') as f:
        json.dump(data, f)

# ==================== Screen Recorder ====================
def screen_recorder(buffer, stop_event):
    with mss.mss() as sct:
        monitor = sct.monitors[SCREEN_MONITOR]
        width = monitor["width"]
        height = monitor["height"]
        size = (width, height)
        print(f"Recording screen: {size} at {FRAME_RATE} FPS.")

        # Calculate the interval between frames
        frame_interval = 1.0 / FRAME_RATE

        while not stop_event.is_set():
            start_time = time.time()
            img = np.array(sct.grab(monitor))
            # Convert BGRA to BGR
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            buffer.append(frame)
            elapsed = time.time() - start_time
            time_to_wait = frame_interval - elapsed
            if time_to_wait > 0:
                time.sleep(time_to_wait)
            else:
                # If processing is taking too long, skip sleeping to catch up
                pass

def save_replay(buffer):
    if not buffer:
        print("No frames to save.")
        return

    # Define the codec and create VideoWriter object
    # fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Alternative codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Recommended codec
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(OUTPUT_DIR, f"replay_{timestamp}.mp4")  # Changed to .mp4

    # Assuming all frames have the same size
    height, width, layers = buffer[0].shape
    video = cv2.VideoWriter(output_filename, fourcc, FRAME_RATE, (width, height))

    print(f"Saving replay to {output_filename}...")
    for frame in buffer:
        video.write(frame)
    video.release()
    print("Replay saved successfully.")

def on_replay(buffer):
    # Run save_replay in a separate thread to avoid blocking the GUI
    threading.Thread(target=save_replay, args=(list(buffer),), daemon=True).start()

# ==================== Donation Prompt ====================
def show_donation_prompt():
    def donate():
        # Handle image upload
        image_path = filedialog.askopenfilename(title="Select Donation Image",
                                                filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if image_path:
            try:
                with open(image_path, 'rb') as img_file:
                    files = {'file': img_file}
                    response = requests.post(DONATION_URL, files=files)
                if response.status_code == 200:
                    messagebox.showinfo("Thank You!", "Thank you for your donation! You now have a perpetual license.")
                    grant_perpetual_license()
                    root.destroy()
                else:
                    messagebox.showerror("Upload Failed", "Failed to upload the image. Please try again.")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")
        else:
            # User canceled the upload
            root.destroy()

    def remind_later():
        root.destroy()

    from tkinter import filedialog

    root = Tk()
    root.title("Donation Required")
    root.geometry("400x200")
    root.attributes("-topmost", True)

    message = (
        "Thank you for using Screen Replay Recorder!\n\n"
        "To continue using the software beyond the trial period, please make a donation.\n"
        "You can donate any amount and upload a receipt image to receive a perpetual license.\n\n"
        "Do you wish to donate now?"
    )
    label = Button(root, text=message, wraplength=380, justify="left", bg="white", borderwidth=0, command=donate)
    label.pack(pady=10)

    donate_button = Button(root, text="Donate Now", command=donate, bg="#4CAF50", fg="white", width=15)
    donate_button.pack(pady=5)

    remind_button = Button(root, text="Remind Me Later", command=remind_later, bg="#f0f0f0", fg="black", width=15)
    remind_button.pack(pady=5)

    root.mainloop()

def check_and_prompt_donation():
    if is_perpetual_license():
        return

    install_date, reminder_index = get_installation_date()
    next_reminder_date = install_date + timedelta(days=REMINDER_INTERVALS[reminder_index])

    if datetime.now() >= next_reminder_date:
        show_donation_prompt()
        # Increment reminder index
        if reminder_index < len(REMINDER_INTERVALS) - 1:
            reminder_index += 1
            update_reminder_index(reminder_index)
        else:
            # Keep the last index if max is reached
            pass

# ==================== GUI Setup ====================
def main():
    # Calculate the maximum number of frames to store
    max_frames = FRAME_RATE * BUFFER_SECONDS
    frame_buffer = deque(maxlen=max_frames)

    # Event to signal the recorder thread to stop
    stop_event = threading.Event()

    # Start the screen recorder thread
    recorder_thread = threading.Thread(target=screen_recorder, args=(frame_buffer, stop_event), daemon=True)
    recorder_thread.start()

    # Check for donation prompt
    threading.Thread(target=check_and_prompt_donation, daemon=True).start()

    # Setup the GUI
    root = Tk()
    root.title("Replay Recorder")

    # Make the window always on top and remove window decorations
    root.attributes("-topmost", True)
    root.overrideredirect(True)  # Removes title bar and borders

    # Position the window at the top-right corner
    window_width = 100
    window_height = 50
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_position = screen_width - window_width - 10  # 10 pixels from the right edge
    y_position = 10  # 10 pixels from the top edge
    root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

    # Create a "Replay" button
    replay_button = Button(
        root,
        text="Replay 30s",
        command=lambda: on_replay(frame_buffer),
        bg="#4CAF50",
        fg="white",
        activebackground="#45a049",
        borderwidth=0,
        highlightthickness=0,
        font=("Helvetica", 10, "bold")
    )
    replay_button.pack(expand=True, fill='both')

    # Optional: Add functionality to close the floating button (e.g., right-click to exit)
    def on_right_click(event):
        stop_event.set()
        recorder_thread.join()
        root.destroy()
        sys.exit()

    replay_button.bind("<Button-3>", on_right_click)  # Right-click to exit

    print("Screen recording started.")
    print("Click the 'Replay 30s' button to save the last thirty seconds of screen recording.")
    print("Right-click the button to exit the application.")

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        stop_event.set()
        recorder_thread.join()

if __name__ == "__main__":
    main()
