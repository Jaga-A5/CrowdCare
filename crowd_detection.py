import os
import cv2
import numpy as np
import base64

# Get the directory of the current script to find the model files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOTXT_PATH = os.path.join(BASE_DIR, "MobileNetSSD_deploy.prototxt")
MODEL_PATH = os.path.join(BASE_DIR, "MobileNetSSD_deploy.caffemodel")

# Load the network once globally to save time
net = None
try:
    if os.path.exists(PROTOTXT_PATH) and os.path.exists(MODEL_PATH):
        if hasattr(cv2.dnn, 'readNetFromCaffe'):
            net = cv2.dnn.readNetFromCaffe(PROTOTXT_PATH, MODEL_PATH)
        else:
            net = cv2.dnn.readNet(MODEL_PATH, PROTOTXT_PATH)
except Exception as e:
    print(f"Failed to load MobileNet SSD: {e}")
    net = None

def estimate_crowd(image_path, threshold=5):
    """
    CROWD ESTIMATION using MobileNet SSD AI model.
    """
    global net
    try:
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            return 0, 'LOW', None
        
        annotated_img = img.copy()
        crowd_count = 0
        
        # If model is loaded, use AI detection
        if net is not None:
            (h, w) = img.shape[:2]
            blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 0.007843, (300, 300), 127.5)
            net.setInput(blob)
            detections = net.forward()
            
            for i in np.arange(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                
                # Filter out weak detections (increased to 0.55 to avoid false positives)
                if confidence > 0.55:
                    idx = int(detections[0, 0, i, 1])
                    
                    # 15 is the class ID for 'person' in MobileNet SSD
                    if idx == 15:
                        crowd_count += 1
                        
                        # Calculate bounding box
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        (startX, startY, endX, endY) = box.astype("int")
                        
                        # Calculate center and radius for a circular "field" visualization
                        centerX = int((startX + endX) / 2)
                        centerY = int((startY + endY) / 2)
                        radius = int(max((endX - startX), (endY - startY)) / 1.5)
                        
                        # Draw advanced circular visualization
                        cv2.circle(annotated_img, (centerX, centerY), radius, (0, 255, 255), 2) # Outer circle
                        cv2.circle(annotated_img, (centerX, centerY), int(radius/2), (0, 200, 255), 1) # Inner ring
                        cv2.circle(annotated_img, (centerX, centerY), 4, (0, 0, 255), -1) # Center dot
                        
                        # Draw a sleek label
                        label = f"Person {crowd_count} [{int(confidence * 100)}%]"
                        cv2.putText(annotated_img, label, (startX, startY - 15), 
                                   cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 255, 255), 1)
        else:
            # Fallback to basic Haar Cascade if DNN fails
            cascade_path = os.path.join(BASE_DIR, "haarcascade_fullbody.xml")
            if os.path.exists(cascade_path):
                body_cascade = cv2.CascadeClassifier(cascade_path)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                bodies = body_cascade.detectMultiScale(gray, 1.1, 3)
                crowd_count = len(bodies)
                for i, (x, y, w_box, h_box) in enumerate(bodies):
                    cv2.rectangle(annotated_img, (x, y), (x+w_box, y+h_box), (0, 255, 0), 2)
                    cv2.putText(annotated_img, f"Person {i+1}", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                crowd_count = 0
        
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
