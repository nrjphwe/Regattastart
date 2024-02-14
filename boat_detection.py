#!/usr/bin/python3
import sys
sys.path.append('/home/pi/opencv/build/lib/python3')
import time
import datetime
import cv2
import numpy as np

# Load the pre-trained object detection model -- YOLO (You Only Look Once) 
net = cv2.dnn.readNet('../darknet/yolov3-tiny.weights', '../darknet/cfg/yolov3-tiny.cfg')

# Load COCO names (class labels)
with open('../darknet/data/coco.names', 'r') as f:
    classes = f.read().strip().split('\n')

# Load the configuration and weights for YOLO
layer_names = net.getUnconnectedOutLayersNames()

# Flag to indicate if recording is in progress
recording = False
video_writer = None

# Set the timeout duration in seconds
timeout_duration = 0.1  # Adjust as needed

# Variable to store the time when the last boat was detected
last_detection_time = time.time()

#Define the codec
today = time.strftime("%Y-%m-%d")
fourcc = cv2.VideoWriter_fourcc(*'x264')  # H.264 codec with MP4 container
fps_out = 25.0
frame_size = (640, 480)

# Open a video capture object 0 for webcam)
cap = cv2.VideoCapture(0)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) + 0.5)
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) + 0.5)
frame_size = (width, height)
video_writer = cv2.VideoWriter('output'+ today + '.x264', fourcc, fps_out, frame_size)

while True:

    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, flipCode = -1) # camera is upside down"

    # Perform object detection, preprocess the frame for object 
    # detection using YOLO. The frame is converted into a blob, and
    # the YOLO model is fed with this blob to obtain the detection results.
    #blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    today = time.strftime("%Y%m%d-%H%M%S")
    print(today, "Before object detection, line 70")
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
                # Update the time when the last boat was detected
                last_detection_time = time.time()
                today = time.strftime("%Y%m%d-%H%M%S")
                print(today, f"Class: {classes[class_id]}, Confidence: {confidence}")
                # Visualize the detected bounding box
                # Visualize the detected bounding box
                h, w, _ = frame.shape
                x, y, w, h = map(int, detection[0:4] * [w, h, w, h])
                pt1 = (int(x), int(y))
                pt2 = (int(x + w), int(y + h))
                # Modify the original frame

                fontFace=cv2.FONT_HERSHEY_DUPLEX
                cv2.rectangle(frame, pt1, pt2, (0, 255, 0), 2, cv2.LINE_AA)
                
                org_center= (200,300)
                fontScale = 0.5
                color=(0,0,255) #(B, G, R)

                cv2.putText(frame,today,org_center,fontFace,fontScale,color,1,cv2.LINE_AA)


                # header label
                label = "2024-02-14 19:30:30 Seconds since last start: 401"
                org = (20,60)
                #font = cv2.FONT_HERSHEY_SIMPLEX
                #font = ImageFont.truetype("PAPYRUS.ttf", 80) 
                
                fontScale = 0.7
                color=(0,0,255) #(B, G, R)
                thickness = 1
                lineType = cv2.LINE_AA
                cv2.putText(frame,label,org,fontFace,fontScale,color,thickness,lineType)
                video_writer.write(frame)

            else:
                boat_detected = False

    # Display the frame with the detection results.
    cv2.imshow('Boat Detection', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
#  Pressing 'q' will exit the script.
# After loop, the script release camera and closes the OpenCV windows
if video_writer is not None:
    video_writer.release()
cv2.destroyAllWindows()