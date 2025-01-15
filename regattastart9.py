#!/home/pi/yolov5_env/bin/python
# after git pull, do: sudo cp regattastart9.py /usr/lib/cgi-bin/
import os
import errno
import select
import sys

# Manually add the virtual environment's site-packages directory to sys.path
venv_path = "/home/pi/yolov5_env/lib/python3.11/site-packages"
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

import torch

# sys.path.append('/home/pi/yolov5_env/lib/python3.11/site-packages')
import threading
import time
import cv2
from datetime import datetime
import datetime as dt
import logging
import logging.config
import json
import tempfile  # to check the php temp file

# Use a deque to store the most recent frames in memory
from collections import deque

# camera
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

# image recognition
import numpy as np
import subprocess
import RPi.GPIO as GPIO

# parameter data
signal_dur = 0.9  # 0.9 sec
log_path = '/var/www/html/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
listening = True  # Define the listening variable
recording_stopped = False  # Global variable

# setup gpio()
ON = GPIO.LOW
OFF = GPIO.HIGH
signal = 26
lamp1 = 20
lamp2 = 21
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(True)
GPIO.setup(signal, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(lamp1, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(lamp2, GPIO.OUT, initial=GPIO.HIGH)

# reset the contents of the status variable, used for flagging that
# video1-conversion is complete.
with open('/var/www/html/status.txt', 'w') as status_file:
    status_file.write("")


def setup_logging():
    global logger  # Make logger variable global
    logging.config.fileConfig('/usr/lib/cgi-bin/logging.conf')
    logger = logging.getLogger('Start')
    logger.info("Start logging regattastart9")
    return logger


def trigger_relay(port):

    if port == 'Signal':
        GPIO.output(signal, ON)
        time.sleep(signal_dur)
        GPIO.output(signal, OFF)
        time.sleep(1 - signal_dur)
        logger.info("Trigger signal %s sec, then wait for 1 - %s sec", signal_dur, signal_dur)
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


def setup_camera(resolution=(640, 480), fps=5):
    """
    Configures the camera using picamera2.
    Sets the desired resolution and FPS for video recordings.
    """
    picam2 = Picamera2()

    # Configure preview settings
    preview_config = picam2.create_preview_configuration(
        main={"size": resolution, "format": "RGB888"},
        controls={"FrameRate": fps}
    )
    picam2.configure(preview_config)

    picam2.start()  # Start the camera

    # actual_resolution = preview_config.main.size
    logger.info(f"Camera initialized with resolution {resolution} and {fps} FPS.")

    return picam2


def annotate_and_write_frames(cam: Picamera2, video_writer):
    """
    Captures frames from the picamera2, annotates each frame with a timestamp
    and writes them to a video file using the provided video writer.
    """
    org = (15, 60)  # x = 15 from left, y = 60 from top
    fontFace = cv2.FONT_HERSHEY_DUPLEX
    fontScale = 0.7
    # color = (0, 0, 0)  # (B, G, R)
    thickness = 1
    lineType = cv2.LINE_AA

    try:
        while True:
            frame = cam.capture_array()  # Capture frame using picamera2
            frame = np.rot90(frame, 2)  # Rotate the frame by 180 degrees

            # Ensure the image is in the correct format for OpenCV
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Draw a rectangle on the image (example processing)
            # top_left = (org[0], org[1] - text_height - 5)
            # bottom_right = (org[0] + text_width + 10, org[1] + 5)
            height, width, _ = frame.shape
            top_left = (int(width * 0.25), int(height * 0.25))
            bottom_right = (int(width * 0.75), int(height * 0.75))
            color = (0, 255, 0)  # Green in BGR
            # thickness = 2

            # Annotate the frame with the current date and time
            current_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Draw background rectangle for the timestamp
            cv2.rectangle(frame, top_left, bottom_right, (255, 255, 255), cv2.FILLED)

            # Calculate text size and background rectangle
            (text_width, text_height), _ = cv2.getTextSize(current_time, fontFace, fontScale, thickness)

            cv2.rectangle(frame, top_left, bottom_right, color, thickness)

            # Draw the timestamp text
            cv2.putText(frame, current_time, org, fontFace, fontScale, color, thickness, lineType)

            # Write the annotated frame to the video file
            video_writer.write(frame)

    except Exception as e:
        logger.error(f"Error while capturing or writing frames: {e}")


def capture_picture(cam: Picamera2, photo_path: str, file_name: str):
    logger.info("Attempting to capture picture...")
    try:
        frame = cam.capture_array()
        # Perform operations on the frame...
        frame = np.copy(frame)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convert to BGR
        frame = np.rot90(frame, 2)  # Rotate the frame by 180 degrees

        logger.debug(f"Frame shape: {frame.shape}, dtype: {frame.dtype}")

        # Annotate the frame with the current date and time
        current_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        org = (15, 60)  # Position for text on the image
        font_scale = 0.7
        color = (0, 0, 0)  # Text color (B, G, R)
        thickness = 1

        # Put the timestamp on the image
        font = cv2.FONT_HERSHEY_DUPLEX
        text_size = cv2.getTextSize(current_time, font, font_scale, thickness)[0]
        text_x = int(org[0])
        text_y = int(org[1] - text_size[1])

        logger.debug(f"Drawing rectangle at: ({text_x}, {text_y}) to ({text_x + text_size[0]}, {text_y + text_size[1]})")

        # Draw the background rectangle for the text
        frame = np.ascontiguousarray(frame)  # Ensure array compatibility
        cv2.rectangle(frame, (text_x, text_y), (text_x + text_size[0], text_y + text_size[1]), (255, 255, 255), -1)

        # Draw the text
        cv2.putText(frame, current_time, org, font, font_scale, color, thickness, cv2.LINE_AA)

        # Save the image
        image_path = os.path.join(photo_path, file_name)
        cv2.imwrite(image_path, frame)

        # Sleep to stabilize the camera
        # time.sleep(0.3)  # 0.3 seconds

    except Exception as e:
        logger.error(f"Error capturing picture: {e}")
        return

    logger.info(f"Successfully captured image picture: {file_name}")


def start_video_recording(cam, video_path, file_name):
    fpsw = 20  # Frames per second for video writing
    width = cam.preview_configuration.main.size[0]  # Get the width from preview configuration
    height = cam.preview_configuration.main.size[1]  # Get the height from preview configuration
    frame_size = (width, height)
    logger.info(f"Camera frame size: {frame_size}")

    # Initialize the video writer (XVID codec or similar)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # XVID codec (you can change this if you prefer another codec)
    video_writer = cv2.VideoWriter(os.path.join(video_path, file_name), fourcc, fpsw, frame_size)

    if not video_writer.isOpened():
        logger.error("VideoWriter failed during recording.")
        return None  # Return None if the VideoWriter failed to open

    logger.info("Started video recording of %s", file_name)
    return video_writer


def stop_video_recording(video_writer):
    video_writer.release()
    logger.info("Stopped video recording")


def video_recording(cam, video_path, file_name, duration=None):
    fpsw = 20  # number of frames written per second
    width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (width, height)
    logger.info(f"Camera frame size: {frame_size}")
    logger.info(f"Recording duration: {duration} seconds")

    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # H.264 codec with MP4 container
    video_writer = cv2.VideoWriter(os.path.join(video_path, file_name + '.avi'), fourcc, fpsw, frame_size)

    logger.info("Started video recording of %s", file_name)
    start_time = time.time()

    while True:
        ret, frame = cam.read()
        if not ret:
            logger.error("Failed to capture frame")
            break

        # Rotate the frame by 180 degrees
        frame = cv2.rotate(frame, cv2.ROTATE_180)
        video_writer.write(frame)

        # Log elapsed time
        elapsed_time = time.time() - start_time
        logger.debug(f"Elapsed time: {elapsed_time:.2f} seconds")

        if duration and elapsed_time > duration:
            logger.info("Recording duration exceeded. Stopping recording.")
            break

    video_writer.release()
    cv2.destroyAllWindows()
    logger.info("Stopped video recording of %s ", file_name)


def annotate_video_duration(camera, start_time_sec):
    time_now = dt.datetime.now()
    seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
    elapsed_time = seconds_since_midnight - start_time_sec  # elapsed since last star until now)
    camera.annotate_text = f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Seconds since last start: {elapsed_time}"


def convert_video_to_mp4(video_path, source_file, destination_file):
    convert_video_str = "MP4Box -add {} -fps 20 -new {}".format(
        os.path.join(video_path, source_file),
        os.path.join(video_path, destination_file)
    )
    subprocess.run(convert_video_str, shell=True)
    logger.info("Video recording %s converted ", destination_file)


def re_encode_video(video_path, source_file, destination_file):
    re_encode_video_str = "ffmpeg -loglevel error -i {} -vf fps=20 -vcodec libx264 -f mp4 {}".format(
        os.path.join(video_path, source_file),
        os.path.join(video_path, destination_file)
    )
    subprocess.run(re_encode_video_str, shell=True)
    logger.info("Video %s re-encoded ", destination_file)


def start_sequence(camera, start_time_sec, num_starts, dur_between_starts, photo_path):
    for i in range(num_starts):
        logger.info(f"Start_sequence. Start of iteration {i}")
        # Adjust the start_time_sec for the second iteration
        # if i == 1:
        #    start_time_sec += dur_between_starts * 60  # Add 5 or 10 minutes for the second iteration
        #    logger.info(f"Start_sequence, Next start_time_sec: {start_time_sec}")

        iteration_start_time = start_time_sec + i * dur_between_starts * 60
        logger.info(f"Start_sequence. Iteration {i + 1}, start time: {iteration_start_time}")

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
        # seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
        seconds_now = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

        '''
        if seconds_since_midnight >= start_time_sec:
            break  # Exit the loop if the condition is met

        for seconds, action, log_message in time_intervals:
            # camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            time_now = dt.datetime.now()
            seconds_now = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

            # Check if the event should be triggered based on the current time
            if seconds_now == seconds:
                # Check if the event has already been triggered for this time interval
                if (log_message) not in last_triggered_events:
                    logger.info(f"Start_sequence, seconds: {seconds}, log_message= {log_message}")
                    logger.info(f"Start_sequence, Triggering event at seconds_now: {seconds_now}")
                    if action:
                        action()
                        picture_name = f"{i + 1}a_start_{log_message[:5]}.jpg"
                        capture_picture(camera, photo_path, picture_name)
                        logger.info(f"Start_sequence, seconds={seconds}  log_message: {log_message}")
                    # Record that the event has been triggered for this time interval
                    last_triggered_events[(seconds, log_message)] = True
        logger.info(f"Start_sequence, End of iteration: {i}")
        '''
        while seconds_now < iteration_start_time:
            for event_time, action, log_message in time_intervals:
                if seconds_now >= event_time and (event_time, log_message) not in last_triggered_events:
                    logger.info(f"Start_sequence: {log_message} at {event_time}")
                    if action:
                        action()
                        picture_name = f"{i + 1}a_start_{log_message[:5]}.jpg"
                        capture_picture(camera, photo_path, picture_name)
                        # Mark the event as triggered
                    last_triggered_events[(event_time, log_message)] = True
                    break  # Break out of the loop to avoid reprocessing this event

            # Sleep until the next event time
            future_events = [t for t, _, _ in time_intervals if t > seconds_now]
            if future_events:
                next_event_time = min(future_events)
                sleep_duration = max(0, next_event_time - seconds_now)
                logger.debug(f"Sleeping for {sleep_duration} seconds until next event.")
                time.sleep(sleep_duration)

            # Update current time
            time_now = dt.datetime.now()
            seconds_now = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
        logger.info(f"End of iteration {i + 1}")


def cv_annotate_video(frame, start_time_sec):
    time_now = dt.datetime.now()
    seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
    # elapsed since last start until now)
    elapsed_time = seconds_since_midnight - start_time_sec
    label = str(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + " Seconds since last start: " + str(elapsed_time)
    org = (15, 60)  # x = 15 from left, y = 60 from top) 
    fontFace = cv2.FONT_HERSHEY_DUPLEX
    fontScale = 0.7
    color = (0, 0, 0)  # (B, G, R)
    thickness = 1
    lineType = cv2.LINE_AA
    # Get text size
    (text_width, text_height), _ = cv2.getTextSize(label, fontFace, fontScale, thickness)
    # Define background rectangle coordinates
    top_left = (org[0], org[1] - text_height) 
    bottom_right = (int(org[0] + text_width), int(org[1] + (text_height/2)))

    # Draw filled rectangle as background for the text
    cv2.rectangle(frame, top_left, bottom_right, (255, 255, 255), cv2.FILLED)

    # Draw text on top of the background

    cv2.putText(frame, label, org, fontFace, fontScale, color, thickness, lineType)


def stop_recording():
    global listening
    global recording_stopped
    recording_stopped = True
    listening = False  # Set flag to False to terminate the loop in listen_for_messages


def listen_for_messages(timeout=0.1):
    global listening  # Use global flag
    logger.info("listen_for_messages from PHP script via a named pipe")
    pipe_path = '/var/www/html/tmp/stop_recording_pipe'
    logger.info(f"pipepath = {pipe_path}")

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


def finish_recording(cam, video_path, num_starts, video_end, start_time):
    # Open a video capture object (replace 'your_video_file.mp4' with the 
    # actual video file or use 0 for webcam) 
    # cam = cv2.VideoCapture(os.path.join(video_path, "finish21-6.mp4"))
    global recording_stopped

    # Load the pre-trained YOLOv5 model (e.g., yolov5s)
    model = torch.hub.load('ultralytics/yolov5', 'yolov5s')
    model.classes = [8]  # Filter for 'boat' class (COCO ID for 'boat' is 8)

    # Setup parameters
    fpsw = 20  # number of frames written per second
    width = cam.preview_configuration.main.size[0]  # Get the width from preview configuration
    height = cam.preview_configuration.main.size[1]  # Get the height from preview configuration
    frame_size = (width, height)
    logger.info(f"Camera frame size: {frame_size}")

    # setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # H.264 codec with MP4 container
    video_writer = cv2.VideoWriter(video_path + 'video1' + '.avi', fourcc, fpsw, frame_size)

    if not video_writer.isOpened():
        logger.error("VideoWriter failed to initialize.")
        return

    # Pre-detection buffer (5 seconds)
    pre_detection_buffer = deque(maxlen=fpsw * 5)  # Stores last 5 seconds of frames
    post_detection_frames = 50  # Frames to record after detection
    boat_in_current_frame = False

    start_time = time.time()  # Record the start time of the recording
    max_duration = 60 * (video_end + 5 * (num_starts - 1))
    logger.info(f"Maximum recording duration: {max_duration} seconds")

    while not recording_stopped:
        frame = cam.capture_array()  # Capture frame as numpy array
        frame = cv2.flip(frame, cv2.ROTATE_180)  # camera is upside down"
        pre_detection_buffer.append(frame)  # Add the frame to pre-detection buffer

        # Perform inference using YOLOv5
        results = model(frame)
        detections = results.pandas().xyxy[0]  # Results as a DataFrame

        # Process detections
        for _, row in detections.iterrows():
            class_name = row['name']
            confidence = row['confidence']
            x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])

        if confidence > 0.2 and class_name == 'boat':  # Check if detection is a boat
            boat_in_current_frame = True
            logger.info("Boat detected, saving pre-detection frames.")

            # Write pre-detection frames to video
            while pre_detection_buffer:
                video_writer.write(pre_detection_buffer.popleft())

            # Draw bounding boxes and save post-detection frames
            for _ in range(post_detection_frames):
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{class_name} {confidence:.2f}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                video_writer.write(frame)

        # Handle post-detection frame countdown
        if boat_in_current_frame:  # boat was in frame previously
            post_detection_frames -= 1
            if post_detection_frames <= 0:
                boat_in_current_frame = False
                post_detection_frames = 50  # Reset for the next detection

        # Check if recording should stop
        elapsed_time = time.time() - start_time
        if elapsed_time >= max_duration:
            logger.info("Maximum recording time reached.")
            recording_stopped = True
            break

        if recording_stopped is True:
            logger.info('Video1 recording stopped')
            break

    cam.release()  # Don't forget to release the camera resources when done
    video_writer.release()  # Release the video writer
    logger.info("cam.release and video_writer release, exited the finish_recording module.")


def stop_listen_thread():
    global listening
    listening = False
    # Log a message indicating that the listen_thread has been stopped
    logger.info("462: stop_listening thread  listening set to False")


def main():
    stop_event = threading.Event()
    global listening  # Declare listening as global
    logger = setup_logging()  # Initialize the logger
    cam = setup_camera()
    if cam is None:
        logger.error("Camera setup failed, exiting.")
        exit()
    listening = True  # Initialize the global listening flag
    listen_thread = None  # Initialize listen_thread variable

    # Check if a command-line argument (JSON data) is provided
    if len(sys.argv) < 2:
        print("No JSON data provided as a command-line argument.")
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

        # Convert to datetime object
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        # Extract hour and minute
        start_hour = start_time.hour
        start_minute = start_time.minute
        # Calculate start_time_sec
        start_time_sec = 60 * start_minute + 3600 * start_hour
        # time when the start-machine should begin to execute.
        t5min_warning = start_time_sec - 5 * 60
        wd = dt.datetime.today().strftime("%A")

        remove_video_files(photo_path, "video")  # clean up
        remove_picture_files(photo_path, ".jpg")  # clean up
        logger.info("Weekday=%s, Start_time=%s, video_end=%s, num_starts=%s", week_day, start_time.strftime("%H:%M"), video_end, num_starts)

        if wd == week_day:
            # A loop that waits until close to the 5-minute mark, a loop
            # that continuously checks the condition without blocking
            # the execution completely
            while True:
                now = dt.datetime.now()
                seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
                if seconds_since_midnight > t5min_warning - 2:
                    logger.info("Start of outer loop iteration. seconds_since_midnight=%s", seconds_since_midnight)
                    if num_starts == 1 or num_starts == 2:
                        logger.info("Start of video recording")
                        video_writer = start_video_recording(cam, video_path, "video0.avi")
                        logger.info("Inner loop, entering the start sequence block.")
                        start_sequence(cam, start_time_sec, num_starts, dur_between_starts, photo_path)
                        if num_starts == 2:
                            start_time_sec = start_time_sec + (dur_between_starts * 60)
                        logger.info("Wait 2 minutes then stop video0 recording")
                        t0 = dt.datetime.now()
                        logger.info("start_time_sec= %s, t0= %s", start_time_sec, t0)  # test
                        logger.info(f"(dt.datetime.now() - t0).seconds: {(dt.datetime.now() - t0).seconds}")
                        while ((dt.datetime.now() - t0).seconds < 119):
                            now = dt.datetime.now()
                            now_strf = time.strftime("%H:%M:%S", now)
                            logger.info(f"now {now} strftime: {now_strf} ")
                            seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
                            logger.info(f"seconds_since_midnight {seconds_since_midnight}")
                            logger.info(f"dt.datetime.now(): {dt.datetime.now()} t0: {t0}")  # test
                            annotate_and_write_frames(cam, video_writer)
                        logger.info("after annotate and write text")
                        stop_video_recording(video_writer)
                        convert_video_to_mp4(video_path, "video0.avi", "video0.mp4")
                        logger.info("Video0 recording stopped and converted to mp4")
                    # Exit the loop after the if condition is met
                    break

        time.sleep(2)  # Introduce a delay of 2 seconds

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON: %", str(e))
        sys.exit(1)
    finally:
        logger.info("Finally section, before listen_for_message")
        # Start a thread for listening for messages with a timeout
        listen_thread = threading.Thread(target=listen_for_messages)
        listen_thread.start()

        logger.info("Finally section, before 'Finish recording'. start_time=%s video_end=%s", start_time, video_end)
        time.sleep(2)
        finish_recording(cam, video_path, num_starts, video_end, start_time)

        # Signal the listening thread to stop
        stop_event.set()
        listen_thread.join(timeout=10)
        if listen_thread.is_alive():
            logger.info("listen_thread is still alive after timeout")
        else:
            logger.info("listen_thread finished")

        time.sleep(2)
        re_encode_video(video_path, "video1.avi", "video1.mp4")

        # After video conversion is complete
        with open('/var/www/html/status.txt', 'w') as status_file:
            status_file.write('complete')
        logger.info("Finished with finish_recording and recording converted to mp4")

        cam.release()  # Release camera resources

        GPIO.cleanup()
        logger.info("After GPIO.cleanup, end of program")


if __name__ == "__main__":
    # logging.basicConfig(level=logging.WARNING)  # Set log level to WARNING
    main()
