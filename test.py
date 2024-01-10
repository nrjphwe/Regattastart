#!/usr/bin/python3
import sys
sys.path.append('/home/pi/opencv/build/lib/python3')
import time
import datetime as dt
import cv2
import numpy as np

def annotate_video(frame, start_time_sec):
    time_now = dt.datetime.now()
    seconds_since_midnight = time_now.hour * 3600 + time_now.minute * 60 + time_now.second
    elapsed_time = seconds_since_midnight - start_time_sec #elapsed since last start until now)
    org = (30,60)
    fontFace=cv2.FONT_HERSHEY_DUPLEX
    fontScale = 0.6
    color=(0,0,255) #(B, G, R)
    thickness = 1
    lineType = cv2.LINE_AA
    label = str(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')) +  " Seconds since last start: " +  str(elapsed_time)
    cv2.putText(frame,label,org,fontFace,fontScale,color,thickness,lineType)
   
# Load the pre-trained object detection model -- YOLO (You Only Look Once) 
net = cv2.dnn.readNet('../darknet/yolov3-tiny.weights', '../darknet/cfg/yolov3-tiny.cfg')
# Load COCO names (class labels) 
with open('../darknet/data/coco.names', 'r') as f:
    classes = f.read().strip().split('\n')
# Load the configuration and weights for YOLO
layer_names = net.getUnconnectedOutLayersNames()

today = time.strftime("%Y%m%d")

# Open a video capture object (replace 'your_video_file.mp4' with the actual video file or use 0 for webcam)
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot open camera")
    exit()
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) + 0.5)
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) + 0.5)
size = (width, height)

fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # H.264 codec with MP4 container
video_writer = cv2.VideoWriter('output'+ today + '.mp4', fourcc, 50, size)

# Timer variables
video_end = 10
start_time_= 0
start_time_sec = 0
number_of_detected_frames = 5
number_of_non_detected_frames = 5

start_time = time.time()

while True:
    ret, frame = cap.read()
    if frame is None:
        print("Frame is None. Ending loop.")
        break

    # if frame is read correctly ret is True
    ret, frame = cap.read()
    if not ret:
        print("Frame is not ret. Ending loop.")
        break

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
                print("boat detected")
                boat_detected = True
                #print(time.strftime("%Y-%m-%d-%H:%M:%S"), f"Class: {classes[class_id]}, Confidence: {confidence}")
                # Visualize the detected bounding box
                h, w, _ = frame.shape
                x, y, w, h = map(int, detection[0:4] * [w, h, w, h])

                # Modify the original frame
                cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2, cv2.LINE_AA)
                
                # Write detected frames to the video file
                i = 1
                while i < number_of_detected_frames:
                    # Write frames to the video file
                    annotate_video(frame, start_time_sec)
                    video_writer.write(frame)
                    i += 1
                
            else:
                # Confidence < 0.2
                if boat_detected == True:
                    i = 1
                    while i < number_of_non_detected_frames:
                        annotate_video(frame, start_time_sec)
                        video_writer.write(frame)
                        i += 1
                    boat_detected = False


        # Display the frame in the 'Video' window
        cv2.imshow("Video", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # Check if the maximum duration has been reached
    elapsed_time = time.time() - start_time
    if elapsed_time >= 60 * video_end:
        break

# Release the video capture object and close all windows
cap.release()
video_writer.release()
cv2.destroyAllWindows()