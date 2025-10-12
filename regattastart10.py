#!/home/pi/yolov5_env/bin/python
# after git pull, do: sudo cp regattastart10.py /usr/lib/cgi-bin/
import os
import csv
from common_module import (
    setup_camera,
    remove_picture_files,
    remove_video_files,
    restart_camera,
    start_video_recording,
    start_sequence,
    stop_video_recording,
    logger,
    text_rectangle,
    process_video,
    get_cpu_model,
    get_h264_writer,
    clean_exit
)

# Use a deque to store the most recent frames in memory
from collections import deque
from datetime import datetime
import datetime as dt
import json
import numpy as np  # image recognition
from libcamera import Transform
from libcamera import ColorSpace
from picamera2 import Picamera2
import pytesseract  # OCR
import select
import threading
import time
import cv2
import torch
import warnings
import queue
import site
import gc
import sys
import subprocess
sys.path.append('/home/pi/yolov5')  # Adjust as needed
logger.info(f"Running with Python: {sys.executable}")
site.ENABLE_USER_SITE = False

warnings.filterwarnings(
    "ignore",
    message="torch.cuda.amp.autocast",
    category=FutureWarning,
    module=".*yolov5_master.models.common*"
)

# --- ADD GLOBALS ---
ocr_queue = queue.Queue(maxsize=1)  # Max size 1: if full, drop new data
ocr_result = queue.Queue(maxsize=1) # To hold the resulting sail number
ocr_thread = None                   # Placeholder for the thread

# Parameter data
fps = 15  # frames per second for video1
signal_dur = 0.9  # seconds
log_path = '/var/www/html/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
crop_width, crop_height = 1440, 1080  # Crop size for inference
stop_event = threading.Event()
listen_thread = None   # placeholder for the listener thread
wd_thread = None

cpu_model = get_cpu_model()
logger.info("="*60)
logger.info(f"Starting new regattastart10.py session at {dt.datetime.now()}")
logger.info(f"Detected CPU model string: '{cpu_model}'")
logger.info("="*60)

# reset the contents of the status variable, used for flagging that
# video1-conversion is complete.
with open('/var/www/html/status.txt', 'w') as status_file:
    status_file.write("")


def stop_recording():
    global listen_thread
    logger.info("stop_recording called. Stopping recording early.")
    stop_event.set()

    # Wait for the listening thread to exit
    if listen_thread is not None and listen_thread.is_alive():
        logger.info("Waiting for listen_thread to exit...")
        listen_thread.join(timeout=1.0)
        logger.info("listen_thread has exited.")


def listen_for_messages(stop_event, timeout=0.1):
    pipe_path = '/var/www/html/tmp/stop_recording_pipe'
    logger.info("listen_for_messages: starting")
    logger.info(f"Pipe path = {pipe_path}")

    # Ensure the named pipe exists
    try:
        if os.path.exists(pipe_path):
            os.unlink(pipe_path)  # Remove existing file or pipe
        os.mkfifo(pipe_path)  # Create a new named pipe
        os.chmod(pipe_path, 0o666)  # Set permissions to allow read/write
        logger.info(f"Pipe created with permissions 666: {pipe_path}")
    except Exception as e:
        logger.error(f"Failed to create named pipe: {e}", exc_info=True)
        return

    while not stop_event.is_set():
        try:
            with open(pipe_path, 'r') as fifo:
                logger.debug("Waiting for input from the pipe...")
                rlist, _, _ = select.select([fifo], [], [], timeout)
                if rlist:
                    message = fifo.readline().strip()
                    logger.debug(f"Message received from pipe: {message}")
                    if message == 'stop_recording':
                        logger.info("Message == stop_recording → setting stop_event")
                        stop_event.set()   # unified stop signal
                        break  # Exit the loop when stop_recording received
        except Exception as e:
            logger.error(f"Error in listen_for_messages: {e}", exc_info=True)
            break
        time.sleep(0.1)
    logger.info("Listening for messages: exiting")


# Clean up processed_timestamps to remove old entries
def cleanup_processed_timestamps(processed_timestamps, threshold_seconds=30):
    current_time = datetime.now()
    filtered_timestamps = {
        ts for ts in processed_timestamps
        if (current_time - ts).total_seconds() <= threshold_seconds
    }
    removed_count = len(processed_timestamps) - len(filtered_timestamps)

    processed_timestamps.clear()
    processed_timestamps.update(filtered_timestamps)  # Add the filtered timestamps

    logger.debug(f"Cleaned up {removed_count} old timestamps.")


# function to load the YOLOv5 model
def load_model_with_timeout(result_queue):
    try:
        if cpu_model and "Raspberry Pi 3" in cpu_model:
            # inference_interval = 2.0  # seconds between inferences
            yolov_model = "yolov5n"   # lighter model
        elif cpu_model and "Raspberry Pi 5" in cpu_model:
            # inference_interval = 0.5  # more frequent
            yolov_model = "yolov5s"
        else:
            # inference_interval = 1.0
            yolov_model = "yolov5s"

        from models.common import DetectMultiBackend
        model_path = "/var/www/html/" + yolov_model + ".pt"  # Path to the YOLOv5 model file
        logger.info(f"Loading YOLOv5 model from {model_path} for {cpu_model} with model {yolov_model}")
        device = 'cpu'
        model = DetectMultiBackend(model_path, device=device)
        result_queue.put(model)  # Put the model in the queue
    except Exception as e:
        logger.error(f"FAILED to load YOLOv5 model: {e}", exc_info=True)
        result_queue.put(e)  # Put the exception in the queue


def prepare_input(img, device='cpu'):
    """
    Prepares an image for YOLOv5 inference.
    Assumes input is a NumPy image in BGR format (from OpenCV).
    """
    if isinstance(img, np.ndarray):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB
        img = np.ascontiguousarray(img)             # Ensure it's contiguous
        img = torch.from_numpy(img).permute(2, 0, 1).float()  # (3, H, W)
        img /= 255.0                                 # Normalize to [0, 1]

    if img.ndim == 3:
        img = img.unsqueeze(0)  # (1, 3, H, W)

    return img.to(device)

def extract_sail_number(frame, box, clahe):
    import pytesseract, re
    x1, y1, x2, y2 = map(int, box)  # YOLO returns float
    w = x2 - x1
    h = y2 - y1

    # ---- ROI focus: upper/main sail band, center horizontally ----
    H_UP = 0.45  # use a bit more of the upper region; adjust if needed
    W_PAD = 0.18
    crop_y1 = max(0, y1 - int(0.15 * h))    # allow slightly above
    crop_y2 = y1 + int(H_UP * h)
    crop_x1 = x1 + int(W_PAD * w)
    crop_x2 = x2 - int(W_PAD * w)

    # Ensure coordinates are within bounds
    crop_y2 = min(crop_y2, frame.shape[0])
    crop_x2 = min(crop_x2, frame.shape[1])
    if crop_y2 <= crop_y1 or crop_x2 <= crop_x1:
        return None

    # Crop region
    sail_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]

    # ---- Preprocess: CLAHE -> adaptive thresholds (both polarities) ----
    gray = cv2.cvtColor(sail_crop, cv2.COLOR_BGR2GRAY)
    g = clahe.apply(gray)

    # try both normal and inverted binarization
    def binarize(img, invert=False):
        if invert:
            img = cv2.bitwise_not(img)
        # adaptive mean is robust on textured sails
        th = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, 31, 5)
        # light morphological clean
        th = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((2,2), np.uint8), iterations=1)
        return th

    candidates = []
    for invert in (False, True):
        th = binarize(g, invert=invert)
        # also try a slightly tighter crop to remove borders/rigging lines
        h2, w2 = th.shape[:2]
        d = max(2, min(h2, w2)//40)
        th_tight = th[d:h2-d, d:w2-d] if (h2-2*d>20 and w2-2*d>20) else th

        for img in (th, th_tight):
            # upscale helps Tesseract
            up = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            cfg = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            txt = pytesseract.image_to_string(up, config=cfg)
            candidates.append(txt)
            logger.debug(f"OCR candidate (normal): {txt!r}")

            # also run on a horizontally flipped image to catch mirrored text
            up_flipped = cv2.flip(up, 1)
            txt_flip = pytesseract.image_to_string(up_flipped, config=cfg)
            candidates.append(txt_flip)
            logger.debug(f"OCR candidate (flipped): {txt_flip!r}")

    # ---- Normalize + score candidates ----
    def correct_ocr_digits(text):
        map_ = {"I":"1","l":"1","O":"0","Q":"0","S":"5","Z":"2","B":"8","G":"6","E":"3"}
        return ''.join(map_.get(c, c) for c in text)

    MIN_DIGITS, MAX_DIGITS = 1, 4
    best = None
    best_score = -1

    for raw in candidates:
        lines = [L.strip().upper() for L in raw.splitlines() if L.strip()]
        # simple two-line heuristic: SWE line + digits line nearby
        for i, L in enumerate(lines):
            if "SWE" in L:
                # check same line first
                combined = correct_ocr_digits(L)
                m = re.search(r'SWE\D*([0-9]{%d,%d})' % (MIN_DIGITS, MAX_DIGITS), combined)
                if m:
                    digits = m.group(1)
                    score = len(digits)  # more digits is better
                    if score > best_score:
                        best = f"SWE {digits}"
                        best_score = score
                    continue
                # check following 1–2 lines for digits
                for j in (1, 2):
                    if i+j < len(lines):
                        nxt = correct_ocr_digits(lines[i+j])
                        m2 = re.search(r'([0-9]{%d,%d})' % (MIN_DIGITS, MAX_DIGITS), nxt)
                        if m2:
                            digits = m2.group(1)
                            score = len(digits)
                            if score > best_score:
                                best = f"SWE {digits}"
                                best_score = score

    # fallback: sometimes only SWE is visible
    if not best:
        for raw in candidates:
            if "SWE" in raw.upper():
                best = "SWE"
                best_score = 0
                break
    # NEW fallback: plain numeric detection (no SWE seen)
    if not best:
        for raw in candidates:
            lines = [correct_ocr_digits(L.strip().upper()) for L in raw.splitlines() if L.strip()]
            for L in lines:
                m = re.search(r'([0-9]{%d,%d})' % (MIN_DIGITS, MAX_DIGITS), L)
                if m:
                    digits = m.group(1)
                    score = len(digits)
                    if score > best_score:
                        best = digits
                        best_score = score

    if best:
        logger.info(f"Detected sail number: {best}")
    return best


def log_sailnumber_to_csv(sailnumber, ts, csv_file="/var/www/html/sailnumbers.csv"):
    try:
        newfile = not os.path.exists(csv_file)
        with open(csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            if newfile:
                writer.writerow(["timestamp", "sailnumber"])
            writer.writerow([ts.strftime("%Y-%m-%d %H:%M:%S"), sailnumber])
    except Exception as e:
        logger.error(f"CSV logging failed: {e}")


def ocr_worker(input_queue, output_queue, stop_event):
    logger.info("OCR Worker started.")
    # Initialize expensive resources once
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'  # Ensure Tesseract path is correct

    while not stop_event.is_set():
        try:
            # Wait for up to 0.5s for a task (Non-blocking check)
            frame_data = input_queue.get(timeout=0.5) 

            # Unpack the data
            frame, box, capture_timestamp = frame_data

            # --- EXECUTE THE HEAVY OCR LOGIC ---
            sail_number = extract_sail_number(frame.copy(), box, clahe)

            # Put result back in queue
            if sail_number:
                output_queue.put({'ts': capture_timestamp, 'num': sail_number})

        except queue.Empty:
            pass # Keep waiting if queue is empty
        except Exception as e:
            logger.error(f"OCR Worker error: {e}", exc_info=True)
            # Continue running even if one OCR attempt fails

    logger.info("OCR Worker stopped.")

# NOTE: You MUST include the full extract_sail_number and log_sailnumber_to_csv 
# definitions in the final script.


def finish_recording(camera, video_path, num_starts, video_end, start_time_dt, fps):
    from utils.general import non_max_suppression
    # config
    DETECTION_CONF_THRESHOLD = 0.5
    LOG_FRAME_THROTTLE = 10  # log every N frames when boat found
    confidence = 0.0  # Initial value
    class_name = ""  # Initial value
    frame_counter = 0  # Initialize a frame counter
    boat_in_current_frame = False  # Initialize detection flag
    last_adjustment = time.time()

    # Set duration of video1 recording
    max_duration = (video_end + (num_starts-1)*5) * 60
    logger.debug(f"Video1, max recording duration: {max_duration} seconds")

    # RESTART CAMERA
    camera = restart_camera(camera, resolution=(1920, 1080), fps=fps)

    while True:
        if stop_event.is_set():
            logger.info("Stop event set, breaking loop")
            break
        # --- Capture and process frame ---
        if camera is None:
            logger.warning("Camera is None, skipping frame capture")
            break  # exit the loop cleanly
        frame = camera.capture_array()

        # Confirm resolution before proceeding
        try:
            frame_size = (frame.shape[1], frame.shape[0])
            time.sleep(0.5)  # Add a short delay to ensure the camera is ready
            logger.info(f"Camera frame size before recording: {frame_size}")
        except Exception as e:
            logger.error(f"Exception occurred while accessing frame size: {e}", exc_info=True)
            return

        # --- CROP DATA FOR INFERENCE ---
        try:
            logger.debug("Calculating crop data for inference only.")

            # Full camera resolution
            frame_height, frame_width = frame.shape[:2]
            camera_frame_size = (frame_width, frame_height)

            shift_offset = 100  # horizontal offset for crop -> right part
            x_start = max((frame_width - crop_width) // 2 + shift_offset, 50)
            y_start = max((frame_height - crop_height) // 2, 0)

            if camera_frame_size != (1920, 1080):
                logger.error(f"Resolution mismatch! Expected (1920, 1080) but got {camera_frame_size}.")
            else:
                logger.debug("Resolution matches expected values.")

            logger.debug(f"Frame size used to crop for inference: {crop_width}x{crop_height}")

        except Exception as e:
            logger.error(f"Unhandled exception occurred during crop setup: {e}", exc_info=True)
            return

        # Set the camera to the desired resolution and frame rate
        fpsw = fps
        logger.debug(f"FPS set to {fpsw}, proceeding to load YOLOv5 model.")

        # LOAD YOLOv5 MODEL
        try:
            result_queue = queue.Queue()  # Create a queue to hold the result
            load_thread = threading.Thread(target=load_model_with_timeout, args=(result_queue,))
            load_thread.start()
            load_thread.join(timeout=60)  # Wait for up to 60 seconds
        except Exception as e:
            logger.error(f"Unhandled exception occurred load_thread: {e}", exc_info=True)
            return

        if not load_thread.is_alive():
            try:
                result = result_queue.get_nowait()  # Get the result from the queue
                if isinstance(result, Exception):
                    logger.error("YOLOv5 model loading failed with an exception.")
                    return
                model = result  # Successfully loaded model
                logger.debug("YOLOv5 model loaded successfully.")
            except queue.Empty:
                logger.error("YOLOv5 model loading failed: No result returned.")
                return
        else:
            logger.error("YOLOv5 model loading timed out.")
            load_thread.join()  # Ensure the thread is cleaned up
            return

        # Filter for 'boat' class (COCO ID for 'boat' is 8)
        model.classes = [8]

        # SETUP VIDEO WRITER
        video1_h264_file = os.path.join(video_path, "video1.h264")
        video_writer, writer_type = get_h264_writer(
            video1_h264_file,
            fps=fps,
            frame_size=frame_size,
            force_sw=True,
            logger=logger)
        logger.info(f"Video writer initialized: {writer_type} -> {video1_h264_file}")

        if video_writer is None:
            logger.error("Failed to initialize H.264 writer, aborting recording")
            return

        # CONFIGURE DETECTION LOGIC
        pre_detection_duration = 0.5  # Seconds
        max_post_detection_duration = 1  # sec

        pre_detection_buffer = deque(maxlen=int(pre_detection_duration * fpsw))  # Adjust buffer size if needed
        number_of_post_frames = 0
        last_written_id = -1   # ensures frames never go backwards in time
        detections_for_frame = []
        last_detections_for_frame = []  # start empty
        in_detection_sequence = False
        frame_written = False

        # Optional: record *all* frames for testing
        write_all_frames = False

        # Compute scaling factors
        inference_width, inference_height = 640, 480  # Since you resize before inference
        scale_x = crop_width / inference_width
        scale_y = crop_height / inference_height
        aspect_crop = crop_width / crop_height
        aspect_infer = inference_width / inference_height
        logger.debug(f"Crop aspect: {aspect_crop:.2f}, Inference aspect: {aspect_infer:.2f}")
        logger.debug(f"inference_width, inference_height = {inference_width, inference_height}")
        logger.debug(f"crop_width, crop_height = {crop_width, crop_height}")
        logger.debug(f"scale_x = {scale_x}, scale_y = {scale_y}")

        # Base scale text size and thickness
        # base_fontScale = 0.9  # Default font size at 640x480
        base_thickness = 2  # Default thickness at 640x480
        scale_factor = (scale_x + scale_y) / 2  # Average scale factor
        # fontScale = max(base_fontScale * scale_factor, 0.6)  # Prevent too small text
        thickness = max(int(base_thickness * scale_factor), 1)  # Prevent too thin lines
        font = cv2.FONT_HERSHEY_DUPLEX
        # (x, y) → OpenCV cv2.putText expects the bottom-left corner of the text string.
        # x = 40 → fixed horizontal offset, i.e. always 40 pixels from the left edge of the frame
        # y = max(50, frame_height - 100) → vertical position
        origin = (40, int(frame.shape[0] * 0.85))  # Bottom-left corner
        colour = (0, 255, 0)  # Green text

        stall_detected = False
        # MAIN LOOP IN
        try:
            last_frame_time = datetime.now()  # watchdog reference
            while True:
                # --- Every 30 seconds, check system load ---
                if time.time() - last_adjustment > 30:
                    temp = get_cpu_temp()
                    throttle = get_throttle_status()
                    logger.info(f"Temp={temp:.1f}°C Throttle=0x{throttle:x} FPS={fps}")
                    if temp is not None:
                        if temp and temp > 82:
                            fps = max(5, fps - 2)   # lower FPS gradually
                            logger.warning(f"High temp {temp:.1f}°C → reducing FPS to {fps}")
                        elif temp and temp < 70 and fps < 15:
                            fps += 1
                            logger.info(f"Cooler now {temp:.1f}°C → increasing FPS to {fps}")

                    last_adjustment = time.time()

                frame_written = False
                try:
                    if stop_event.is_set():
                        logger.info("stop event set, break recording loop")
                        break

                    # --- WATCHDOG CHECK ---
                    if (datetime.now() - last_frame_time).total_seconds() > 5:
                        logger.error("Watchdog: no new frame for >5s, breaking loop")
                        break

                    # Capture a frame from the camera
                    try:
                        frame = camera.capture_array()
                    except Exception as e:
                        logger.error(f"Camera capture failed: {e}")
                        time.sleep(1 / fps)
                        continue

                    if frame is None or not isinstance(frame, np.ndarray):
                        logger.error("CAPTURE: invalid frame, skipping")
                        time.sleep(1 / fps)
                        continue

                    # Success → update watchdog timer
                    last_frame_time = datetime.now()

                    frame_counter += 1  # Increment the frame counter
                    frame_height, frame_width = frame.shape[:2]

                    # --- TIMESTAMP ---
                    capture_timestamp = datetime.now()
                    text_rectangle(frame, capture_timestamp.strftime("%Y-%m-%d %H:%M:%S"), origin)

                    # Initialize list to store detections for this frame
                    detections_for_frame = []
                    boat_in_current_frame = False

                    # Always-record mode (for testing smoothness & timing)
                    if write_all_frames:
                        if frame_counter > last_written_id:
                            if not safe_write(video_writer, frame):
                                logger.error("Breaking loop due to video writer stall")
                                break
                            last_written_id = frame_counter
                        continue

                    # Store in pre-detection buffer
                    if pre_detection_duration > 0:
                        pre_detection_buffer.append((frame_counter, frame.copy(), capture_timestamp))

                    boat_in_current_frame = False

                    # --- INFERENCE ON EVERY 4TH FRAME ---
                    # Crop region of interest
                    cropped_frame = frame[y_start:y_start + crop_height, x_start:x_start + crop_width]
                    resized_frame = cv2.resize(cropped_frame, (inference_width, inference_height))
                    input_tensor = prepare_input(resized_frame, device='cpu')

                    if frame_counter % 4 == 0:
                        # Run YOLOv5 inference
                        results = model(input_tensor)  # DetectMultiBackend returns list-of-tensors
                        detections = non_max_suppression(results, conf_thres=0.25, iou_thres=0.45)[0]

                        new_detections = []  # temporary holder for this inference step

                        if detections is not None and len(detections):
                            for *xyxy, conf, cls in detections:
                                confidence = float(conf)
                                class_name = model.names[int(cls)]
                                if confidence > DETECTION_CONF_THRESHOLD and class_name == 'boat':
                                    boat_in_current_frame = True
                                    x1, y1, x2, y2 = map(int, xyxy)
                                    # Scale coordinates back to original frame
                                    x1 = int(x1 * scale_x) + x_start
                                    y1 = int(y1 * scale_y) + y_start
                                    x2 = int(x2 * scale_x) + x_start
                                    y2 = int(y2 * scale_y) + y_start

                                    new_detections.append((x1, y1, x2, y2, confidence))

                                    # --- LOGGING ---
                                    # Log every N frames to avoid flooding
                                    if frame_counter % LOG_FRAME_THROTTLE == 0:
                                        logger.info(f"Boat detected in frame {frame_counter} with conf {confidence:.2f}")
                        # --- END OF INFERENCE ---
                        if boat_in_current_frame and not in_detection_sequence:
                            # ... flush pre-buffer ...
                            in_detection_sequence = True

                        # replace detections only on inference frame
                        detections_for_frame = new_detections
                        last_detections_for_frame = new_detections  # cache results
                        logger.debug(f"detections_for_frame length={len(detections_for_frame)}")
                    else:
                        detections_for_frame = last_detections_for_frame
                        logger.debug(f"Reused detections_for_frame length={len(detections_for_frame)}")

                    # --- Check for detections every frame (reuse last until refreshed) ---
                    boat_in_current_frame = bool(last_detections_for_frame)

                    # Detect transitions: from detection → post phase
                    if boat_in_current_frame:
                        # Active detection → reset post-frame counter
                        if number_of_post_frames <= 0:
                            number_of_post_frames = int(max_post_detection_duration * fpsw)
                    else:
                        # No detection → count down only if previously detecting
                        if number_of_post_frames > 0:
                            number_of_post_frames -= 1

                    frame_written = False
                    # --- DETECTION ACTIVE ---
                    if boat_in_current_frame and not frame_written:
                        # If entering detection for the first time → flush pre-buffer
                        if not in_detection_sequence:

                            logger.debug("=== Entering detection sequence ===")
                            while pre_detection_buffer:
                                buf_id, buf_frame, buf_ts = pre_detection_buffer.popleft()
                                label = f"{buf_ts:%Y-%m-%d %H:%M:%S} PRE"
                                text_rectangle(buf_frame, label, origin)
                                if not safe_write(video_writer, buf_frame):
                                    logger.error("Breaking loop due to video writer stall")
                                    stall_detected = True
                                    break
                                last_written_id = buf_id
                            in_detection_sequence = True

                        # --- CURRENT FRAME ---
                        for (x1, y1, x2, y2, confidence) in last_detections_for_frame:
                            cv2.rectangle(frame, (x1, y1), (x2, y2), colour, thickness)
                            cv2.putText(frame, f"{confidence:.2f}", (x1, y1 - 10),
                                        font, 0.7, (0, 255, 0), 2)

                        label = capture_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        text_rectangle(frame, label, origin)
                        if not safe_write(video_writer, frame):
                            logger.error("Breaking loop due to video writer stall")
                            stall_detected = True
                            break
                        last_written_id = frame_counter
                        frame_written = True
                        number_of_post_frames = int(max_post_detection_duration * fpsw)
                        logger.debug(f"Current FRAME @ {capture_timestamp:%H:%M:%S} (frame={frame_counter})")

                        # === NEW: ASYNCHRONOUS OCR EXECUTION ===
                        # Only try to run OCR if the queue is not currently busy
                        if ocr_queue.empty() and frame_counter % 30 == 0: # <-- Throttle to max once per 2 seconds (30 frames)

                            # We need the full frame (not the cropped/resized one) and the box
                            # Use the *last_detections_for_frame* which contains the coordinates
                            if last_detections_for_frame:
                                # Take the first (largest/most confident) boat detection box
                                box_data = last_detections_for_frame[0][:4]

                                # Put the required data into the queue. frame.copy() is CRITICAL.
                                try:
                                    ocr_queue.put((frame.copy(), box_data, capture_timestamp), block=False)
                                    logger.debug("Pushed frame to OCR queue.")
                                except queue.Full:
                                    logger.debug("OCR queue full, skipping this frame.")

                    # --- POST-DETECTION FRAMES ---
                    elif number_of_post_frames > 0 and not frame_written:
                        label = f"{capture_timestamp:%Y-%m-%d %H:%M:%S} POST"
                        text_rectangle(frame, label, origin)
                        if not safe_write(video_writer, frame):
                            logger.error("Breaking loop due to video writer stall")
                            stall_detected = True
                            break
                        last_written_id = frame_counter
                        frame_written = True
                        number_of_post_frames -= 1
                        logger.debug(
                            f"FRAME: post-detection written @ {capture_timestamp:%H:%M:%S} "
                            f"(countdown={number_of_post_frames})"
                        )
                    # --- NO DETECTION ACTIVE ---
                    else:
                        if in_detection_sequence and number_of_post_frames == 0:
                            logger.debug("=== Exiting detection sequence ===")
                            in_detection_sequence = False
                    # --- NO WRITING OTHERWISE ---
                    if not frame_written:
                        logger.debug(f"Frame {frame_counter} skipped (no detection, no post frames active)")

                except Exception as e:
                    logger.error(f"Unhandled error in recording loop: {e}", exc_info=True)
                    continue  # skip this iteration

                # === CHECK OCR RESULTS and LOG ===
                try:
                    result = ocr_result.get(block=False)  # Check for a result immediately
                    sail_number = result['num']
                    timestamp = result['ts']
                    log_sailnumber_to_csv(sail_number, timestamp)
                    # OPTIONAL: You can draw the recognized number on the current live frame here if desired
                    # ...
                except queue.Empty:
                    pass  # No result yet, keep going

                # --- Sleep according to current FPS ---
                time.sleep(1 / fps)

                # Stop condition
                elapsed_time = (datetime.now() - start_time_dt).total_seconds()

                if stop_event.is_set() or elapsed_time >= max_duration:
                    logger.debug(f"STOP: stop_event set or max duration reached ({elapsed_time:.1f}s)")
                    break
        finally:
            # ---ENSURE RELEASE OUTSIDE LOOP ---
            logger.info('Video1 recording stopped')
            # Stop camera cleanly
            try:
                if camera is not None:
                    logger.info("Stopping camera after recording loop")
                    camera.stop()
                    camera = None
            except Exception as e:
                logger.error(f"Error stopping camera: {e}")

            # Release video writer
            try:
                if video_writer is not None:
                    video_writer.release()
                    video_writer = None
                    logger.info(f"Video1 H.264 writer released: {video1_h264_file}")
            except Exception as e:
                logger.error(f"Error releasing video_writer: {e}")

            # Remux H264 → MP4
            video1_mp4_file = os.path.join(video_path, "video1.mp4")
            try:
                if stall_detected:
                    logger.warning("Video writer stall detected → attempting immediate remux of partial file")
                else:
                    logger.info("Normal stop → remuxing video")
                process_video(video_path, "video1.h264", "video1.mp4", mode="remux")
                logger.info(f"Video1 remuxed to MP4: {video1_mp4_file}")
            except Exception as e:
                logger.error(f"Error during remux: {e}")


def safe_write(video_writer, frame, timeout=2.0):
    """Write a frame with timeout protection."""
    result = [False]

    def _write():
        try:
            video_writer.write(frame)
            result[0] = True
        except Exception as e:
            logger.error(f"Video write failed: {e}")

    t = threading.Thread(target=_write, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        logger.error("Video write timeout — encoder likely stalled")
        return False
    return result[0]


def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read()) / 1000.0  # °C
    except FileNotFoundError:
        return None


def get_throttle_status():
    try:
        output = subprocess.check_output(["vcgencmd", "get_throttled"]).decode().strip()
        return int(output.split('=')[1], 16)
    except Exception:
        return 0


def main():
    camera = None
    global stop_event, listen_thread, wd_thread
    global ocr_thread
    try:
        # --- Camera setup ---
        camera = setup_camera()  # choose resolution internally
        if camera is None:
            logger.error("CAMERA SETUP: failed")
            return 1

        # --- Parse JSON ---
        if len(sys.argv) < 2:
            logger.error("No JSON data provided as a command-line argument.")
            return 1

        # logger.info("form_data: %s", form_data)
        form_data = json.loads(sys.argv[1])
        week_day = str(form_data["day"])
        video_end = int(form_data["video_end"])
        num_starts = int(form_data["num_starts"])
        start_time_str = str(form_data["start_time"])  # this is the first start
        dur_between_starts = int(form_data["dur_between_starts"])

        today = dt.date.today()
        start_time_today = dt.datetime.combine(today, dt.datetime.strptime(start_time_str, "%H:%M").time())

        # If start_time has already passed today, schedule for tomorrow
        if start_time_today < dt.datetime.now():
            start_time_dt = start_time_today + dt.timedelta(days=1)
        else:
            start_time_dt = start_time_today

        t5min_warning = start_time_dt - dt.timedelta(minutes=5)  # time to start start-machine.
        # wd = dt.datetime.today().strftime("%A")

        remove_video_files(photo_path, "video")  # clean up
        remove_picture_files(photo_path, ".jpg")  # clean up

        logger.info("Weekday=%s, Start_time=%s, num_starts=%s",
                    week_day, start_time_dt, num_starts)

        # --- Wait until 5-minute warning ---
        while dt.datetime.now() < t5min_warning:
            time.sleep(1)

        # --- Start listening thread ---
        global listen_thread
        listen_thread = threading.Thread(target=listen_for_messages, args=(stop_event,), daemon=True)
        listen_thread.start()

        # --- Start OCR thread before the main recording loop ---
        ocr_thread = threading.Thread(target=ocr_worker, 
                                      args=(ocr_queue, ocr_result, stop_event), 
                                      daemon=True)
        ocr_thread.start()
        logger.info("OCR Thread started.")

        # --- Start video0 recording & start sequences ---
        start_video_recording(camera, video_path, "video0.h264", resolution=(1640,1232), bitrate=4000000)
        start_sequence(camera, start_time_dt, num_starts, dur_between_starts, photo_path)
        last_start = start_time_dt + dt.timedelta(minutes=(num_starts - 1) * dur_between_starts)
        end_time = last_start + dt.timedelta(minutes=2)
        while dt.datetime.now() < end_time:
            time.sleep(0.2)

        # VIDEO0 RECORDING STOP & PROCESS
        stop_video_recording(camera)
        # process_video(video_path, "video0.h264", "video0.mp4", frame_rate=30, resolution=(1640,1232))
        process_video(video_path, "video0.h264", "video0.mp4", mode="remux")

        # --- VIDEO1, Finish recording & process videos ---
        finish_recording(camera, video_path, num_starts, video_end, start_time_dt, fps)

        # --- Write status --
        with open('/var/www/html/status.txt', 'w') as status_file:
            status_file.write('complete')
        return 0  # success

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return 1
    finally:
        logger.info("Main finally: cleanup")
        stop_event.set()  # ensure listener and recording exit
        if listen_thread:
            listen_thread.join(timeout=2)
            if listen_thread.is_alive():
                logger.warning("listen_thread did not stop manually, within timeout.")
            else:
                logger.info("listen_thread stopped cleanly.")
        if wd_thread:
            wd_thread.join(timeout=1)
            logger.info("Watchdog thread stopped cleanly.")

        if ocr_thread:
            ocr_thread.join(timeout=2)
            if ocr_thread.is_alive():
                logger.warning("OCR thread did not stop gracefully.")
            else:
                logger.info("OCR thread stopped cleanly.")
        gc.collect()
        logger.info("Cleanup complete")

if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:
        logger.error(f"An unhandled exception occurred: {e}", exc_info=True)
        rc = 1
    sys.exit(rc)