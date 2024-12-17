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

# parameter data
signal_dur = 0.9 # 0.9 sec
log_path = '/var/www/html/'
video_path = '/var/www/html/images/'
photo_path = '/var/www/html/images/'
listening = True  # Define the listening variable
recording_stopped = False # Global variable

# setup gpio()
ON = GPIO.LOW
OFF = GPIO.HIGH
signal = 26
lamp1 = 20
lamp2 = 21
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(True)
GPIO.setup(signal, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(lamp1, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(lamp2, GPIO.OUT, initial=GPIO.HIGH)

# reset the contents of the status variable, used for flagging that video1-conversion is complete. 
with open('/var/www/html/status.txt', 'w') as status_file:
    status_file.write("")

def setup_logging():
    global logger  # Make logger variable global
    logging.config.fileConfig('/usr/lib/cgi-bin/logging.conf')
    logger = logging.getLogger('Start')
    logger.info("Start logging regattastart9")
    return logger

def trigger_relay(port):

    if port == 'Signal':
        GPIO.output(signal, ON)
        time.sleep(signal_dur)
        GPIO.output(signal, OFF)
        time.sleep(1 - signal_dur)
        logger.info ("Trigger signal %s sec, then wait for 1 - %s sec", signal_dur, signal_dur)
    elif port == 'Lamp1_on':
        GPIO.output(lamp1, ON)
        logger.info ('Lamp1_on')
    elif port == 'Lamp2_on':
        GPIO.output(lamp2, ON)
        logger.info ('Lamp2_on')
    elif port == 'Lamp1_off':
        GPIO.output(lamp1, OFF)
        logger.info ('Lamp1_off')
    elif port == 'Lamp2_off':
        GPIO.output(lamp2, OFF)
        logger.info ('Lamp2_off')

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

def setup_camera():
    """
    Opens the camera and sets the desired properties for video_recordings
    """
    #cam = cv2.VideoCapture("/home/pi/Regattastart/video3.mp4")
    cam = cv2.VideoCapture(0)  # Use 0 for the default camera
    cam.set(cv2.CAP_PROP_FPS, 5)

    # Select a supported resolution from the listed ones
    resolution = (1024, 768)  # Choose a resolution from the supported list
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

    # Verify the resolution was set correctly
    actual_width = cam.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cam.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if (actual_width, actual_height) != resolution:
        logger.error(f"Failed to set resolution to {resolution}, using {actual_width}x{actual_height} instead")

    if not cam.isOpened():
        logger.error("Cannot open camera")
        cam.release() # Release the camera resources
        exit()
    logger.info("Camera initialized successfully.")
    return cam


def annotate_and_write_frames(cam, video_writer):
    org = (15, 60)  # x = 15 from left, y = 60 from top)
    fontFace = cv2.FONT_HERSHEY_DUPLEX
    fontScale = 0.7
    color = (0, 0, 0)  # (B, G, R)
    thickness = 1
    lineType = cv2.LINE_AA

    while True:
        ret, frame = cam.read()
        if not ret:
            logger.error("Failed to capture frame")
            break

        # Rotate the frame by 180 degrees
        frame = cv2.rotate(frame, cv2.ROTATE_180)

        # Annotate the frame with the current date and time
        current_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        (text_width, text_height), _ = cv2.getTextSize(current_time, fontFace,
                                                       fontScale, thickness)
        # Define background rectangle coordinates
        top_left = (org[0], org[1] - text_height)
        bottom_right = (int(org[0] + text_width), int(org[1] + (text_height/2)))

        # Draw filled rectangle as background for the text
        cv2.rectangle(frame, top_left, bottom_right, (255, 255, 255), 
                      cv2.FILLED)

        # Draw text on top of the background
        cv2.putText(frame, current_time, org, fontFace, fontScale, color, 
                    thickness, lineType)

        video_writer.write(frame)
        return

def capture_picture(cam, photo_path, file_name):
    org = (15,60) # x = 15 from left, y = 60 from top) 
    fontFace=cv2.FONT_HERSHEY_DUPLEX
    fontScale = 0.7
    color=(0,0,0) #(B, G, R)
    thickness = 1
    lineType = cv2.LINE_AA
    # Flush the camera buffer
    for _ in range(8):
        ret, frame = cam.read()
        if not ret:
            logger.error("Failed to capture image")
            return

    # Adding a small delay to stabilize the camera
    cv2.waitKey(100)  # 100 milliseconds delay

    # Capture the frame to be saved
    ret, frame = cam.read()
    if not ret:
        logger.error("Failed to capture image")
        return

    # Rotate the frame by 180 degrees
    frame = cv2.rotate(frame, cv2.ROTATE_180)
    # Annotate the frame with the current date and time
    current_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    (text_width, text_height), _ = cv2.getTextSize(current_time, fontFace,
                                                   fontScale, thickness)
    # Define background rectangle coordinates
    top_left = (org[0], org[1] - text_height) 
    bottom_right = (int(org[0] + text_width), int(org[1] + (text_height/2)))

    # Draw filled rectangle as background for the text
    cv2.rectangle(frame, top_left, bottom_right, (255, 255, 255), cv2.FILLED)

    # Draw text on top of the background
    cv2.putText(frame, current_time, org, fontFace, fontScale, color,
                thickness, lineType)

    cv2.imwrite(os.path.join(photo_path, file_name), frame)
    time.sleep(0.3) # sleep 0.3 sec
    logger.info("Capture picture = %s", file_name)

def start_video_recording(cam, video_path, file_name):
    fpsw = 20  # number of frames written per second
    width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (width, height)
    logger.info(f"Camera frame size: {frame_size}")
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # H.264 codec with MP4 container
    video_writer = cv2.VideoWriter(os.path.join(video_path, file_name), fourcc, fpsw, frame_size)

    logger.info("Started video recording of %s", file_name)
    return video_writer


def stop_video_recording(video_writer):
    video_writer.release()
    logger.info("Stopped video recording")


def video_recording(cam, video_path, file_name, duration=None):
    fpsw = 20  # number of frames written per second
    width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (width, height)
    logger.info(f"Camera frame size: {frame_size}")
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # H.264 codec with MP4 container
    video_writer = cv2.VideoWriter(os.path.join(video_path, file_name + '.avi'), fourcc, fpsw, frame_size)

    logger.info("Started video recording of %s", file_name)
    start_time = time.time()

    while True:
        ret, frame = cam.read()
        if not ret:
            logger.error("Failed to capture frame")
            break

        # Rotate the frame by 180 degrees
        frame = cv2.rotate(frame, cv2.ROTATE_180)
        video_writer.write(frame)

        if duration and (time.time() - start_time) > duration:
            break

    video_writer.release()
    cv2.destroyAllWindows()
    logger.info ("Stopped video recording of %s ", file_name)

def annotate_video_duration(camera, start_time_sec):
    time_now = dt.datetime.now()
    seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
    elapsed_time = seconds_since_midnight - start_time_sec  # elapsed since last star until now)
    camera.annotate_text = f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Seconds since last start: {elapsed_time}"

def convert_video_to_mp4(video_path, source_file, destination_file):
    convert_video_str = "MP4Box -add {} -fps 20 -new {}".format(
        os.path.join(video_path, source_file),
        os.path.join(video_path, destination_file)
    )
    subprocess.run(convert_video_str, shell=True)
    logger.info ("Video recording %s converted ", destination_file)

def re_encode_video(video_path, source_file, destination_file):
    re_encode_video_str = "ffmpeg -loglevel error -i {} -vf fps=20 -vcodec libx264 -f mp4 {}".format(
        os.path.join(video_path, source_file),
        os.path.join(video_path, destination_file)
    )
    subprocess.run(re_encode_video_str, shell=True)
    logger.info ("Video %s re-encoded ", destination_file)

def start_sequence(camera, start_time_sec, num_starts, dur_between_starts, photo_path):
    for i in range(num_starts):
        logger.info(f"Start_sequence. Start of iteration {i}")
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
            (start_time_sec - 0 * 60, lambda: trigger_relay('Signal'), "Start signal")
        ]

        last_triggered_events = {}

        while True:
            time_now = dt.datetime.now()
            seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

            if seconds_since_midnight >= start_time_sec:
                break  # Exit the loop if the condition is met

            for seconds, action, log_message in time_intervals:
                #camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                time_now = dt.datetime.now()
                seconds_now = time_now.hour * 3600 + time_now.minute * 60 + time_now.second

                # Check if the event should be triggered based on the current time
                if seconds_now == seconds:
                    # Check if the event has already been triggered for this time interval
                    if (log_message) not in last_triggered_events:
                        logger.info(f"Start_sequence, seconds: {seconds}, log_message= {log_message}")
                        logger.info(f"Start_sequence, Triggering event at seconds_now: {seconds_now}")
                        if action:
                            action()
                            picture_name = f"{i + 1}a_start_{log_message[:5]}.jpg"
                            capture_picture(camera, photo_path, picture_name)
                            logger.info(f"Start_sequence, seconds={seconds}  log_message: {log_message}")
                        # Record that the event has been triggered for this time interval
                        last_triggered_events[(seconds, log_message)] = True
        logger.info(f"Start_sequence, End of iteration: {i}")


def cv_annotate_video(frame, start_time_sec):
    time_now = dt.datetime.now()
    seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
    # elapsed since last start until now)
    elapsed_time = seconds_since_midnight - start_time_sec
    label = str(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + " Seconds since last start: " + str(elapsed_time)
    org = (15,60) # x = 15 from left, y = 60 from top) 
    fontFace=cv2.FONT_HERSHEY_DUPLEX
    fontScale = 0.7
    color=(0,0,0) #(B, G, R)
    thickness = 1
    lineType = cv2.LINE_AA
    # Get text size
    (text_width, text_height), _ = cv2.getTextSize(label, fontFace, fontScale, thickness)
    # Define background rectangle coordinates
    top_left = (org[0], org[1] - text_height) 
    bottom_right = (int(org[0] + text_width), int(org[1] + (text_height/2)))

    # Draw filled rectangle as background for the text
    cv2.rectangle(frame, top_left, bottom_right, (255, 255, 255), cv2.FILLED)

    # Draw text on top of the background

    cv2.putText(frame, label, org, fontFace, fontScale, color, thickness, lineType)


def stop_recording():
    global listening
    global recording_stopped
    recording_stopped = True
    listening = False  # Set flag to False to terminate the loop in listen_for_messages


def listen_for_messages(timeout=0.1):
    global listening  # Use global flag
    logger.info("listen_for_messages from PHP script via a named pipe")
    pipe_path = '/var/www/html/tmp/stop_recording_pipe'
    logger.info(f"pipepath = {pipe_path}")

    while listening == True:
        try:
            os.unlink(pipe_path)  # Remove existing pipe
        except OSError as e:
            if e.errno != errno.ENOENT:  # Ignore if file doesn't exist
                logger.error(f"331: OS error: {e.errno}")
                raise

        os.mkfifo(pipe_path)  # Create a new named pipe

        with open(pipe_path, 'r') as fifo:
            # Use select to wait for input with a timeout
            rlist, _, _ = select.select([fifo], [], [], timeout)
            if rlist:
                message = fifo.readline().strip()
                if message == 'stop_recording':
                    stop_recording()
                    logger.info("Message == stop_recording")
                    break  # Exit the loop when stop_recording received
        recording_stopped = True
        logger.info("end of with open(pipe_path, r)")
    logger.info("Listening thread terminated")


def finish_recording(cam, video_path, num_starts, video_end, start_time, start_time_sec):
    # Open a video capture object (replace 'your_video_file.mp4' with the 
    # actual video file or use 0 for webcam) 
    # cam = cv2.VideoCapture(os.path.join(video_path, "finish21-6.mp4"))
    global recording_stopped

    # Load the pre-trained object detection model -- YOLO (You Only Look Once)
    net = cv2.dnn.readNet('/home/pi/darknet/yolov3.weights', '/home/pi/darknet/cfg/yolov3.cfg')
    # Load COCO names (class labels)
    with open('/home/pi/darknet/data/coco.names', 'r') as f:
        classes = f.read().strip().split('\n')
    # Load the configuration and weights for YOLO
    layer_names = net.getUnconnectedOutLayersNames()

    # Initialize variables
    # fps = cam.get(cv2.CAP_PROP_FPS)
    fpsw = 50  # number of frames written per second
    today = time.strftime("%Y%m%d")
    width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (width, height)
    # setup cv2 writer 
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # H.264 codec with MP4 container
    video_writer = cv2.VideoWriter(video_path + 'video1' + '.avi', fourcc, fpsw, frame_size)

    number_of_non_detected_frames = 60 # was 30 in May
    number_of_detected_frames = 3 # Set the number of frames to record after detecting a boat
    start_time = time.time()  # Record the start time of the recording
    iteration = number_of_non_detected_frames
    # Assume no boat is detected initially
    boat_in_current_frame = False

    while recording_stopped == False:
        # read frame
        ret, frame = cam.read()
        if frame is None:
            logger.warning("Frame is None. Ending loop.")
            break

        # if frame is read correctly ret is True
        if not ret:
            logger.error("End of video stream. Or can't receive frame (stream end?). Exiting ...")
            break

        frame = cv2.flip(frame, flipCode=-1)  # camera is upside down"

        # Prepare the input image (frame) for the neural network.
        scalefactor = 0.00392  # A scale factor to normalize the pixel values. This is often set to 1/255.0.
        size = (416, 416)  # The size to which the input image is resized. YOLO models are often trained on 416x416 images.
        swapRB = True  # This swaps the Red and Blue channels, as OpenCV loads images in BGR format by default, but many pre-trained models expect RGB.
        crop = False  # The image is not cropped.
        blob = cv2.dnn.blobFromImage(frame, scalefactor, size, swapRB, crop)
        net.setInput(blob)  # Sets the input blob as the input to the neural network
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
                    # time in rectangle
                    # fontFace=cv2.FONT_HERSHEY_PLAIN
                    # detect_time= time.strftime("%H:%M:%S")
                    # posx = int(x) + 5
                    # posy = int(y + h - 5) 
                    # org = (posx,posy)
                    # fontScale = 0.7
                    # color=(0,0,255) #(B, G, R)
                    # cv2.putText(frame,detect_time,org,fontFace,fontScale,color,1,cv2.LINE_AA)

                    for i in range(number_of_detected_frames):
                        # logger.info("331: boat detected.")
                        cv_annotate_video(frame, start_time_sec)
                        video_writer.write(frame)

        if boat_in_current_frame is True:  # boat was in frame previously
            if iteration > 0:   # Keep recording for a few frames after no boat is detected
                cv_annotate_video(frame, start_time_sec)
                video_writer.write(frame)
                iteration -= 1
            else:
                boat_in_current_frame = False

        # Check if the maximum recording duration has been reached
        elapsed_time = time.time() - start_time
        if elapsed_time >= 60 * (video_end + 5 * (num_starts - 1)):
            logger.info(f"elapsed time: {elapsed_time}")
            listening = False
            recording_stopped = True
            break

        if recording_stopped is True:
            logger.info('Video1 recording stopped')
            listening = False
            break

    cam.release()  # Don't forget to release the camera resources when done
    video_writer.release()  # Release the video writer
    logger.info("cam.release and video_writer release, exited the finish_recording module.")


def stop_listen_thread():
    global listening
    listening = False
    # Log a message indicating that the listen_thread has been stopped
    logger.info("462: stop_listening thread  listening set to False")


def main():
    stop_event = threading.Event()
    global listening  # Declare listening as global
    logger = setup_logging()  # Initialize the logger
    cam = setup_camera()
    listening = True  # Initialize the global listening flag
    listen_thread = None  # Initialize listen_thread variable

    # Check if a command-line argument (JSON data) is provided
    if len(sys.argv) < 2:
        print("No JSON data provided as a command-line argument.")
        sys.exit(1)

    try:
        # logger.info("form_data: %s", form_data)
        form_data = json.loads(sys.argv[1])
        week_day = str(form_data["day"])
        video_end = int(form_data["video_end"])
        num_starts = int(form_data["num_starts"])
        # this is the first start
        start_time_str = str(form_data["start_time"])
        dur_between_starts = int(form_data["dur_between_starts"])

        # Convert to datetime object
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        # Extract hour and minute
        start_hour = start_time.hour
        start_minute = start_time.minute
        # Calculate start_time_sec
        start_time_sec = 60 * start_minute + 3600 * start_hour
        # time when the start-machine should begin to execute.
        t5min_warning = start_time_sec - 5 * 60
        wd = dt.datetime.today().strftime("%A")

        remove_video_files(photo_path, "video")  # clean up
        remove_picture_files(photo_path, ".jpg") # clean up
        logger.info("Weekday=%s, Start_time=%s, video_end=%s, num_starts=%s", week_day, start_time.strftime("%H:%M"), video_end, num_starts)

        if wd == week_day:
            # A loop that waits until close to the 5-minute mark, a loop that 
            # continuously checks the condition without blocking the execution 
            # completely
            while True:
                now = dt.datetime.now()
                seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
                if seconds_since_midnight > t5min_warning - 2:
                    logger.info("Start of outer loop iteration. seconds_since_midnight=%s", seconds_since_midnight)
                    if num_starts == 1 or num_starts == 2:
                        logger.info("Start of video recording")
                        video_writer = start_video_recording(cam, video_path, "video0.avi")
                        logger.info("Inner loop, entering the start sequence block.")
                        start_sequence(cam, start_time_sec, num_starts, dur_between_starts, photo_path)
                        if num_starts == 2:
                            start_time_sec = start_time_sec + (dur_between_starts * 60)
                        logger.info("Wait 2 minutes then stop video0 recording")
                        t0 = dt.datetime.now()
                        logger.info("start_time_sec= %s, t0= %s",start_time_sec, t0)  # test
                        while (dt.datetime.now() - t0).seconds < (119):
                            now = dt.datetime.now()
                            seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second
                            annotate_and_write_frames(cam,video_writer)
                        logger.info("after annotate and write text")
                        stop_video_recording(video_writer)
                        convert_video_to_mp4(video_path, "video0.avi", "video0.mp4")
                        logger.info("Video0 recording stopped and converted to mp4")
                    # Exit the loop after the if condition is met
                    break

        time.sleep(2)  # Introduce a delay of 2 seconds

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON: %", str(e))
        sys.exit(1)
    finally:
        logger.info("Finally section, before listen_for_message")
        # Start a thread for listening for messages with a timeout
        listen_thread = threading.Thread(target=listen_for_messages)
        listen_thread.start()

        logger.info("Finally section, before 'Finish recording'. start_time=%s video_end=%s", start_time, video_end)
        time.sleep(2)
        finish_recording(cam, video_path, num_starts, video_end, start_time, start_time_sec)

        # Signal the listening thread to stop
        stop_event.set()
        listen_thread.join(timeout=10)
        if listen_thread.is_alive():
            logger.info("listen_thread is still alive after timeout")
        else:
            logger.info("listen_thread finished")

        time.sleep(2)
        re_encode_video(video_path, "video1.avi", "video1.mp4")

        # After video conversion is complete
        with open('/var/www/html/status.txt', 'w') as status_file:
            status_file.write('complete')
        logger.info("Finished with finish_recording and recording converted to mp4")

        cam.release()  # Release camera resources

        GPIO.cleanup()
        logger.info("After GPIO.cleanup, end of program")


if __name__ == "__main__":
    # logging.basicConfig(level=logging.WARNING)  # Set log level to WARNING
    main()
