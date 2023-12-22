#!/usr/bin/python3
import sys
sys.path.append('/home/pi/opencv/build/lib/python3')
import time
import cv2
import numpy as np

# Load the pre-trained object detection model -- YOLO (You Only Look Once) 
net = cv2.dnn.readNet('../darknet/yolov3-tiny.weights', '../darknet/cfg/yolov3-tiny.cfg')

# Load COCO names (class labels)
with open('../darknet/data/coco.names', 'r') as f:
    classes = f.read().strip().split('\n')

# Load the configuration and weights for YOLO
layer_names = net.getUnconnectedOutLayersNames()

fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # H.264 codec with MP4 container
today = time.strftime("%Y%m%d")

# Open a video capture object (replace 'your_video_file.mp4' with the actual video file or use 0 for webcam)
cap = cv2.VideoCapture(0)
out = cv2.VideoWriter('output'+ today + '.mp4', fourcc, 10, (640, 480))

# Set the frame skipping factor
#frame_skip_factor = 2
frame_counter = 0

#video_writer = cv2.VideoWriter.write(image)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    video_writer = cv2.VideoWriter('output'+ today + '.mp4', fourcc, 10, (640, 480))
   
    # Variable to check if any boat is detected in the current frame
    boat_detected = False

    blob = cv2.dnn.blobFromImage(frame, scalefactor=0.00392, size=(416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    outs = net.forward(layer_names)

    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
        
            if confidence > 0.2 and classes[class_id] == 'boat':
                boat_detected = True
                print(time.strftime("%Y-%m-%d-%H:%M:%S"), f"Class: {classes[class_id]}, Confidence: {confidence}")
                # Visualize the detected bounding box
                h, w, _ = frame.shape
                x, y, w, h = map(int, detection[0:4] * [w, h, w, h])

                # Modify the original frame
                cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2, cv2.LINE_AA)
                out.write(frame)

            else:
                boat_detected = False
                #time.sleep(0.1)

    # Display the frame in the 'Video' window
    cv2.imshow("Video", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Release the video capture object and close all windows
cap.release()
if video_writer is not None:
    video_writer.release()
cv2.destroyAllWindows()