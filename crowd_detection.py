import os
import cv2
import numpy as np
import base64
from ultralytics import YOLO

# Determine if we are running locally (Windows) or on Render (Linux)
import platform

# Only try to load the heavy YOLO model if we are running locally on your laptop.
# Render's Free Tier (Linux) only has 512MB RAM and will crash if it tries to load PyTorch.
model = None
if platform.system() == "Windows":
    # Use local yolo11m.pt file in the project directory
    MODEL_PATH = os.path.join(os.path.dirname(__file__), 'yolo11m.pt')
    try:
        if os.path.exists(MODEL_PATH):
            model = YOLO(MODEL_PATH)
            print(f"YOLO model loaded successfully from {MODEL_PATH}")
        else:
            print(f"YOLO model not found at {MODEL_PATH}")
    except Exception as e:
        print(f"Failed to load YOLO model locally: {e}")

def process_frame(img):
    """
    Processes a single OpenCV frame for crowd detection with improved YOLO configuration.
    """
    global model
    annotated_img = img.copy()
    crowd_count = 0
    max_conf = 0.0
    
    try:
        # If model is loaded, use AI detection
        if model is not None:
            # Run YOLO inference with optimized parameters for person detection
            results = model(img, stream=False, verbose=False, 
                          conf=0.25,  # Confidence threshold
                          iou=0.45,   # NMS IOU threshold
                          max_det=300, # Maximum detections
                          classes=[0], # Only detect person class (COCO class 0)
                          agnostic_nms=True) # Class-agnostic NMS
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    if conf > max_conf:
                        max_conf = conf
                            
                    # Filter out weak detections with improved threshold
                    if conf > 0.25:
                        crowd_count += 1
                        x1, y1, x2, y2 = box.xyxy[0]
                        startX, startY, endX, endY = int(x1), int(y1), int(x2), int(y2)
                        
                        # Draw bounding box with improved visibility
                        cv2.rectangle(annotated_img, (startX, startY), (endX, endY), (0, 255, 0), 3)
                        
                        # Add label with confidence score
                        label = f"Person [{int(conf * 100)}%]"
                        cv2.putText(annotated_img, label, (startX, startY - 10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                                       
            cv2.putText(annotated_img, f"AI: YOLO11 (Max Conf: {int(max_conf*100)}%)", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        else:
            # Fallback to basic Haar Cascade if DNN fails
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if face_cascade.empty():
                raise Exception("Haar cascade XML not found")
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            bodies = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # detectMultiScale returns a tuple if empty, array if found
            if len(bodies) > 0:
                for (x, y, w, h) in bodies:
                    crowd_count += 1
                    cv2.rectangle(annotated_img, (x, y), (x+w, y+h), (0, 255, 0), 4)
                    cv2.putText(annotated_img, "Face", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
            cv2.putText(annotated_img, "AI: Haar Cascade (Cloud Mode)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
    except Exception as e:
        # If ANYTHING crashes, print the exact python error on the camera screen!
        error_msg = str(e)[:60] # truncate to fit on screen
        cv2.putText(annotated_img, f"CRASH: {error_msg}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        print(f"Frame Processing Error: {e}")
        
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

def train_yolo_model(data_path, epochs=50, batch_size=16, img_size=640):
    """
    Train or retrain the YOLO model on custom data for improved person detection.
    
    Args:
        data_path: Path to the dataset configuration file (YAML format)
        epochs: Number of training epochs
        batch_size: Batch size for training
        img_size: Image size for training
        
    Returns:
        trained_model: The trained YOLO model
    """
    global model
    
    try:
        print(f"Starting YOLO model training on {data_path}...")
        
        # Load the base model
        base_model = YOLO('yolo11m.pt')
        
        # Train the model
        results = base_model.train(
            data=data_path,
            epochs=epochs,
            batch=batch_size,
            imgsz=img_size,
            device='0',  # Use GPU if available
            project='yolo_training',
            name='person_detection',
            exist_ok=True,
            pretrained=True,
            optimizer='Adam',
            lr0=0.001,
            patience=20
        )
        
        # Update the global model with the trained one
        model = YOLO('yolo_training/person_detection/weights/best.pt')
        print("Model training completed successfully!")
        
        return model
        
    except Exception as e:
        print(f"Error during model training: {e}")
        return None

def validate_model():
    """
    Validate the current YOLO model performance on a test dataset.
    """
    global model
    
    if model is None:
        print("No model loaded for validation")
        return None
    
    try:
        # Run validation
        results = model.val(
            data='coco8.yaml',  # Use COCO8 for quick validation
            split='val',
            device='0'
        )
        
        print(f"Validation Results:")
        print(f"mAP50-95: {results.box.map}")
        print(f"mAP50: {results.box.map50}")
        print(f"Precision: {results.box.mp}")
        print(f"Recall: {results.box.mr}")
        
        return results
        
    except Exception as e:
        print(f"Error during model validation: {e}")
        return None
