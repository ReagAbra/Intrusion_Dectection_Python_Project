from flask import Flask, render_template, request, jsonify, redirect, url_for
import cv2
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
from PIL import Image
import os
from datetime import datetime
from dotenv import load_dotenv
import threading
import time
import io
import base64

# Custom modules
from utils.auth import is_logged_in
from login import login_blueprint
from consent_form import consent_blueprint
from make_call import start_intrusion_call
from Record import record_blueprint, start_recording_intruder_from_frames, cleanup_old_files

load_dotenv()
app = Flask(__name__)

# Register blueprints
app.register_blueprint(login_blueprint)
app.register_blueprint(consent_blueprint)
app.register_blueprint(record_blueprint)

# Cleanup old files at startup
cleanup_old_files()

# Initialize face detection and recognition models
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(keep_all=True, device=device)
resnet = InceptionResnetV1(pretrained='vggface2').to(device).eval()

# Create directories if they don't exist
os.makedirs('registered_faces', exist_ok=True)
os.makedirs('detected_faces', exist_ok=True)

# Global variables
face_embeddings_cache = {}
last_cache_update = 0
CACHE_UPDATE_INTERVAL = 300  # 5 minutes
consecutive_intrusion_frames = 0

# Load registered face embeddings with caching
def load_registered_faces():
    global face_embeddings_cache, last_cache_update
    current_time = time.time()
    if current_time - last_cache_update < CACHE_UPDATE_INTERVAL and face_embeddings_cache:
        return face_embeddings_cache

    registered_faces = {}
    for person_folder in os.listdir('registered_faces'):
        person_path = os.path.join('registered_faces', person_folder)
        if os.path.isdir(person_path):
            embeddings = []
            face_files = sorted([f for f in os.listdir(person_path) if f.endswith('.npy')])
            for face_file in face_files:
                embedding = np.load(os.path.join(person_path, face_file))
                embeddings.append(embedding)
            if embeddings:
                registered_faces[person_folder] = embeddings

    face_embeddings_cache = registered_faces
    last_cache_update = current_time
    return registered_faces

# Draw bounding boxes on image
def draw_bounding_boxes(img, results):
    try:
        img_array = np.array(img)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        for bbox, label, status in results:
            x1, y1, x2, y2 = bbox
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(img_cv.shape[1], x2)
            y2 = min(img_cv.shape[0], y2)

            box_color = (0, 255, 0) if status == 'authorized' else (0, 0, 255)
            text_color = (255, 255, 255)

            # Draw rectangle and label
            cv2.rectangle(img_cv, (x1, y1), (x2, y2), box_color, 4)
            label_text = f"{label}"
            status_text = "Authorized" if status == 'authorized' else "Intrusion"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.9
            font_thickness = 2

            (text_width, text_height), baseline = cv2.getTextSize(label_text, font, font_scale, font_thickness)
            cv2.rectangle(img_cv, (x1, y1 - text_height - 10), (x1 + text_width + 10, y1), box_color, -1)
            cv2.putText(img_cv, label_text, (x1 + 5, y1 - 5), font, font_scale, text_color, font_thickness, cv2.LINE_AA)

            (status_width, status_height), _ = cv2.getTextSize(status_text, font, font_scale, font_thickness)
            cv2.rectangle(img_cv, (x1, y2), (x1 + status_width + 10, y2 + status_height + 10), box_color, -1)
            cv2.putText(img_cv, status_text, (x1 + 5, y2 + status_height + 5), font, font_scale, text_color, font_thickness, cv2.LINE_AA)

        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        return Image.fromarray(img_rgb)
    except Exception as e:
        print(f"Error in draw_bounding_boxes: {str(e)}")
        return img

# Process faces from image
def process_multiple_faces(img):
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img_array = np.array(img)
    boxes, _ = mtcnn.detect(img_array)
    if boxes is None:
        return None, None, None

    faces = []
    face_tensors = []
    bboxes = []
    for box in boxes:
        x1, y1, x2, y2 = [int(b) for b in box]
        padding = 20
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(img_array.shape[1], x2 + padding)
        y2 = min(img_array.shape[0], y2 + padding)

        face = img_array[y1:y2, x1:x2]
        face = Image.fromarray(face)
        face = face.resize((160, 160))

        face_tensor = torch.from_numpy(np.array(face)).float()
        face_tensor = face_tensor.permute(2, 0, 1).unsqueeze(0)
        face_tensor = (face_tensor - 127.5) / 128.0

        faces.append(face)
        face_tensors.append(face_tensor)
        bboxes.append((x1, y1, x2, y2))

    return face_tensors, faces, bboxes

# Routes
@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login.login_form'))
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register_face():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    name = request.form.get('name', 'unknown')

    try:
        person_dir = os.path.join('registered_faces', name)
        os.makedirs(person_dir, exist_ok=True)
        img = Image.open(file.stream)
        face_tensors, faces, bboxes = process_multiple_faces(img)
        if face_tensors is None:
            return jsonify({'error': 'No face detected'}), 400

        with torch.no_grad():
            embedding = resnet(face_tensors[0].to(device)).cpu().numpy()

        existing_variations = [f for f in os.listdir(person_dir) if f.endswith('.npy')]
        new_variation_number = len(existing_variations) + 1
        np.save(os.path.join(person_dir, f'image_{new_variation_number}.npy'), embedding)
        faces[0].save(os.path.join(person_dir, f'image_{new_variation_number}.jpg'))

        global face_embeddings_cache
        face_embeddings_cache = {}

        return jsonify({
            'message': f'Face variation {new_variation_number} registered successfully for {name}',
            'total_variations': new_variation_number,
            'person_directory': person_dir
        })

    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@app.route('/detect', methods=['POST'])
def detect_face():
    global consecutive_intrusion_frames
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    mode = request.form.get('mode', 'run')
    if mode != 'run':
        consecutive_intrusion_frames = 0
        return jsonify({'status': 'success', 'message': 'Detection disabled in register mode.', 'results': [], 'annotated_image': None})

    file = request.files['image']
    try:
        img = Image.open(file.stream)
        face_tensors, faces, bboxes = process_multiple_faces(img)
        if face_tensors is None:
            consecutive_intrusion_frames = 0
            return jsonify({'status': 'error', 'message': 'No faces detected', 'results': [], 'annotated_image': None})

        registered_faces = load_registered_faces()
        if not registered_faces:
            consecutive_intrusion_frames = 0
            return jsonify({'status': 'error', 'message': 'No registered faces found', 'results': [], 'annotated_image': None})

        results = []
        authorized_persons = set()
        intrusion_count = 0
        intrusion_in_this_frame = False

        for face_tensor, face, bbox in zip(face_tensors, faces, bboxes):
            with torch.no_grad():
                embedding = resnet(face_tensor.to(device)).cpu().numpy()

            min_distance = float('inf')
            matched_name = None
            for name, embeddings in registered_faces.items():
                person_min_distance = min(np.linalg.norm(embedding - e) for e in embeddings)
                if person_min_distance < min_distance:
                    min_distance = person_min_distance
                    matched_name = name

            if min_distance < 0.7:
                authorized_persons.add(matched_name)
                results.append((bbox, matched_name, 'authorized'))
            else:
                intrusion_count += 1
                results.append((bbox, f'Intrusion {intrusion_count}', 'intrusion'))
                intrusion_in_this_frame = True

        annotated_img = draw_bounding_boxes(img, results)

        if intrusion_in_this_frame:
            consecutive_intrusion_frames += 1
        else:
            consecutive_intrusion_frames = 0

        recording_started = False
        if mode == 'run' and consecutive_intrusion_frames >= 10:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_path = f'detected_faces/intrusion_{timestamp}.jpg'
            annotated_img.save(image_path)

            # Trigger call & recording (email removed)
            threading.Thread(target=start_intrusion_call).start()
            threading.Thread(target=start_recording_intruder_from_frames).start()
            recording_started = True
            consecutive_intrusion_frames = 0

        auth_persons_str = ', '.join(authorized_persons) if authorized_persons else 'None'
        intrusion_str = f'{intrusion_count} intrusion(s)' if intrusion_count > 0 else 'No intrusions'
        message = f'Authorized persons: {auth_persons_str}. {intrusion_str}'

        buffered = io.BytesIO()
        annotated_img.save(buffered, format="JPEG", quality=95)
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return jsonify({
            'status': 'success',
            'message': message,
            'results': [{'bbox': bbox, 'label': label, 'status': status} for bbox, label, status in results],
            'annotated_image': img_str,
            'email_alert_triggered': False,  # No emails
            'email_count': 0,  # No emails
            'recording_started': recording_started
        })

    except Exception as e:
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500

# Frame rate limiter
def limit_frame_rate(frame_count, target_fps=10):
    if not hasattr(limit_frame_rate, 'last_time'):
        limit_frame_rate.last_time = time.time()
        limit_frame_rate.frame_count = 0

    current_time = time.time()
    elapsed = current_time - limit_frame_rate.last_time

    if elapsed >= 1.0:
        fps = limit_frame_rate.frame_count / elapsed
        if fps > target_fps:
            time.sleep(1.0 / target_fps - 1.0 / fps)
        limit_frame_rate.last_time = current_time
        limit_frame_rate.frame_count = 0

    limit_frame_rate.frame_count += 1
    return True

if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=5050)
