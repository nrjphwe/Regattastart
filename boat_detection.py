#!/usr/bin/python3
import cv2
import numpy as np

# Load the pre-trained object detection model
# YOLO (You Only Look Once) 
net = cv2.dnn.readNet('/../darknet/yolov3.weights', '/../darknet/cfg/yolov3.cfg')

# Load COCO names (class labels)
with open('coco.names', 'r') as f:
    classes = f.read().strip().split('\n')

# Load the configuration and weights for YOLO
layer_names = net.getUnconnectedOutLayersNames()

# Initialize the camera
cap = cv2.VideoCapture(0)  # 0 for default camera

while True:
    ret, frame = cap.read()
    # ret is a boolean indicating whether the frame was successfully 
    # captured and frame is the captured frame

    # Perform object detection, preprocess the frame for object 
    # detection using YOLO. The frame is converted into a blob, and
    # the YOLO model is fed with this blob to obtain the detection results.
    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(layer_names)

    # Process the detection results
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            
            if confidence > 0.5 and classes[class_id] == 'boat':
                # Implement your logic to start/stop recording here
                print("Boat detected!")
    # Display the frame with the detection results.
    cv2.imshow('Boat Detection', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
# After loop, the script release camera and closes the OpenCV windows
cap.release()
cv2.destroyAllWindows()
