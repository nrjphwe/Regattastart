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
            origin = (50, max(50, height - 100))  # Ensure text is within the frame
            cv2.putText(frame, timestamp, origin, font, fontScale, colour, thickness)

    except Exception as e:
        logger.error(f"Error in apply_timestamp: {e}", exc_info=True)


def start_video_recording(cam, video_path, file_name, bitrate=2000000):
    """
    Start video recording using H264Encoder and with timestamp.
    """
    output_file = os.path.join(video_path, file_name)
    logger.debug(f"Will start video rec. output file: {output_file}")
    encoder = H264Encoder(bitrate=bitrate)
    #cam.pre_callback = apply_timestamp
   
    video_config = cam.create_video_configuration(main={"size": (1296, 730)}, controls={"FrameRate": 5})
    cam.configure(video_config)  # Configure before starting recording
    cam.start(encoder, output_file)
    logger.info(f"Started recording video: {output_file}")


def stop_video_recording(cam):
    cam.stop_recording()
    cam.stop()  # Fully stop the camera
    logger.info("Recording stopped and camera fully released.")


# Define ON/OFF states for clarity
ON = GPIO.LOW
OFF = GPIO.HIGH

# Define GPIO pins
PINS = {
    "signal": 26,
    "lamp1": 20,
    "lamp2": 21
}


def setup_gpio():
    global logger 
    """Initialize GPIO pins and return them as a dictionary."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(True)

    # Setup pins
    for name, pin in PINS.items():
        GPIO.setup(pin, GPIO.OUT, initial=OFF)
        logger.info(f"Initialized {name} (pin {pin}) to OFF")

    return PINS  # Return the dictionary of pins


def trigger_relay(port):
    global logger
    """Controls relays based on the given port command."""
    if port == "Signal":
        GPIO.output(PINS["Signal"], ON)
        time.sleep(signal_dur)
        GPIO.output(PINS["Signal"], OFF)
        time.sleep(1 - signal_dur)
        logger.info(f"Triggered Signal: {signal_dur} sec ON, then {1 - signal_dur} sec OFF")

    elif port in ["Lamp1_on", "Lamp2_on"]:
        pin = PINS[port.replace("_on", "")]
        GPIO.output(pin, ON)
        logger.info(f"{port} activated")

    elif port in ["Lamp1_off", "Lamp2_off"]:
        pin = PINS[port.replace("_off", "")]
        GPIO.output(pin, OFF)
        logger.info(f"{port} deactivated")

    else:
        logger.warning(f"Unknown port command: {port}")


def cleanup_gpio():
    global logger
    """Clean up GPIO on script exit."""
    GPIO.cleanup()
    logger.info("GPIO cleaned up")
