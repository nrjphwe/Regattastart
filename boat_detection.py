boat_detection.py
import cv2

# Load the pre-trained object detection model
net = cv2.dnn.readNet('yolov3.weights', 'yolov3.cfg')

# Load COCO names (class labels)
with open('coco.names', 'r') as f:
    classes = f.read().strip().split('\n')

# Load the configuration and weights for YOLO
layer_names = net.getUnconnectedOutLayersNames()

# Initialize the camera
cap = cv2.VideoCapture(0)  # 0 for default camera

while True:
    ret, frame = cap.read()

    # Perform object detection
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

    cv2.imshow('Boat Detection', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()