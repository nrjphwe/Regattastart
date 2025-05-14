#!/home/pi/yolov5_env/bin/python
# after git pull, do: sudo cp regattastart9.py /usr/lib/cgi-bin/
from common_module import (
    setup_camera,
    capture_picture,
    remove_picture_files,
    remove_video_files,
    start_video_recording,
    start_sequence,
    stop_video_recording,
    logger,
    text_rectangle,
    setup_gpio,
    trigger_relay,
    process_video,
)
import sys
print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("sys.path:", sys.path)

import os
# The os.chdir('/home/pi/yolov5') and manual addition of venv_path to "
# sys.path in your script may be unnecessary if the virtual environment "
# is correctly set up."
# os.chdir('/home/pi/yolov5')
"""
# Manually add the virtual environment's site-packages directory to sys.path
venv_path = "/home/pi/yolov5_env/lib/python3.11/site-packages"
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)
"""

# Use a deque to store the most recent frames in memory
from collections import deque
from datetime import datetime, timedelta
import datetime as dt
import json
# import numpy as np # image recognition
from libcamera import Transform

from picamera2 import Picamera2
import select
import threading
import time
import cv2
import torch
import warnings
import RPi.GPIO as GPIO  # Import GPIO library
import queue

warnings.filterwarnings(
    "ignore",
    message="torch.cuda.amp.autocast",
    category=FutureWarning,
    module=".*yolov5_master.models.common*"
)


# parameter data
fps = 5
signal_dur = 0.9  # 0.9 sec
log_path = '/var/www/html/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
# gpio_handle, LAMP1, LAMP2, SIGNAL, = setup_gpio()
listening = True  # Define the listening variable
recording_stopped = False  # Global variable
# reset the contents of the status variable, used for flagging that
# video1-conversion is complete.
with open('/var/www/html/status.txt', 'w') as status_file:
    status_file.write("")


def restart_camera(camera, resolution=(1920, 1080), fps=5):
    time.sleep(2)  # Ensure the camera is fully released
    try:
        if camera is not None:
            camera.stop()
            camera.close()
            logger.info("Previous camera instance stopped and closed.")
        time.sleep(2)  # Ensure the camera is fully released

        camera = Picamera2()
        logger.info("New Picamera2 instance created.")
        time.sleep(2)

        # List available sensor modes
        sensor_modes = camera.sensor_modes
        if not sensor_modes:
            logger.error("No sensor modes available. Camera may not be detected!")
            return None

        # logger.debug(f"Available sensor modes: {sensor_modes}")

        # Find a sensor mode that best matches the requested resolution
        best_mode = min(sensor_modes, key=lambda m: abs(m["size"][0] - resolution[0]) + abs(m["size"][1] - resolution[1]))
        # logger.debug(f"Using sensor mode: {best_mode}")

        config = camera.create_video_configuration(
            main={"size": best_mode["size"], "format": "BGR888"},
            transform=Transform(hflip=True, vflip=True)
        )
        camera.set_controls({"FrameRate": fps})
        logger.debug(f"Config before applying: {config}")
        camera.configure(config)

        camera.start()
        logger.info(f"Camera restarted with resolution {best_mode['size']} and FPS: {fps}.")
        return camera  # Return new camera instance

    except Exception as e:
        logger.error(f"Failed to restart camera: {e}")
        return None  # Avoid using an uninitialized camera


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
        model = torch.hub.load('/home/pi/yolov5', 'yolov5s', source='local', force_reload=True)
        logger.debug("YOLOv5 model loaded successfully.")
        result_queue.put(model)  # Put the model in the queue
    except Exception as e:
        logger.error(f"Failed to load YOLOv5 model: {e}", exc_info=True)
        result_queue.put(e)  # Put the exception in the queue


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
        video_config = camera.create_video_configuration(
            main={"size": (1920, 1080)},
            transform=Transform(hflip=True, vflip=True)
        )
        time.sleep(0.5)  # Add a short delay to ensure the camera is ready
        camera.set_controls({"FrameRate": fps})
        camera.configure(video_config)
        logger.info(f"Camera configured with resolution (1920, 1080) and FPS {fps}.")
        time.sleep(0.5)  # Add a short delay to ensure the camera is ready
    except Exception as e:
        logger.error(f"Failed to configure camera: {e}")
        return

    if camera is None:
        logger.error("Camera object is None before restarting.")
        return

    camera = restart_camera(camera, resolution=(1920, 1080), fps=fps)

    # Confirm cam is initialized
    if camera is None:
        logger.error("Camera restart failed, exiting.")
        return  # Prevents crashing if camera restart fails

    try:
        # Attempt to capture a frame
        logger.debug("Attempting to capture the first frame.")
        frame = camera.capture_array()
        if frame is None:
            logger.error("First captured frame is None! Exiting video recording.")
            return
        else:
            logger.debug(f"First frame captured successfully. Frame shape: {frame.shape}")
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

    logger.debug("Frame size confirmed, proceeding to crop the frame.")

    try:
        # Crop the original frame to maintain a square (1:1) aspect ratio
        logger.debug("Attempting to crop the frame.")
        # crop_width, crop_height = 1280, 720
        # crop_width, crop_height = 1640, 1080
        crop_width, crop_height = 1440, 1080
        shift_offset = 100  # horisontal offset for crop -> right part
        # Get dimensions of the full-resolution frame (1920x1080 in your case)
        frame_height, frame_width = frame.shape[:2]  # shape = (height, width, channels)
        x_start = max((frame_width - crop_width) // 2 + shift_offset, 50)
        y_start = max((frame_height - crop_height) // 2, 0)
        # logger.info(f"shift_offset = {shift_offset}, x_start= {x_start}, y_start = {y_start}")

        if frame_size[0] != 1920 or frame_size[1] != 1080:
            logger.error(f"Resolution mismatch! Expected (1920, 1080) but got {frame_size}.")
        else:
            logger.debug("Resolution matches expected values.")

    except Exception as e:
        logger.error(f"Unhandled exception occurred: {e}", exc_info=True)
        return
    logger.debug(f"Frame cropped successfully. Crop size: {crop_width}x{crop_height}")  

    # Set the camera to the desired resolution and frame rate
    fpsw = fps
    logger.debug(f"FPS set to {fpsw}, proceeding to load YOLOv5 model.")

    try:
        # Inference ## Load the pre-trained YOLOv5 model (e.g., yolov5s)
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
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Use 'XVID' for .avi, or 'mp4v' for .mp4
    video_writer = cv2.VideoWriter(video_path + 'video1' + '.avi', fourcc, fpsw, frame_size) 
    if not video_writer.isOpened():
        logger.error(f"Failed to open video1.avi for writing. Selected frame_size: {frame_size}")
        exit(1)
    logger.debug("Video writer initialized successfully.")

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

    inference_width, inference_height = 640, 480  # Since you resize before inference

    # Compute scaling factors
    scale_x = crop_width / inference_width
    scale_y = crop_height / inference_height

    # Base scale text size and thickness
    base_fontScale = 0.9  # Default font size at 640x480
    base_thickness = 2  # Default thickness at 640x480
    scale_factor = (scale_x + scale_y) / 2  # Average scale factor
    fontScale = max(base_fontScale * scale_factor, 0.6)  # Prevent too small text
    thickness = max(int(base_thickness * scale_factor), 1)  # Prevent too thin lines
    font = cv2.FONT_HERSHEY_DUPLEX
    colour = (0, 255, 0)  # Green text
    logger.info(f"inference_width, inference_height = {inference_width, inference_height}")
    logger.info(f"crop_width, crop_height = {crop_width, crop_height}")
    logger.info(f"scale_x = {scale_x}, scale_y= {scale_y}")

    while not recording_stopped:
        # logger.debug(f"recording_stopped = {recording_stopped}")
        # elapsed_time = time.time() - camera_start_time
        # logger.debug(f"Elapsed time: {elapsed_time:.2f} seconds, Max duration: {max_duration}")
        # if elapsed_time >= max_duration:
        #    logger.warning("Timeout reached, stopping recording")
        #    recording_stopped = True
        #    break
        boat_in_current_frame = False  # Reset detection flag for this frame
        frame_counter += 1  # Increment the frame counter

        # Capture a frame from the camera
        try:
            frame = camera.capture_array()
            if frame is None:
                logger.error("Captured frame is None! Skipping write.")
                continue
            capture_timestamp = datetime.now() + timedelta(microseconds=frame_counter)
            # logger.debug(f"  Capture timestamp: {capture_timestamp}")

            if previous_capture_time:
                time_diff = (capture_timestamp - previous_capture_time).total_seconds()
                # logger.debug(f"Time since last frame: {time_diff:.3f} sec")

            previous_capture_time = capture_timestamp  # Update for next iteration

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

        # Perform inference only on every x frame
        if frame_counter % 8 == 0:  # every frame from 4 to 8
            # The cropped frame will cover pixels from (520, 180) to (1800, 900) 
            # of the original frame.
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
                # logger.debug("Detection made")
                for _, row in detections.iterrows():
                    class_name = row['name']
                    confidence = row['confidence']

                    if confidence > 0.3 and class_name == 'boat':
                        origin = (50, max(50, frame_height - 100))  # Position on frame
                        font = cv2.FONT_HERSHEY_DUPLEX
                        # text_rectangle(frame, f"{capture_timestamp}", origin)
                        text_rectangle(frame, (f'{capture_timestamp.strftime("%Y-%m-%d, %H:%M:%S")}'), origin)
                        # cv2.putText(frame, f"{capture_timestamp}", origin, font, fontScale, colour, thickness)
                        boat_in_current_frame = True
                        # logger.debug(f"Confidence {confidence:.2f}, capture_timestamp = {capture_timestamp}")
                        detected_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")  # timestamp (with microseconds)
                        # logger.debug(f"Detected_timestamp={detected_timestamp}")

                        #  Adjust the bounding box coordinates to reflect the original frame
                        x1 = int(row['xmin'] * scale_x) + x_start
                        y1 = int(row['ymin'] * scale_y) + y_start
                        x2 = int(row['xmax'] * scale_x) + x_start
                        y2 = int(row['ymax'] * scale_y) + y_start

                        # Draw bounding box and label on the frame
                        cv2.rectangle(frame, (x1, y1), (x2, y2), colour, thickness)
                        cv2.putText(frame, f"{confidence:.2f}", (x1, y2 + 50),
                                    font, fontScale, colour, thickness)

                        if frame is not None:
                            video_writer.write(frame)
                            # logger.debug("Detected frame written  !!!")
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
                        origin = (50, max(50, frame_height - 100))  # (50, 1820)
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
        # logger.debug(f"Elapsed time since start: {elapsed_time} seconds")
        if elapsed_time >= max_duration:
            logger.debug(f"Maximum recording time reached, elapsed _time={elapsed_time}")
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


def main():
    stop_event = threading.Event()
    global listening  # Declare listening as global
    # camera = setup_picam2(resolution=(1920, 1080), fps=fps)
    camera = setup_camera()
    if camera is None:
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
            # A loop that waits until close to the 5-minute mark, and 
            # continuously checks the condition without blocking the 
            # execution completely
            while True:
                now = dt.datetime.now()
                seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second

                if seconds_since_midnight > t5min_warning - 4:
                    logger.debug("Start of outer loop iteration. seconds_since_midnight=%d", seconds_since_midnight)
                    logger.debug("start_time_sec=%d", start_time_sec)

                    if num_starts == 1 or num_starts == 2:
                        # Start video recording just before 5 minutes before the first start
                        logger.debug("Start of video0 recording")
                        start_video_recording(camera, video_path, "video0.avi", bitrate=2000000)
                        logger.debug("Inner loop, entering the start sequence block.")
                        start_sequence(camera, start_time_sec, num_starts, dur_between_starts, photo_path)
                        if num_starts == 2:
                            start_time_sec = start_time_sec + (dur_between_starts * 60)
                        logger.debug("Wait 2 minutes then stop video0 recording")
                        t0 = dt.datetime.now()
                        logger.debug(f"t0 = {t0}, dt.datetime.now(): {dt.datetime.now()}")
                        logger.debug("(dt.datetime.now() - t0).seconds: %d", (dt.datetime.now() - t0).seconds)
                        while ((dt.datetime.now() - t0).seconds < 119):
                            now = dt.datetime.now()
                            time.sleep(0.2)  # Small delay to reduce CPU usage
                        stop_video_recording(camera)
                        logger.debug("Stopping video0 recording")
                        process_video(video_path, "video0.avi", "video0.mp4", frame_rate=30)
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
            process_video(video_path, "video1.avi", "video1.mp4")

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

            # GPIO.cleanup(gpio_handle)
            # logger.debug("After GPIO.cleanup, end of program")

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
