import cv2
import time
import threading
import queue
from datetime import datetime
import torch
import numpy as np

# Import SAM 2 modules
from sam2.build_sam import build_sam2_video_predictor
from sam2.sam2_predictor import SAM2VideoPredictor

# Adjustable parameters
FRAME_PROCESS_INTERVAL = 0.5  # Time in seconds between processing frames
MODEL_CHECKPOINT = "./checkpoints/sam2_hiera_base_plus.pt"  # Update path if necessary
MODEL_CONFIG = "sam2_hiera_b_plus.yaml"  # Update path if necessary

# Queue to hold frames to be processed
frame_queue = queue.Queue()

def process_frames(predictor):
    state = None  # SAM 2 video predictor state
    while True:
        if not frame_queue.empty():
            frame, timestamp = frame_queue.get()

            # Convert the frame to the expected input format
            # SAM 2 expects frames in RGB format
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Initialize the predictor state if not already done
            if state is None:
                # SAM 2 expects a list of frames as a video
                video_frames = [frame_rgb]
                state = predictor.init_state(video_frames)
            else:
                # Append the new frame to the state
                state.add_frame(frame_rgb)

            # For demonstration purposes, we'll use automatic mask generation
            # If you have specific prompts, you can modify this section accordingly
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
                # Propagate the masks in the video
                for frame_idx, object_ids, masks in predictor.propagate_in_video(state):
                    # Process the masks for the current frame
                    current_masks = masks[-1]  # Get masks for the latest frame
                    break  # We only need the latest frame's masks

            # Overlay the masks on the frame
            mask_overlay = np.zeros_like(frame_rgb, dtype=np.uint8)
            for mask in current_masks:
                # Convert mask to uint8 and resize to frame size if necessary
                mask = mask.cpu().numpy().astype(np.uint8) * 255
                # Create a colored mask
                colored_mask = np.zeros_like(frame_rgb, dtype=np.uint8)
                colored_mask[mask > 0] = [0, 255, 0]  # Green color for the mask
                # Overlay the colored mask on the original frame
                mask_overlay = cv2.addWeighted(mask_overlay, 1, colored_mask, 0.5, 0)

            # Combine the original frame and the mask overlay
            frame_with_masks = cv2.addWeighted(frame_rgb, 1, mask_overlay, 0.5, 0)

            # Convert back to BGR for OpenCV display and saving
            frame_with_masks_bgr = cv2.cvtColor(frame_with_masks, cv2.COLOR_RGB2BGR)

            # Display the timestamp on the frame
            display_text = f"{timestamp}"
            cv2.putText(frame_with_masks_bgr, display_text,
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (255, 255, 255), 2)

            # Save the image with masks
            filename = f"frame_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            cv2.imwrite(filename, frame_with_masks_bgr)

            # Optionally, display the processed frame
            cv2.imshow('Processed Frame', frame_with_masks_bgr)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        else:
            time.sleep(0.01)  # Sleep briefly to avoid busy waiting

def main():
    # Initialize the SAM 2 video predictor
    predictor = build_sam2_video_predictor(MODEL_CONFIG, MODEL_CHECKPOINT)

    # Start the frame processing thread
    threading.Thread(target=process_frames, args=(predictor,), daemon=True).start()

    # Open the video capture (0 for default webcam, or provide a video file path)
    cap = cv2.VideoCapture(0)
    last_processed_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame from video source")
            break

        current_time = time.time()
        if current_time - last_processed_time >= FRAME_PROCESS_INTERVAL:
            timestamp = datetime.now()
            frame_queue.put((frame.copy(), timestamp))
            last_processed_time = current_time

        # Optionally display the video stream
        cv2.imshow('Video Stream', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()