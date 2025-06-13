#!/home/pi/yolov5_env/bin/python
import os
import subprocess
import time
import datetime as dt
import logging
import logging.config
from libcamera import Transform
from libcamera import ColorSpace
from picamera2 import Picamera2, MappedArray
from picamera2.encoders import H264Encoder
import RPi.GPIO as GPIO
import cv2
import lgpio

# Initialize global variables
logger = None
signal_dur = 0.9  # Default signal duration

FONT = cv2.FONT_HERSHEY_DUPLEX  # Font settings for text annotations
FONT_SCALE = 2   # Font scale for text annotations
THICKNESS = 2  # Thickness of the text annotations

sensor_size = 1640, 1232  # sensors aspect ratio

# text_colour = (0, 0, 255)  # Blue text in RGB
# text_colour = (255, 0, 0)  # Blue text in BGR
# bg_colour = (200, 200, 200)  # Light grey background

# GPIO pin numbers for the relay and lamps
signal_pin = 26
lamp1 = 20
lamp2 = 21

# Define ON/OFF states for clarity
ON = GPIO.LOW
OFF = GPIO.HIGH


def setup_logging():
    """
    Initialize logging using configuration from an INI file 
    and dynamically set the logging level.

    Set LOG_LEVEL as an environment variable before running the script:
    For full debugging: export LOG_LEVEL=DEBUG
    For normal info level: export LOG_LEVEL=INFO
    For only warnings and above: export LOG_LEVEL=WARNING
    For only errors: export LOG_LEVEL=ERROR
    """
    global logger  # Ensure logger is a global variable
    # remove log file
    file_path = "/var/www/html/python.log"
    os.remove(file_path)

    # Load configuration
    logging.config.fileConfig('/usr/lib/cgi-bin/logging.conf')

    # Create a logger
    logger = logging.getLogger('start')

    # Logga den aktuella nivån från logging.conf
    current_level = logging.getLevelName(logger.getEffectiveLevel())
    print(f"Current logging level from logging.conf: {current_level}")
    logger.info("Logging initialized in common_module")


# Initialize logging immediately when the module is imported
setup_logging()


def get_cpu_model():
    try:
        with open("/proc/cpuinfo", "r") as f:
            lines = f.readlines()
            for line in lines:
                if any(key in line for key in ("Model", "model name", "Hardware")) and ":" in line:
                    return line.strip().split(":")[1].strip()
            # Fallback if no match
            logger.warning("No matching CPU model line found. Dumping /proc/cpuinfo:")
            for line in lines:
                logger.warning(line.strip())
            return "Unknown"
    except Exception as e:
        logger.error(f"Exception while reading /proc/cpuinfo: {e}")
        return "Unknown"


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


def setup_camera(resolution=(1640, 1232)):
    global logger  # Explicitly declare logger as global
    try:
        camera = Picamera2()
        # Stop the camera if it is running (no need to check is_running)
        logger.info("Stopping the camera before reconfiguring.")
        camera.stop()  # Stop the camera if it is running
        # Configure the camera
        config = camera.create_still_configuration(
            main={"size": (resolution), "format": "BGR888"},
            colour_space=ColorSpace.Srgb()  # OR ColorSpace.Sycc()
        )
        camera.configure(config)
        logger.info(f"size: {resolution}, format: BGR888")
        return camera  # Add this line to return the camera object
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        return None


def letterbox(image, target_size=(640, 480)):
    ih, iw = image.shape[:2]
    w, h = target_size  # (width, height)

    scale = min(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)

    logger.debug(f"Original: {iw}x{ih}, Target: {w}x{h}, New: {nw}x{nh}")

    image_resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)

    top = (h - nh) // 2
    bottom = h - nh - top
    left = (w - nw) // 2
    right = w - nw - left

    logger.debug(f"Padding: top={top}, bottom={bottom}, left={left}, right={right}")

    return cv2.copyMakeBorder(
        image_resized, top, bottom, left, right,
        cv2.BORDER_CONSTANT, value=(0, 0, 0)
    )


def capture_picture(camera, photo_path, file_name, rotate=False):
    try:
        request = camera.capture_request()  # Capture a single request

        with MappedArray(request, "main") as m:
            frame = m.array  # Get the frame as a NumPy array
            logger.debug(f"frame shape: {frame.shape} dtype: {frame.dtype}")
            # Ensure the frame is in BGR format
            if frame.shape[-1] == 3:  # Assuming 3 channels for RGB/BGR
                # logger.debug("Converting frame from RGB to BGR")
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Apply timestamp (reuse the same logic as in apply_timestamp)
            timestamp = time.strftime("%Y-%m-%d %X")
            origin = (40, max(50, frame.shape[0] - 50))  # Bottom-left corner
            text_colour = (255, 0, 0)  # Blue text in BGR, Blue text RGB = (0, 0, 255)
            bg_colour = (200, 200, 200)  # Gray background
            # Use text_rectangle function in common_module to draw timestamp
            text_rectangle(frame, timestamp, origin, text_colour, bg_colour)
            if rotate:
                frame = cv2.rotate(frame, cv2.ROTATE_180)

            # Use this version for display and saved images
            # resized_for_display = letterbox(frame, (640, 480))
            resized_for_display = letterbox(frame, (1280, 960))
            cv2.imwrite(os.path.join(photo_path, file_name), resized_for_display)
            logger.debug(f"Saved resized_for_display size: {resized_for_display.shape}")
            # cv2.imwrite(os.path.join(photo_path, file_name), frame)
        request.release()
        logger.info(f'Captured picture: {file_name}')
    except Exception as e:
        logger.error(f"Failed to capture picture: {e}", exc_info=True)


def text_rectangle(frame, text, origin, text_colour=(255, 0, 0), bg_colour=(200, 200, 200), font=FONT, font_scale=FONT_SCALE, thickness=THICKNESS):
    """
    Draw a background rectangle and overlay text on a frame.
    Default values for text_colour is Blue and for background is grey.
    """
    try:
        # OpenCV uses BGR by default, ensure colours are set in BGR format

        # Calculate text size
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_width, text_height = text_size

        # Calculate background rectangle coordinates
        bg_top_left = (origin[0] - 10, origin[1] - text_height - 10)  # Top-left corner
        bg_bottom_right = (origin[0] + text_width + 10, origin[1] + 10)  # Bottom-right corner

        # Draw the background rectangle
        cv2.rectangle(frame, bg_top_left, bg_bottom_right, bg_colour, -1)  # -1 fills the rectangle

        # Overlay the text on top of the background
        cv2.putText(frame, text, origin, font, font_scale, text_colour, thickness, cv2.LINE_AA)

    except Exception as e:
        logger.error(f"Error in text_rectangle: {e}", exc_info=True)


def apply_timestamp(request):
    timestamp = time.strftime("%Y-%m-%d %X")
    try:
        with MappedArray(request, "main") as m:
            frame = m.array  # Get the frame
            if frame is None or frame.shape[0] == 0:
                logger.error("apply_timestamp: Frame is None or empty!")
                return
            # Define text position
            origin = (40, max(50, frame.shape[0] - 50))  # Bottom-left corner
            text_colour = (0, 0, 255)  # Red text in BGR
            # Use text_rectangle to draw the timestamp
            text_rectangle(frame, timestamp, origin, text_colour)
    except Exception as e:
        logger.error(f"Error in apply_timestamp: {e}", exc_info=True)


def start_video_recording(camera, video_path, file_name, resolution = (1640, 1232), bitrate=2000000):
    """
    Start video recording using H264Encoder and with timestamp.
    """
    output_file = os.path.join(video_path, file_name)
    logger.debug(f"Will start video rec. output file: {output_file}")
    encoder = H264Encoder(bitrate=bitrate)

    video_config = camera.create_video_configuration(
        main={"size": resolution, "format": "BGR888"},
        transform=Transform(hflip=True, vflip=True),  # Rotate 180-degree
        controls={"FrameRate": 5}
        )
    camera.configure(video_config)  # Configure before starting recording

    # Set the pre_callback to apply the timestamp AFTER configuration
    logger.debug("Setting pre_callback to apply_timestamp")
    camera.pre_callback = apply_timestamp

    # Start recording
    camera.start_recording(encoder, output_file)
    logger.info(f"Started recording video: {output_file}")


def stop_video_recording(cam):
    cam.stop_recording()
    cam.stop()  # Fully stop the camera
    logger.info("Recording stopped and camera fully released.")


def process_video(video_path, input_file, output_file, frame_rate=None):
    source = os.path.join(video_path, input_file)
    dest = os.path.join(video_path, output_file)
    if not os.path.exists(source) or os.path.getsize(source) <= 5000:
        logger.debug(f"Warning: {input_file} is empty or does not exist. Skipping conversion.")
        return
    command = ["ffmpeg", "-i", source, "-vcodec", "libx264", "-crf", "23", "-preset", "ultrafast"]

    # vf_filters = ["scale=640:480"]
    vf_filters = ["scale=1640:1232"]
    if frame_rate:
        vf_filters.append(f"fps={frame_rate}")
    command.extend(["-vf", ",".join(vf_filters)])

    #  Add pixel format for consistent output
    command.extend(["-pix_fmt", "yuv420p"])

    command.extend(["-y", dest])  # Add output destination

    try:
        subprocess.run(command, check=True)
        logger.debug("Video processed: %s", output_file)
    except Exception as e:
        logger.error(f"Failed to process video: {e}")
        return


def setup_gpio():
    try:
        # seems like initial value off corresponds to 1
        h = lgpio.gpiochip_open(0)  # Open GPIO chip 0
        lgpio.gpio_claim_output(h, 26, 1)  # Signal pin
        lgpio.gpio_claim_output(h, 20, 1)  # Lamp1
        lgpio.gpio_claim_output(h, 21, 1)  # Lamp2
        logger.info("GPIO setup successful: Signal=26, Lamp1=20, Lamp2=21")
        return h, 26, 20, 21  # Return the GPIO handle and pin numbers
    except Exception as e:
        logger.error(f"Error in setup_gpio: {e}")
        raise


def trigger_relay(handle, pin, state, duration=None):
    """Control a relay by turning it ON or OFF, optionally with a delay."""
    try:
        # logger.info(f"Triggering relay on pin {pin} to state {state}")
        lgpio.gpio_write(handle, pin, 0 if state == "on" else 1)
        # logger.debug(f"Pin {pin} set to {'HIGH' if state == 'on' else 'LOW'}")
        if duration:
            time.sleep(int(duration))
            lgpio.gpio_write(handle, pin, 1)  # Turn off after the duration
            # logger.debug(f"Pin {pin} turned OFF after {duration} seconds")
    except Exception as e:
        logger.error(f"Failed to trigger relay on pin {pin}: {e}")


def cleanup_gpio(handle):
    global logger
    try:
        lgpio.gpiochip_close(handle)  # Close GPIO chip 0
        logger.debug("GPIO resources cleaned up successfully.")
    except Exception as e:
        logger.error(f"Error while cleaning up GPIO: {e}")


def start_sequence(camera, start_time_sec, num_starts, dur_between_starts, photo_path):
    gpio_handle, SIGNAL, LAMP1, LAMP2 = setup_gpio()
    for i in range(num_starts):
        logger.info(f"Start_sequence. Start of iteration {i+1}")
        # Adjust the start_time_sec for the second iteration
        if i == 1:
            start_time_sec += dur_between_starts * 60  # Add 5 or 10 minutes for the second iteration
            logger.info(f"Start_sequence, Next start_time_sec: {start_time_sec}")

        # Define time intervals for each relay trigger
        time_intervals = [
            (start_time_sec - 5 * 60, lambda: trigger_relay(gpio_handle, LAMP1, "on"), "5_min Lamp1 ON -- Flag P UP"),
            (start_time_sec - 5 * 60 + 1, lambda: trigger_relay(gpio_handle, SIGNAL, "on", 2), "5_min Warning Signal"),
            (start_time_sec - 4 * 60 - 2, lambda: trigger_relay(gpio_handle, LAMP2, "on"), "4_min Lamp2 ON"),
            (start_time_sec - 4 * 60, lambda: trigger_relay(gpio_handle, SIGNAL, "on", 2), "4_min Preparation Signal"),
            (start_time_sec - 1 * 60 - 2, lambda: trigger_relay(gpio_handle, LAMP2, "off"), "1_min Lamp2 OFF -- Flag P DOWN"),
            (start_time_sec - 1 * 60, lambda: trigger_relay(gpio_handle, SIGNAL, "on", 2), "1_min Signal"),
            (start_time_sec - 2, lambda: trigger_relay(gpio_handle, LAMP1, "off"), "Lamp1 OFF at Start"),
            (start_time_sec, lambda: trigger_relay(gpio_handle, SIGNAL, "on", 1), "Start Signal"),
        ]

        # last_triggered_events = {}
        last_triggered_events = set()

        while True:
            time_now = dt.datetime.now()
            seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

            all_triggered = all((event_time, log_message) in last_triggered_events for event_time, _, log_message in time_intervals)
            if all_triggered:
                logger.info("All events triggered, exiting loop.")
                break
            
            for idx, (event_time, action, log_message) in enumerate(time_intervals):
            # for event_time, action, log_message in time_intervals:
                # time_now = dt.datetime.now()
                # seconds_now = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
                if event_time <= seconds_since_midnight < event_time + 2 and (event_time, log_message) not in last_triggered_events:
                    logger.info(f"Start_sequence: {log_message} at {event_time}")
                    if action:
                        action()
                    if "Signal" in log_message:
                        picture_name = f"{idx + 1}a_start_{log_message[:5]}.jpg"
                        capture_picture(camera, photo_path, picture_name)
                        time.sleep(0.1)
                    logger.info(f"Start_sequence, log_message: {log_message}")
                    last_triggered_events.add((event_time, log_message))
                    logger.info(f'event_time: {event_time}, log_message: {log_message}')
                time.sleep(0.1)  # avoid busy loop

        logger.info(f"Start_sequence, End of iteration: {i+1}")
    cleanup_gpio(gpio_handle)  # Clean up GPIO after each iteration
