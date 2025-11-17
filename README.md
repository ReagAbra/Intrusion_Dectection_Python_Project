#PROJECT TITLE: Intelligent Intruder Detection & Face Recognition System

#Description

This project is a Flask-based intruder detection and face recognition system.
It uses deep learning models (MTCNN + InceptionResnetV1) to detect faces,
identify authorized users, and trigger an intrusion workflow that includes:

• Real-time face detection
• Intruder classification
• Automatic phone call alerts using Twilio
• Automatic video recording of the intruder
• Consent form submission & digital signature storage
• Admin login system
• Frame-streaming from browser to server for recording
• Automatic cleanup of video files older than 30 days

The system is designed for Raspberry Pi or PC-based security CCTV applications.

#Features

• Multi-face detection using MTCNN
• Face recognition with pretrained VGGFace2 model
• Register multiple face variations per person
• Intrusion detection after consecutive frames
• Automated Twilio phone call alert workflow
• Records intruder video from client frames (not direct webcam)
• Login authentication with SHA256-hashed password
• Consent form with digital signature capture
• CSV-based consent database
• Automatic folder creation and management

#Project Structure

app.py - Main Flask application
login.py - Login authentication system
consent_form.py - Consent form + CSV writing
make_call.py - Twilio phone call alert
record.py - Intruder video recording, frame capture

#Installation

Install dependencies:
pip install -r requirements.txt

#Network Requirements

• An active internet connection is REQUIRED for:
  – Twilio phone call alerts
  – First-time model downloading (if not already cached)

#Configure the system :

Inside login.py
APP_USERNAME = "admin"
PASSWORD_HASH = "123"

Inside make_call.py
ACCOUNT_SID = "your_twilio_sid"
AUTH_TOKEN = "your_twilio_auth_token"
TWILIO_NUMBER = "+123456789"
TO_NUMBER = "+123456789"

Inside record.py
SAVE_DIR = "videos"

Run the server:
python app.py

Open in browser:
http://127.0.0.1:5050


Author

Reagan Abrahams
Cape Town, South Africa
0764618185
www.linkedin.com/in/reagan-abrahams
