#!/usr/bin/python3
import sys
sys.path.append('/home/pi/opencv/build/lib/python3')
import cv2
print(sys.path)
print(sys.executable)
import numpy as np

def on_key(event):
    if event == ord('q'):
        cv2.destroyAllWindows()

# Load the pre-trained object detection model
# YOLO (You Only Look Once) 
net = cv2.dnn.readNet('../darknet/yolov3-tiny.weights', '../darknet/cfg/yolov3-tiny.cfg')

# Load COCO names (class labels)
with open('../darknet/data/coco.names', 'r') as f:
    classes = f.read().strip().split('\n')

# Load the configuration and weights for YOLO
layer_names = net.getUnconnectedOutLayersNames()

# Initialize the camera
#cap = cv2.VideoCapture('video0.mp4')  # 0 for default camera
cap = cv2.VideoCapture(0)  # 0 for default camera

while True:
    ret, frame = cap.read()
    frame = cv2.resize(frame, (640, 480))
    if not ret or frame is None:
        break

    # ret is a boolean indicating whether the frame was successfully 
    # captured and frame is the captured frame

    # Perform object detection, preprocess the frame for object 
    # detection using YOLO. The frame is converted into a blob, and
    # the YOLO model is fed with this blob to obtain the detection results.
    #blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    blob = cv2.dnn.blobFromImage(frame, scalefactor=0.00392, size=(416, 416), swapRB=True, crop=False)

    net.setInput(blob)
    outs = net.forward(layer_names)

    # Process the detection results
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]

            # Visualize the detected bounding box
            if confidence > 0.5 and classes[class_id] == 'boat':
                print(f"Class: {classes[class_id]}, Confidence: {confidence}")
                h, w, _ = frame.shape
                x, y, w, h = map(int, detection[0:4] * [w, h, w, h])
                #cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

    # Display the frame with the detection results.
    cv2.imshow('Boat Detection', frame)

    # Wait for a key event (100 ms delay)
    key = cv2.waitKey(100)
    if key != -1:
        on_key(key)
    
#  Pressing 'q' will exit the script.
# After loop, the script release camera and closes the OpenCV windows
cap.release()
cv2.destroyAllWindows()