#!/usr/bin/python3
import sys
sys.path.append('/home/pi/opencv/build/lib/python3')
import time
import datetime
import picamera
import picamera.array
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

# Set the timeout duration in seconds
timeout_duration = 5  # Adjust as needed

# Variable to store the time when the last boat was detected
last_detection_time = time.time()

#Define the codec
today = time.strftime("%Y%m%d-%H%M%S")
fourcc = cv2.VideoWriter_fourcc(*'xvid')  # XVID
#fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # H.264 codec with MP4 container
fps_out = 25.0
frame_size = (640, 480)

# Initialize video writer outside the loop
video_writer = None
#video_writer = cv2.VideoWriter('output'+ today + '.mp4', fourcc, fps_out, frame_size)

# Initialize PiCamera outside the loop
with picamera.PiCamera() as camera:
    camera.resolution = (640, 480)
    time.sleep(2)  # Allow the camera to warm up
    
    while True:
        today = time.strftime("%Y%m%d-%H%M%S")
        # Open the PiCamera as a stream and convert it to a numpy array
        stream = picamera.array.PiRGBArray(camera, size=frame_size )
        print(today, "Before frame capture")
        camera.capture(stream, format='bgr')
        print(today, "After frame capture")

        frame = np.copy(stream.array)
        #frame = stream.array

        # Increment the frame counter
        frame_counter += 1

        # Only process frames that meet the skipping criteria
        if frame_counter % frame_skip_factor == 0:
            frame_counter = 0

            # Perform object detection, preprocess the frame for object 
            # detection using YOLO. The frame is converted into a blob, and
            # the YOLO model is fed with this blob to obtain the detection results.
            #blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
            today = time.strftime("%Y%m%d-%H%M%S")
            print(today, "Before object detection")
            blob = cv2.dnn.blobFromImage(frame, scalefactor=0.00392, size=(416, 416), swapRB=True, crop=False)
            net.setInput(blob)
            outs = net.forward(layer_names)
            print(today, "After object detection")

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
                        h, w, _ = frame.shape
                        x, y, w, h = map(int, detection[0:4] * [w, h, w, h])

                        # Modify the original frame
                        cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2, cv2.LINE_AA)

                        # Trigger video recording
                        print(today,"Before video writer, line 107")
                        if video_writer is None:
                            video_writer = cv2.VideoWriter('output'+today + '.mp4', fourcc, fps_out, (640, 480))
                            print(today,"After video writer, line 110")

                        # Trigger video recording
                        if not recording:
                            recording = True
                            print(today, "not recording boat detected, line 115")
                            # Create a deep copy of the frame for video recording
                            #video_frame = np.copy(frame)
                            boat_detected = True

            # Check for inactivity timeout
            if recording and time.time() - last_detection_time > timeout_duration:
                # Pause video recording
                recording = False
                if video_writer is not None:
                    print(today, "video_writer is not None, line 125")
                    video_writer.release()
                    video_writer = None 

            elif not recording and boat_detected:
                # Resume video recording
                recording = True
                print(today, "Resume recording, line 132")
                video_writer = cv2.VideoWriter('output' + 'today' + '.mp4', fourcc, fps_out, frame_size)
                camera.wait_recording(5)
                print(today,"After wait 5 sec")
            
            print(today,"Before video writing")
            if recording:
                video_writer.write(frame)
            print(today,"After video writing")

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