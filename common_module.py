#!/home/pi/yolov5_env/bin/python
import cv2
import os
import subprocess, threading, time
import datetime as dt
import logging
import logging.config
from queue import Queue, Full, Empty

# --- Konfigurerbara konstanter ---
LOG_FILE_PATH = "/var/www/html/python.log"
LOG_CONF_PATH = "/usr/lib/cgi-bin/logging.conf"

Picamera2 = None
H264Encoder = None
Transform = None
ColorSpace = None

try:
    from picamera2 import Picamera2
except Exception as e:
    print(f"[import] Picamera2 failed: {e}")

try:
    from picamera2.encoders import H264Encoder
except Exception as e:
    print(f"[import] H264Encoder failed: {e}")

try:
    from picamera2 import Transform
except Exception as e1:
    try:
        from libcamera import Transform
    except Exception as e2:
        print(f"[import] Transform failed: {e1} / {e2}")

try:
    from picamera2 import ColorSpace
except Exception as e1:
    try:
        from libcamera import ColorSpace
    except Exception as e2:
        print(f"[import] ColorSpace failed: {e1} / {e2}")

try:
    from picamera2 import MappedArray
    HAVE_MAPPEDARRAY = True
except Exception:
    HAVE_MAPPEDARRAY = False

try:
    import lgpio  # type: ignore
except ImportError:
    lgpio = None

# Globala inställningar
logger = None
signal_dur = 0.9

FONT = cv2.FONT_HERSHEY_DUPLEX
sensor_size = 1640, 1232
TARGET_RESOLUTION = 1280, 960

text_colour = (255, 0, 0)  # BGR Blue

# GPIO-pinnar för relä/lampor
signal = 20
lamp1 = 21
lamp2 = 26

ON = 1
OFF = 0

_relay_lock = threading.Lock()
_active_relay_timers = []


def setup_logging():
    global logger
    try:
        if os.path.exists(LOG_FILE_PATH):
            os.remove(LOG_FILE_PATH)
    except OSError:
        pass

    if os.path.exists(LOG_CONF_PATH):
        logging.config.fileConfig(LOG_CONF_PATH)
    else:
        logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger('start')
    logger.info("Logging initialized in common_module")


setup_logging()


def remove_picture_files(directory, pattern):
    for file in os.listdir(directory):
        if file.endswith(pattern):
            os.remove(os.path.join(directory, file))


def remove_video_files(directory, pattern):
    for file in os.listdir(directory):
        if file.startswith(pattern):
            os.remove(os.path.join(directory, file))


def get_cpu_model():
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if any(key in line for key in ("Model", "model name", "Hardware")) and ":" in line:
                    return line.strip().split(":")[1].strip()
            return "Unknown"
    except Exception as e:
        logger.error(f"Exception while reading /proc/cpuinfo: {e}")
        return "Unknown"


def should_rotate_image():
    model = get_cpu_model().lower()
    logger.info(f"Detected CPU model: {model}")
    if "compute module 5" in model or "cm5" in model or "raspberry pi 5" in model:
        logger.info("Detected CM5/Pi5 - rotating 180 degrees")
        return True
    return False


ROTATE_CAMERA = should_rotate_image()


def setup_camera(resolution=(1640, 1232)):
    logger.info("Setup of camera")
    try:
        camera = Picamera2()
        config = camera.create_still_configuration(
            main={"size": resolution, "format": "BGR888"},
            colour_space=ColorSpace.Srgb()
        )
        camera.configure(config)
        return camera
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        return None


def letterbox(image, target_size=(1280, 960)):
    ih, iw = image.shape[:2]
    w, h = target_size

    scale = min(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)

    image_resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)

    top = (h - nh) // 2
    bottom = h - nh - top
    left = (w - nw) // 2
    right = w - nw - left

    return cv2.copyMakeBorder(
        image_resized, top, bottom, left, right,
        cv2.BORDER_CONSTANT, value=(0, 0, 0)
    )


def capture_picture(camera, photo_path, file_name, rotate=True):
    try:
        frame = camera.capture_array("main")
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        timestamp = time.strftime("%Y-%m-%d %X")
        origin = (40, int(frame.shape[0] * 0.85))

        text_rectangle(frame, timestamp, origin, text_colour=(255, 0, 0), bg_colour=(200, 200, 200))

        if frame.shape[1] != TARGET_RESOLUTION[0] or frame.shape[0] != TARGET_RESOLUTION[1]:
            resized_for_display = letterbox(frame, TARGET_RESOLUTION)
        else:
            resized_for_display = frame

        cv2.imwrite(os.path.join(photo_path, file_name), resized_for_display)
        logger.info(f'Captured picture: {file_name}')

    except Exception as e:
        logger.error(f"Failed to capture picture: {e}", exc_info=True)


def text_rectangle(frame, text, origin, text_colour=(255, 0, 0), bg_colour=(200, 200, 200),
                   font=FONT, font_scale=1.5, thickness=2):
    try:
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_width, text_height = text_size
        pad = max(2, int(5 * font_scale))
        bg_top_left = (origin[0] - pad, origin[1] - text_height - pad)
        bg_bottom_right = (origin[0] + text_width + pad, origin[1] + pad)

        cv2.rectangle(frame, bg_top_left, bg_bottom_right, bg_colour, -1)
        cv2.putText(frame, text, origin, font, font_scale, text_colour, thickness, cv2.LINE_AA)
    except Exception as e:
        logger.error(f"Error in text_rectangle: {e}", exc_info=True)


def setup_gpio():
    level = 0
    try:
        h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(h, signal, level)
        lgpio.gpio_claim_output(h, lamp1, level)
        lgpio.gpio_claim_output(h, lamp2, level)
        logger.info("GPIO setup successful: Signal=20, Lamp1=21, Lamp2=26")
        return h, signal, lamp1, lamp2
    except Exception as e:
        logger.error(f"Error in setup_gpio: {e}")
        raise


def trigger_relay(handle, pin, state, duration=None):
    try:
        if state == "on":
            lgpio.gpio_write(handle, pin, 1)
            logger.info(f"Triggering relay on GPIO {pin} to state ON")
            if duration:
                def _turn_off():
                    try:
                        lgpio.gpio_write(handle, pin, 0)
                        logger.debug(f"GPIO {pin} turned OFF after {duration}s")
                    except Exception as e:
                        logger.error(f"Deferred turn-off failed for GPIO {pin}: {e}")

                timer = threading.Timer(duration, _turn_off)
                timer.daemon = True
                with _relay_lock:
                    _active_relay_timers.append(timer)
                timer.start()
        else:
            lgpio.gpio_write(handle, pin, 0)
            logger.info(f"Triggering relay on GPIO {pin} to state OFF")
    except Exception as e:
        logger.error(f"Failed to trigger relay on GPIO {pin}: {e}")


def flush_pending_relay_timers(handle, pins):
    global _active_relay_timers
    with _relay_lock:
        timers = list(_active_relay_timers)
        _active_relay_timers.clear()

    for t in timers:
        t.join(timeout=2)

    for pin in pins:
        try:
            lgpio.gpio_write(handle, pin, 0)
        except Exception as e:
            logger.error(f"Fail-safe: could not force GPIO {pin} OFF: {e}")
    logger.info(f"Fail-safe: forced GPIOs {pins} OFF")


def cleanup_gpio(handle):
    try:
        lgpio.gpiochip_close(handle)
        logger.debug("GPIO resources cleaned up successfully.")
    except Exception as e:
        logger.error(f"Error while cleaning up GPIO: {e}")


def start_sequence(camera, first_start_time, num_starts, dur_between_starts, photo_path):
    """
    Optimerad startsekvens med exakt tidsväntan (sleep till nästa event)
    istället för en intensiv polling-loop.
    """
    gpio_handle, SIGNAL, LAMP1, LAMP2 = setup_gpio()

    try:
        for i in range(num_starts):
            logger.info(f"Start_sequence: Start av iteration {i+1}")
            start_time = first_start_time + dt.timedelta(minutes=i * dur_between_starts)

            # Schemalägg alla händelser i kronologisk ordning
            events = [
                (start_time - dt.timedelta(minutes=5), lambda: trigger_relay(gpio_handle, LAMP1, "on"), "5_min Lamp1 ON -- Flag P UP", "5_min"),
                (start_time - dt.timedelta(minutes=5) + dt.timedelta(seconds=1), lambda: trigger_relay(gpio_handle, SIGNAL, "on", 1), "5_min Warning Signal", None),
                (start_time - dt.timedelta(minutes=4, seconds=2), lambda: trigger_relay(gpio_handle, LAMP2, "on"), "4_min Lamp2 ON", None),
                (start_time - dt.timedelta(minutes=4), lambda: trigger_relay(gpio_handle, SIGNAL, "on", 1), "4_min Preparation Signal", "4_min"),
                (start_time - dt.timedelta(minutes=1, seconds=2), lambda: trigger_relay(gpio_handle, LAMP2, "off"), "1_min Lamp2 OFF -- Flag P DOWN", None),
                (start_time - dt.timedelta(minutes=1), lambda: trigger_relay(gpio_handle, SIGNAL, "on", 1), "1_min Signal", "1_min"),
                (start_time - dt.timedelta(seconds=2), lambda: trigger_relay(gpio_handle, LAMP1, "off"), "Lamp1 OFF at Start", None),
                (start_time, lambda: trigger_relay(gpio_handle, SIGNAL, "on", 1), "Start Signal", "Start"),
            ]

            for event_time, action, label, photo_tag in events:
                now = dt.datetime.now()
                wait_seconds = (event_time - now).total_seconds()

                if wait_seconds > 0:
                    time.sleep(wait_seconds)

                logger.info(f"Triggering: {label} at {dt.datetime.now()}")
                action()

                if photo_tag:
                    image_name = f"{i+1}a_start_{photo_tag}.jpg"
                    capture_picture(camera, photo_path, image_name, rotate=ROTATE_CAMERA)

            logger.info(f"Start_sequence: Slut på iteration {i+1}")
            flush_pending_relay_timers(gpio_handle, [SIGNAL, LAMP1, LAMP2])

    finally:
        cleanup_gpio(gpio_handle)
