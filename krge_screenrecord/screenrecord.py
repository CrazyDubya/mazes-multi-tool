import mss
import numpy as np
import cv2
import threading
import time
from collections import deque
from tkinter import Tk, Button, messagebox, filedialog
from datetime import datetime, timedelta
import sys
import os
import json
import requests
import platform
import subprocess

# ==================== Application Overview ====================
"""
Screen Replay Recorder

This application records your screen and allows you to save 
recorded footage. Currently, the features include:

- Record your screen in real-time at a specified frame rate.
- Save the entire recording as a video file.

NOTE: The "Save Last 30 Seconds" functionality is currently 
disabled and requires further testing and adjustments. 

Requirements:
- Install required libraries: mss, numpy, opencv-python, etc.
- Ensure FFmpeg is available for video encoding.

TODO: Fix the "Save Last 30 Seconds" feature and re-enable the button.
"""

# ==================== Configuration ====================
CONFIG_FILE = "config.json"


# Load configuration
def load_config():
    default_config = {
        "FRAME_RATE": 60,  # Frames per second
        "BUFFER_SECONDS": 30,  # Seconds to keep in buffer (not used anymore)
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
        return datetime.now(), 0
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


# ==================== FFmpeg Handling ====================
def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        # If the application is bundled by PyInstaller
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    if platform.system() == "Windows":
        ffmpeg_path = os.path.join(application_path, "ffmpeg", "ffmpeg.exe")
    else:
        ffmpeg_path = os.path.join(application_path, "ffmpeg", "ffmpeg")

    return ffmpeg_path


def verify_ffmpeg():
    ffmpeg_path = get_ffmpeg_path()
    try:
        subprocess.run([ffmpeg_path, "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("FFmpeg is available.")
    except Exception as e:
        print(f"FFmpeg verification failed: {e}")
        sys.exit(1)


# ==================== Multi-Tier Buffer ====================
BUFFER_TIERS = [
    (30, 60),  # 0-30s at 60 FPS
    (270, 45),  # 30s-5min at 45 FPS
    (1500, 30),  # 5min-30min at 30 FPS
    (1800, 15),  # 30min-60min at 15 FPS
    (82800, 10),  # 60min-24h at 10 FPS
    (172800, 5),  # 24h-48h at 5 FPS
    (259200, 1),  # 48h-72h at 1 FPS
    (9999999, 0.5)  # 72h+ at 0.5 FPS
]


class MultiTierBuffer:
    def __init__(self, tiers):
        """
        Initialize the multi-tier buffer.
        :param tiers: List of tuples (duration_in_seconds, frame_rate)
        """
        self.tiers = tiers
        self.buffers = []
        for duration, fps in self.tiers:
            max_frames = int(duration * fps)
            self.buffers.append(deque(maxlen=max_frames))
        self.start_time = datetime.now()

    def add_frame(self, frame):
        """
        Add a frame to the appropriate buffers based on its timestamp.
        :param frame: The frame to add.
        """
        current_time = datetime.now()  # This should be the timestamp
        elapsed = (current_time - self.start_time).total_seconds()
        for idx, (duration, fps) in enumerate(self.tiers):
            if elapsed <= duration:
                # Calculate the frame interval
                frame_interval = 1.0 / fps
                buffer = self.buffers[idx]
                if len(buffer) == 0 or (current_time - buffer[-1][0]).total_seconds() >= frame_interval:
                    buffer.append((current_time, frame))  # Append with current_time
                break
        # Add to all older buffers
        for j in range(idx + 1, len(self.tiers)):
            buffer = self.buffers[j]
            frame_interval = 1.0 / self.tiers[j][1]
            if len(buffer) == 0 or (current_time - buffer[-1][0]).total_seconds() >= frame_interval:
                buffer.append((current_time, frame))  # Append with current_time

    def get_all_frames(self):
        """
        Retrieve all frames from all buffers.
        :return: List of frames ordered by time.
        """
        all_frames = []
        for buffer in self.buffers:
            all_frames.extend(buffer)
        # Sort frames by timestamp
        all_frames.sort(key=lambda x: x[0])
        return all_frames  # This should return tuples of (timestamp, frame)


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
            buffer.add_frame(frame)  # Add frame to multi-tier buffer
            elapsed = time.time() - start_time
            time_to_wait = frame_interval - elapsed
            if time_to_wait > 0:
                time.sleep(time_to_wait)
            else:
                # If processing is taking too long, skip sleeping to catch up
                pass


def save_replay(frames, thirty_seconds_ago):
    """
    Save recent frames where timestamp >= thirty_seconds_ago
    """
    recent_frames = []

    for item in frames:
        try:
            # Unpack timestamp and frame
            timestamp, frame = item

            # Make sure timestamp is datetime and compare
            if isinstance(timestamp, datetime) and timestamp >= thirty_seconds_ago:
                recent_frames.append(frame)
        except ValueError:
            print(f"Skipping item due to unexpected structure: {item}")

    if not recent_frames:
        print("No frames in the last 30 seconds.")
        return

    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Recommended codec
    output_filename = os.path.join(OUTPUT_DIR, f"replay_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")

    # Assuming all frames have the same size
    height, width, layers = recent_frames[0].shape
    video = cv2.VideoWriter(output_filename, fourcc, 60, (width, height))  # 60 FPS

    print(f"Saving replay to {output_filename}...")
    for frame in recent_frames:
        video.write(frame)
    video.release()
    print("Replay saved successfully.")


def on_replay(buffer):
    # Currently disabled for testing purposes
    pass  # Threading for save_replay would go here


def on_full_replay(buffer):
    # Run save_full_replay in a separate thread to avoid blocking the GUI
    threading.Thread(target=save_full_replay, args=(buffer.get_all_frames(),), daemon=True).start()


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
    # Verify FFmpeg availability
    verify_ffmpeg()

    # Initialize the multi-tier buffer
    frame_buffer = MultiTierBuffer(BUFFER_TIERS)

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
    window_width = 200
    window_height = 100
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_position = screen_width - window_width - 10  # 10 pixels from the right edge
    y_position = 10  # 10 pixels from the top edge
    root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

    # Create a button for saving the entire recording
    full_replay_button = Button(
        root,
        text="Save Entire Recording",
        command=lambda: on_full_replay(frame_buffer),
        bg="#2196F3",
        fg="white",
        activebackground="#1976D2",
        borderwidth=0,
        highlightthickness=0,
        font=("Helvetica", 10, "bold")
    )
    full_replay_button.pack(expand=True, fill='both')

    # Disable and hide the 30-second button for now
    # replay_button = Button(
    #     root,
    #     text="Save Last 30 Seconds",
    #     command=lambda: on_replay(frame_buffer),
    #     bg="#4CAF50",
    #     fg="white",
    #     activebackground="#45a049",
    #     borderwidth=0,
    #     highlightthickness=0,
    #     font=("Helvetica", 10, "bold")
    # )
    # replay_button.pack(expand=True, fill='both')
    # replay_button.config(state="disabled")  # Disable the button

    # Optional: Add functionality to close the floating button (e.g., right-click to exit)
    def on_right_click(event):
        stop_event.set()
        recorder_thread.join()
        root.destroy()
        sys.exit()

    # full_replay_button.bind("<Button-3>", on_right_click)  # Right-click to exit

    print("Screen recording started.")
    print("Click the button to save the recording.")
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