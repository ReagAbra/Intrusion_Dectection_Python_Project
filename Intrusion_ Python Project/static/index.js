// Mode selection logic
let systemMode = null; // 'register' or 'run'
const modeOverlay = document.getElementById("modeOverlay");
const registerModeBtn = document.getElementById("registerModeBtn");
const runModeBtn = document.getElementById("runModeBtn");
const modeBanner = document.getElementById("modeBanner");
const switchModeBtn = document.getElementById("switchModeBtn");

// Variable to hold the detection interval ID
let detectionIntervalId = null;
// Variable to hold the webcam stream
let webcamStream = null;

// Function to start the webcam
async function startWebcam() {
  if (webcamStream) return; // Prevent starting if already running
  try {
    console.log("Attempting to start webcam...");
    webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = webcamStream;
    console.log("Webcam started successfully.");

    // Enable capture button only after webcam is started
    if (systemMode === "register") {
      captureBtn.disabled = false; // Enable capture when in Register mode and webcam is ready
    }
  } catch (error) {
    console.error("Error accessing webcam:", error);
    alert(
      "Could not access webcam. Please ensure you have a camera connected and grant permissions."
    );
  }
}

// Function to stop the webcam
function stopWebcam() {
  if (webcamStream) {
    console.log("Attempting to stop webcam...");
    webcamStream.getTracks().forEach((track) => track.stop());
    video.srcObject = null;
    webcamStream = null;
    console.log("Webcam stopped successfully.");
  }
}

registerModeBtn.onclick = function () {
  systemMode = "register";
  modeOverlay.style.display = "none";
  modeBanner.textContent = "Mode: Register Faces";
  modeBanner.style.display = "block";
  switchModeBtn.style.display = "inline-block";

  // Stop detection interval and clear image
  if (detectionIntervalId !== null) {
    clearInterval(detectionIntervalId);
    detectionIntervalId = null;
  }
  liveDetectionImg.src = "";
  statusDiv.style.display = "none"; // Hide status in register mode

  // Ensure webcam is running for capture and enable button on success
  startWebcam();

  // Disable register button initially
  registerBtn.disabled = true;
};
runModeBtn.onclick = function () {
  systemMode = "run";
  modeOverlay.style.display = "none";
  modeBanner.textContent = "Mode: Run System";
  modeBanner.style.display = "block";
  switchModeBtn.style.display = "inline-block";

  // Ensure webcam is running for detection
  startWebcam();

  // Start the detection interval if not already running
  if (detectionIntervalId === null) {
    detectionIntervalId = setInterval(sendFrameToBackend, 700);
  }

  // Disable capture and register buttons in run mode
  captureBtn.disabled = true;
  registerBtn.disabled = true;

  // Show status in run mode (will be updated by backend)
  statusDiv.style.display = "block";
};

// Access webcam
const video = document.getElementById("video");
const canvas = document.createElement("canvas"); // offscreen for capture
const statusDiv = document.getElementById("status");
const registerForm = document.getElementById("registerForm");
const nameInput = document.getElementById("name");
const captureBtn = document.getElementById("captureBtn");
const registerBtn = document.getElementById("registerBtn");
const previewImage = document.getElementById("previewImage");
const registerStatus = document.getElementById("registerStatus");
const liveDetectionImg = document.getElementById("live-detection-img");
const emailAlertStatusDiv = document.getElementById("emailAlertStatus"); // Get the new div for status
const emailAlertCountDiv = document.getElementById("emailAlertCount"); // Get the new div for count

// ADDDED

// Frame sending intervals
let recordingInterval = null;

// Function to call the sendFrameToRecording for 11 seconds at 10 FPS
function startRecordingFrames() {
  if (!recordingInterval) {
    recordingInterval = setInterval(sendFrameToRecording, 100); // 10 FPS
    setTimeout(() => {
      clearInterval(recordingInterval);
      recordingInterval = null;
    }, 11000); // Record for 11 seconds
  }
}

// This function sends frames to the recording endpoint every 5 seconds when in 'run' mode
async function sendFrameToRecording() {
  if (video.readyState === 4 && webcamStream) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(async (blob) => {
      const formData = new FormData();
      formData.append("frame", blob, "frame.jpg");
      fetch("/record_frame", { method: "POST", body: formData });
    }, "image/jpeg");
  }
}

// Function to capture and send frame to backend
async function sendFrameToBackend() {
  if (systemMode !== "run") return; // Only run detection in 'run' mode
  // Ensure video is ready and webcam stream is active
  if (video.readyState === 4 && webcamStream) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(async (blob) => {
      const formData = new FormData();
      formData.append("image", blob, "frame.jpg");
      formData.append("mode", systemMode);
      const response = await fetch("/detect", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      // ADDED
      // Start services when intrusion detected
      if (data.recording_started) {
        startRecordingFrames();
      }

      if (data.annotated_image) {
        liveDetectionImg.src = "data:image/jpeg;base64," + data.annotated_image;
      }
      // Update status/message based on backend response
      if (data.message) {
        statusDiv.textContent = data.message;
        // statusDiv.style.display = 'block'; // Already shown in run mode
        // Update alert class based on status from backend if needed
        if (data.status === "error") {
          statusDiv.className = "alert alert-danger";
        } else {
          statusDiv.className = "alert alert-info"; // Default info color
        }
      }

      // Check if email alert was triggered and update the new status div
      if (systemMode === "run") {
        if (data.email_alert_triggered) {
          emailAlertStatusDiv.style.display = "block";
          emailAlertStatusDiv.className = "alert alert-warning"; // Use warning color for alerts
          emailAlertStatusDiv.textContent = "Intrusion email alert sent!";
        } else {
          // Optional: Hide the message if no alert was sent in this frame
          // emailAlertStatusDiv.style.display = 'none';
          // Or clear the message if you want it to appear only when sent
          // emailAlertStatusDiv.textContent = '';
        }
        // Ensure the main status div is visible in run mode for detection messages
        statusDiv.style.display = "block";

        // Update the email alert count
        if (data.hasOwnProperty("email_count")) {
          emailAlertCountDiv.style.display = "block";
          emailAlertCountDiv.textContent = `Email Alerts Sent: ${data.email_count}`;
        } else {
          emailAlertCountDiv.style.display = "none";
          emailAlertCountDiv.textContent = "";
        }
      } else {
        // In register mode, hide the email alert status div
        emailAlertStatusDiv.style.display = "none";
        // In register mode, hide the email alert count div as well
        emailAlertCountDiv.style.display = "none";
        emailAlertCountDiv.textContent = "";
        // Keep the original registerStatus div handling for registration messages
      }
    }, "image/jpeg");
  } else {
    console.log("sendFrameToBackend: Webcam not ready or stream not active.");
  }
}

// Helper to capture image from video
async function captureImage() {
  // This function uses the main video element, which should be fine
  // Ensure video is ready and webcam stream is active before capturing
  console.log("Attempting to capture image...");
  if (video.readyState === 4 && webcamStream) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    console.log("Image captured from video.");
    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), "image/jpeg");
    });
  } else {
    console.error("Webcam not ready for capture in captureImage.");
    alert(
      "Webcam is not ready for capture. Please ensure you have selected Register Faces mode and the webcam is active."
    );
    return Promise.reject("Webcam not ready");
  }
}

// Capture button click handler
captureBtn.addEventListener("click", async () => {
  // Capture button is only enabled when webcam is ready in Register mode
  if (!captureBtn.disabled) {
    // Ensure webcam is started if not already (redundant due to startWebcam on mode select, but safe)
    // await startWebcam();
    try {
      const imageBlob = await captureImage();
      const imageUrl = URL.createObjectURL(imageBlob);
      previewImage.src = imageUrl;
      previewImage.style.display = "block";
      registerBtn.disabled = false; // Enable register button after capture
      // Hide status message when preview is shown for clarity
      statusDiv.style.display = "none";
    } catch (error) {
      console.error("Capture failed:", error);
      // Keep capture and register disabled on failure
      captureBtn.disabled = true;
      registerBtn.disabled = true;
      statusDiv.style.display = "block";
      statusDiv.className = "alert alert-danger";
      statusDiv.textContent = "Capture failed. Please try again.";
    }
  } else {
    console.log("Capture button is disabled.");
  }
});

// Register face
registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = nameInput.value.trim();
  if (!name) {
    alert("Please enter a name.");
    return;
  }

  // Register button is only enabled after a successful capture
  if (!registerBtn.disabled) {
    // Ensure webcam is started if not already (redundant, but safe)
    // await startWebcam();
    try {
      const imageBlob = await captureImage(); // Re-capture for registration
      const formData = new FormData();
      formData.append("image", imageBlob, "face.jpg");
      formData.append("name", name);
      formData.append("mode", systemMode);

      registerStatus.style.display = "block";
      registerStatus.className = "alert alert-info";
      registerStatus.textContent = "Registering face...";

      fetch("/register", {
        method: "POST",
        body: formData,
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.error) {
            registerStatus.className = "alert alert-danger";
            registerStatus.textContent = data.error;
          } else {
            registerStatus.className = "alert alert-success";
            registerStatus.textContent = data.message || "Face registered!";
            // Reset form and preview
            nameInput.value = "";
            previewImage.style.display = "none";
            previewImage.src = ""; // Clear preview image source
            registerBtn.disabled = true; // Disable register button until next capture
            // Re-enable capture button after registration (webcam is still active)
            // captureBtn.disabled = false;
          }
        })
        .catch((error) => {
          console.error("Registration fetch error:", error);
          registerStatus.className = "alert alert-danger";
          registerStatus.textContent =
            "Registration failed due to network error.";
        });
    } catch (error) {
      console.error("Registration capture failed:", error);
      registerStatus.style.display = "block";
      registerStatus.className = "alert alert-danger";
      registerStatus.textContent =
        "Registration failed: Could not capture image.";
    }
  } else {
    console.log("Register button is disabled.");
    registerStatus.style.display = "block";
    registerStatus.className = "alert alert-warning";
    registerStatus.textContent = "Please capture a face first.";
  }
});

// Switch Mode button handler
switchModeBtn.onclick = function () {
  modeOverlay.style.display = "flex";
  modeBanner.style.display = "none";
  switchModeBtn.style.display = "none";

  // Stop detection interval and clear image
  if (detectionIntervalId !== null) {
    clearInterval(detectionIntervalId);
    detectionIntervalId = null;
  }
  liveDetectionImg.src = "";
  statusDiv.style.display = "none"; // Hide status when showing overlay

  // Stop webcam when returning to mode selection
  stopWebcam();

  // Disable buttons when showing overlay
  captureBtn.disabled = true;
  registerBtn.disabled = true;
};

// Initial state: show mode overlay and disable buttons
modeOverlay.style.display = "flex";
captureBtn.disabled = true;
registerBtn.disabled = true;
// Initial webcam start is now handled by mode selection

// Function to load names from consents.csv
async function loadConsentNames() {
  try {
    const response = await fetch("/get_consent_names");
    const names = await response.json();
    const nameSelect = document.getElementById("name");

    console.log(names);

    // Clear existing options except the first one
    nameSelect.innerHTML = '<option value="">Select a name...</option>';

    // Add names to dropdown
    names.forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      nameSelect.appendChild(option);
    });
  } catch (error) {
    console.error("Error loading consent names:", error);
  }
}

// Call this when page loads
document.addEventListener("DOMContentLoaded", loadConsentNames);
