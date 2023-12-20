#!/usr/bin/python3
import sys
sys.path.append('/home/pi/opencv/build/lib/python3')
import time
import datetime
import picamera
import cv2
import numpy as np

# Load the pre-trained object detection model -- YOLO (You Only Look Once) 
net = cv2.dnn.readNet('../darknet/yolov3-tiny.weights', '../darknet/cfg/yolov3-tiny.cfg')

# Load COCO names (class labels)
with open('../darknet/data/coco.names', 'r') as f:
    classes = f.read().strip().split('\n')

# Load the configuration and weights for YOLO
layer_names = net.getUnconnectedOutLayersNames()

# Initialize the camera
#cap = cv2.VideoCapture('video0.mp4')  # 0 for default camera
cap = cv2.VideoCapture(0)  # 0 for default camera

# Set the frame skipping factor
frame_skip_factor = 2
frame_counter = 0

# Flag to indicate if recording is in progress
recording = False
video_writer = None

#Define the codec
today = time.strftime("%Y%m%d-%H%M%S")
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # H.264 codec with MP4 container
fps_out = 20.0

# Initialize PiCamera outside the loop
with picamera.PiCamera() as camera:
    camera.resolution = (640, 480)
    time.sleep(2)  # Allow the camera to warm up


    while True:
        # Open the PiCamera as a stream and convert it to a numpy array
        with picamera.array.PiRGBArray(camera) as stream:
            camera.capture(stream, format='bgr')

        # Increment the frame counter
        frame_counter += 1

        # Only process frames that meet the skipping criteria
        if frame_counter % frame_skip_factor == 0:
            frame_counter = 0

            # Perform object detection, preprocess the frame for object 
            # detection using YOLO. The frame is converted into a blob, and
            # the YOLO model is fed with this blob to obtain the detection results.
            #blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
            blob = cv2.dnn.blobFromImage(frame, scalefactor=0.00392, size=(416, 416), swapRB=True, crop=False)
            net.setInput(blob)
            outs = net.forward(layer_names)

            # Variable to check if any boat is detected in the current frame
            boat_detected = False

            # Process the detection results
            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]

                
                    if confidence > 0.2 and classes[class_id] == 'boat':
                        print(f"Class: {classes[class_id]}, Confidence: {confidence}")
                        # Visualize the detected bounding box
                        h, w, _ = frame.shape
                        x, y, w, h = map(int, detection[0:4] * [w, h, w, h])
                        #cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

                        # Trigger video recording
                        if not recording:
                            recording = True
                            video_writer = cv2.VideoWriter('output.mp4', fourcc, fps_out, (640, 480))
                            boat_detected = True

            if recording and not boat_detected:
                # Pause video recording
                time.sleep(3)
                recording = False
                if video_writer is not None:
                    video_writer.release()
                    video_writer = None

            elif not recording and boat_detected:
                # Resume video recording
                recording = True
                video_writer = cv2.VideoWriter('output.mp4', fourcc, fps_out, (640, 480))

            if recording:
                video_writer.write(frame)

            # Display the frame with the detection results.
            cv2.imshow('Boat Detection', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
#  Pressing 'q' will exit the script.
# After loop, the script release camera and closes the OpenCV windows
cap.release()

if video_writer is not None:
    video_writer.release()

cv2.destroyAllWindows()