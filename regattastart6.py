#!/usr/bin/python3 -u
# after git pull, do: sudo cp regattastart6.py /usr/lib/cgi-bin/
from common_module import (
    remove_picture_files,
    remove_video_files,
    setup_camera,
    start_video_recording,
    start_sequence,
    stop_video_recording,
    logger,
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


def finish_recording(camera, video_path, video_delay, num_video, video_dur, start_time_sec):
    # Wait for finish, when the next video will start (delay)
    delay_time = int(video_delay - 2) * 60  # Convert delay (minus 2 seconds after start) to seconds
    time.sleep(delay_time)  # Convert delay to seconds
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
                        # time.sleep(0.8)  # Small delay to reduce CPU usage
                        stop_video_recording(camera)
                        process_video(video_path, "video0.avi", "video0.mp4", frame_rate=30)
                        logger.debug("Video0 converted to mp4")
                    break  # Exit the loop after the condition is met
                time.sleep(1)  # Introduce a delay of 1 seconds

        logger.info(f'Start Finish recording outside inner loop. start_time_sec: {start_time_sec}')
        finish_recording(camera, video_path, video_delay, num_video, video_dur, start_time_sec)

    finally:
        logger.info("This is finally section")
        if camera is not None:
            camera.close()  # Release the camera resources
        GPIO.cleanup()


if __name__ == "__main__":
    # logger = setup_logging()  # Initialize logger before using it
    try:
        main()
    except Exception as e:
        logger.error(f"An unhandled exception occurred: {e}", exc_info=True)
    finally:
        logger.info("Exiting program")
