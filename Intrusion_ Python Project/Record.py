import cv2
import numpy as np
import os
import time
from flask import Blueprint, jsonify, request

record_blueprint = Blueprint('record', __name__)

save_dir = "videos"  # raw string for Windows path
os.makedirs(save_dir, exist_ok=True)

fourcc = cv2.VideoWriter_fourcc(*'XVID')



latest_recording_frame = None
recording_active = False


#Receive the frames from the client/Javascript
@record_blueprint.route('/record_frame', methods=['POST'])
def record_frame():
    global latest_recording_frame, recording_active
    if 'frame' in request.files:
        latest_recording_frame = request.files['frame'].read()
        recording_active = True
        print("Recording frame received")
    return jsonify({'status': 'success'})





# Will use frames instead of opening camera directly
def start_recording_intruder_from_frames(duration=11):
    global latest_recording_frame
    
    output_path = os.path.join(save_dir, f"outPut_{int(time.time())}.avi")
    out = None
    start_time = time.time()
    
    while time.time() - start_time < duration:
        if latest_recording_frame:
            # Convert bytes to cv2 image
            nparr = np.frombuffer(latest_recording_frame, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if out is None:
                h, w = img.shape[:2]
                out = cv2.VideoWriter(output_path, fourcc, 10.0, (w, h))
            
            out.write(img)
        
        time.sleep(0.1)  # 10 FPS
    
    if out:
        out.release()
    print(f"Video saved to: {output_path}")




# Function to delete video after a month
def cleanup_old_files(save_dir_path=save_dir):
    "Delete files older than 30 days"
    current_time = time.time()
    thirty_days = 30 * 24 * 60 * 60  # 30 days in seconds
    
    for filename in os.listdir(save_dir_path):
        file_path = os.path.join(save_dir_path, filename)
        if os.path.isfile(file_path):
            file_age = current_time - os.path.getctime(file_path)
            if file_age > thirty_days:
                try:
                    os.remove(file_path)
                    print(f"Deleted old file: {filename}")
                except OSError as e:
                    print(f"Error deleting {filename}: {e}")