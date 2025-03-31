import os
import time
import logging
import logging.config
from picamera2 import Picamera2, MappedArray
from picamera2.encoders import H264Encoder
import RPi.GPIO as GPIO
import cv2


# Initialize global variables
logger = None  
signal_dur = 0.9  # Default signal duration


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
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    print(f"Current LOG_LEVEL: {os.getenv('LOG_LEVEL', 'NOT SET')}")


    # Load configuration
    logging.config.fileConfig('/usr/lib/cgi-bin/logging.conf')
    logging.getLogger().setLevel(log_level) # Dynamically set the logging level
    print(f"Set logging level to: {log_level}")

    # Create a logger
    logger = logging.getLogger('start')
    logger.info("Logging initialized in common_module")


# Initialize logging immediately when the module is imported
setup_logging()


def setup_camera():
    global logger  # Explicitly declare logger as global
    try:
        camera = Picamera2()
        camera.resolution = (1296, 730)
        camera.framerate = 5
        # camera.annotate_background = Color('black')
        # camera.annotate_foreground = Color('white')
        camera.rotation = (180)  # Depends on how camera is mounted
        return camera  # Add this line to return the camera object
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        return None


def apply_timestamp(request):
    timestamp = time.strftime("%Y-%m-%d %X")
    text_colour = (0, 255, 0)  # Green text
    bg_colour = (0, 0, 0)  # Black background
    font = cv2.FONT_HERSHEY_DUPLEX
    fontScale = 2
    thickness = 2

    try:
        with MappedArray(request, "main") as m:
            frame = m.array  # Get the frame
            if frame is None or frame.shape[0] == 0:
                logger.error("apply_timestamp: Frame is None or empty!")
                return

            # Calculate text size and position
            text_size = cv2.getTextSize(timestamp, font, font_scale, thickness)[0]
            text_width, text_height = text_size
            origin = (50, max(50, frame.shape[0] - 100))  # Bottom-left corner of the text
            bg_top_left = (origin[0] - 10, origin[1] - text_height - 10)  # Top-left corner of the background
            bg_bottom_right = (origin[0] + text_width + 10, origin[1] + 10)  # Bottom-right corner of the background

            # Draw the background rectangle
            cv2.rectangle(frame, bg_top_left, bg_bottom_right, bg_colour, -1)  # -1 fills the rectangle

            # Overlay the text on top of the background
            cv2.putText(frame, timestamp, origin, font, fontScale, text_colour, thickness)

    except Exception as e:
        logger.error(f"Error in apply_timestamp: {e}", exc_info=True)


def start_video_recording(cam, video_path, file_name, bitrate=2000000):
    """
    Start video recording using H264Encoder and with timestamp.
    """
    output_file = os.path.join(video_path, file_name)
    logger.debug(f"Will start video rec. output file: {output_file}")
    encoder = H264Encoder(bitrate=bitrate)

    # Set the pre_callback to apply the timestamp
    cam.pre_callback = apply_timestamp

    video_config = cam.create_video_configuration(main={"size": (1296, 730)}, controls={"FrameRate": 5})
    cam.configure(video_config)  # Configure before starting recording
    cam.start_recording(encoder, output_file)
    logger.info(f"Started recording video: {output_file}")


def stop_video_recording(cam):
    cam.stop_recording()
    cam.stop()  # Fully stop the camera
    logger.info("Recording stopped and camera fully released.")


# Define ON/OFF states for clarity
ON = GPIO.LOW
OFF = GPIO.HIGH

# Define GPIO pins
signal = 26
lamp1 = 20
lamp2 = 21


def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(True)
    GPIO.setup(signal, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(lamp1, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(lamp2, GPIO.OUT, initial=GPIO.HIGH)
    return signal, lamp1, lamp2


def trigger_relay(pin, state, duration=None):
    """Control a relay by turning it ON or OFF, optionally with a delay."""
    GPIO.output(pin, GPIO.HIGH if state == "on" else GPIO.LOW)
    if duration:
        time.sleep(duration)
        GPIO.output(pin, GPIO.LOW)  # Turn it off after the specified duration


def cleanup_gpio():
    global logger
    """Clean up GPIO on script exit."""
    GPIO.cleanup()
    logger.info("GPIO cleaned up")
