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
)

# Use a deque to store the most recent frames in memory
from collections import deque
from datetime import datetime, timedelta
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
import pandas
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
# parameter data
fps = 15
cpu_model = get_cpu_model()
logger.info(f"Detected CPU model string: '{cpu_model}'")

signal_dur = 0.9  # 0.9 sec
log_path = '/var/www/html/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
crop_width, crop_height = 1440, 1080  # Crop size for inference
# gpio_handle, LAMP1, LAMP2, SIGNAL, = setup_gpio()
listening = True  # Define the listening variable
recording_stopped = False  # Global variable

logger.info("="*40)
logger.info(f"Starting new regattastart9.py session at {dt.datetime.now()}")
logger.info("="*40)
# reset the contents of the status variable, used for flagging that
# video1-conversion is complete.
with open('/var/www/html/status.txt', 'w') as status_file:
    status_file.write("")


def stop_recording():
    global listening
    global recording_stopped
    logger.info("stop_recording function called. Setting flags to stop listening and recording.")
    recording_stopped = True
    listening = False  # Set flag to False to terminate the loop in listen_for_messages
    logger.debug(f"recording_stopped = {recording_stopped}, listening = {listening}")


def listen_for_messages(stop_event, timeout=0.1):
    global listening  # Use global flag
    logger.debug(f"Listening flag value: {listening}")
    logger.info("listen_for_messages from PHP script via a named pipe")
    pipe_path = '/var/www/html/tmp/stop_recording_pipe'
    logger.info(f"pipepath = {pipe_path}")

    # Ensure the named pipe exists
    try:
        if os.path.exists(pipe_path):
            if os.path.isdir(pipe_path):
                logger.error(f"{pipe_path} is a directory. Remove it or use another path.")
                raise IsADirectoryError(f"{pipe_path} is a directory.")
            else:
                os.unlink(pipe_path)  # Remove existing file or pipe
        os.mkfifo(pipe_path)  # Create a new named pipe
        os.chmod(pipe_path, 0o666)  # Set permissions to allow read/write for all users
        logger.info(f"Pipe created with permissions 666: {pipe_path}")
    except Exception as e:
        logger.error(f"Failed to create named pipe: {e}", exc_info=True)
        return

    while not stop_event.is_set():
        try:
            if not listening:
                logger.info("Listening flag is False. Exiting listen_for_messages.")
                break
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
        except OSError as e:
            logger.error(f"Error while opening or reading pipe: {e}")
            break
        except Exception as e:
            logger.error(f"Error in listen_for_messages: {e}", exc_info=True)
            break
        time.sleep(0.1)  # Add a small delay to prevent high CPU usage
    logger.info("Listening thread exiting")


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
        logger.info(f"Detected CPU model string: '{cpu_model}'")
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
        # model = torch.hub.load('/home/pi/yolov5', 'yolov5s', source='local', force_reload=True)
        # model = torch.hub.load('/home/pi/yolov5', 'custom', path='/var/www/html/yolov5s.pt', source='local')
        result_queue.put(model)  # Put the model in the queue
    except Exception as e:
        logger.error(f"Failed to load YOLOv5 model: {e}", exc_info=True)
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


def finish_recording(camera, video_path, num_starts, video_end, start_time_sec, fps):
    global recording_stopped
    confidence = 0.0  # Initial value
    class_name = ""  # Initial value

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

    # Inference ## Load the pre-trained YOLOv5 model (e.g., yolov5s)
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

    # setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')  # Use 'XVID' for .avi, or 'mp4v' for .mp4
    video_writer = cv2.VideoWriter(video_path + 'video1' + '.avi', fourcc, fpsw, frame_size)
    if not video_writer.isOpened():
        logger.error(f"Failed to open video1.avi for writing. Selected frame_size: {frame_size}")
        exit(1)
    logger.debug(f"Video writer initialized successfully, frame_size: {frame_size}")

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
    boat_in_current_frame = False

    frame_counter = 0  # Initialize a frame counter
    # previous_capture_time = None  # Track previous frame timestamp

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
    origin = (50, max(50, frame_height - 100))
    colour = (0, 255, 0)  # Green text

    while not recording_stopped:
        frame_counter += 1  # Increment the frame counter

        # Capture a frame from the camera
        try:
            frame = camera.capture_array()
            if frame is None:
                logger.error(f"CAPTURE: frame is None, skipping")
                continue
            capture_timestamp = datetime.now() + timedelta(microseconds=frame_counter)

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

        # --- INFERENCE ---
        boat_in_current_frame = False  # Reset detection flag for this frame

        if frame_counter % 4 == 0:  # process every 4th frame
            # Crop region of interest
            cropped_frame = frame[y_start:y_start + crop_height, x_start:x_start + crop_width]
            resized_frame = cv2.resize(cropped_frame, (inference_width, inference_height))

            # Run YOLOv5 inference
            input_tensor = prepare_input(resized_frame, device='cpu')
            results = model(input_tensor)
            detections = results.pandas().xyxy[0]  # DataFrame output

            if not detections.empty:
                for _, row in detections.iterrows():
                    class_name = row['name']
                    confidence = float(row['confidence'])

                    if confidence > 0.5 and class_name == 'boat':
                        boat_in_current_frame = True

                        # Timestamp overlay
                        text_rectangle(frame, capture_timestamp.strftime("%Y-%m-%d, %H:%M:%S"), origin)

                        # Scale bounding box back to original coords
                        x1 = int(row['xmin'] * scale_x) + x_start
                        y1 = int(row['ymin'] * scale_y) + y_start
                        x2 = int(row['xmax'] * scale_x) + x_start
                        y2 = int(row['ymax'] * scale_y) + y_start

                        # Draw bounding box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), colour, thickness)

                        # Draw confidence
                        cv2.putText(frame, f"{confidence:.2f}", (x1, y1 - 10),
                                    font, 0.7, (0, 255, 0), 2)

                        # Draw timestamp below box
                        detected_timestamp = capture_timestamp.strftime("%H:%M:%S")
                        cv2.putText(frame, detected_timestamp, (x1, y2 + 50),
                                    font, fontScale, colour, thickness)

        # --- DECISION LOGIC FOR WRITING ---
        if boat_in_current_frame:
            if frame is not None:
                # Write this detection frame
                video_writer.write(frame)
                logger.debug(f"FRAME: detection written @ {capture_timestamp}")

            # Flush pre-detection buffer
            while pre_detection_buffer:
                buf_frame, buf_ts = pre_detection_buffer.popleft()
                if buf_frame is not None:
                    cv2.putText(buf_frame, f"PRE {buf_ts.strftime('%H:%M:%S')}", (50, max(50, frame_height - 100)),
                                font, fontScale, colour, thickness)
                    video_writer.write(buf_frame)
                    logger.debug(f"FRAME: pre-detection written @ {buf_ts}")
            pre_detection_buffer.clear()

            # Reset post-detection countdown
            number_of_post_frames = int(max_post_detection_duration * fpsw)

        elif number_of_post_frames > 0:
            if frame is not None:
                #  Still within post-detection window
                cv2.putText(frame, f"POST  {capture_timestamp.strftime('%H:%M:%S')}", (50, max(50, frame_height - 100)),
                            font, fontScale, (0, 255, 0), thickness)
                video_writer.write(frame)
                number_of_post_frames -= 1
                logger.debug(f"FRAME: post-detection written @ {capture_timestamp} (countdown={number_of_post_frames})")

        # Check if recording should stop
        time_now = dt.datetime.now()
        seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
        elapsed_time = seconds_since_midnight - start_time_sec
        # logger.debug(f"Elapsed time since start: {elapsed_time} seconds")
        if elapsed_time >= max_duration:
            logger.debug(f"STOP: max duration reached ({elapsed_time:.1f}s)")
            recording_stopped = True

    if recording_stopped:
        logger.info('Video1 recording stopped')
    else:
        logger.info("Calling stop_video_recording")
        stop_video_recording(camera)
        recording_stopped = True
    if video_writer is not None:
        video_writer.release()  # Release the video writer
        logger.info("Video writer released")
    logger.info("Exited the finish_recording module.")


def stop_listen_thread():
    global listening
    listening = False
    # Log a message indicating that the listen_thread has been stopped
    logger.info("stop_listening thread  listening set to False")


def clean_exit():
    logger.info("Forced exit with os._exit(0)")
    os._exit(0)


def main():
    stop_event = threading.Event()
    global listening  # Declare listening as global
    listening = True  # Initialize the global listening flag
    listen_thread = None  # Initialize listen_thread variable
    try:
        if cpu_model and "Raspberry Pi 3" in cpu_model:
            camera = setup_camera((1280, 720))  # Initialize camera
        elif cpu_model and "Raspberry Pi 5" in cpu_model:
            camera = setup_camera((1920, 1080))  # Initialize camera
        else:
            camera = setup_camera((1640, 1232))  # Initialize camera
    except Exception as e:
        logger.error(f"Failed to fins CPU model: {e}", exc_info=True)

    if camera is None:
        logger.error("CAMERA SETUP: failed, exiting.")
        exit()

    # Check if a command-line argument (JSON data) is provided
    if len(sys.argv) < 2:
        logger.error("No JSON data provided as a command-line argument.")
        sys.exit(1)

    try:
        # logger.info("form_data: %s", form_data)
        form_data = json.loads(sys.argv[1])
        week_day = str(form_data["day"])
        video_end = int(form_data["video_end"])
        num_starts = int(form_data["num_starts"])
        # this is the first start
        start_time_str = str(form_data["start_time"])
        dur_between_starts = int(form_data["dur_between_starts"])
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        # Extract hour and minute
        start_hour = start_time.hour
        start_minute = start_time.minute
        start_time_sec = 60 * start_minute + 3600 * start_hour
        t5min_warning = start_time_sec - 5 * 60  # time to start start-machine.
        wd = dt.datetime.today().strftime("%A")

        remove_video_files(photo_path, "video")  # clean up
        remove_picture_files(photo_path, ".jpg")  # clean up
        logger.info("Weekday=%s, Start_time=%s, video_end=%s, num_starts=%s", week_day, start_time.strftime("%H:%M"), video_end, num_starts)

        if wd == week_day:
            # A loop that waits until close to the 5-minute mark, and 
            # continuously checks the condition without blocking the 
            # execution completely
            while True:
                now = dt.datetime.now()
                seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second

                if seconds_since_midnight > t5min_warning - 4:
                    logger.debug("Start of outer loop iteration. seconds_since_midnight=%d", seconds_since_midnight)
                    logger.debug("start_time_sec=%d", start_time_sec)

                    if num_starts == 1 or num_starts == 2 or num_starts == 3:
                        # Start video recording just before 5 minutes before the first start
                        logger.debug("Start of video0 recording")
                        start_video_recording(camera, video_path, "video0.h264", resolution=(1640,1232),  bitrate=4000000)
                        logger.debug("Inner loop, entering the start sequence block.")
                        start_sequence(camera, start_time_sec, num_starts, dur_between_starts, photo_path)
                        if num_starts != 1:
                            start_time_sec = start_time_sec + (dur_between_starts * 60) * num_starts
                        logger.debug("Wait 2 minutes then stop video0 recording")
                        t0 = dt.datetime.now()
                        logger.debug(f"t0 = {t0}, dt.datetime.now(): {dt.datetime.now()}")
                        logger.debug("(dt.datetime.now() - t0).seconds: %d", (dt.datetime.now() - t0).seconds)
                        while ((dt.datetime.now() - t0).seconds < 119):
                            now = dt.datetime.now()
                            time.sleep(0.2)  # Small delay to reduce CPU usage
                        stop_video_recording(camera)
                        logger.debug("Stopping video0 recording")
                        process_video(video_path, "video0.h264", "video0.mp4", frame_rate=30,resolution=(1640, 1232))
                        logger.info("Video0 converted to mp4")
                    break  # Exit the loop after the if condition is met
                time.sleep(1)  # Introduce a delay of 2 seconds

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON: %", str(e))
        sys.exit(1)
    finally:
        logger.info("Finally section, before listen_for_message")
        # Start a thread for listening for messages with a timeout
        listen_thread = threading.Thread(target=listen_for_messages, args=(stop_event,))
        listen_thread.start()
        logger.info("Finally section, before 'Finish recording'. start_time=%s video_end=%s", start_time, video_end)
        time.sleep(2)
        finish_recording(camera, video_path, num_starts, video_end, start_time_sec, fps)
        logger.info("After function finished_recording")
        try:
            stop_event.set()  # Signal the listening thread to stop
            listen_thread.join(timeout=10)
            if listen_thread.is_alive():
                logger.info("listen_thread is still alive after timeout")
            else:
                logger.info("listen_thread finished")

            time.sleep(2)
            process_video(video_path, "video1.avi", "video1.mp4", frame_rate=30,resolution=(1920, 1080))

            # After video conversion is complete
            with open('/var/www/html/status.txt', 'w') as status_file:
                status_file.write('complete')
            logger.info("Finished with finish_recording and recording converted to mp4")

        except Exception as e:
            logger.error(f"An error occurred in the 'finally' section: {e}", exc_info=True)

        finally:
            try:
                stop_video_recording(camera)
                camera.close()
                logger.info("Camera closed successfully.")
            except Exception as e:
                logger.error(f"Error while cleaning up camera: {e}")

            # clean up threads
            for thread in threading.enumerate():
                if thread is not threading.current_thread():
                    thread.join(timeout=1)

            # force GC and exit
            gc.collect()
            logger.info("Exiting cleanly")

            # Log the end of the program
            logger.info("Program has ended")
            os._exit(0)  # Forcibly terminate the process


if __name__ == "__main__":
    # logger = setup_logging()  # Initialize logger before using it
    try:
        main()
    except Exception as e:
        logger.error(f"An unhandled exception occurred: {e}", exc_info=True)
    finally:
        logger.info("Exiting program")
        atexit.register(clean_exit)
        sys.exit(0)  # Now clean_exit() is guaranteed to run after this
