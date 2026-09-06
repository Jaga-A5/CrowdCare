import os
import cv2
from ultralytics import YOLO

# Load the user-provided YOLO model (using the nano version for fastest CPU inference)
MODEL_PATH = r"D:\python\AI_Vision_Monitor\models\yolo11n.pt"
model = None

try:
    if os.path.exists(MODEL_PATH):
        model = YOLO(MODEL_PATH)
    else:
        print(f"Warning: Model not found at {MODEL_PATH}")
except Exception as e:
    print(f"Failed to load YOLO model: {e}")

def estimate_crowd(image_path, threshold=5):
    """
    Real-Time Crowd Estimation using Ultralytics YOLOv11 Object Detection.
    Detects only class 0 (person) to provide highly accurate crowd counts.
    """
    try:
        if model is None:
            return 0, 'LOW'
            
        # Run inference on the image
        # classes=[0] filters the detection to ONLY humans
        # conf=0.4 ensures we only count confident detections
        results = model(image_path, classes=[0], conf=0.4, verbose=False)
        
        # The number of bounding boxes is the number of people detected
        crowd_count = len(results[0].boxes)
        
        # Plot the bounding boxes on the image so the user can see what the AI identified
        annotated_img = results[0].plot()
        _, buffer = cv2.imencode('.jpg', annotated_img)
        
        # Convert to base64 string
        import base64
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
        print(f"Error in crowd AI estimation: {e}")
        return 0, 'LOW', None
