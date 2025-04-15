#!/usr/bin/python3 -u
# after git pull, do: sudo cp regattastart6.py /usr/lib/cgi-bin/
from common_module import (
    setup_camera,
    capture_picture,
    start_video_recording,
    start_sequence,
    stop_video_recording,
    logger,
    setup_gpio,
    trigger_relay,
    process_video,
)
import os
import sys
import time
# import cgitb; cgitb.enable()
from datetime import datetime
import datetime as dt
import json
import subprocess
import cv2
import RPi.GPIO as GPIO  # Import GPIO library
from picamera2 import MappedArray

# parameter data
# signal_dur = 0.9  # 0.9 sec default
log_path = '/usr/lib/cgi-bin/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
#gpio_handle, LAMP1, LAMP2, SIGNAL = setup_gpio()


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


def xx_start_sequence(camera, start_time_sec, num_starts, dur_between_starts, photo_path):
    for i in range(num_starts):
        logger.info(f"Start_sequence. Start of iteration {i}")
        # Adjust the start_time_sec for the second iteration
        if i == 1:
            start_time_sec += dur_between_starts * 60  # Add 5 or 10 minutes for the second iteration
            logger.info(f"Start_sequence, Next start_time_sec: {start_time_sec}")

        # Define time intervals for each relay trigger
        time_intervals = [
            (start_time_sec - 5 * 60, lambda: trigger_relay(gpio_handle, LAMP1, "on"), "5_min Lamp1 ON -- Flag O UP"),
            (start_time_sec - 5 * 60 + 1, lambda: trigger_relay(gpio_handle, SIGNAL, "on", 1), "5_min Warning Signal"),
            (start_time_sec - 4 * 60 - 2, lambda: trigger_relay(gpio_handle, LAMP2, "on"), "4_min Lamp2 ON"),
            (start_time_sec - 4 * 60, lambda: trigger_relay(gpio_handle, SIGNAL, "on", 1), "4_min Warning Signal"),
            (start_time_sec - 1 * 60 - 2, lambda: trigger_relay(gpio_handle, LAMP2, "off"), "1_min Lamp2 OFF -- Flag P DOWN"),
            (start_time_sec - 1 * 60, lambda: trigger_relay(gpio_handle, SIGNAL, "on", 1), "1_min Warning Signal"),
            (start_time_sec - 2, lambda: trigger_relay(gpio_handle, LAMP1, "off"), "Lamp1 OFF at Start"),
            (start_time_sec, lambda: trigger_relay(gpio_handle, SIGNAL, "on", 1), "Start Signal"),
        ]

        last_triggered_events = {}

        while True:
            time_now = dt.datetime.now()
            seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

            if seconds_since_midnight >= start_time_sec:
                break  # Exit the loop if the condition is met

            for event_time, action, log_message in time_intervals:
                time_now = dt.datetime.now()
                seconds_now = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

                if seconds_now == event_time:
                    # Check if the event should be triggered based on the current time
                    if (event_time, log_message) not in last_triggered_events:
                        logger.info(f"Start_sequence: {log_message} at {event_time}")
                        if action:
                            action()
                        picture_name = f"{i + 1}a_start_{log_message[:5]}.jpg"
                        capture_picture(camera, photo_path, picture_name)
                        logger.info(f"Start_sequence, log_message: {log_message}")
                        # logger.info(f'last_triggered_events = {last_triggered_events}')
                    last_triggered_events[(event_time, log_message)] = True
        logger.info(f"Start_sequence, End of iteration: {i}")


def finish_recording(camera, video_path, video_delay, num_video, video_dur, start_time_sec):
    # Wait for finish, when the next video will start (delay)
    time.sleep((video_delay - 2) * 60)  # Convert delay (minus 2 minutes after start) to seconds

    # Result video, chopped into numeral videos with each duration at "video_dur"
    stop = num_video + 1
    for i in range(1, stop):
        logger.info(f'Start video recording for: video{i}.avi')
        video = f'video{i}.avi'
        logger.info(f'video: {video}')
        start_video_recording(camera, video_path, video)
        logger.info(f'Recording started for: {video}')
        # Video running, duration at "video_dur"
        t2 = dt.datetime.now()
        logger.info(f"Start of {video} recording")
        while (dt.datetime.now() - t2).seconds < (60 * video_dur):
            time.sleep(0.5)  # was 0.5

        stop_video_recording(camera)
        process_video(video_path, video, f"video{i}.mp4", frame_rate=30)
    logger.info("This was the last recorded video =====")


def main():
    camera = None  # Initialize the camera variable

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
            logger.error("Camera initialization failed. Exiting.")
            sys.exit(1)
        remove_video_files(photo_path, "video")  # clean up
        remove_picture_files(photo_path, ".jpg")  # clean up
        logger.info("Weekday=%s, Start_time=%s, video_delay=%s, num_video=%s, video_dur=%s, num_starts=%s",
                    week_day, start_time, video_delay, num_video, video_dur, num_starts)

        start_hour, start_minute = start_time.split(':')
        start_time_sec = 60 * (int(start_minute) + 60 * int(start_hour))

        t5min_warning = start_time_sec - 5 * 60  # time when the start-machine should begin to execute.
        wd = dt.datetime.today().strftime("%A")

        if wd == week_day:
            # A loop that waits until close to the 5-minute mark, a loop that 
            # continuously checks the condition without blocking the execution 
            # completely
            while True:
                now = dt.datetime.now()
                seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second

                if seconds_since_midnight > t5min_warning - 4:
                    logger.info(f'Start of outer loop iteration. seconds_since_midnight= {seconds_since_midnight}')

                    if num_starts == 1 or num_starts == 2:
                        # Start video recording just before 5 minutes before the first start
                        logger.debug("Start of video0 recording")
                        start_video_recording(camera, video_path, "video0.avi")
                        logger.info("Inner loop, entering the start sequence block.")
                        start_sequence(camera, start_time_sec, num_starts, dur_between_starts, photo_path)
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
        #stop = num_video + 1
        #for i in range(1, stop):
        #    process_video(video_path, f"video{i}.avi", f"video{i}.mp4", frame_rate=30)
        #logger.info("This was the last converted video =====")

    finally:
        logger.info("This is finally section")
        if camera is not None:
            camera.close()  # Release the camera resources
        """
        if signal is not None:
            GPIO.output(signal, OFF)  # Turn off the signal output
            GPIO.output(lamp1, OFF)  # Turn off the signal output
            GPIO.output(lamp2, OFF)  # Turn off the signal output
        """
        GPIO.cleanup()


if __name__ == "__main__":
    # logger = setup_logging()  # Initialize logger before using it
    try:
        main()
    except Exception as e:
        logger.error(f"An unhandled exception occurred: {e}", exc_info=True)
    finally:
        logger.info("Exiting program")
