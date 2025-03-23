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

