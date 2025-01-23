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
from datetime import datetime
import datetime as dt
import errno
import json
import logging
import logging.config
import numpy as np # image recognition
import os
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


def setup_picam2(resolution=(640, 480), fps=5):
    """
    Configures the camera using picamera2.
    Sets the desired resolution and FPS for video recordings.
    """
    picam2 = Picamera2()

    # Configure preview settings
    # Apply 180-degree rotation (horizontal and vertical flip)
    preview_config = picam2.create_preview_configuration(
        main={"size": resolution, "format": "RGB888"},
        controls={"FrameRate": fps},
        transform=Transform(hflip=True, vflip=True)  # Apply horizontal and vertical flips
    )
    picam2.configure(preview_config)

    picam2.start()  # Start the camera
    logger.info(f"setup_camera with resolution {resolution} and {fps} FPS.")
    return picam2


def annotate_frame(frame, text):  # Not used
    org = (15, 60)  # x = 15 from left, y = 60 from top
    fontFace = cv2.FONT_HERSHEY_DUPLEX
    fontScale = 0.7
    color = (0, 255, 0)  # (B, G, R)
    thickness = 1
    lineType = cv2.LINE_AA

    # Draw the timestamp text
    cv2.putText(frame, text, org, fontFace, fontScale, color, thickness, lineType)


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
        # seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
        seconds_now = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

        while seconds_now < iteration_start_time:
            for event_time, action, log_message in time_intervals:
                if seconds_now >= event_time and (event_time, log_message) not in last_triggered_events:
                    logger.info(f"Start_sequence: {log_message} at {event_time}")
                    if action:
                        action()
                        # logger.debug(f"log_message[:5] = {log_message[:5]}")
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


def apply_timestamp(request):  # Function for adding the timestamp
    timestamp = time.strftime("%Y-%m-%d %X")  # Current timestamp
    colour = (0, 255, 0)  # Green text
    origin = (15, 50)  # Position on frame
    # font = cv2.FONT_HERSHEY_SIMPLEX
    font = cv2.FONT_HERSHEY_DUPLEX
    fontScale = 1
    thickness = 1

    # Overlay the timestamp on the frame
    with MappedArray(request, "main") as m:
        cv2.putText(m.array, timestamp, origin, font, fontScale, colour, thickness)


def start_video_recording_new(cam, video_path, file_name, bitrate=2000000):
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
    logger.info("Recording stopped.")


def process_video(video_path, input_file, output_file, frame_rate=None):
    source = os.path.join(video_path, input_file)
    dest = os.path.join(video_path, output_file)
    if not os.path.exists(source) or os.path.getsize(source) <= 6000:
        logger.debug(f"Warning: {input_file} is empty or does not exist. Skipping conversion.")
        return

    command = ["ffmpeg", "-i", source, "-vcodec", "libx264", "-crf", "23", "-preset", "fast"]

    if frame_rate:
        command.extend(["-vf", f"fps={frame_rate}"])

    command.append(dest)
    subprocess.run(command, check=True)
    logger.debug("Video processed: %s", output_file)


def annotate_video_cv(frame, start_time_sec):  # Not used
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


def finish_recording(cam, video_path, num_starts, video_end, start_time_sec):
    global recording_stopped
    confidence = 0.0  # Default value
    class_name = ""

    if not cam.started:  # ensure camera being started.
        logger.error("Camera is not started. Starting it now...")
        cam.start()

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
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Use 'XVID' for .avi, or 'mp4v' for .mp4
    video_writer = cv2.VideoWriter(video_path + 'video1' + '.avi', fourcc, fpsw, frame_size)

    if not video_writer.isOpened():
        logger.error("VideoWriter failed to initialize.")
        return

    # Pre-detection buffer (5 seconds)
    pre_detection_buffer = deque(maxlen=fpsw * 5)  # Stores last 5 seconds of frames
    post_detection_frames = 50  # Frames to record after detection
    boat_in_current_frame = False

    # Duration of video1 recording
    max_duration = video_end * 60 + (num_starts-1)*5
    logger.debug(f"Video1, max recording duration: {max_duration} seconds")

    while not recording_stopped:
        try:
            frame = cam.capture_array()
        except Exception as e:
            logger.error(f"Failed to capture frame: {e}")
            break  # Exit the loop if the camera fails

        pre_detection_buffer.append(frame)  # Add the frame to pre-detection buffer
        boat_in_current_frame = False  # Reset detection flag for this frame

        # Perform inference using YOLOv5
        try:
            results = model(frame)
        except Exception as e:
            logger.error(f"YOLOv5 inference failed: {e}")
            break  # Exit the loop or handle it appropriately

        detections = results.pandas().xyxy[0]  # Results as a DataFrame
        logger.debug(f"Total detections: {len(detections)}")

        # Parse the detection results
        if len(detections) == 0:
            logger.debug("No detections in the current frame.")

        for _, row in detections.iterrows():
            class_name = row['name']
            confidence = row['confidence']
            x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])

            if confidence > 0.3 and class_name == 'boat':  # Check if detection is a boat
                boat_in_current_frame = True
                logger.debug(f"Boat detected: {class_name} ({confidence:.2f}) at [{x1}, {y1}, {x2}, {y2}]")

                # Draw bounding box and label on the frame
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{class_name} {confidence:.2f}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                # Write pre-detection frames to video
                while pre_detection_buffer:
                    video_writer.write(pre_detection_buffer.popleft())
                    logger.debug("Flushing pre-detection buffer.")

        # Write frames if a boat is detected or during post-detection countdown
        if boat_in_current_frame or post_detection_frames > 0:
            video_writer.write(frame)
            logger.debug("Frame written (boat detected or post-detection).")

            if boat_in_current_frame:
                post_detection_frames = 50  # Reset post-detection countdown
            else:
                post_detection_frames -= 1
                logger.debug(f"Post-detection frames remaining: {post_detection_frames}")

        # Check if recording should stop
        time_now = dt.datetime.now()
        seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
        elapsed_time = seconds_since_midnight - start_time_sec
        if elapsed_time >= max_duration:
            logger.debug(f"Maximum recording time reached, elapsed _time={elapsed_time}")
            recording_stopped = True
            break

    if recording_stopped is True:
        logger.info('Video1 recording stopped')

    stop_video_recording(cam)
    video_writer.release()  # Release the video writer
    logger.info("video_writer release, exited the finish_recording module.")


def stop_listen_thread():
    global listening
    listening = False
    # Log a message indicating that the listen_thread has been stopped
    logger.info("462: stop_listening thread  listening set to False")


def main():
    stop_event = threading.Event()
    global listening  # Declare listening as global
    logger = setup_logging()  # Initialize the logger
    cam = setup_picam2(resolution=(640, 480), fps=5)
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
                    logger.info("Start of outer loop iteration. seconds_since_midnight=%d", seconds_since_midnight)
                    logger.info("start_time_sec=%d", start_time_sec)
                    if num_starts == 1 or num_starts == 2:
                        logger.info("Start of video0 recording")
                        start_video_recording_new(cam, video_path, "video0.avi", bitrate=2000000)
                        logger.info("Inner loop, entering the start sequence block.")
                        start_sequence(cam, start_time_sec, num_starts, dur_between_starts, photo_path)

                        if num_starts == 2:
                            start_time_sec = start_time_sec + (dur_between_starts * 60)

                        logger.info("Wait 2 minutes then stop video0 recording")
                        t0 = dt.datetime.now()
                        # logger.debug(f"t0 = {t0}, dt.datetime.now(): {dt.datetime.now()}")
                        # logger.debug("(dt.datetime.now() - t0).seconds: %d", (dt.datetime.now() - t0).seconds)
                        while ((dt.datetime.now() - t0).seconds < 119):
                            # logger.debug("in while loop")
                            now = dt.datetime.now()
                            # logger.debug(f"(dt.datetime.now() - t0).seconds: {(dt.datetime.now() - t0).seconds}")
                            time.sleep(0.9)  # Small delay to reduce CPU usage
                        stop_video_recording(cam)
                        logger.debug("Stopping video0 recording after after annotate and write frames")
                        process_video(video_path, "video0.avi", "video0.mp4", frame_rate=20)
                        logger.debug("Video0 converted to mp4")

                    # Exit the loop after the if condition is met
                    break

                time.sleep(2)  # Introduce a delay of 2 seconds

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
                stop_video_recording(cam) # Ensure the camera recording is stopped
                cam.close()           # Release the camera resources
            except Exception as e:
                logger.error(f"Error while cleaning up camera: {e}")

            GPIO.cleanup()
            logger.info("After GPIO.cleanup, end of program")

            # Log the end of the program
            logger.info("Program has ended")
            os._exit(0)  # Forcibly terminate the process


if __name__ == "__main__":
    # logging.basicConfig(level=logging.WARNING)  # Set log level to WARNING
    try:
        main()
    except Exception as e:
        logger.error(f"An unhandled exception occurred: {e}", exc_info=True)
    finally:
        logger.info("Exiting program")
        # sys.exit(0)  # Exit the program cleanly
