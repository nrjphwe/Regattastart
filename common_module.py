import os, subprocess
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
# Font settings for text annotations
FONT = cv2.FONT_HERSHEY_DUPLEX
FONT_SCALE = 2
THICKNESS = 2


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
        camera.rotation = 180  # Rotate the camera output by 180 degrees
        return camera  # Add this line to return the camera object
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        return None


def text_rectangle(frame, text, origin, text_colour=(255, 255, 255), bg_colour=(0, 0, 0), font=cv2.FONT_HERSHEY_DUPLEX, font_scale=2, thickness=2):
    """
    Draw a background rectangle and overlay text on a frame.
    """
    try:
        # Calculate text size
        text_size = cv2.getTextSize(text, FONT, FONT_SCALE, THICKNESS)[0]
        text_width, text_height = text_size

        # Calculate background rectangle coordinates
        bg_top_left = (origin[0] - 10, origin[1] - text_height - 10)  # Top-left corner
        bg_bottom_right = (origin[0] + text_width + 10, origin[1] + 10)  # Bottom-right corner

        # Draw the background rectangle
        cv2.rectangle(frame, bg_top_left, bg_bottom_right, bg_colour, -1)  # -1 fills the rectangle

        # Overlay the text on top of the background
        cv2.putText(frame, text, origin, FONT, FONT_SCALE, text_colour, THICKNESS, cv2.LINE_AA)

    except Exception as e:
        logger.error(f"Error in text_rectangle: {e}", exc_info=True)


def apply_timestamp(request):
    timestamp = time.strftime("%Y-%m-%d %X")
    # ext_colour = (0, 47, 255)  # Blue text
    text_colour = (255, 0, 0)  # Blue text in BGR
    bg_colour = (200, 200, 200)  # Light grey background

    try:
        with MappedArray(request, "main") as m:
            frame = m.array  # Get the frame
            if frame is None or frame.shape[0] == 0:
                logger.error("apply_timestamp: Frame is None or empty!")
                return

            # Define text position
            origin = (40, max(50, frame.shape[0] - 50))  # Bottom-left corner of the text

            # Use text_rectangle to draw the timestamp
            text_rectangle(frame, timestamp, origin, text_colour, bg_colour)

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
