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
stop_event = threading.Event()
listen_thread = None   # placeholder for the listener thread
wd_thread = None

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


def finish_recording(camera, video_path, num_starts, video_end, start_time_dt, fps):
    from utils.general import non_max_suppression
    # config
    DETECTION_CONF_THRESHOLD = 0.5
    LOG_FRAME_THROTTLE = 10  # log every N frames when boat found
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
    pre_detection_duration = 0.2  # Seconds
    max_post_detection_duration = 0.7  # sec

    pre_detection_buffer = deque(maxlen=int(pre_detection_duration * fpsw))  # Adjust buffer size if needed
    number_of_post_frames = 0
    last_written_id = -1   # ensures frames never go backwards in time
    detections_for_frame = []

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
    base_fontScale = 0.9  # Default font size at 640x480
    base_thickness = 2  # Default thickness at 640x480
    scale_factor = (scale_x + scale_y) / 2  # Average scale factor
    # fontScale = max(base_fontScale * scale_factor, 0.6)  # Prevent too small text
    thickness = max(int(base_thickness * scale_factor), 1)  # Prevent too thin lines
    font = cv2.FONT_HERSHEY_DUPLEX
    # (x, y) → OpenCV cv2.putText expects the bottom-left corner of the text string.
    # x = 50 → fixed horizontal offset, i.e. always 50 pixels from the left edge of the frame
    # y = max(50, frame_height - 100) → vertical position
    origin = (40, int(frame.shape[0] * 0.90))  # Bottom-left corner
    colour = (0, 255, 0)  # Green text

    # MAIN LOOP IN finish_recording
    try:
        while True:
            try:
                if stop_event.is_set():
                    logger.info("stop event set, break recording loop")
                    break

                # Capture a frame from the camera
                frame = camera.capture_array()
                if frame is None:
                    time.sleep(1/fps)
                    logger.error("CAPTURE: frame is None, skipping")
                    continue
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
                        video_writer.write(frame)
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

                    # replace detections only on inference frame
                    detections_for_frame = new_detections
                    last_detections_for_frame = new_detections  # cache results
                    logger.debug(f"detections_for_frame length={len(detections_for_frame)}")
                else:
                    detections_for_frame = last_detections_for_frame

                # --- Check for detections every frame (reuse last until refreshed) ---
                boat_in_current_frame = bool(detections_for_frame)

                # -- WRITE VIDEO ---
                if boat_in_current_frame:
                    # --- PRE-FRAMES ---
                    while pre_detection_buffer:
                        buf_id, buf_frame, buf_ts = pre_detection_buffer.popleft()
                        label = f"{buf_ts:%Y-%m-%d %H:%M:%S} PRE"
                        text_rectangle(buf_frame, label, origin)
                        video_writer.write(buf_frame)
                        last_written_id = buf_id
                        logger.debug(
                            f"PRE FRAME @ {buf_ts:%H:%M:%S} "
                            f"(pre_detection_buffer size={len(pre_detection_buffer)})"
                        )
                    # --- CURRENT FRAME ---
                    for (x1, y1, x2, y2, confidence) in detections_for_frame:
                        # Draw all detections for this frame
                        cv2.rectangle(frame, (x1, y1), (x2, y2), colour, thickness)
                        cv2.putText(frame, f"{confidence:.2f}", (x1, y1 - 10),
                                    font, 0.7, (0, 255, 0), 2)

                    # Timestamp (always added last so it stays visible)
                    label = capture_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    text_rectangle(frame, label, origin)

                    video_writer.write(frame)
                    last_written_id = frame_counter
                    logger.debug(
                        f"Current FRAME @ {capture_timestamp:%H:%M:%S} "
                        f"(framecounter={frame_counter})"
                    )

                    # Reset post-detection counter
                    number_of_post_frames = int(max_post_detection_duration * fpsw)

                # --- POST-FRAMES ---
                elif number_of_post_frames > 0:
                    label = f"{capture_timestamp:%Y-%m-%d %H:%M:%S} POST"
                    text_rectangle(frame, label, origin)
                    video_writer.write(frame)
                    last_written_id = frame_counter
                    number_of_post_frames -= 1
                    logger.debug(
                        f"FRAME: post-detection written @ {capture_timestamp:%H:%M:%S} "
                        f"(countdown={number_of_post_frames})"
                    )

            except Exception as e:
                logger.error(f"Unhandled error in recording loop: {e}", exc_info=True)
                continue  # skip this iteration

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
            logger.info("Calling process_video for %s → %s", video1_h264_file, video1_mp4_file)
            process_video(video_path, "video1.h264", "video1.mp4", mode="remux")
            logger.info(f"Video1 remuxed to MP4: {video1_mp4_file}")
        except Exception as e:
            logger.error(f"Error during remux: {e}")


def main():
    camera = None
    global stop_event, listen_thread, wd_thread
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

        # --- Start watchdog ---
        # stop_event = threading.Event()
        # wd_thread = start_watchdog_thread(heartbeat_file="/tmp/regattastart.heartbeat", interval=5)
        # wd_thread = start_watchdog(timeout=15)  # adjust timeout as needed
        # logger.info("Watchdog thread started")

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
                logger.warning("listen_thread did not stop within timeout.")
            else:
                logger.info("listen_thread stopped cleanly.")
        if wd_thread:
            wd_thread.join(timeout=1)
            logger.info("Watchdog thread stopped cleanly.")
        gc.collect()
        logger.info("Cleanup complete")


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:
        logger.error(f"An unhandled exception occurred: {e}", exc_info=True)
        rc = 1
    sys.exit(rc)