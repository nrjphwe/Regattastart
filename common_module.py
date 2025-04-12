#!/home/pi/yolov5_env/bin/python
import os
import sys
import subprocess
import time
import logging
import logging.config
from libcamera import Transform
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

    # Load configuration
    logging.config.fileConfig('/usr/lib/cgi-bin/logging.conf')

    # Create a logger
    logger = logging.getLogger('start')

    # Logga den aktuella nivån från logging.conf
    current_level = logging.getLevelName(logger.getEffectiveLevel())
    print(f"Current logging level from logging.conf: {current_level}")
    logger.info("Logging initialized in common_module")
    '''
    # Redirect stdout and stderr to the Python logger to 
    # capture all output in your python.log file.
    class StreamToLogger:
        def __init__(self, logger, log_level):
            self.logger = logger
            self.log_level = log_level
            self.linebuf = ''

        def write(self, buf):
            if not buf.strip():  # Ignore empty or whitespace-only lines
                return
            for line in buf.rstrip().splitlines():
                self.logger.log(self.log_level, line)
            self.logger.debug("StreamToLogger.write() called")  # Debug log

        def flush(self):
            self.logger.debug("StreamToLogger.flush() called")  # Debug log
            pass  # This is required for compatibility with file-like objects

    # Redirect stdout and stderr to the logger
    stdout_logger = logging.getLogger('STDOUT')
    stderr_logger = logging.getLogger('STDERR')

    sys.stdout = StreamToLogger(stdout_logger, logging.INFO)
    sys.stderr = StreamToLogger(stderr_logger, logging.ERROR)
    '''


# Initialize logging immediately when the module is imported
setup_logging()


def setup_camera():
    global logger  # Explicitly declare logger as global
    try:
        camera = Picamera2()
        # Stop the camera if it is running (no need to check is_running)
        logger.info("Stopping the camera before reconfiguring.")
        camera.stop()  # Stop the camera if it is running
        # Configure the camera
        config = camera.create_still_configuration(
            main={"size": (1296, 730), "format": "BGR888"}
        )
        camera.configure(config)
        return camera  # Add this line to return the camera object
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        return None


def capture_picture(camera, photo_path, file_name, rotate=False):
    try:
        request = camera.capture_request()  # Capture a single request

        with MappedArray(request, "main") as m:
            frame = m.array  # Get the frame as a NumPy array

            # Ensure the frame is in BGR format
            if frame.shape[-1] == 3:  # Assuming 3 channels for RGB/BGR
                logger.debug("Converting frame from RGB to BGR")
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
            cv2.imwrite(os.path.join(photo_path, file_name), frame)
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


def start_video_recording(camera, video_path, file_name, bitrate=2000000):
    """
    Start video recording using H264Encoder and with timestamp.
    """
    output_file = os.path.join(video_path, file_name)
    logger.debug(f"Will start video rec. output file: {output_file}")
    encoder = H264Encoder(bitrate=bitrate)

    video_config = camera.create_video_configuration(
        main={"size": (1296, 730), "format": "BGR888"},
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
    if frame_rate:
        command.extend(["-vf", f"fps={frame_rate}"])
    command.append(dest)
    try:
        subprocess.run(command, check=True)
        logger.debug("Video processed: %s", output_file)
    except Exception as e:
        logger.error(f"Failed to process video: {e}")
        return


def old_setup_gpio():
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(True)
        GPIO.setup(signal_pin, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(lamp1, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(lamp2, GPIO.OUT, initial=GPIO.HIGH)
        return lamp1, lamp2, signal_pin
    except Exception as e:
        logger.error(f"Error in setup_gpio: {e}", exc_info=True)
        raise


def setup_gpio():
    try:
        h = lgpio.gpiochip_open(0)  # Open GPIO chip 0
        lgpio.gpio_claim_output(h, 26, 1)  # Signal pin
        lgpio.gpio_claim_output(h, 20, 1)  # Lamp1
        lgpio.gpio_claim_output(h, 21, 1)  # Lamp2
        logger.info("GPIO setup successful: Signal=26, Lamp1=20, Lamp2=21")
        return h, 26, 20, 21  # Return the GPIO handle and pin numbers
    except Exception as e:
        logger.error(f"Error in setup_gpio: {e}")
        raise


def old_trigger_relay(pin, state, duration=None):
    """Control a relay by turning it ON or OFF, optionally with a delay."""
    GPIO.output(pin, GPIO.HIGH if state == "on" else GPIO.LOW)
    if duration:
        time.sleep(duration)
        GPIO.output(pin, GPIO.LOW)  # Turn it off after the specified duration


def trigger_relay(handle, pin, state, duration=None):
    """Control a relay by turning it ON or OFF, optionally with a delay."""
    try:
        logger.info(f"Triggering relay on pin {pin} to state {state}")
        lgpio.gpio_write(handle, pin, 1 if state == "on" else 0)
        logger.debug(f"Pin {pin} set to {'HIGH' if state == 'on' else 'LOW'}")
        if duration:
            time.sleep(duration)
            lgpio.gpio_write(handle, pin, 0)  # Turn off after the duration
            logger.debug(f"Pin {pin} turned OFF after {duration} seconds")
    except Exception as e:
        logger.error(f"Failed to trigger relay on pin {pin}: {e}")


def old_cleanup_gpio():
    global logger
    """Clean up GPIO on script exit."""
    GPIO.cleanup()
    logger.info("GPIO cleaned up")


def cleanup_gpio(handle):
    global logger
    try:
        lgpio.gpiochip_close(handle)  # Close GPIO chip 0
        logger.debug("GPIO resources cleaned up successfully.")
    except Exception as e:
        logger.error(f"Error while cleaning up GPIO: {e}")

