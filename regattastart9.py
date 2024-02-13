#!/usr/bin/python3 -u
# after git pull, do: sudo cp regattastart9.py /usr/lib/cgi-bin/
import os
import errno
import select
import sys
sys.path.append('/home/pi/opencv/build/lib/python3')
import threading
import time
from datetime import datetime
import datetime as dt
import logging
import logging.config
import json
import tempfile # to check the php temp file

# image recognition
import cv2
import numpy as np

import subprocess
import RPi.GPIO as GPIO
from gpiozero import OutputDevice, Device
from picamera import PiCamera, Color

# parameter data
signal_dur = 0.3 # 0.3 sec
log_path = '/usr/lib/cgi-bin/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
ON = True
OFF = False

# Global variable
recording_stopped = False

def setup_logging():
    global logger  # Make logger variable global
    logging.config.fileConfig('/usr/lib/cgi-bin/logging.conf')
    logger = logging.getLogger('Start')
    logger.info("Start logging")
    return logger

def setup_camera():
    try:
        camera = PiCamera()
        #camera.resolution = (1296, 730)
        camera.resolution = (720, 480)
        camera.framerate = 5
        camera.annotate_background = Color('black')
        camera.annotate_foreground = Color('white')
        camera.rotation = (180) # Depends on how camera is mounted
        return camera  # Add this line to return the camera object
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        return None

def setup_gpio():
    try:
        # Set the pin factory to use BCM numbering mode
        Device._default_pin_factory()
        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BCM)
        signal_pin = 26
        lamp1_pin = 20
        lamp2_pin = 21
        signal = OutputDevice(signal_pin)
        lamp1 = OutputDevice(lamp1_pin)
        lamp2 = OutputDevice(lamp2_pin)
        return signal, lamp1, lamp2
    except Exception as e:
        logger.error(f"Failed to initialize GPIO: {e}")
        return None

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

def trigger_warning_signal(signal):
    signal.on()
    time.sleep(signal_dur)
    signal.off()
    time.sleep(1 - signal_dur)
    logger.info ("     Trigger signal %s sec, then wait for 1 - %s sec", signal_dur, signal_dur)

def capture_picture(camera, photo_path, file_name):
    camera.capture(os.path.join(photo_path, file_name), use_video_port=True)
    logger.info ("     Capture picture = %s ", file_name)

def start_video_recording(camera, video_path, file_name):
    if camera.recording:
        camera.stop_recording()
    camera.start_recording(os.path.join(video_path, file_name))
    logger.info (" Started recording of %s ", file_name)

def stop_video_recording(camera):
    camera.stop_recording()
    logger.info (" video recording stopped")

def annotate_video_duration(camera, start_time_sec):
    time_now = dt.datetime.now()
    seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
    elapsed_time = seconds_since_midnight - start_time_sec #elapsed since last star until now)
    camera.annotate_text = f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Seconds since last start: {elapsed_time}"

def convert_video_to_mp4(video_path, source_file, destination_file):
    #convert_video_str = "MP4Box -add {} -new {}".format(os.path.join(video_path,source_file), os.path.join(video_path,destination_file))
    convert_video_str = "MP4Box -add {} -fps 10 -new {}".format(
        os.path.join(video_path, source_file),
        os.path.join(video_path, destination_file)
    )
    subprocess.run(convert_video_str, shell=True)
    logger.info ("Line 118: Video recording %s converted ", destination_file)

def re_encode_video(video_path, source_file, destination_file):
    re_encode_video_str = "ffmpeg -i -vcodec libx264 -f mp4 {}".format(
        os.path.join(video_path, source_file),
        os.path.join(video_path, destination_file)
    )
    subprocess.run(re_encode_video_str, shell=True)
    logger.info ("Line 131: Video %s re-encoded ", destination_file)

def start_sequence(camera, signal, start_time_sec, num_starts, photo_path):
    for i in range(num_starts):
        logger.info(f"  Line 122: Start_sequence. Start of iteration {i}")
        # Adjust the start_time_sec for the second iteration
        if i == 1:
            start_time_sec += 5 * 60  # Add 5 minutes for the second iteration
            logger.info(f"  Line 126Start_sequence, Next start_time_sec: {start_time_sec}")

        # Define time intervals for each iteration
        time_intervals = [
            (start_time_sec - 5 * 60, lambda: trigger_warning_signal(signal), "5_min Lamp-1 On -- Up with Flag O"),
            (start_time_sec - 4 * 60, lambda: trigger_warning_signal(signal), "4_min Lamp-2 On  --- Up with Flag P"),
            (start_time_sec - 1 * 60, lambda: trigger_warning_signal(signal), "1_min  Lamp-2 Off -- Flag P down"),
            (start_time_sec - 1, lambda: trigger_warning_signal(signal), "Start signal"),
        ]

        while True:
            time_now = dt.datetime.now()
            seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

            if seconds_since_midnight >= start_time_sec:
                break  # Exit the loop if the condition is met

            for seconds, action, log_message in time_intervals:
                camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                time_now = dt.datetime.now()
                seconds_now = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
                # Iterate through time intervals
                if seconds_now == seconds:
                    logger.info(f"  Start_sequence, Triggering event at seconds_now: {seconds_now}")
                    if action:
                        action()
                    picture_name = f"{i + 1}a_start_{log_message[:5]}.jpg"
                    capture_picture(camera, photo_path, picture_name)
                    logger.info(f"     Start_sequence, log_message: {log_message}")
                    logger.info(f"     Start_sequence, seconds_since_midnight: {seconds_since_midnight}, start_time_sec: {start_time_sec}")
        logger.info(f" Line 156: Start_sequence, End of iteration: {i}")

def open_camera():
    """
    Opens the camera and returns the VideoCapture object.
    """
    #cap = cv2.VideoCapture("/home/pi/Regattastart/finish21-6.mp4")
    #cap = cv2.VideoCapture("/home/pi/Regattastart/finish.mp4")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FPS, 5)
    if not cap.isOpened():
        logger.info("Line 164 Cannot open camera")
        cap.release()  # Don't forget to release the camera resources when done
        exit()
    return cap

def cv_annotate_video(frame, start_time_sec):
    time_now = dt.datetime.now()
    seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
    elapsed_time = seconds_since_midnight - start_time_sec #elapsed since last start until now)
    label = str(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')) +  " Seconds since last start: " +  str(elapsed_time)
    org = (30,60)
    #font = cv2.FONT_HERSHEY_SIMPLEX
    #font = ImageFont.truetype("PAPYRUS.ttf", 80) 
    fontFace=cv2.FONT_HERSHEY_DUPLEX
    fontScale = 0.7
    color=(0,0,255) #(B, G, R)
    thickness = 1
    lineType = cv2.LINE_AA
    cv2.putText(frame,label,org,fontFace,fontScale,color,thickness,lineType)

def stop_recording():
    global listening
    global recording_stopped
    recording_stopped = True
    listening = False  # Set flag to False to terminate the loop in listen_for_messages

# Flag to control the loop in listen_for_messages
listening = True

def listen_for_messages(timeout=0.1):
    global listening  # Use global flag
    logger.info(" Line 206: Listen for messages from PHP script via a named pipe")
    pipe_path = '/var/www/html/tmp/stop_recording_pipe'
    logger.info(f"Line 209:, pipepath {pipe_path}")

    try:
        os.unlink(pipe_path)  # Remove existing pipe
    except OSError as e:
        if e.errno != errno.ENOENT:  # Ignore if file doesn't exist
            logger.info(f"Line 215, OS error: {e.errno}")
            raise

    os.mkfifo(pipe_path)  # Create a new named pipe

    with open(pipe_path, 'r') as fifo:
        while True:
            logger.info(f"Line 222, openpipe path: {pipe_path}")
            # Use select to wait for input with a timeout
            rlist, _, _ = select.select([fifo], [], [], timeout)
            if rlist:
                message = fifo.readline().strip()
                if message == 'stop_recording':
                    stop_recording()
                    break  # Exit the loop when stop_recording message is received

            else:
                logger.info(f"Line 232, not rlist {rlist}")
                # Handle timeout (no input received within timeout period)
                # You can perform any necessary actions here

def finish_recording(video_path, num_starts, video_end, start_time, start_time_sec):
    # Open a video capture object (replace 'your_video_file.mp4' with the actual video file or use 0 for webcam)
    #cap = cv2.VideoCapture(os.path.join(video_path, "finish21-6.mp4"))
    cap = open_camera()

    # Load the pre-trained object detection model -- YOLO (You Only Look Once)
    net = cv2.dnn.readNet('/home/pi/darknet/yolov3-tiny.weights', '/home/pi/darknet/cfg/yolov3-tiny.cfg')
    # Load COCO names (class labels)
    with open('/home/pi/darknet/data/coco.names', 'r') as f:
        classes = f.read().strip().split('\n')
    # Load the configuration and weights for YOLO
    layer_names = net.getUnconnectedOutLayersNames()

    # Initialize variables
    #fps = cap.get(cv2.CAP_PROP_FPS)
    fpsw = 50  # number of frames written per second
    today = time.strftime("%Y%m%d")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (width, height)
    # setup cv2 writer 
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # H.264 codec with MP4 container
    #fourcc = 0
    #video_writer = cv2.VideoWriter(video_path + 'video1' + '.mp4', fourcc, fpsw, frame_size)
    video_writer = cv2.VideoWriter(video_path + 'video1' + '.avi', fourcc, fpsw, frame_size)

    number_of_non_detected_frames = 30
    number_of_detected_frames = 3 # Set the number of frames to record after detecting a boat
    start_time = time.time()  # Record the start time of the recording
    iteration = number_of_non_detected_frames
    # Assume no boat is detected initially
    boat_in_current_frame = False

    while True:
        # read frame
        ret, frame = cap.read()
        if frame is None:
            logger.info("Frame is None. Ending loop.")
            break

        # if frame is read correctly ret is True
        if not ret:
            logger.info("End of video stream. Or can't receive frame (stream end?). Exiting ...")
            break

        frame = cv2.flip(frame, flipCode = -1) # camera is upside down"

        # Prepare the input image (frame) for the neural network.
        scalefactor = 0.00392 # A scale factor to normalize the pixel values. This is often set to 1/255.0.
        size = (416, 416) # The size to which the input image is resized. YOLO models are often trained on 416x416 images.
        swapRB = True # This swaps the Red and Blue channels, as OpenCV loads images in BGR format by default, but many pre-trained models expect RGB.
        crop = False # The image is not cropped.
        blob = cv2.dnn.blobFromImage(frame, scalefactor, size, swapRB, crop)
        net.setInput(blob) # Sets the input blob as the input to the neural network
        outs = net.forward(layer_names)

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]

                if confidence > 0.2 and classes[class_id] == 'boat':
                    boat_in_current_frame = True
                    iteration = number_of_non_detected_frames  # Reset the count
                    # Visualize the detected bounding box
                    h, w, _ = frame.shape
                    x, y, w, h = map(int, detection[0:4] * [w, h, w, h])
                    pt1 = (int(x), int(y))
                    pt2 = (int(x + w), int(y + h))
                    cv2.rectangle(frame, pt1, pt2, (0, 255, 0), 2, cv2.LINE_AA)
                    for i in range(number_of_detected_frames):
                        logger.info("Line 306: boat detected.")
                        cv_annotate_video(frame, start_time_sec)
                        video_writer.write(frame)

        # boat_detected == False:
        if boat_in_current_frame == True: # boat was in frame previously
            if iteration  > 0:   # Keep recording for a few frames after no boat is detected
                cv_annotate_video(frame, start_time_sec)
                video_writer.write(frame)
                iteration  -= 1
            else:
                boat_in_current_frame = False

        # Check if the maximum recording duration has been reached
        elapsed_time = time.time() - start_time
        logger.info(f"elapsed time: {elapsed_time}")
        if elapsed_time >= 60 * (video_end + 5 * (num_starts - 1)):
            break

        logger.info(f"Line 325, Recording stopped: {recording_stopped}")
        if recording_stopped == True:
            break

    cap.release()  # Don't forget to release the camera resources when done
    video_writer.release()  # Release the video writer
    logger.info("Line 326, Exited finish_recording module.")

def main():
    logger = setup_logging()  # Initialize the logger
    camera = None # Initialize the camera variable
    signal = None # Initialize the signal relay/variable

    # Check if a command-line argument (JSON data) is provided
    if len(sys.argv) < 2:
        print("No JSON data provided as a command-line argument.")
        sys.exit(1)

    try:
        #logger.info("form_data: %s", form_data)
        form_data = json.loads(sys.argv[1])
        week_day = str(form_data["day"])
        video_end = int(form_data["video_end"])
        num_starts = int(form_data["num_starts"])
        start_time_str = str(form_data["start_time"]) # this is the first start

        # Convert to datetime object
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        # Extract hour and minute
        start_hour = start_time.hour
        start_minute = start_time.minute
        # Calculate start_time_sec
        start_time_sec = 60 * start_minute + 3600 * start_hour
        t5min_warning = start_time_sec - 5 * 60 # time when the start-machine should begin to execute.
        wd = dt.datetime.today().strftime("%A")

        camera = setup_camera()
        if camera is None:
            logger.error("Camera initialization failed. Exiting.")
            sys.exit(1)
        signal, lamp1, lamp2 = setup_gpio()
        remove_video_files(photo_path, "video")  # clean up
        remove_picture_files(photo_path, ".jpg") # clean up
        logger.info("Line 368 Weekday=%s, Start_time=%s, video_end=%s, num_starts=%s",
                    week_day, start_time.strftime("%H:%M"), video_end, num_starts)

        if wd == week_day:
            # A loop that waits until close to the 5-minute mark, a loop that continuously checks the
            # condition without blocking the execution completely
            while True:
                now = dt.datetime.now()
                seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
                if seconds_since_midnight > t5min_warning - 2:
                    logger.info("Line 378 Start of outer loop iteration. seconds_since_midnight=%s", seconds_since_midnight)

                    if num_starts == 1 or num_starts == 2:
                        # Start video recording just before 5 minutes before the first start
                        start_video_recording(camera, video_path, "video0.h264")
                        logger.info("Inner loop, entering the start sequence block.")
                        start_sequence(camera, signal, start_time_sec, num_starts, photo_path)
                        if num_starts == 2:
                            start_time_sec = start_time_sec + (5 * 60)
                        logger.info(" Wait 2 minutes then stop video0 recording")
                        t0 = dt.datetime.now()
                        logger.info(" start_time_sec= %s, t0= %s",start_time_sec, t0)  #test
                        while (dt.datetime.now() - t0).seconds < (119):
                            now = dt.datetime.now()
                            seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
                            annotate_video_duration(camera, start_time_sec)
                            camera.wait_recording(0)
                        stop_video_recording(camera)
                        convert_video_to_mp4(video_path, "video0.h264", "video0.mp4")
                    # Exit the loop after the if condition is met
                    break

        # After finishing the initial recording with PiCamera
        camera.close()
        time.sleep(2)  # Introduce a delay of 2 seconds

    except json.JSONDecodeError as e:
        logger.info ("Line 405, Failed to parse JSON: %", str(e))
        sys.exit(1)
    finally:
        logger.info("Line 408 Finally section, before listen_for_message")
          # Start a thread for listening for messages
        listen_thread = threading.Thread(target=listen_for_messages)
        listen_thread.start()
        logger.info("Line 412, Finally section, before 'Finish recording'. start_time=%s video_end%s", start_time, video_end)
        finish_recording(video_path, num_starts, video_end, start_time, start_time_sec)
        convert_video_to_mp4(video_path, "video1.avi", "video1x.mp4")
        re_encode_video(video_path, "video1x.mp4", "video1.mp4")
        logger.info("Line 415, Finished with finish_recording and recording converted to mp4")
        if camera is not None:
            camera.close()  # Release the camera resources
        if signal is not None:
            signal.off() # Turn off the signal output
            signal.close() # Turn off the signal output
            lamp1.off() # Turn off the lamp1
            lamp1.close() # Turn off the lamp1
            lamp2.off() # Turn off the lamp2
            lamp2.close() # Turn off the lamp2

if __name__ == "__main__":
    #logging.basicConfig(level=logging.WARNING)  # Set log level to WARNING
    main()