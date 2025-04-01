import os
from datetime import datetime
from PIL import Image

def get_mock_frame():
    try:
        return Image.open("assets/camera_feed.jpg")
    except:
        return Image.new('RGB', (640, 480), color='gray')

def get_tk_image():
    frame = get_mock_frame()
    frame = frame.resize((640, 360))  # Resize to fit UI area
    return ImageTk.PhotoImage(frame)

def take_mock_snapshot(uid, frame):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_dir = "assets/snapshots"
    os.makedirs(snapshot_dir, exist_ok=True)
    path = os.path.join(snapshot_dir, f"{uid}_{timestamp}.jpg")
    frame.save(path)
    return path

def take_snapshot(uid="unknown"):
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Camera could not be opened.")

        ret, frame = cap.read()
        cap.release()

        if not ret:
            raise RuntimeError("Failed to capture frame.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{uid}_{timestamp}.jpg"
        path = os.path.join(SNAPSHOT_DIR, filename)

        cv2.imwrite(path, frame)
        return path
    except Exception as e:
        print(f"[Camera Error] {e}")
        return None

