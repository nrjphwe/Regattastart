{\rtf1\ansi\ansicpg1252\cocoartf2709
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fnil\fcharset0 Menlo-Regular;}
{\colortbl;\red255\green255\blue255;\red0\green0\blue0;}
{\*\expandedcolortbl;;\csgray\c0;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\pardirnatural\partightenfactor0

\f0\fs22 \cf2 \CocoaLigature0 #!/usr/bin/python3\
import sys\
sys.path.append('/home/pi/opencv/build/lib/python3')\
import cv2\
\
print(sys.path)\
\
print(sys.executable)\
\
\
def on_key(event):\
    if event == ord('q'):\
        cv2.destroyAllWindows()\
\
# Open a video capture object (replace 'your_video_file.mp4' with the actual video file or use 0 for webcam)\
cap = cv2.VideoCapture('video0.mp4')\
\
\
while True:\
    ret, frame = cap.read()\
    if not ret:\
        break\
\
    # Display the frame in the 'Video' window\
    cv2.imshow("Video", frame)\
\
    # Wait for a key event (100 ms delay)\
    key = cv2.waitKey(100)\
    if key != -1:\
        on_key(key)\
\
# Release the video capture object and close all windows\
cap.release()\
cv2.destroyAllWindows()\
}