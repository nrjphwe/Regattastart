#!/usr/bin/python3 -u
# after git pull, do: sudo cp regattastart6.py /usr/lib/cgi-bin/
import os
import sys
import cgitb
import time
from datetime import datetime
import datetime as dt
import logging
import logging.config
import json

import subprocess
import RPi.GPIO as GPIO
from picamera import PiCamera, Color

# parameter data
signal_dur = 0.3 # 0.3 sec
log_path = '/usr/lib/cgi-bin/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
# GPIO
## below changed 2024-05-02
ON = GPIO.LOW
OFF = GPIO.HIGH
signal = 26
lamp1 = 20
lamp2 = 21

def setup_logging():
    global logger  # Make logger variable global
    logging.config.fileConfig('/usr/lib/cgi-bin/logging.conf')
    logger = logging.getLogger('Start')
    logger.info("Start logging regattastart6")
    return logger

def setup_camera():
    try:
        camera = PiCamera()
        camera.resolution = (1296, 730)
        camera.framerate = 5
        camera.annotate_background = Color('black')
        camera.annotate_foreground = Color('white')
        camera.rotation = (180) # Depends on how camera is mounted
        return camera  # Add this line to return the camera object
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
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
        logger.info ("  Line 78:    Trigger signal %s sec, then wait for 1 - %s sec", signal_dur, signal_dur)
    elif port == 'Lamp1_on':
        GPIO.output(lamp1, ON)
        logger.info ('  Line 81 Lamp1_on')
    elif port == 'Lamp2_on':
        GPIO.output(lamp2, ON)
        logger.info ('  Line 84 Lamp2_on')
    elif port == 'Lamp1_off':
        GPIO.output(lamp1, OFF)
        logger.info ('  Line 87 Lamp1_off')
    elif port == 'Lamp2_off':
        GPIO.output(lamp2, OFF)
        logger.info ('  Line 90 Lamp2_off')

def capture_picture(camera, photo_path, file_name):
    camera.capture(os.path.join(photo_path, file_name), use_video_port=True)
    logger.info ("  Line 94:     Capture picture = %s ", file_name)

def start_video_recording(camera, video_path, file_name):
    if camera.recording:
        camera.stop_recording()
    camera.start_recording(os.path.join(video_path, file_name))
    logger.info ("  Line 100: Started recording of %s ", file_name)

def stop_video_recording(camera):
    camera.stop_recording()
    logger.info (" 104 video recording stopped")

def annotate_video_duration(camera, start_time_sec):
    time_now = dt.datetime.now()
    seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
    elapsed_time = seconds_since_midnight - start_time_sec #elapsed since last star until now)
    camera.annotate_text = f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Seconds since last start: {elapsed_time}"

def convert_video_to_mp4(video_path, source_file, destination_file):
    convert_video_str = "MP4Box -add {} -new {}".format(os.path.join(video_path,source_file), os.path.join(video_path,destination_file))
    subprocess.run(convert_video_str, shell=True)
    logger.info ("  Line 115 Video recording %s converted ", destination_file)

def start_sequence(camera, signal, start_time_sec, num_starts, dur_between_starts, photo_path):
    for i in range(num_starts):
        logger.info(f"  Line 119: Start_sequence. Start of iteration {i}")
        # Adjust the start_time_sec for the second iteration
        if i == 1:
            start_time_sec += dur_between_starts * 60  # Add 5 or 10 minutes for the second iteration
            logger.info(f"  Line 123: Start_sequence, Next start_time_sec: {start_time_sec}")

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
                        logger.info(f"  Line 155: Start_sequence, Triggering event at seconds_now: {seconds_now}")
                        if action:
                            action()
                        picture_name = f"{i + 1}a_start_{log_message[:5]}.jpg"
                        capture_picture(camera, photo_path, picture_name)
                        logger.info(f"   Line 160: Start_sequence, log_message: {log_message}")
                        logger.info(f"   Line 161: Start_sequence, seconds_since_midnight: {seconds_since_midnight}, start_time_sec: {start_time_sec}")
                        # Record that the event has been triggered for this time interval
                        last_triggered_events[(seconds, log_message)] = True
        logger.info(f"   Line 164:  Start_sequence, End of iteration: {i}")

def finish_recording(camera, video_path, video_delay, num_video, video_dur, start_time_sec):
    # Wait for finish, when the next video will start (delay)
    time.sleep((video_delay - 2) * 60)  # Convert delay (minus 2 minutes after start) to seconds 

    # Result video, chopped into numeral videos with duration at "video_dur"
    stop = num_video + 1
    for i in range(1, stop):
        start_video_recording(camera, video_path, f"video{i}.h264")
        # Video running, duration at "video_dur"
        t2 = dt.datetime.now()
        start_time = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(seconds=start_time_sec)

        while (dt.datetime.now() - t2).seconds < (60 * video_dur):
            annotate_video_duration(camera, start_time_sec)
            #camera.annotate_text = f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Seconds since first start: {elapsed_time.seconds}"
            camera.wait_recording(0) # was 0.5

        stop_video_recording(camera)
        convert_video_to_mp4(video_path, f"video{i}.h264", f"video{i}.mp4")
    logger.info(" Line 185 This was the last video =====")

def main():
    logger = setup_logging()  # Initialize the logger
    camera = None # Initialize the camera variable
    signal = None # Initialize the signal relay/variable
    video_recording_started = False

    # Check if a command-line argument (JSON data) is provided
    if len(sys.argv) < 2:
        print("  Line : 1956 No JSON data provided as a command-line argument.")
        sys.exit(1)

    try:
        form_data = json.loads(sys.argv[1])
        #logger.info("form_data: %s", form_data)
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
        remove_picture_files(photo_path, ".jpg") # clean up
        logger.info(" Line 216 Weekday=%s, Start_time=%s, video_delay=%s, num_video=%s, video_dur=%s, num_starts=%s",
                    week_day, start_time, video_delay, num_video, video_dur, num_starts)
        
        start_hour, start_minute = start_time.split(':')
        start_time_sec = 60 * (int(start_minute) + 60 * int(start_hour))

        t5min_warning = start_time_sec - 5 * 60 # time when the start-machine should begin to execute.
        wd = dt.datetime.today().strftime("%A")
        
        if wd == week_day:
            # A loop that waits until close to the 5-minute mark, a loop that continuously checks the 
            # condition without blocking the execution completely
            while True:
                now = dt.datetime.now()
                seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
    
                if seconds_since_midnight > t5min_warning - 2:         
                    logger.info(" Line 233: Start of outer loop iteration. seconds_since_midnight=%s", seconds_since_midnight)

                    if num_starts == 1 or num_starts == 2:
                        # Start video recording just before 5 minutes before the first start
                        start_video_recording(camera, video_path, "video0.h264")
                        logger.info(" Line 238: Inner loop, entering the start sequence block.")
                        start_sequence(camera, signal, start_time_sec, num_starts, dur_between_starts,photo_path)
                        if num_starts == 2:
                            start_time_sec = start_time_sec + (dur_between_starts * 60)
                        logger.info(" Line 235: Wait 2 minutes then stop video recording")
                        t0 = dt.datetime.now()
                        logger.info(" Line 244: start_time_sec= %s, t0= %s",start_time_sec, t0)  #test
                        while (dt.datetime.now() - t0).seconds < (119):
                            now = dt.datetime.now()
                            seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
                            #logger.info("Inside inner loop. seconds_since_midnight=%s", seconds_since_midnight)
                            annotate_video_duration(camera, start_time_sec)
                            camera.wait_recording(0)
                    
                        stop_video_recording(camera)
                        convert_video_to_mp4(video_path, "video0.h264", "video0.mp4")
                    # Exit the loop after the condition is met
                    break
                
        logger.info("Line 257 Finish recording outside inner loop. start_time_sec=%s", start_time_sec)
        finish_recording(camera, video_path, video_delay, num_video, video_dur, start_time_sec)

    except json.JSONDecodeError as e:
        logger.info ("Failed to parse JSON: %", str(e))
        sys.exit(1)
    finally:
        logger.info(" Line 264: This is finally section")
        if camera is not None:
            camera.close()  # Release the camera resources
        if signal is not None:
            GPIO.output(signal, OFF)  # Turn off the signal output
            GPIO.output(lamp1, OFF)  # Turn off the signal output
            GPIO.output(lamp2, OFF)  # Turn off the signal output
        GPIO.cleanup()
        
if __name__ == "__main__":
    #logging.basicConfig(level=logging.WARNING)  # Set log level to WARNING
    main()