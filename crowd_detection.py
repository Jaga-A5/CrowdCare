import os
import cv2
import numpy as np
import base64
from ultralytics import YOLO

# Use the Nano model (yolo11n.pt) because Render's Free Tier (512MB RAM) 
# will crash/run out of memory if we try to load the Medium model.
MODEL_PATH = "yolo11n.pt"

# Load the network once globally to save time
model = None
try:
    model = YOLO(MODEL_PATH)
except Exception as e:
    print(f"Failed to load YOLO model: {e}")
    model = None

def process_frame(img):
    """
    Processes a single OpenCV frame for crowd detection.
    Returns:
        annotated_img: Image with visualizations drawn.
        crowd_count: Integer count of detected people.
    """
    global model
    annotated_img = img.copy()
    crowd_count = 0
    max_conf = 0.0
    
    # If model is loaded, use AI detection
    if model is not None:
        # Run YOLO inference
        results = model(img, stream=False, verbose=False) # Changed to stream=False for simpler processing
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # class 0 is 'person' in COCO dataset (default for YOLO11)
                cls = int(box.cls[0])
                if cls == 0:
                    conf = float(box.conf[0])
                    if conf > max_conf:
                        max_conf = conf
                        
                    # Filter out weak detections
                    if conf > 0.15: # Lowered further to 15% for extreme debugging
                        crowd_count += 1
                        
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0]
                        startX, startY, endX, endY = int(x1), int(y1), int(x2), int(y2)
                        
                        # Draw standard thick green bounding box (as requested)
                        cv2.rectangle(annotated_img, (startX, startY), (endX, endY), (0, 255, 0), 4)
                        
                        # Draw a sleek label
                        label = f"Person [{int(conf * 100)}%]"
                        cv2.putText(annotated_img, label, (startX, startY - 10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                                   
        cv2.putText(annotated_img, f"AI: YOLO11n (Max Conf: {int(max_conf*100)}%)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    else:
        # Fallback to basic Haar Cascade if DNN fails
        # Use facial detection since webcams mostly capture head/shoulders, not full bodies
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        bodies = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        for (x, y, w, h) in bodies:
            crowd_count += 1
            cv2.rectangle(annotated_img, (x, y), (x+w, y+h), (0, 255, 0), 4)
            cv2.putText(annotated_img, "Face", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
        cv2.putText(annotated_img, "AI: Haar Cascade (YOLO Failed)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
    return annotated_img, crowd_count

def estimate_crowd(image_path, threshold=5):
    """
    CROWD ESTIMATION using MobileNet SSD AI model.
    """
    try:
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            return 0, 'LOW', None
        
        annotated_img, crowd_count = process_frame(img)
        
        # Convert to base64
        _, buffer = cv2.imencode('.jpg', annotated_img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Determine density based on the threshold
        if crowd_count >= threshold:
            density = 'CRITICAL'
        elif crowd_count >= threshold * 0.75:
            density = 'HIGH'
        elif crowd_count >= threshold * 0.4:
            density = 'MEDIUM'
        else:
            density = 'LOW'
            
        return crowd_count, density, img_base64
        
    except Exception as e:
        print(f"Error in AI crowd estimation: {e}")
        return 0, 'LOW', None
