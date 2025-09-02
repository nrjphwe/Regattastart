#!/home/pi/yolov5_env/bin/python
# after git pull, do: sudo cp regattastart9.py /usr/lib/cgi-bin/
import os
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
    clean_exit,
)
import sys
import cv2

""" The os.chdir('/home/pi/yolov5') and manual addition of venv_path to "
sys.path in your script may be unnecessary if the virtual environment "
is correctly set up." os.chdir('/home/pi/yolov5')

Manually add the virtual environment's site-packages directory to sys.path
venv_path = "/home/pi/yolov5_env/lib/python3.11/site-packages"
if venv_path not in sys.path: sys.path.insert(0, venv_path)
"""

# Use a deque to store the most recent frames in memory
from collections import deque, Counter
from datetime import datetime
import datetime as dt
import json
# import numpy as np # image recognition
import select
import threading
import time
import numpy as np  # image recognition
import torch
import gc
import warnings
import queue
import atexit
import csv

warnings.filterwarnings(
    "ignore",
    message="torch.cuda.amp.autocast",
    category=FutureWarning,
    module=".*yolov5_master.models.common*"
)
# Parameter data
fps = 15
signal_dur = 0.9  # sec
log_path = '/var/www/html/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
# crop_width, crop_height = 1440, 1080  # Crop size for inference
crop_width, crop_height = 1280, 720  # Crop size for inference
listening = True  # Define the listening variable
recording_stopped = False  # Global variable

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
    global listening, recording_stopped
    logger.info("stop_recording function called. Setting flags to stop listening and recording.")
    recording_stopped = True
    listening = False  # Set flag to False to terminate the loop in listen_for_messages
    logger.debug(f"recording_stopped = {recording_stopped}, listening = {listening}")


def listen_for_messages(stop_event, timeout=0.1):
    pipe_path = '/var/www/html/tmp/stop_recording_pipe'
    logger.info("listen_for_messages: starting")
    logger.info(f"pipepath = {pipe_path}")

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
                    if message == 'stop_recording':
                        stop_recording()
                        logger.info("Message == stop_recording")
                        break  # Exit the loop when stop_recording received
        except Exception as e:
            logger.error(f"Error in listen_for_messages: {e}", exc_info=True)
        time.sleep(0.05)
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
        model = torch.hub.load('/home/pi/yolov5', 'yolov5s', source='local', force_reload=True)
        result_queue.put(model)  # Put the model in the queue
    except Exception as e:
        logger.error(f"Failed to load YOLOv5 model: {e}", exc_info=True)
        result_queue.put(e)  # Put the exception in the queue


def correct_ocr_digits(text):
    corrections = {
        "I": "1",
        "l": "1",   # lowercase L
        "O": "0",
        "Q": "0",
        "S": "5",   # depending on font, this can be optional
        "Z": "2",
        "B": "8",
        "G": "6",   # sometimes 'G' looks like '6' in OCR
        "E": "3",   # if needed
    }

    corrected = ""
    for char in text:
        corrected += corrections.get(char, char)
    return corrected


def extract_sail_number(frame, box,clahe):
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



def finish_recording(camera, model, video_path, num_starts, video_end, start_time_dt, fps):
    from utils.general import non_max_suppression
    # config
    DETECTION_CONF_THRESHOLD = 0.5
    LOG_FRAME_THROTTLE = 10  # log every N frames when boat found
    global recording_stopped
    confidence = 0.0  # Initial value
    class_name = ""  # Initial value
    frame_counter = 0  # Initialize a frame counter
    boat_in_current_frame = False  # Initialize detection flag

    # Set duration of video1 recording
    max_duration = (video_end + (num_starts-1)*5) * 60
    logger.debug(f"Video1, max recording duration: {max_duration} seconds")

    # Ensure the camera is stopped before reconfiguring
    try:
        if camera is not None:
            logger.info("Stopping the camera before reconfiguring.")
            camera.stop()
        else:
            logger.warning("Camera was already None before restart.")

    except Exception as e:
        logger.error(f"Error while stopping camera: {e}")
        return

    camera = restart_camera(camera, resolution=(1920, 1080), fps=fps)
    # Confirm cam is initialized
    if camera is None:
        logger.error("CAMERA RESTART: failed.")
        return  # Prevents crashing if camera restart fails

    # Attempt to capture a frame
    try:
        logger.debug("Attempting to capture the first frame.")
        frame = camera.capture_array()
        if frame is None:
            logger.error("First captured frame is None! Exiting video recording.")
            return
        else:
            logger.debug(f"First frame captured successfully. Frame shape: {frame.shape}, dtype={frame.dtype}")
    except Exception as e:
        logger.error(f"Exception occurred while capturing the first frame: {e}", exc_info=True)
        return

    # Confirm resolution before proceeding
    try:
        frame_size = (frame.shape[1], frame.shape[0])
        time.sleep(0.5)  # Add a short delay to ensure the camera is ready
        logger.info(f"Camera frame size before recording: {frame_size}")
    except Exception as e:
        logger.error(f"Exception occurred while accessing frame size: {e}", exc_info=True)
        return

    # Define crop data to maintain the square (1:1) aspect ratio
    try:
        logger.debug("calculate crop data for the frame.")
        shift_offset = 100  # horisontal offset for crop -> right part
        # Get dimensions of the full-resolution frame (1640x1232 in your case)
        frame_height, frame_width = frame.shape[:2]  # shape = (height, width, channels)
        x_start = max((frame_width - crop_width) // 2 + shift_offset, 50)
        y_start = max((frame_height - crop_height) // 2, 0)

        if frame_size != (1920, 1080):
            logger.error(f"Resolution mismatch! Expected (1920, 1080) but got {frame_size}.")
        else:
            logger.debug("Resolution matches expected values.")

    except Exception as e:
        logger.error(f"Unhandled exception occurred: {e}", exc_info=True)
        return
    logger.debug(f"Frame size used to crop for inference calculated, size: {crop_width}x{crop_height}")

    # Set the camera to the desired resolution and frame rate
    fpsw = fps
    logger.debug(f"FPS set to {fpsw}, proceeding to load YOLOv5 model.")

    # --- SETUP VIDEO_WRITER (H.264 hardware if possible) ---
    # 'avc1' is the MP4-friendly FourCC for H.264
    # 'H264' also works, but 'avc1' avoids some playback issues on Windows/Mac

    # setup video writer
    video1_file = os.path.join(video_path, "video1.mp4")
    video_writer, writer_type = get_h264_writer(video1_file, fps, frame_size)
    logger.info(f"Video writer backend: {writer_type}")
    if video_writer is None or getattr(video_writer, "proc", None) is None:
        logger.error("FFmpeg writer failed to initialize — no video will be created!")
    else:
        logger.info(f"FFmpeg writer started for {video_path}")

    # Buffers
    pre_detection_duration = 0  # Seconds
    pre_detection_buffer = deque(maxlen=int(pre_detection_duration*fpsw))  # Adjust buffer size if needed
    processed_timestamps = set()  # Use a set for fast lookups
    max_post_detection_duration = 0  # sec
    # logger.info(f"max_duration,{max_duration}, FPS={fpsw},"
    #            f"pre_detection_duration = {pre_detection_duration}, "
    #            f"max_post_detection_duration={max_post_detection_duration}")
    number_of_post_frames = int(fpsw * max_post_detection_duration)  # Initial setting, to record after detection
    boat_in_current_frame = False
    frame_counter = 0  # Initialize a frame counter

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

    # Font size and thickness
    base_fontScale = 0.9  # Default font size at 640x480
    base_thickness = 2  # Default thickness at 640x480
    scale_factor = (scale_x + scale_y) / 2  # Average scale factor
    fontScale = max(base_fontScale * scale_factor, 0.6)  # Prevent too small text
    thickness = max(int(base_thickness * scale_factor), 1)  # Prevent too thin lines
    font = cv2.FONT_HERSHEY_DUPLEX
    # (x, y) → OpenCV cv2.putText expects the bottom-left corner of the text string.
    # x = 50 → fixed horizontal offset, i.e. always 50 pixels from the left edge of the frame
    # y = max(50, frame_height - 100) → vertical position
    origin = (40, int(frame.shape[0] * 0.90))  # Bottom-left corner
    colour = (0, 255, 0)  # Green text

    # OCR init
    ocr_history = deque(maxlen=40)  # ~8–12 s depending on your sampling
    OCR_EVERY = 2
    ocr_tick = 0

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

    # MAIN LOOP
    while not recording_stopped:
        frame_counter += 1
        # Capture a frame from the camera
        try:
            frame = camera.capture_array()
            if frame is None:
                logger.error("CAPTURE: frame is None, skipping")
                continue
            capture_timestamp = datetime.now()

        except Exception as e:
            logger.error(f"Failed to capture frame: {e}")
            continue  # Skips this iteration but keeps running the loop

        # --- Buffering ---
        if pre_detection_duration != 0 and capture_timestamp not in processed_timestamps:
            # Add frame to buffer and record its timestamp
            pre_detection_buffer.append((frame.copy(), capture_timestamp))
            processed_timestamps.add(capture_timestamp)

            # Trim processed_timestamps only when necessary
            if len(processed_timestamps) > pre_detection_buffer.maxlen:
                # Keep only the most recent N entries
                processed_timestamps = set(
                    list(processed_timestamps)[-pre_detection_buffer.maxlen:]
                )
                logger.debug(f"Trimmed processed_timestamps to {len(processed_timestamps)} entries")
            if frame_counter % 20 == 0:
                cleanup_processed_timestamps(processed_timestamps)

        boat_in_current_frame = False   # Reset per frame

        # --- INFERENCE ---
        if frame_counter % 4 == 0:  # process every 4th frame
            # Crop region of interest
            cropped_frame = frame[y_start:y_start + crop_height, x_start:x_start + crop_width]
            resized_frame = cv2.resize(cropped_frame, (inference_width, inference_height))
            results = model(resized_frame)
            detections = results.pandas().xyxy[0]  # DataFrame output

            if not detections.empty:
                for _, row in detections.iterrows():
                    class_name = row['name']
                    confidence = row['confidence']

                    if confidence > DETECTION_CONF_THRESHOLD and class_name == 'boat':
                        boat_in_current_frame = True
                        # Timestamp overlay
                        text_rectangle(frame, capture_timestamp.strftime("%Y-%m-%d, %H:%M:%S"), origin)

                        # Scale bounding box back to original coords
                        x1 = int(row['xmin'] * scale_x) + x_start
                        y1 = int(row['ymin'] * scale_y) + y_start
                        x2 = int(row['xmax'] * scale_x) + x_start
                        y2 = int(row['ymax'] * scale_y) + y_start
                        cv2.rectangle(frame, (x1, y1), (x2, y2), colour, thickness)
                        # Draw bounding box + confidence
                        cv2.putText(frame, f"{confidence:.2f}", (int(x1), int(y1) - 10),
                                    font, 0.7, (0, 255, 0), 2)

                        detected_timestamp = capture_timestamp.strftime("%H:%M:%S")
                        cv2.putText(frame, detected_timestamp, (x1, y2 + 50),
                                    font, fontScale, colour, thickness)

                        # --- OCR ---
                        w = x2 - x1
                        h = y2 - y1
                        if w >= 120 and h >= 120:
                            ocr_tick += 1
                            if ocr_tick % OCR_EVERY == 0:
                                sail_number = extract_sail_number(frame, (x1,y1,x2,y2), clahe)
                                if sail_number:
                                    logger.debug(f"RAW sailnumber seen: {sail_number} @ {capture_timestamp:%H:%M:%S}")
                                    ocr_history.append((sail_number, capture_timestamp))
                                    # promote when seen >=3 times in last ~8s
                                    recent = [v for v, t in ocr_history 
                                              if (capture_timestamp - t).total_seconds() <= 8]
                                    if recent:
                                        val, cnt = Counter(recent).most_common(1)[0]
                                        if cnt >= 3:
                                            logger.info(f"CONFIRMED sailnumber: {val} @ {ts:%H:%M:%S}")
                                            log_sailnumber_to_csv(val, ts)  # <-- new line
                                            cv2.putText(frame, val, (x1, y1-25),
                                                        cv2.FONT_HERSHEY_DUPLEX, 0.9, (0,255,0), 2)

                        # --- LOGGING ---
                        if boat_in_current_frame and (frame_counter % LOG_FRAME_THROTTLE == 0):
                            logger.info(f"Boat detected in frame {frame_counter} with conf {confidence:.2f}")

        # -- WRITE VIDEO ---
        if boat_in_current_frame:
            # Flush pre-detection buffer
            while pre_detection_buffer:
                buf_frame, buf_ts = pre_detection_buffer.popleft()
                if buf_frame is not None:
                    buf_frame = cv2.resize(buf_frame, frame_size)  # enforce correct size
                    cv2.putText(buf_frame, f"PRE {buf_ts.strftime('%H:%M:%S')}",
                                (50, max(50, frame_height - 100)), font,
                                fontScale, colour, thickness)
                    video_writer.write(buf_frame)
            pre_detection_buffer.clear()

            # Overlay timestamp
            if frame is not None:
                frame = cv2.resize(frame, frame_size)
                text_rectangle(frame, capture_timestamp.strftime("%Y-%m-%d, %H:%M:%S"), origin)
                video_writer.write(frame)
                logger.debug(f"FRAME: detection written @ {capture_timestamp.strftime('%H:%M:%S')}")

            # Reset post-detection countdown
            number_of_post_frames = int(max_post_detection_duration * fpsw)

        elif number_of_post_frames > 0:
            if frame is not None:
                frame = cv2.resize(frame, frame_size)
                text_rectangle(frame, f"POST {capture_timestamp.strftime('%H:%M:%S')}", origin)
                video_writer.write(frame)
                number_of_post_frames -= 1
                logger.debug(f"FRAME: post-detection written @ {capture_timestamp.strftime('%H:%M:%S')} (countdown={number_of_post_frames})")

        # Check if recording should stop
        time_now = dt.datetime.now()
        elapsed_time = (time_now - start_time_dt).total_seconds()
        if elapsed_time >= max_duration:
            logger.debug(f"STOP: max duration reached ({elapsed_time:.1f}s)")
            recording_stopped = True

    # ---ENSURE RELEASE OUTSIDE LOOP ---
    if recording_stopped:
        logger.info('Video1 recording stopped')
        if video_writer is not None:
            try:
                video_writer.release()
                logger.info(f"Video1 writer released. File finalized at {video1_file}")
            except Exception as e:
                logger.error(f"Error releasing video_writer: {e}")
            video_writer = None
        else:
            logger.warning("Video1 writer was None at shutdown!")
    return video1_file


def stop_listen_thread():
    global listening
    listening = False
    # Log a message indicating that the listen_thread has been stopped
    logger.info("stop_listening thread: listening set to False")


def main():
    stop_event = threading.Event()
    global listening  # Declare listening as global
    camera = None
    listen_thread = None  # Initialize listen_thread variable

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

        # Parse into datetime for today's date
        start_time_dt = dt.datetime.combine(dt.date.today(),
                                            dt.datetime.strptime(start_time_str, "%H:%M").time())
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
        listen_thread = threading.Thread(target=listen_for_messages, args=(stop_event,), daemon=True)
        listen_thread.start()

        # --- Start video0 recording & start sequences ---
        start_video_recording(camera, video_path, "video0.h264", resolution=(1640,1232), bitrate=4000000)
        start_sequence(camera, start_time_dt, num_starts, dur_between_starts, photo_path)
        last_start = start_time_dt + dt.timedelta(minutes=(num_starts - 1) * dur_between_starts)
        end_time = last_start + dt.timedelta(minutes=2)
        while dt.datetime.now() < end_time:
            time.sleep(0.2)

        stop_video_recording(camera)
        process_video(video_path, "video0.h264", "video0.mp4", frame_rate=30, resolution=(1640,1232))

        # ---- load YOLO once here ----
        logger.info("Loading YOLOv5 model once...")
        model = torch.hub.load('/home/pi/yolov5','yolov5s',source='local')
        model.classes = [8]  # boats only
        model.conf = 0.35  # lower conf for recall
        model.iou = 0.45

        # --- Finish recording & process videos ---
        finish_recording(camera, model, video_path, num_starts, video_end, start_time_dt, fps)

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
        stop_event.set()
        if listen_thread:
            listen_thread.join(timeout=2)
            if listen_thread.is_alive():
                logger.warning("listen_thread did not stop within timeout.")
            else:
                logger.info("listen_thread stopped cleanly.")

        clean_exit(camera)
        gc.collect()
        logger.info("Cleanup complete")


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:
        logger.error(f"An unhandled exception occurred: {e}", exc_info=True)
        rc = 1
    sys.exit(rc)
