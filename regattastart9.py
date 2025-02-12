#!/home/pi/yolov5_env/bin/python
# after git pull, do: sudo cp regattastart9.py /usr/lib/cgi-bin/

import sys
# Manually add the virtual environment's site-packages directory to sys.path
venv_path = "/home/pi/yolov5_env/lib/python3.11/site-packages"
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

import cv2
# Use a deque to store the most recent frames in memory
from collections import deque
from datetime import datetime, timedelta
import datetime as dt
import errno
import json
import logging
import logging.config
import numpy as np # image recognition
import os
# from picamera2 import Transform
from libcamera import Transform
from picamera2.encoders import H264Encoder
from picamera2 import Picamera2, MappedArray
from picamera2.outputs import FileOutput
import RPi.GPIO as GPIO
import select
import subprocess

import threading
import time
import torch
import tempfile  # to check the php temp file
import warnings

warnings.filterwarnings(
    "ignore",
    message="`torch.cuda.amp.autocast(args...)` is deprecated",
    category=FutureWarning,
    module=".*ultralytics_yolov5_master.*"
)

picamera2_logger = logging.getLogger('picamera2')
picamera2_logger.setLevel(logging.ERROR)  # Change to ERROR to suppress more logs

# parameter data
signal_dur = 0.9  # 0.9 sec
log_path = '/var/www/html/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
listening = True  # Define the listening variable
recording_stopped = False  # Global variable


def setup_logging():
    # global logger  # Make logger variable global
    logging.config.fileConfig('/usr/lib/cgi-bin/logging.conf')
    logger = logging.getLogger('start')
    logger.info("Start logging regattastart9")
    return logger


# setup gpio()
ON = GPIO.LOW
OFF = GPIO.HIGH
signal = 26
lamp1 = 20
lamp2 = 21
try:  # GPIO
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(True)
    GPIO.setup(signal, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(lamp1, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(lamp2, GPIO.OUT, initial=GPIO.HIGH)
except Exception as e:
    print(f"Failed to setup GPIO: {e}")

# reset the contents of the status variable, used for flagging that
# video1-conversion is complete.
with open('/var/www/html/status.txt', 'w') as status_file:
    status_file.write("")


def trigger_relay(port):

    if port == 'Signal':
        GPIO.output(signal, ON)
        time.sleep(signal_dur)
        GPIO.output(signal, OFF)
        time.sleep(1 - signal_dur)
        logger.info(f"Trigger signal {signal_dur} sec, then wait for {(1 - signal_dur)} sec")
    elif port == 'Lamp1_on':
        GPIO.output(lamp1, ON)
        logger.info('Lamp1_on')
    elif port == 'Lamp2_on':
        GPIO.output(lamp2, ON)
        logger.info('Lamp2_on')
    elif port == 'Lamp1_off':
        GPIO.output(lamp1, OFF)
        logger.info('Lamp1_off')
    elif port == 'Lamp2_off':
        GPIO.output(lamp2, OFF)
        logger.info('Lamp2_off')


def remove_picture_files(directory, pattern):
    files = os.listdir(directory)
    for file in files:
        if file.endswith(pattern):
            file_path = os.path.join(directory, file)
            os.remove(file_path)


def remove_video_files(directory, pattern):
    files = os.listdir(directory)
    for file in files:
        if file.startswith(pattern):
            file_path = os.path.join(directory, file)
            os.remove(file_path)


def setup_picam2(resolution=(1920, 1080), fps=5):
    # def setup_picam2(resolution=(1640, 1232), fps=5):
    # def setup_picam2(resolution=(1280, 720), fps=5):c
    try:
        cam = Picamera2()
        config = cam.create_video_configuration(
            main={"size": resolution, "format": "RGB888"},
            controls={"FrameRate": fps}, 
            transform=Transform(hflip=True, vflip=True)  # Apply horizontal and vertical flips
        )
        logger.debug(f"Config before applying: {config}")
        cam.configure(config)
        # Apply 180-degree rotation by flipping horizontally and vertically
        # cam.set_controls({"Transform": {"hflip": True, "vflip": True}})
        cam.start()

        logger.info(f"Camera started with resolution {resolution} and FPS: {fps}.")
        return cam  # Ensure it returns a valid camera object
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        return None  # Avoid using an uninitialized camera


def restart_camera(cam, resolution=(1920, 1080), fps=5):
    time.sleep(2)  # Ensure the camera is fully released
    try:
        cam = Picamera2()
        logger.info("New Picamera2 instance created.")
        time.sleep(2)

        # List available sensor modes
        sensor_modes = cam.sensor_modes
        if not sensor_modes:
            logger.error("No sensor modes available. Camera may not be detected!")
            return None

        logger.debug(f"Available sensor modes: {sensor_modes}")

        # Find a sensor mode that best matches the requested resolution
        best_mode = min(sensor_modes, key=lambda m: abs(m["size"][0] - resolution[0]) + abs(m["size"][1] - resolution[1]))
        logger.debug(f"Using sensor mode: {best_mode}")

        config = cam.create_video_configuration(
            main={"size": best_mode["size"], "format": "RGB888"},
            controls={"FrameRate": fps},
            transform=Transform(hflip=True, vflip=True)
        )
        logger.debug(f"Config before applying: {config}")
        cam.configure(config)

        if cam is None:
            logger.error("Exit if camera object is None before starting.")
            return

        cam.start()
        logger.info(f"Camera restarted with resolution {best_mode['size']} and FPS: {fps}.")
        return cam  # Return new camera instance

    except Exception as e:
        logger.error(f"Failed to restart camera: {e}")
        return None  # Avoid using an uninitialized camera


def measure_frame_rate(cam, duration=5):
    frame_timestamps = []
    start_time = time.time()

    while time.time() - start_time < duration:
        try:
            frame = cam.capture_array()
            if frame is None:
                frame_timestamps.append(time.time())  # Record the timestamp

        except Exception as e:
            logger.error(f"Failed to capture frame: {e}")
            return  # Skips this iteration but keeps running the loop

    # Calculate frame intervals and average frame rate
    intervals = [t2 - t1 for t1, t2 in zip(frame_timestamps[:-1], frame_timestamps[1:])]
    avg_frame_rate = 1 / (sum(intervals) / len(intervals)) if intervals else 0

    return avg_frame_rate


def capture_picture(camera, photo_path, file_name):
    request = camera.capture_request()  # Capture a single request
    with MappedArray(request, "main") as m:
        frame = m.array  # Get the frame as a NumPy array
        # Rotate the frame by 180 degrees
        # rotated_frame = cv2.rotate(frame, cv2.ROTATE_180)
        # Save the frame to the file
        # cv2.imwrite(os.path.join(photo_path, file_name), rotated_frame)
        cv2.imwrite(os.path.join(photo_path, file_name), frame)
    request.release()
    logger.info("Captured picture = %s", file_name)


def start_sequence(camera, start_time_sec, num_starts, dur_between_starts, photo_path):
    for i in range(num_starts):
        logger.info(f"Start_sequence. Start of iteration {i+1}")
        iteration_start_time = start_time_sec + (i) * dur_between_starts * 60
        logger.debug(f"Start_sequence. Iteration {i+1}, iteration_start time: {iteration_start_time}")

        # Define time intervals for each relay trigger
        time_intervals = [
            (start_time_sec - 5 * 60, lambda: trigger_relay('Lamp1_on'), "5_min Lamp-1 On -- Up with Flag O"),
            (start_time_sec - 5 * 60 + 1, lambda: trigger_relay('Signal'), "5_min Warning signal"),
            (start_time_sec - 4 * 60 - 2, lambda: trigger_relay('Lamp2_on'), "4_min Lamp-2 On"),
            (start_time_sec - 4 * 60, lambda: trigger_relay('Signal'), "4_min Warning signal"),
            (start_time_sec - 1 * 60 - 2, lambda: trigger_relay('Lamp2_off'), "1_min Lamp-2 off -- Flag P down"),
            (start_time_sec - 1 * 60, lambda: trigger_relay('Signal'), "1_min  Warning signal"),
            (start_time_sec - 0 * 60 - 2, lambda: trigger_relay('Lamp1_off'), "Start Lamp1-off"),
            (start_time_sec - 0 * 60, lambda: trigger_relay('Signal'), "Start signal")
        ]

        last_triggered_events = {}
        time_now = dt.datetime.now()
        seconds_now = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

        # Adjust this value based on acceptable precision
        TIME_TOLERANCE = 1

        while seconds_now < iteration_start_time:
            for event_time, action, log_message in time_intervals:
                if abs(seconds_now - event_time) <= TIME_TOLERANCE and (event_time, log_message) not in last_triggered_events:
                    logger.info(f"Start_sequence: {log_message} at {event_time}")
                    if action:
                        action()
                        picture_name = f"{i + 1}a_start_{log_message[:5]}.jpg"
                        try:
                            capture_picture(camera, photo_path, picture_name)
                            logger.info(f"Start_sequence, Captured picture: {picture_name}")
                        except Exception as e:
                            logger.error(f"Failed to capture picture {picture_name}: {e}")
                            break
                    last_triggered_events[(event_time, log_message)] = True

            # Sleep until the next event time
            future_events = [t for t, _, _ in time_intervals if t > seconds_now]
            if future_events:
                next_event_time = min(future_events)
                sleep_duration = max(0.1, next_event_time - seconds_now)
                logger.debug(f"Sleeping for {sleep_duration} seconds until next event.")
                time.sleep(sleep_duration)

            # Update current time
            time_now = dt.datetime.now()
            seconds_now = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
        logger.info(f"End of iteration {i + 1}")


def apply_timestamp(request):
    timestamp = time.strftime("%Y-%m-%d %X")
    colour = (0, 255, 0)  # Green text
    font = cv2.FONT_HERSHEY_DUPLEX
    fontScale = 2
    thickness = 2

    try:
        with MappedArray(request, "main") as m:
            frame = m.array  # Get the frame
            if frame is None or frame.shape[0] == 0:
                logger.error("apply_timestamp: Frame is None or empty!")
                return

            height, width, _ = frame.shape
            # logger.debug(f"Frame shape: {frame.shape}")
            origin = (50, max(50, height - 100))  # Ensure text is within the frame

            cv2.putText(frame, timestamp, origin, font, fontScale, colour, thickness)

    except Exception as e:
        logger.error(f"Error in apply_timestamp: {e}", exc_info=True)


def start_video_recording(cam, video_path, file_name, bitrate=2000000):
    """
    Start video recording using H264Encoder and with timestamp.
    """
    output_file = os.path.join(video_path, file_name)
    # Configure the pre-callback for adding the timestamp
    cam.pre_callback = apply_timestamp
    encoder = H264Encoder(bitrate=bitrate)
    cam.start_recording(encoder, output_file)
    logger.info(f"Started recording video: {output_file} with bitrate {bitrate}")


def stop_video_recording(cam):
    cam.stop_recording()
    cam.stop()  # Fully stop the camera
    cam.close()  # Release camera resources
    logger.info("Recording stopped and camera fully released.")


def process_video(video_path, input_file, output_file, frame_rate=None):
    source = os.path.join(video_path, input_file)
    dest = os.path.join(video_path, output_file)
    if not os.path.exists(source) or os.path.getsize(source) <= 6000:
        logger.debug(f"Warning: {input_file} is empty or does not exist. Skipping conversion.")
        return
    command = ["ffmpeg", "-i", source, "-vcodec", "libx264", "-crf", "23", "-preset", "ultrafast"]
    if frame_rate:
        command.extend(["-vf", f"fps={frame_rate}"])
    command.append(dest)
    try:
        subprocess.run(command, check=True)
        logger.debug("Video processed: %s", output_file)
    except Exception as e:
        logger.error(f"Failed to process video: {e}")
        return


def stop_recording():
    global listening
    global recording_stopped
    recording_stopped = True
    listening = False  # Set flag to False to terminate the loop in listen_for_messages


def listen_for_messages(stop_event, timeout=0.1):
    global listening  # Use global flag
    logger.info("listen_for_messages from PHP script via a named pipe")
    pipe_path = '/var/www/html/tmp/stop_recording_pipe'
    logger.info(f"pipepath = {pipe_path}")
    while not stop_event.is_set():
        try:
            while listening:
                try:
                    if os.path.exists(pipe_path):
                        if os.path.isdir(pipe_path):
                            logger.error(f"{pipe_path} is a directory. Remove it or use another path.")
                            raise IsADirectoryError(f"{pipe_path} is a directory.")
                        else:
                            os.unlink(pipe_path)  # Remove existing file or pipe
                except OSError as e:
                    if e.errno != errno.ENOENT:  # Ignore if file doesn't exist
                        logger.error(f"os.unlink -> OS error: {e.errno}")
                        raise
                try:
                    os.mkfifo(pipe_path)  # Create a new named pipe
                except OSError as e:
                    logger.error(f"Failed to create pipe: {e}")
                    raise
                try:
                    with open(pipe_path, 'r') as fifo:
                        # Use select to wait for input with a timeout
                        rlist, _, _ = select.select([fifo], [], [], timeout)
                        if rlist:
                            message = fifo.readline().strip()
                            if message == 'stop_recording':
                                stop_recording()
                                logger.info("Message == stop_recording")
                                break  # Exit the loop when stop_recording received
                    logger.info("end of with open(pipe_path, r)")
                except OSError as e:
                    logger.error(f"Error while opening or reading pipe: {e}")
                    raise
            logger.info("Listening thread terminated")
            time.sleep(1)  # Add a small delay to prevent high CPU usage
        except Exception as e:
            logger.error(f"Error in listen_for_messages: {e}", exc_info=True)
            break
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


def finish_recording(cam, video_path, num_starts, video_end, start_time_sec):
    global recording_stopped
    confidence = 0.0  # Initial value
    class_name = ""  # Initial value
    fps = 10

    # Set duration of video1 recording
    max_duration = (video_end + (num_starts-1)*5) * 60
    logger.debug(f"Video1, max recording duration: {max_duration} seconds")

    if cam is None:
        logger.error("Camera object is None before restarting.")

    cam = restart_camera(cam, resolution=(1920, 1080), fps=fps)

    # Confirm cam is initialized
    if cam is None:
        logger.error("Camera restart failed, exiting.")
        return  # Prevents crashing if camera restart fails

    # Confirm resolution before proceeding
    frame = cam.capture_array()
    if frame is None:
        logger.error("First captured frame is None! Exiting video recording.")
        return

    frame_size = (frame.shape[1], frame.shape[0])
    logger.info(f"Camera frame size before recording: {frame_size}")

    if frame_size[0] != 1920 or frame_size[1] != 1080:
        logger.error(f"Resolution mismatch! Expected (1920, 1080) but got {frame_size}.")
    # if frame_size[0] != 1280 or frame_size[1] != 720:
    #    logger.error(f"Resolution mismatch! Expected (1280, 720) but got {frame_size}.")
    # if frame_size != (1640, 1232):
    #    logger.error(f"Resolution mismatch! Expected (1640, 1232) got {frame_size}.")

    fpsw = fps

    # Inference ##
    # Load the pre-trained YOLOv5 model (e.g., yolov5s)
    model = torch.hub.load('ultralytics/yolov5', 'yolov5s')
    model.classes = [8]  # Filter for 'boat' class (COCO ID for 'boat' is 8)

    # setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Use 'XVID' for .avi, or 'mp4v' for .mp4
    video_writer = cv2.VideoWriter(video_path + 'video1' + '.avi', fourcc, fpsw, frame_size) 
    if not video_writer.isOpened():
        logger.error(f"Failed to open video1.avi for writing. Selected frame_size: {frame_size}")
        exit(1)

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
    previous_capture_time = None  # Track previous frame timestamp

    while not recording_stopped:
        boat_in_current_frame = False  # Reset detection flag for this frame
        frame_counter += 1  # Increment the frame counter

        # Capture a frame from the camera
        try:
            frame = cam.capture_array()
            if frame is None:
                logger.error("Captured frame is None! Skipping write.")
                continue
            capture_timestamp = datetime.now() + timedelta(microseconds=frame_counter)
            logger.debug(f"  Capture timestamp: {capture_timestamp}")

            if previous_capture_time:
                time_diff = (capture_timestamp - previous_capture_time).total_seconds()
                logger.debug(f"QQQ  Time since last frame: {time_diff:.3f} sec")

            previous_capture_time = capture_timestamp  # Update for next iteration

            # Get dimensions of the full-resolution frame (1920x1080 in your case)
            frame_height, frame_width = frame.shape[:2]  # shape = (height, width, channels)

        except Exception as e:
            logger.error(f"Failed to capture frame: {e}")
            continue  # Skips this iteration but keeps running the loop

        if pre_detection_duration != 0:
            if capture_timestamp not in processed_timestamps:
                # Add frame to buffer and record its timestamp
                pre_detection_buffer.append((frame.copy(), capture_timestamp))
                processed_timestamps.add(capture_timestamp)  # Store timestamp in set
                logger.debug(f"Added frame to pre-detection buffer, length: {len(pre_detection_buffer)}")

                # Trim set to match buffer size
                if len(processed_timestamps) > pre_detection_buffer.maxlen:
                    processed_timestamps = set(list(processed_timestamps)[-pre_detection_buffer.maxlen:])
            else:
                logger.debug(f"Duplicate frame detected: Timestamp={capture_timestamp}. Skipping.")

            if frame_counter % 20 == 0:
                cleanup_processed_timestamps(processed_timestamps)

        # Set the dimensions for resizing inference frame (to 640x480)
        # inference_width, inference_height = 640, 480  # Since you resize before inference
        inference_width, inference_height = 640, 640  # Since you resize before inference

        # Compute scaling factors
        scale_x = frame_width / inference_width
        scale_y = frame_height / inference_height

        # Base scale text size and thickness
        base_fontScale = 0.8  # Default font size at 640x480
        base_thickness = 2  # Default thickness at 640x480
        scale_factor = (scale_x + scale_y) / 2  # Average scale factor
        fontScale = max(base_fontScale * scale_factor, 0.5)  # Prevent too small text
        thickness = max(int(base_thickness * scale_factor), 1)  # Prevent too thin lines
        font = cv2.FONT_HERSHEY_DUPLEX
        colour = (0, 255, 0)  # Green text

        # Perform inference only on every 3rd frame
        if frame_counter % 2 == 0:  # every frame
            crop_width, crop_height = 960, 720
            # crop_width, crop_height = 1280, 720
            # x_start = (frame_width - crop_width) // 2  # Center horizontally
            # x_start = (frame_width - crop_width)  # capture more on right side
            x_start = max(frame_width - crop_width, 0)  # capture more on right side
            y_start = (frame_height - crop_height) // 2  # Center vertically

            # Crop the frame
            cropped_frame = frame[y_start:y_start + crop_height, x_start:x_start + crop_width]
            # Resize cropped frame to 640x480 for inference
            resized_frame = cv2.resize(cropped_frame, (inference_width, inference_height))
            # Use resized_frame for YOLO detection instead of full frame
            results = model(resized_frame)

            detections = results.pandas().xyxy[0]  # Results as a DataFrame

            # Parse the detection results
            if len(detections) == 0:
                logger.debug("No detections in the current frame.")
            else:
                logger.debug("Detection made")
                for _, row in detections.iterrows():
                    class_name = row['name']
                    confidence = row['confidence']

                    if confidence > 0.4 and class_name == 'boat':
                        origin = (50, max(50, frame_height - 100)) # Position on frame
                        font = cv2.FONT_HERSHEY_DUPLEX
                        cv2.putText(frame, f"{capture_timestamp}", origin, font, fontScale, colour, thickness)
                        boat_in_current_frame = True
                        logger.info(f"Confidence {confidence:.2f}, capture_timestamp = {capture_timestamp}")
                        detected_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")  # timestamp (with microseconds)
                        logger.debug(f"Detected_timestamp={detected_timestamp}")

                        # x =
                        x1, y1 = int(row['xmin'] * scale_x), int(row['ymin'] * scale_y)
                        x2, y2 = int(row['xmax'] * scale_x), int(row['ymax'] * scale_y)

                        # Draw bounding box and label on the frame
                        cv2.rectangle(frame, (x1, y1), (x2, y2), colour, thickness)
                        cv2.putText(frame, f"{confidence:.2f}", (x1, y2 + 50),
                                    font, fontScale, colour, thickness)

                        if frame is not None:
                            video_writer.write(frame)
                            logger.debug("Detected frame written  !!!")
                        else:
                            logger.error("Captured frame is None! Skipping write.")
                            continue

                        if pre_detection_buffer:
                            # Remove the most recent frame
                            if len(pre_detection_buffer) >= 1:
                                pre_detection_buffer.pop()  # Removes the most recent frame

                            # Write pre-detection frames to video
                            while pre_detection_buffer:
                                # origin = (50, 700)  # Position on frame
                                frame, timestamp = pre_detection_buffer.popleft()
                                cv2.putText(frame, f"PRE {timestamp}", origin, font, fontScale, colour, thickness)
                                try:
                                    video_writer.write(frame)
                                    logger.debug(f"Pre-detection Timestamp={timestamp}")
                                except Exception as e:
                                    logger.error(f"Failed to write pre-detection frame: {e}")
                                    continue  # Skips writing this frame but keeps recording
                            pre_detection_buffer.clear()  # Clear the pre-detection buffer
                            logger.debug("Pre-detection buffer cleared after writing frames.")

        # Handle POST-detection frames
        skip_first_post_frame = False  # Initialize the flag
        if max_post_detection_duration != 0:
            colour = (0, 255, 0)  # Green text
            if boat_in_current_frame:
                number_of_post_frames = int(max_post_detection_duration * fpsw) # Reset countdown
                skip_first_post_frame = True  # Set flag to skip the first post-detection frame

            if boat_in_current_frame or number_of_post_frames > 0:
                if skip_first_post_frame:
                    skip_first_post_frame = False  # Skip this frame, process the next ones
                else:
                    try:
                        # origin = (500, 900)  # Position on frame
                        origin = (50, max(50, frame_height - 100))
                        cv2.putText(frame, f"POST {capture_timestamp}", origin, font, fontScale, colour, thickness)
                        video_writer.write(frame)
                        logger.debug(f"Post-detection Timestamp={capture_timestamp}")
                    except Exception as e:
                        logger.error(f"Failed to write post frame: {e}")

                if not boat_in_current_frame:
                    number_of_post_frames -= 1
                logger.debug(f"Number_of_post_frames Post-detection countdown: {number_of_post_frames}")

            if number_of_post_frames == 1:
                boat_in_current_frame = False

        # Check if recording should stop
        time_now = dt.datetime.now()
        seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
        elapsed_time = seconds_since_midnight - start_time_sec
        if elapsed_time >= max_duration:
            logger.debug(f"Maximum recording time reached, elapsed _time={elapsed_time}")
            recording_stopped = True

    if recording_stopped:
        logger.info('Video1 recording stopped')

    stop_video_recording(cam)
    if video_writer is not None:
        video_writer.release()  # Release the video writer
    logger.info("video_writer release, exited the finish_recording module.")


def stop_listen_thread():
    global listening
    listening = False
    # Log a message indicating that the listen_thread has been stopped
    logger.info("stop_listening thread  listening set to False")


def main():
    stop_event = threading.Event()
    global listening  # Declare listening as global
    # cam = setup_picam2(resolution=(1280, 720), fps=5)
    # cam = setup_picam2(resolution=(1640, 1232), fps=5)
    cam = setup_picam2(resolution=(1920, 1080), fps=10)
    if cam is None:
        logger.error("Camera setup failed, exiting.")
        exit()
    listening = True  # Initialize the global listening flag
    listen_thread = None  # Initialize listen_thread variable

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
            # A loop that waits until close to the 5-minute mark, and continuously 
            #  checks the condition without blocking the execution completely
            while True:
                now = dt.datetime.now()
                seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second

                if seconds_since_midnight > t5min_warning - 4:
                    logger.info("Start of outer loop iteration. seconds_since_midnight=%d", seconds_since_midnight)
                    logger.info("start_time_sec=%d", start_time_sec)

                    if num_starts == 1 or num_starts == 2:
                        logger.info("Start of video0 recording")
                        start_video_recording(cam, video_path, "video0.avi", bitrate=2000000)
                        logger.info("Inner loop, entering the start sequence block.")
                        start_sequence(cam, start_time_sec, num_starts, dur_between_starts, photo_path)

                        if num_starts == 2:
                            start_time_sec = start_time_sec + (dur_between_starts * 60)

                        logger.info("Wait 2 minutes then stop video0 recording")
                        t0 = dt.datetime.now()
                        # logger.debug(f"t0 = {t0}, dt.datetime.now(): {dt.datetime.now()}")
                        # logger.debug("(dt.datetime.now() - t0).seconds: %d", (dt.datetime.now() - t0).seconds)
                        while ((dt.datetime.now() - t0).seconds < 119):
                            now = dt.datetime.now()
                            time.sleep(0.9)  # Small delay to reduce CPU usage
                        stop_video_recording(cam)
                        # try:
                        #    video_writer.release()
                        # except Exception as e:
                        #    logger.error(f"Error closing video file: {e}")

                        logger.debug("Stopping video0 recording")
                        process_video(video_path, "video0.avi", "video0.mp4", frame_rate=30)
                        logger.debug("Video0 converted to mp4")

                    break  # Exit the loop after the if condition is met
                time.sleep(0.1)  # Introduce a delay of 2 seconds

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON: %", str(e))
        GPIO.cleanup()
        sys.exit(1)
    finally:
        logger.info("Finally section, before listen_for_message")
        # Start a thread for listening for messages with a timeout
        listen_thread = threading.Thread(target=listen_for_messages, args=(stop_event,))
        listen_thread.start()

        logger.info("Finally section, before 'Finish recording'. start_time=%s video_end=%s", start_time, video_end)
        time.sleep(2)
        finish_recording(cam, video_path, num_starts, video_end, start_time_sec)
        logger.info("After finished_recording")
        try:
            stop_event.set()  # Signal the listening thread to stop
            listen_thread.join(timeout=10)
            if listen_thread.is_alive():
                logger.info("listen_thread is still alive after timeout")
            else:
                logger.info("listen_thread finished")

            time.sleep(2)
            process_video(video_path, "video1.avi", "video1.mp4")

            # After video conversion is complete
            with open('/var/www/html/status.txt', 'w') as status_file:
                status_file.write('complete')
            logger.info("Finished with finish_recording and recording converted to mp4")

        except Exception as e:
            logger.error(f"An error occurred in the 'finally' section: {e}", exc_info=True)

        finally:
            try:
                stop_video_recording(cam)  # Ensure the camera recording is stopped
            except Exception as e:
                logger.error(f"Error while cleaning up camera: {e}")

            GPIO.cleanup()
            logger.info("After GPIO.cleanup, end of program")

            # Log the end of the program
            logger.info("Program has ended")
            os._exit(0)  # Forcibly terminate the process


if __name__ == "__main__":
    logger = setup_logging()  # Initialize logger before using it
    try:
        main()
    except Exception as e:
        logger.error(f"An unhandled exception occurred: {e}", exc_info=True)
    finally:
        logger.info("Exiting program")

