#!/home/pi/yolov5_env/bin/python
import cv2
import os
import subprocess, threading, time
import datetime as dt
import logging
import logging.config
from libcamera import Transform
from libcamera import ColorSpace
from picamera2 import Picamera2, MappedArray
from picamera2.encoders import H264Encoder
import RPi.GPIO as GPIO
import lgpio
from queue import Queue, Full, Empty

# Initialize global variables
logger = None
signal_dur = 0.9  # Default signal duration

FONT = cv2.FONT_HERSHEY_DUPLEX  # Font settings for text annotations
FONT_SCALE = 2   # Font scale for text annotations
THICKNESS = 2  # Thickness of the text annotations

sensor_size = 1640, 1232  # sensors aspect ratio

# text_colour = (0, 0, 255)  # Blue text in RGB
text_colour = (255, 0, 0)  # Blue text in BGR
# bg_colour = (200, 200, 200)  # Light grey background

# GPIO pin numbers for the relay and lamps
signal = 26  # for signal to pin 37 left 2nd from the bottom,
# for new startmachine: Relay channel 3 input (IN3) purple wire
lamp1 = 20   # , for lamp1 to pin 38 right 2nd from the bottom
# for new startmachine: Relay channel 1 input (IN1) blue wire
lamp2 = 21   # for lamp2 to pin 40 right bottom
# for new startmachine Relay channel 2 input (IN2) green wire

# for new startmachine GND grey wire

"""
Purple GPIO 26 (37)-(38) GPIO 20 blue
Grey Ground  (39)-(40) GPIO 21 Green
"""


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
            origin = (40, int(frame.shape[0] * 0.85))  # Bottom-left corner
            text_colour = (255, 0, 0)  # Blue text in BGR, Blue text RGB = (0, 0, 255)
            bg_colour = (200, 200, 200)  # Gray background
            # Use text_rectangle function in common_module to draw timestamp
            text_rectangle(frame, timestamp, origin, text_colour, bg_colour)
            if rotate:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            resized_for_display = letterbox(frame, (1280, 960))
            cv2.imwrite(os.path.join(photo_path, file_name), resized_for_display)
            logger.debug(f"Saved resized_for_display size: {resized_for_display.shape}")
        request.release()
        logger.info(f'Captured picture: {file_name}')
    except Exception as e:
        logger.error(f"Failed to capture picture: {e}", exc_info=True)


def text_rectangle(frame, text, origin, text_colour=(255, 0, 0), bg_colour=(200, 200, 200), font=FONT, font_scale=FONT_SCALE, thickness=THICKNESS):
    """
    Draw a background rectangle and overlay text on a frame.
    Default values for text_colour is Blue and for background is grey.
    OpenCV uses BGR by default, ensure colours are set in BGR format
    """
    try:
        # Calculate text size
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_width, text_height = text_size

        # Calculate background rectangle coordinates
        pad = int(5 * font_scale)
        bg_top_left = (origin[0] - pad, origin[1] - text_height - pad) 
        bg_bottom_right = (origin[0] + text_width + pad, origin[1] + pad)

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
            origin = (40, int(frame.shape[0] * 0.85))  # Bottom-left corner
            text_colour = (0, 0, 255)  # Red text in BGR
            text_rectangle(frame, timestamp, origin, text_colour)
    except Exception as e:
        logger.error(f"Error in apply_timestamp: {e}", exc_info=True)


def restart_camera(camera, resolution=(1640, 1232), fps=15):
    try:
        if camera is not None:
            camera.stop()
            camera.close()
            logger.info("Previous camera instance stopped and closed.")
        time.sleep(2)  # Ensure the camera is fully released

        camera = Picamera2()
        logger.info("New Picamera2 instance created.")

        # List available sensor modes
        sensor_modes = camera.sensor_modes
        if not sensor_modes:
            logger.error("No sensor modes available. Camera may not be detected!")
            return None

        # Find a sensor mode that best matches the requested resolution
        best_mode = min(sensor_modes, key=lambda m: abs(m["size"][0] - resolution[0]) + abs(m["size"][1] - resolution[1]))
        logger.debug(f"Using sensor mode: {best_mode}")

        config = camera.create_video_configuration(
            # main={"size": best_mode["size"], "format": "BGR888"},
            main={"size": best_mode["size"], "format": "RGB888"},
            transform=Transform(hflip=True, vflip=True),
            colour_space=ColorSpace.Srgb()  # OR ColorSpace.Sycc()
        )
        logger.debug(f"Config before applying: {config}")
        camera.configure(config)
        camera.set_controls({"FrameRate": fps})

        camera.start()
        logger.info(f"Camera restarted with best mode resolution {best_mode['size']} and FPS: {fps}.")
        return camera  # Return new camera instance

    except Exception as e:
        logger.error(f"Failed to restart camera: {e}")
        return None  # Avoid using an uninitialized camera


class FFmpegVideoWriter:
    """
    Non-blocking ffmpeg video writer using background thread and queue.
    Automatically restarts ffmpeg if it crashes or stalls.
    """

    def __init__(self, filename, fps, frame_size, force_sw=False, logger=None):
        self.filename = filename
        self.fps = fps
        self.frame_size = frame_size
        self.force_sw = force_sw
        self.logger = logger

        self.proc = None
        self.hw_enabled = False
        self.queue = Queue(maxsize=100)
        self.stop_event = threading.Event()
        self.lock = threading.Lock()

        # Start ffmpeg process
        self._start_ffmpeg_with_fallback()

        # Start background writer thread
        self.thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.thread.start()

    # -------------------------------------------------------------------
    def _start_ffmpeg_with_fallback(self):
        """Try hardware first, then software encoder if needed."""
        if not self.force_sw and self._start_ffmpeg(hw=True):
            self.hw_enabled = True
            if self.logger:
                self.logger.info(f"[FFmpegVideoWriter] Started hardware H.264 (v4l2m2m) for {self.filename}")
        else:
            if self.logger:
                self.logger.info(f"[FFmpegVideoWriter] Using software H.264 (libx264) for {self.filename}")
            if not self._start_ffmpeg(hw=False):
                raise RuntimeError("Failed to start FFmpeg (hw and sw both failed).")

    # -------------------------------------------------------------------
    def _start_ffmpeg(self, hw=True):
        width, height = self.frame_size
        codec = "h264_v4l2m2m" if hw else "libx264"

        ffmpeg_cmd = [
            "ffmpeg", "-y", "-fflags", "+genpts",
            "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-s", f"{width}x{height}", "-r", str(self.fps),
            "-i", "-", "-an"
        ]

        if hw:
            ffmpeg_cmd += ["-vf", "format=nv12", "-c:v", codec, "-b:v", "2M"]
        else:
            ffmpeg_cmd += ["-c:v", codec, "-preset", "ultrafast",
                           "-tune", "zerolatency", "-crf", "28"]

        ffmpeg_cmd += ["-pix_fmt", "yuv420p", "-movflags", "+faststart", self.filename]

        try:
            self.proc = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=10**6,
            )
            # Monitor stderr for debug info
            threading.Thread(target=self._read_stderr, daemon=True).start()
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"[FFmpegVideoWriter] Failed to start FFmpeg ({codec}): {e}")
            return False

    # -------------------------------------------------------------------
    def _read_stderr(self):
        """Read ffmpeg stderr for debugging."""
        if not self.proc or not self.proc.stderr:
            return
        for line in self.proc.stderr:
            text = line.decode(errors="ignore").strip()
            if self.logger and text:
                if "error" in text.lower() or "frame=" in text:
                    self.logger.debug(f"[FFmpeg] {text}")

    # -------------------------------------------------------------------
    def _restart_ffmpeg(self):
        """Restart ffmpeg process if it has died."""
        with self.lock:
            if self.proc and self.proc.poll() is None:
                return  # still alive
            if self.logger:
                self.logger.warning("[FFmpegVideoWriter] Restarting ffmpeg encoder due to crash/stall...")
            try:
                self._start_ffmpeg_with_fallback()
            except Exception as e:
                if self.logger:
                    self.logger.error(f"[FFmpegVideoWriter] Restart failed: {e}")

    # -------------------------------------------------------------------
    def write(self, frame):
        """Enqueue frame for non-blocking write."""
        if self.proc is None or self.proc.poll() is not None:
            self._restart_ffmpeg()

        h, w = frame.shape[:2]
        exp_w, exp_h = self.frame_size
        if (w, h) != (exp_w, exp_h):
            frame = cv2.resize(frame, (exp_w, exp_h))

        try:
            self.queue.put_nowait(frame.copy())
        except Full:
            if self.logger:
                self.logger.warning("[FFmpegVideoWriter] Frame queue full, dropping frame")

    # -------------------------------------------------------------------
    def _writer_loop(self):
        """Background writer thread that pushes frames to ffmpeg."""
        while not self.stop_event.is_set():
            try:
                frame = self.queue.get(timeout=1)
            except Empty:
                continue

            if frame is None:
                break

            try:
                if not self.proc or self.proc.poll() is not None:
                    self._restart_ffmpeg()
                self.proc.stdin.write(frame.tobytes())
            except BrokenPipeError:
                if self.logger:
                    self.logger.error("[FFmpegVideoWriter] Broken pipe detected, restarting encoder.")
                self._restart_ffmpeg()
            except Exception as e:
                if self.logger:
                    self.logger.error(f"[FFmpegVideoWriter] Write error: {e}")
                self._restart_ffmpeg()

    # -------------------------------------------------------------------
    def release(self):
        """Stop the writer thread and close ffmpeg cleanly."""
        self.stop_event.set()
        try:
            self.queue.put_nowait(None)
        except Full:
            pass

        if self.thread.is_alive():
            self.thread.join(timeout=3)

        if self.proc:
            try:
                if self.proc.stdin:
                    self.proc.stdin.close()
                self.proc.wait(timeout=5)
                if self.proc.stderr:
                    err = self.proc.stderr.read().decode(errors="ignore")
                    if err.strip() and self.logger:
                        self.logger.debug(f"[FFmpegVideoWriter] FFmpeg final log:\n{err}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"[FFmpegVideoWriter] Error during release: {e}")
            finally:
                self.proc = None


def get_h264_writer(video_path, fps, frame_size, force_sw=False, logger=None):
    writer = FFmpegVideoWriter(video_path, fps, frame_size, force_sw=force_sw, logger=logger)
    if writer.hw_enabled:
        return writer, "ffmpeg-hw"
    else:
        return writer, "ffmpeg-sw"


def start_video_recording(camera, video_path, file_name, resolution=(1640, 1232), bitrate=4000000):
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
    logger.info(f"video_config {video_config}, resolution: {resolution}, bitrate: {bitrate}")
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


# Changed this with New_7, from libx264 to h264_v4l2m2m
def process_video(video_path, input_file, output_file, frame_rate=None, resolution=None, mode="remux"):
    source = os.path.join(video_path, input_file)
    dest = os.path.join(video_path, output_file)

    if not os.path.exists(source) or os.path.getsize(source) <= 5000:
        logger.info(f"Warning: {input_file} is empty or does not exist. Skipping conversion.")
        return

    if mode == "remux":
        #  Fastest, no re-encode
        command = [
            "ffmpeg", "-fflags", "+genpts", "-i", source,
            "-c", "copy",
            "-y", dest
        ]
        resolution = None  # explicitly ignore resolution for remux

    elif mode == "hw":
        #  Hardware encoder (keeps Pi cool)
        command = [
            "ffmpeg", "-i", source,
            "-c:v", "h264_v4l2m2m",
            "-b:v", "4M",  # adjust bitrate
            "-movflags", "+faststart",
            "-y", dest
        ]
        if frame_rate or resolution:
            vf_filters = []
            if resolution:
                vf_filters.append(f"scale={resolution[0]}:{resolution[1]}:in_range=full:out_range=tv")
            if frame_rate:
                vf_filters.append(f"fps={frame_rate}")
            if vf_filters:
                command.extend(["-vf", ",".join(vf_filters)])

    else:
        # Software fallback (not recommended on Pi for high-res)
        command = [
            "ffmpeg", "-i", source,
            "-vcodec", "libx264",
            "-crf", "23",
            "-preset", "fast",
            "-movflags", "+faststart",
        ]
        vf_filters = [f"scale={resolution[0]}:{resolution[1]}:in_range=full:out_range=tv"]
        if frame_rate:
            vf_filters.append(f"fps={frame_rate}")
        command.extend(["-vf", ",".join(vf_filters)])
        command.extend(["-pix_fmt", "yuv420p"])
        command.extend(["-y", dest])

    try:
        subprocess.run(command, check=True)
        logger.debug(f"Video processed: {output_file} (mode={mode})")
    except Exception as e:
        logger.error(f"Failed to process video {input_file}: {e}")
        return


def setup_gpio():
    level = 0  # Initial level LOW
    try:
        # seems like initial value off corresponds to 1
        h = lgpio.gpiochip_open(0)  # Open GPIO chip 0
        lgpio.gpio_claim_output(h, 26, level)  # Signal pin
        lgpio.gpio_claim_output(h, 20, level)  # Lamp1
        lgpio.gpio_claim_output(h, 21, level)  # Lamp2
        logger.info("GPIO setup successful: Signal=26, Lamp1=20, Lamp2=21")
        return h, 26, 20, 21  # Return the GPIO handle and pin numbers
    except Exception as e:
        logger.error(f"Error in setup_gpio: {e}")
        raise


def trigger_relay(handle, pin, state, duration=None):
    """Control a relay by turning it ON or OFF, optionally with a delay."""
    try:
        if state == "on":
            lgpio.gpio_write(handle, pin, 1)  # HIGH = ON
        else:
            lgpio.gpio_write(handle, pin, 0)  # LOW = OFF

        logger.info(f"Triggering relay on pin {pin} to state {state}")
        if duration:
            time.sleep(int(duration))
            lgpio.gpio_write(handle, pin, 0)  # Turn off after the duration
            logger.debug(f"Pin {pin} turned OFF after {duration} seconds")
    except Exception as e:
        logger.error(f"Failed to trigger relay on pin {pin}: {e}")


def cleanup_gpio(handle):
    global logger
    try:
        lgpio.gpiochip_close(handle)  # Close GPIO chip 0
        logger.debug("GPIO resources cleaned up successfully.")
    except Exception as e:
        logger.error(f"Error while cleaning up GPIO: {e}")


def start_sequence(camera, first_start_time, num_starts, dur_between_starts, photo_path):
    """
    Run one or more start sequences.
    - first_start_time: datetime of the FIRST start
    - num_starts: how many start sequences (1–3 typically)
    - dur_between_starts: minutes between starts
    """
    gpio_handle, SIGNAL, LAMP1, LAMP2 = setup_gpio()

    for i in range(num_starts):
        logger.info(f"Start_sequence. Start of iteration {i+1}")

        start_time = first_start_time + dt.timedelta(minutes=i * dur_between_starts)
        logger.info(f"Start_sequence, start_time : {start_time}")

        # Define time intervals for each relay trigger
        # Define schedule of events
        time_intervals = [
            (start_time - dt.timedelta(minutes=5), lambda: trigger_relay(gpio_handle, LAMP1, "on"), "5_min Lamp1 ON -- Flag P UP"),
            (start_time - dt.timedelta(minutes=5) + dt.timedelta(seconds=1), lambda: trigger_relay(gpio_handle, SIGNAL, "on", 2), "5_min Warning Signal"),
            (start_time - dt.timedelta(minutes=4, seconds=2), lambda: trigger_relay(gpio_handle, LAMP2, "on"), "4_min Lamp2 ON"),
            (start_time - dt.timedelta(minutes=4), lambda: trigger_relay(gpio_handle, SIGNAL, "on", 2), "4_min Preparation Signal"),
            (start_time - dt.timedelta(minutes=1, seconds=2), lambda: trigger_relay(gpio_handle, LAMP2, "off"), "1_min Lamp2 OFF -- Flag P DOWN"),
            (start_time - dt.timedelta(minutes=1), lambda: trigger_relay(gpio_handle, SIGNAL, "on", 2), "1_min Signal"),
            (start_time - dt.timedelta(seconds=2), lambda: trigger_relay(gpio_handle, LAMP1, "off"), "Lamp1 OFF at Start"),
            (start_time, lambda: trigger_relay(gpio_handle, SIGNAL, "on", 1), "Start Signal"),
        ]

        last_triggered = set()
        timeout = start_time + dt.timedelta(seconds=30)  # fail-safe

        while True:
            now = dt.datetime.now()

            if now > timeout:
                logger.warning(f"Start_sequence: Timeout reached for iteration {i+1}")
                break

            all_done = all((t, l) in last_triggered for t, _, l in time_intervals)
            if all_done:
                logger.info(f"Start_sequence: All events triggered for iteration {i+1}")
                break

            for event_time, action, label in time_intervals:
                if abs((now - event_time).total_seconds()) <= 1 and (event_time, label) not in last_triggered:
                    logger.info(f"Triggering: {label} at {event_time}")
                    action()
                    if any(k in label for k in ["5_min", "4_min", "1_min", "Start"]):
                        trigger_label = label.split()[0]  # "5_min", "4_min", etc.
                        image_name = f"{i+1}a_start_{trigger_label}.jpg"
                        capture_picture(camera, photo_path, image_name)
                        time.sleep(0.1)
                    last_triggered.add((event_time, label))

            time.sleep(0.1)
        logger.info(f"Start_sequence, End of iteration: {i+1}")
    cleanup_gpio(gpio_handle)  # Clean up GPIO after each iteration


def clean_exit(camera=None, video_writer=None):
    """Release camera, video writer, and log clean shutdown."""
    logger.info("Clean exit initiated")

    # Stop detection-driven video
    if video_writer is not None:
        try:
            video_writer.release()
            logger.info("Video1 writer released, file finalized.")
        except Exception as e:
            logger.error(f"Error releasing video_writer: {e}")

    # Stop continuous recording (Video0)
    if camera is not None:
        try:
            stop_video_recording(camera)
            camera.close()
            logger.info("Camera stopped and closed.")
        except Exception as e:
            logger.error(f"Error stopping/closing camera: {e}")

    logger.info("Exiting now.")