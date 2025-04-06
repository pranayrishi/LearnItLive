import cv2
from ultralytics import YOLO
import os
import threading
import time
import numpy as np


class YOLOTracker:
    def __init__(self):
        # Suppress YOLO console output
        os.environ['YOLO_VERBOSE'] = 'False'
        self.model = YOLO("yolov8n.pt")
        self.model.verbose = False
        self.running = False
        self.thread = None
        self.frame = None
        self.processed_frame = None
        self.detected_objects = []
        self.lock = threading.Lock()
        self.display_enabled = True

    def detect_objects(self, frame):
        detected_objects = []
        processed_frame = frame.copy()

        # Use the silent parameter to suppress terminal output during inference
        try:
            for r in self.model.predict(frame, verbose=False):
                for box in r.boxes:
                    if box.conf[0].item() > 0.5:
                        label = self.model.names[int(box.cls[0])]
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(processed_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0),
                                    2)
                        detected_objects.append(label)
        except Exception as e:
            print(f"Error in object detection: {e}")

        return processed_frame, detected_objects

    def capture_loop(self):
        """Thread function to capture frames only"""
        cap = cv2.VideoCapture(0)
        self.running = True

        while self.running:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame")
                time.sleep(0.1)
                continue

            # Process the frame
            try:
                processed_frame, objects = self.detect_objects(frame)

                # Update the shared data with lock to prevent race conditions
                with self.lock:
                    self.frame = frame.copy()
                    self.processed_frame = processed_frame
                    self.detected_objects = objects.copy()
            except Exception as e:
                print(f"Error processing frame: {e}")

            time.sleep(0.01)  # Small delay to prevent high CPU usage

        cap.release()
        print("Capture thread stopped")

    def start(self):
        """Start the YOLO tracking"""
        if self.thread is None or not self.thread.is_alive():
            self.running = True
            self.thread = threading.Thread(target=self.capture_loop)
            self.thread.daemon = True
            self.thread.start()
            return True
        return False

    def stop(self):
        """Stop the YOLO tracking"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            self.thread = None
        # DO NOT call cv2.destroyAllWindows() here - let the main thread handle GUI

    def get_latest_frame(self):
        """Get the latest processed frame (for external use)"""
        with self.lock:
            if self.processed_frame is not None:
                return self.processed_frame.copy()
            return None

    def get_detected_objects(self):
        """Get the latest detected objects (for external use)"""
        with self.lock:
            return self.detected_objects.copy()

    def enable_display(self, enable=True):
        """Enable or disable frame display"""
        self.display_enabled = enable


# Global tracker instance
tracker = None


def YOLOTracking():
    """Initialize and start the YOLO tracking"""
    global tracker
    if tracker is None:
        tracker = YOLOTracker()

    if not tracker.start():
        print("Tracker already running")

    tracker.enable_display(True)


def StopYOLOTracking():
    """Stop the YOLO tracking"""
    global tracker
    if tracker:
        tracker.enable_display(False)  # First disable display
        tracker.stop()
        cv2.destroyAllWindows()  # This should be called in the main thread


def GetLatestFrame():
    """Get the latest processed frame with detections"""
    global tracker
    if tracker:
        return tracker.get_latest_frame()
    return None


def GetDetectedObjects():
    """Get list of latest detected objects"""
    global tracker
    if tracker:
        return tracker.get_detected_objects()
    return []


def DisplayFrames():
    """Display frames in the main thread - call this from the main loop"""
    global tracker
    if tracker and tracker.display_enabled:
        frame = tracker.get_latest_frame()
        if frame is not None:
            try:
                cv2.imshow("AI Vision", frame)
                cv2.waitKey(1)
            except Exception as e:
                print(f"Error in main thread display: {e}")