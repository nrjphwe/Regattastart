import os
import logging
import logging.config
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder

logger: logging.Logger  # Explicitly declare the logger variable


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

    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    print(f"Current LOG_LEVEL: {os.getenv('LOG_LEVEL', 'NOT SET')}")
    # Load logging configuration from the INI file
    logging.config.fileConfig('/usr/lib/cgi-bin/logging.conf')
    logging.getLogger().setLevel(log_level) # Dynamically set the logging level
    print(f"Set logging level to: {log_level}")
    # Create a logger instance with the "start" configuration
    logger = logging.getLogger('start')
    logger.info("Logging initialized in common_module")

    return logger


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


def start_video_recording(cam, video_path, file_name, bitrate=2000000):
    """
    Start video recording using H264Encoder and with timestamp.
    """
    output_file = os.path.join(video_path, file_name)
    logger.debug(f"Will start video rec. output file: {output_file}")
    cam.pre_callback = apply_timestamp
    encoder = H264Encoder(bitrate=bitrate)
    cam.start(encoder, output_file)
    logger.info(f"Started recording video: {output_file}")


def stop_video_recording(cam):
    cam.stop_recording()
    cam.stop()  # Fully stop the camera
    logger.info("Recording stopped and camera fully released.")
