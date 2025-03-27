#!/usr/bin/python3 -u
# after git pull, do: sudo cp regattastart6.py /usr/lib/cgi-bin/
import os
import sys
# import cgitb; cgitb.enable()
import time
from datetime import datetime
import datetime as dt
import logging
import logging.config
import json

import subprocess
import cv2
from picamera2 import Picamera2, MappedArray
from picamera2.encoders import H264Encoder
import RPi.GPIO as GPIO

# parameter data
signal_dur = 0.9  # 0.3 sec
log_path = '/usr/lib/cgi-bin/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
# GPIO
ON = GPIO.LOW
OFF = GPIO.HIGH
signal = 26
lamp1 = 20
lamp2 = 21


def setup_logging():
    global logger  # Make logger variable global
    logging.config.fileConfig('/usr/lib/cgi-bin/logging.conf')
    logger = logging.getLogger('Start')
    logger.info("  Line  34: Start logging regattastart6")
    return logger


def setup_camera():
    try:
        camera = Picamera2()
        camera.resolution = (1296, 730)
        camera.framerate = 5
        # camera.annotate_background = Color('black')
        # camera.annotate_foreground = Color('white')
        camera.rotation = (180)  # Depends on how camera is mounted
        return camera  # Add this line to return the camera object
    except Exception as e:
        logger.error(f"  Line  47: Failed to initialize camera: {e}")
        return None


def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(True)
    GPIO.setup(signal, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(lamp1, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(lamp2, GPIO.OUT, initial=GPIO.HIGH)
    return signal, lamp1, lamp2


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


def trigger_relay(port):
    if port == 'Signal':
        GPIO.output(signal, ON)
        time.sleep(signal_dur)
        GPIO.output(signal, OFF)
        time.sleep(1 - signal_dur)
        logger.info(f"Trigger signal {signal_dur} sec, then wait for 1 - {signal_dur} sec")
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
    #cam.pre_callback = apply_timestamp
    encoder = H264Encoder(bitrate=bitrate)
    logger.info(f"Encoder {encoder} with bitrate {bitrate}")
    cam.start_recording(encoder, output_file)
    logger.info(f"Started recording video: {output_file}")

"""
def start_video_recording(camera, video_path, file_name):
    if camera.recording:
        camera.stop_recording()
    camera.start_recording(os.path.join(video_path, file_name))
    logger.info(f'Started recording of {file_name}')
"""


def stop_video_recording(cam):
    cam.stop_recording()
    cam.stop()  # Fully stop the camera
    cam.close()  # Release camera resources
    logger.info("Recording stopped and camera fully released.")


def annotate_video_duration(camera, start_time_sec):
    time_now = dt.datetime.now()
    seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
    elapsed_time = seconds_since_midnight - start_time_sec  # elapsed since last star until now)
    camera.annotate_text = f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Seconds since last start: {elapsed_time}"


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


def start_sequence(camera, signal, start_time_sec, num_starts, dur_between_starts, photo_path):
    for i in range(num_starts):
        logger.info(f"  Line 119: Start_sequence. Start of iteration {i}")
        # Adjust the start_time_sec for the second iteration
        if i == 1:
            start_time_sec += dur_between_starts * 60  # Add 5 or 10 minutes for the second iteration
            logger.info(f"Start_sequence, Next start_time_sec: {start_time_sec}")

        # Define time intervals for each relay trigger
        time_intervals = [
            (start_time_sec - 5 * 60, lambda: trigger_relay('Lamp1_on'), "5_min Lamp-1 On -- Up with Flag O"),
            (start_time_sec - 5 * 60 + 1, lambda: trigger_relay('Signal'), "5_min Warning signal"),
            (start_time_sec - 4 * 60 - 2, lambda: trigger_relay('Lamp2_on'), "4_min Lamp-2 On"),
            (start_time_sec - 4 * 60, lambda: trigger_relay('Signal'), "4_min Warning signal"),
            (start_time_sec - 1 * 60 - 2, lambda: trigger_relay('Lamp2_off'), "1_min Lamp-2 off -- Flag P down"),
            (start_time_sec - 1 * 60, lambda: trigger_relay('Signal'), "1_min  Warning signal"),
            (start_time_sec - 0 * 60 - 2, lambda: trigger_relay('Lamp1_off'), "Lamp1-off at start"),
            (start_time_sec - 0 * 60, lambda: trigger_relay('Signal'), "Start signal"),
        ]

        last_triggered_events = {}

        while True:
            time_now = dt.datetime.now()
            seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

            if seconds_since_midnight >= start_time_sec:
                break  # Exit the loop if the condition is met

            for seconds, action, log_message in time_intervals:
                camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                time_now = dt.datetime.now()
                seconds_now = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

                # Check if the event should be triggered based on the current time
                if seconds_now == seconds:
                    # Check if the event has already been triggered for this time interval
                    if (seconds, log_message) not in last_triggered_events:
                        logger.info(f"Start_sequence, Triggering event at seconds_now: {seconds_now}")
                        if action:
                            action()
                        picture_name = f"{i + 1}a_start_{log_message[:5]}.jpg"
                        capture_picture(camera, photo_path, picture_name)
                        logger.info(f"Start_sequence, log_message: {log_message}")
                        logger.info(f"Start_sequence, seconds_since_midnight: {seconds_since_midnight}, start_time_sec: {start_time_sec}")
                        # Record that the event has been triggered for this time interval
                        logger.info(f'last_triggered_events = {last_triggered_events}')
                    last_triggered_events[(seconds, log_message)] = True
        logger.info(f"  Line 164:  Start_sequence, End of iteration: {i}")


def finish_recording(camera, video_path, video_delay, num_video, video_dur, start_time_sec):
    # Wait for finish, when the next video will start (delay)
    time.sleep((video_delay - 2) * 60)  # Convert delay (minus 2 minutes after start) to seconds

    # Result video, chopped into numeral videos with each duration at "video_dur"
    stop = num_video + 1
    for i in range(1, stop):
        logger.info(f'Start video recording for: video{i}.avi')
        start_video_recording(camera, video_path, f"video{i}.avi")
        logger.info(f'Recording started for: video{i}.h264')
        # Video running, duration at "video_dur"
        t2 = dt.datetime.now()
        logger.info(f"Start of video{i} recording")
        while (dt.datetime.now() - t2).seconds < (60 * video_dur):
            # annotate_video_duration(camera, start_time_sec)
            # camera.annotate_text = f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Seconds since first start: {elapsed_time.seconds}"
            camera.wait_recording(0.5)  # was 0.5

        stop_video_recording(camera)
    logger.info("This was the last recorded video =====")


def main():
    logger = setup_logging()  # Initialize the logger
    camera = None  # Initialize the camera variable
    signal = None  # Initialize the signal relay/variable

    try:
        form_data = json.loads(sys.argv[1])
        # logger.info("form_data: %s", form_data)
        start_time = str(form_data["start_time"]) # this is the first start
        week_day = str(form_data["day"])
        video_delay = int(form_data["video_delay"])
        video_dur = int(form_data["video_dur"])
        num_video = int(form_data["num_video"])
        num_starts = int(form_data["num_starts"])
        dur_between_starts = int(form_data["dur_between_starts"])

        camera = setup_camera()
        if camera is None:
            logger.error("Line 211 Camera initialization failed. Exiting.")
            sys.exit(1)
        signal, lamp1, lamp2 = setup_gpio()
        remove_video_files(photo_path, "video")  # clean up 
        remove_picture_files(photo_path, ".jpg")  # clean up
        logger.info(" Line 216 Weekday=%s, Start_time=%s, video_delay=%s, num_video=%s, video_dur=%s, num_starts=%s",
                    week_day, start_time, video_delay, num_video, video_dur, num_starts)

        start_hour, start_minute = start_time.split(':')
        start_time_sec = 60 * (int(start_minute) + 60 * int(start_hour))

        t5min_warning = start_time_sec - 5 * 60  # time when the start-machine should begin to execute.
        wd = dt.datetime.today().strftime("%A")

        if wd == week_day:
            # A loop that waits until close to the 5-minute mark, a loop that continuously checks the 
            # condition without blocking the execution completely
            while True:
                now = dt.datetime.now()
                seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second

                if seconds_since_midnight > t5min_warning - 2:
                    logger.info(f'Start of outer loop iteration. seconds_since_midnight= {seconds_since_midnight}')

                    if num_starts == 1 or num_starts == 2:
                        # Start video recording just before 5 minutes before the first start
                        logger.debug("Start of video0 recording")
                        start_video_recording(camera, video_path, "video0.avi")
                        logger.info("Inner loop, entering the start sequence block.")
                        start_sequence(camera, signal, start_time_sec, num_starts, dur_between_starts, photo_path)
                        if num_starts == 2:
                            start_time_sec = start_time_sec + (dur_between_starts * 60)
                        logger.debug("Wait 2 minutes then stop video recording")
                        t0 = dt.datetime.now()
                        logger.debug(f"t0 = {t0}, dt.datetime.now(): {dt.datetime.now()}")
                        logger.debug("(dt.datetime.now() - t0).seconds: %d", (dt.datetime.now() - t0).seconds)
                        logger.info("start_time_sec= %s, t0= %s", start_time_sec, t0)  # test
                        while (dt.datetime.now() - t0).seconds < (119):
                            now = dt.datetime.now()
                            time.sleep(0.2)  # Small delay to reduce CPU usage
                        stop_video_recording(camera)
                        process_video(video_path, "video0.avi", "video0.mp4", frame_rate=30)
                        logger.debug("Video0 converted to mp4")
                    break  # Exit the loop after the condition is met
                time.sleep(1)  # Introduce a delay of 1 seconds

        logger.info(f'Start Finish recording outside inner loop. start_time_sec: {start_time_sec}')
        finish_recording(camera, video_path, video_delay, num_video, video_dur, start_time_sec)

        # convert all the videos to mp4
        stop = num_video + 1
        for i in range(1, stop):
            process_video(video_path, f"video{i}.avi", f"video{i}.mp4", frame_rate=30)
        logger.info("This was the last converted video =====")

    finally:
        logger.info("This is finally section")
        if camera is not None:
            camera.close()  # Release the camera resources
        if signal is not None:
            GPIO.output(signal, OFF)  # Turn off the signal output
            GPIO.output(lamp1, OFF)  # Turn off the signal output
            GPIO.output(lamp2, OFF)  # Turn off the signal output
        GPIO.cleanup()


if __name__ == "__main__":
    # logger = setup_logging()  # Initialize logger before using it
    try:
        main()
    except Exception as e:
        logger.error(f"An unhandled exception occurred: {e}", exc_info=True)
    finally:
        logger.info("Exiting program")
