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
import select
import threading
import time
import cv2
import torch
import warnings
import queue
import site
import gc
import atexit
import sys
sys.path.append('/home/pi/yolov5')  # Adjust as needed
logger.info(f"Running with Python: {sys.executable}")
site.ENABLE_USER_SITE = False

warnings.filterwarnings(
    "ignore",
    message="torch.cuda.amp.autocast",
    category=FutureWarning,
    module=".*yolov5_master.models.common*"
)
# Parameter data
fps = 15  # frames per second for video1
signal_dur = 0.9  # seconds
log_path = '/var/www/html/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
crop_width, crop_height = 1440, 1080  # Crop size for inference
listening = True  # Define the listening variable
recording_stopped = False  # Global variable

cpu_model = get_cpu_model()
logger.info("="*60)
logger.info(f"Starting new regattastart9.py session at {dt.datetime.now()}")
logger.info(f"Detected CPU model string: '{cpu_model}'")
logger.info("="*60)

# reset the contents of the status variable, used for flagging that
# video1-conversion is complete.
with open('/var/www/html/status.txt', 'w') as status_file:
    status_file.write("")


def stop_recording():
    global listening, recording_stopped
    logger.info("stop_recording called. Stopping recording early.")
    recording_stopped = True
    listening = False  # exit listen_for_messages loop
    logger.debug(f"recording_stopped = {recording_stopped}, listening = {listening}")


def listen_for_messages(stop_event, timeout=0.1):
    global listening  # Use global flag
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
                        stop_recording()
                        logger.info("Message == stop_recording")
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


def finish_recording(camera, video_path, num_starts, video_end, start_time_dt, fps):
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
        logger.error("CAMERA RESTART: failed, exiting.")
        return  # Prevents crashing if camera restart fails

    # Attempt to capture a frame
    try:
        logger.debug("Attempting to capture the first frame.")
        frame = camera.capture_array()
        if frame is None:
            logger.error("CAPTURE: frame is None, skipping")
            time.sleep(1/fps)
            return
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

    # Load the pre-trained YOLOv5 model (e.g., yolov5s)
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

    # Continue with the rest of the `finish_recording` logic
    logger.debug("After loading YOLOv5 model.")

    # Filter for 'boat' class (COCO ID for 'boat' is 8)
    model.classes = [8]

    # SETUP VIDEO WRITER
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

    # Setup pre-detection parameters
    pre_detection_duration = 0  # Seconds
    pre_detection_buffer = deque(maxlen=int(pre_detection_duration*fpsw))  # Adjust buffer size if needed
    processed_timestamps = set()  # Use a set for fast lookups

    # setup Post detection
    max_post_detection_duration = 0  # sec
    logger.info(f"max_duration,{max_duration}, FPS={fpsw},"
                f"pre_detection_duration = {pre_detection_duration}, "
                f"max_post_detection_duration={max_post_detection_duration}")
    number_of_post_frames = int(fpsw * max_post_detection_duration)  # Initial setting, to record after detection

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
    last_written_id = -1   # keep track of last written frame

    # MAIN LOOP
    while not recording_stopped:
        frame_counter += 1  # Increment the frame counter
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

        # --- PRE-DETECTION BUFFER ---
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
        # --- INFERENCE ON EVERY 5TH FRAME ---
        if frame_counter % 5 == 0:
            # Crop region of interest
            cropped_frame = frame[y_start:y_start + crop_height, x_start:x_start + crop_width]
            resized_frame = cv2.resize(cropped_frame, (inference_width, inference_height))
            input_tensor = prepare_input(resized_frame, device='cpu')

            # Run YOLOv5 inference
            results = model(input_tensor)  # DetectMultiBackend returns list-of-tensors
            detections = non_max_suppression(results, conf_thres=0.25, iou_thres=0.45)[0]

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

                        # Draw bounding box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), colour, thickness)
                        # Draw confidence
                        cv2.putText(frame, f"{confidence:.2f}", (x1, y1 - 10), 
                                    font, 0.7, (0, 255, 0), 2)
                        # Draw timestamp below box
                        y_text = min(y2 + 50, int(frame_height * 0.92))  # clamp so text does not go outside
                        detected_timestamp = capture_timestamp.strftime("%H:%M:%S")
                        cv2.putText(frame, detected_timestamp, (x1, y_text),
                                    font, fontScale, colour, thickness)

                        # --- LOGGING ---
                        # Log every N frames to avoid flooding
                        LOG_FRAME_THROTTLE = 10
                        if boat_in_current_frame and (frame_counter % LOG_FRAME_THROTTLE == 0):
                            logger.info(f"Boat detected in frame {frame_counter} with conf {confidence:.2f}")

        # -- WRITE VIDEO ---
        if boat_in_current_frame:
            # Flush pre-detection buffer
            while pre_detection_buffer:
                buf_frame, buf_ts = pre_detection_buffer.popleft()
                if buf_frame is not None:
                    if buf_frame.shape[1] != camera_frame_size[0] or buf_frame.shape[0] != camera_frame_size[1]:
                        buf_frame_full = cv2.resize(buf_frame, camera_frame_size)
                    else:
                        buf_frame_full = buf_frame
                    text_rectangle(buf_frame_full, f"PRE {buf_ts:%H:%M:%S}", origin)

                    # write only if newer than last_written_id
                    if frame_counter > last_written_id:
                        video_writer.write(buf_frame_full)
                        last_written_id = frame_counter

            pre_detection_buffer.clear()

            # Overlay timestamp on the ORIGINAL full frame (not the cropped inference frame)
            if frame is not None:
                if frame.shape[1] != camera_frame_size[0] or frame.shape[0] != camera_frame_size[1]:
                    frame_full = cv2.resize(frame, camera_frame_size)
                else:
                    frame_full = frame
                text_rectangle(frame_full, capture_timestamp.strftime("%Y-%m-%d, %H:%M:%S"), origin)

                # write only if newer than last_written_id
                if frame_counter > last_written_id:
                    video_writer.write(frame_full)
                    last_written_id = frame_counter
                    logger.debug(f"FRAME: detection written @ {capture_timestamp.strftime('%H:%M:%S')} with writer_frame_size: {camera_frame_size}")

            # Reset post-detection countdown
            number_of_post_frames = int(max_post_detection_duration * fpsw)

        elif number_of_post_frames > 0:
            if frame is not None:
                if frame.shape[1] != camera_frame_size[0] or frame.shape[0] != camera_frame_size[1]:
                    frame_full = cv2.resize(frame, camera_frame_size)
                else:
                    frame_full = frame
                text_rectangle(frame_full, f"POST {capture_timestamp.strftime('%H:%M:%S')}", origin)

                # write only if newer than last_written_id
                if frame_counter > last_written_id:
                    video_writer.write(frame_full)
                    last_written_id = frame_counter
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
        try:
            if video_writer is not None:
                video_writer.release()
                video_writer = None
                logger.info(f"Video1 H.264 writer released: {video1_h264_file}")
        except Exception as e:
            logger.error(f"Error releasing video_writer: {e}")
    # Remux
    video1_mp4_file = os.path.join(video_path, "video1.mp4")
    process_video(video_path, "video1.h264", "video1.mp4", mode="remux")
    logger.info(f"Video1 remuxed to MP4: {video1_mp4_file}")
    return


def stop_listen_thread():
    global listening
    listening = False
    logger.info("stop_listening thread called: listening set to False")


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

        # --- Finish recording & process videos ---
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
