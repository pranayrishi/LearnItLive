from flask import Flask, render_template_string, jsonify, url_for, send_from_directory
import threading
import queue
import os
import sys
import time
import logging
import signal
import atexit
import hashlib
import subprocess
import importlib
from main import main as main_function

# Configure Flask to silence the default logging
app = Flask(__name__)
# Disable Flask's default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
# Also disable Flask internal logging
app.logger.disabled = True
log.disabled = True

# Set up the static folder
STATIC_FOLDER = "static"
os.makedirs(STATIC_FOLDER, exist_ok=True)

# Queue for transcript messages
transcript_queue = queue.Queue()

# File monitoring
monitored_files = {
    'video': {
        'path': os.path.join(STATIC_FOLDER, 'final_video.mp4'),
        'last_modified': 0,
        'hash': None
    },
    'image': {
        'path': os.path.join(STATIC_FOLDER, 'latest_frame.jpg'),
        'last_modified': 0,
        'hash': None
    }
}

whiteboard_process = None


# Redirect stdout from main.py to transcript_queue
class StreamToQueue:
    def __init__(self, q):
        self.q = q
        self.original_stdout = sys.stdout

    def write(self, message):
        message = message.strip()
        if message:
            self.q.put(message)
            # Also write to original stdout for debugging
            self.original_stdout.write(message + '\n')
            self.original_stdout.flush()

    def flush(self):
        self.original_stdout.flush()


# Global variable to control the main thread
main_thread_running = False
main_thread = None


def get_file_hash(filepath):
    """Get a hash of the file to detect content changes"""
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


def check_for_file_updates():
    """Check if monitored files have been updated"""
    updates = {'video': False, 'image': False}

    for file_type, info in monitored_files.items():
        filepath = info['path']

        # Check if file exists
        if not os.path.exists(filepath):
            # Check if it exists in root directory
            root_file = os.path.basename(filepath)
            if os.path.exists(root_file):
                # Copy file to static folder
                import shutil
                shutil.copy2(root_file, filepath)
                updates[file_type] = True
                monitored_files[file_type]['last_modified'] = os.path.getmtime(filepath)
                monitored_files[file_type]['hash'] = get_file_hash(filepath)
            continue

        # Check if file has been modified
        current_mtime = os.path.getmtime(filepath)
        current_hash = get_file_hash(filepath)

        if (current_mtime > monitored_files[file_type]['last_modified'] or
                current_hash != monitored_files[file_type]['hash']):
            updates[file_type] = True
            monitored_files[file_type]['last_modified'] = current_mtime
            monitored_files[file_type]['hash'] = current_hash
    return updates


def run_whiteboard():
    """Run the VirtualPainter in a separate process"""
    global whiteboard_process

    # Kill any existing whiteboard process
    if whiteboard_process and whiteboard_process.poll() is None:
        try:
            whiteboard_process.terminate()
            time.sleep(1)
        except:
            pass

    try:
        # Start VirtualPainter in a separate process
        whiteboard_process = subprocess.Popen([sys.executable, "-c",
                                               "from WhiteBoardFeature import VirtualPainter; VirtualPainter.VirtualPainter()"],
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        transcript_queue.put("🤖 AI: Starting the whiteboard feature...")
        return True
    except Exception as e:
        transcript_queue.put(f"🤖 AI: Error starting whiteboard: {str(e)}")
        return False


def intercept_whiteboard_calls(user_input):
    """Monitor for whiteboard requests in the main function"""
    if ("teach me" in user_input.lower() or "learn" in user_input.lower()) and main_thread_running:
        # Launch whiteboard in separate thread to not block main thread
        threading.Thread(target=run_whiteboard, daemon=True).start()


def modified_main():
    """Modified version of main.py's main function that intercepts whiteboard calls"""
    from main import main as original_main

    # Import get_voice_input to monkey patch it
    from main import get_voice_input as original_get_voice_input
    import main

    # Create a patched version of get_voice_input
    def patched_get_voice_input():
        user_input = original_get_voice_input()
        if user_input:
            intercept_whiteboard_calls(user_input)
        return user_input

    # Monkey patch the function
    main.get_voice_input = patched_get_voice_input

    # Run the original main
    original_main()


def run_main():
    global main_thread_running
    main_thread_running = True
    sys.stdout = StreamToQueue(transcript_queue)

    try:
        main_function()
    except Exception as e:
        transcript_queue.put(f"Error in main function: {e}")
    finally:
        main_thread_running = False
        sys.stdout = sys.__stdout__


def cleanup():
    """Clean up resources before exit"""
    global main_thread_running
    main_thread_running = False
    # Terminate whiteboard process if running
    if whiteboard_process and whiteboard_process.poll() is None:
        try:
            whiteboard_process.terminate()
        except:
            pass

    print("Cleaning up resources...")


# Register cleanup function
atexit.register(cleanup)

# Register signal handlers
signal.signal(signal.SIGINT, lambda s, f: cleanup())
signal.signal(signal.SIGTERM, lambda s, f: cleanup())


@app.route('/')
def index():
    """Render the main application page"""
    current_time = int(time.time())

    # Initialize file information
    for file_type, info in monitored_files.items():
        if os.path.exists(info['path']):
            monitored_files[file_type]['last_modified'] = os.path.getmtime(info['path'])
            monitored_files[file_type]['hash'] = get_file_hash(info['path'])

    # Check if video and image exist
    has_video = os.path.exists(monitored_files['video']['path'])
    has_image = os.path.exists(monitored_files['image']['path'])

    html = """
  <!DOCTYPE html>
  <html>
  <head>
      <title>LearnItLive</title>
      <style>
          body {
              margin: 0;
              padding: 0;
              height: 100vh;
              display: flex;
              background: linear-gradient(to right, #36d1dc, #5b86e5);
              font-family: Arial, sans-serif;
          }
          h1 {
            font-size: 60px;
            font-weight: bold;
            margin: 30px 0;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3); /* Optional: adds a subtle shadow */
            letter-spacing: 1px; /* Optional: spaces out the letters slightly */
          }
          .left-side {
              flex: 1;
              color: white;
              display: flex;
              justify-content: center;
              align-items: center;
              text-align: center;
          }
          .right-side {
              flex: 1;
              display: flex;
              flex-direction: column;
              padding: 20px;
              color: white;
          }
          .top-right {
              flex: 1;
              display: flex;
              justify-content: center;
              align-items: center;
              text-align: center;
              margin-bottom:10px;
          }
          .bottom-right {
              flex: 1;
              display: flex;
              justify-content: center;
              align-items: center;
              text-align: center;
          }
          #transcript {
              color: black;
              font-size: 1.2em;
              background-color: white;
              border-radius: 8px;
              padding: 10px;
              width: 90%;
              height: 100%;
              overflow-y: auto;
          }
          .controls {
              margin-top: 10px;
              display: flex;
              justify-content: center;
          }
          button {
              padding: 10px 15px;
              margin: 0 5px;
              border: none;
              border-radius: 5px;
              background-color: #4CAF50;
              color: white;
              cursor: pointer;
              font-weight: bold;
              transition: background-color 0.3s;
          }
          button:hover {
              background-color: #45a049;
          }
          button:disabled {
              background-color: #cccccc;
              cursor: not-allowed;
          }
          
          /* Circle animation styles */
           .wave-circle {
               width: 200px;
               height: 200px;
               border-radius: 50%;
               background-color: rgba(255, 255, 255, 0.5);
               margin: 30px 0; /*Originally -400px*/
               margin-left: 50px;
               animation: wave 2s infinite;
               opacity: 0; /* Initially invisible */
               animation-play-state: paused; /* Animation is paused initially */
           }
          .media-container {
              width: 620px;
              height: 360px;
              background-color: #000;
              border-radius: 8px;
              overflow: hidden;
              display: flex;
              justify-content: center;
              align-items: center;
              position: relative;
          }
          .media-container video, .media-container img {
              max-width: 100%;
              max-height: 100%;
              object-fit: contain;
          }
          .media-timestamp {
              position: absolute;
              bottom: 5px;
              right: 5px;
              color: white;
              font-size: 10px;
              background-color: rgba(0,0,0,0.5);
              padding: 2px 5px;
              border-radius: 3px;
          }
          .refresh-btn {
              position: absolute;
              top: 5px;
              right: 5px;
              background-color: rgba(0,0,0,0.5);
              color: white;
              border: none;
              border-radius: 3px;
              cursor: pointer;
              padding: 2px 5px;
              font-size: 12px;
          }
          .refresh-btn:hover {
              background-color: rgba(0,0,0,0.8);
          }
          #statusBadge {
              display: inline-block;
              padding: 5px 10px;
              border-radius: 15px;
              font-weight: bold;
              margin-left: 10px;
              font-size: 0.9em;
          }
          
          /* Circle animation keyframes */
           @keyframes wave {
               0% {
                   transform: scale(1);
                   opacity: 0.5;
               }
               50% {
                   transform: scale(1.5);
                   opacity: 0;
               }
               100% {
                   transform: scale(1);
                   opacity: 0.5;
               }
           }

          .whiteboard-btn {
              background-color: #007BFF;
              margin-top: 10px;
          }
          .whiteboard-btn:hover {
              background-color: #0056b3;
          }
      </style>
      <script>
          // Global variable to track if main program is running
          let isMainRunning = false;
          let mediaTimestamps = {
              video: 0,
              image: 0
          };




          function fetchTranscript() {
              fetch('/transcript')
                  .then(response => response.json())
                  .then(data => {
                      const transcriptDiv = document.getElementById('transcript');
                      if (data.clear) {
                          transcriptDiv.innerText = ''; // clear before new AI prompt
                      }
                      if (data.message) {
                          transcriptDiv.innerText += data.message + '\\n';
                          // Auto-scroll to bottom
                          transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
                      }




                      // Update UI based on server status
                      isMainRunning = data.is_running;
                      updateButtonState();
                  })
                  .catch(error => console.log(error));
          }




          function checkMediaUpdate() {
              fetch('/check_media')
                  .then(response => response.json())
                  .then(data => {
                      let updateNeeded = false;




                      // Check if there are updates
                      if (data.hasVideo && (data.videoTimestamp > mediaTimestamps.video)) {
                          mediaTimestamps.video = data.videoTimestamp;
                          updateNeeded = true;




                          // Update video element with cache-busting timestamp
                          const videoSrc = document.getElementById('videoSrc');
                          videoSrc.src = `{{ url_for('static', filename='final_video.mp4') }}?t=${Date.now()}`; // removed static




                          // Display video, hide image
                          document.getElementById('videoPlayer').style.display = 'block';
                          document.getElementById('capturedImage').style.display = 'none';




                          // Load video with new source
                          document.getElementById('videoPlayer').load();
                          document.getElementById('videoTimestamp').innerText = new Date().toLocaleTimeString();
                      }




                      if (data.hasImage && (data.imageTimestamp > mediaTimestamps.image)) {
                          mediaTimestamps.image = data.imageTimestamp;
                          updateNeeded = true;




                          // Update image element with cache-busting timestamp
                          const imgElement = document.getElementById('capturedImage');
                          imgElement.src = `{{ url_for('static', filename='latest_frame.jpg') }}?t=${Date.now()}`;




                          // If no video, show the image
                          if (!data.hasVideo) {
                              document.getElementById('videoPlayer').style.display = 'none';
                              document.getElementById('capturedImage').style.display = 'block';
                          }
                          document.getElementById('imageTimestamp').innerText = new Date().toLocaleTimeString();
                      }




                      // If any updates, log them
                      if (updateNeeded) {
                          console.log("Media updated at: " + new Date().toLocaleTimeString());
                      }
                  })
                  .catch(error => console.log(error));
          }




          function startMain() {
              fetch('/start_main', { method: 'POST' })
                  .then(response => response.json())
                  .then(data => {
                      if (data.status === 'started') {
                          isMainRunning = true;
                          updateButtonState();
                          document.getElementById("waveCircle").style.animationPlayState = "running";
                      } else {
                          alert('Failed to start program: ' + data.message);
                      }
                  })
                  .catch(error => {
                      console.log(error);
                      alert('Error starting program');
                  });
          }




          function stopMain() {
              fetch('/stop_main', { method: 'POST' })
                  .then(response => response.json())
                  .then(data => {
                      if (data.status === 'stopped') {
                          isMainRunning = false;
                          updateButtonState();
                          document.getElementById("waveCircle").style.animationPlayState = "paused";
                      } else {
                          alert('Failed to stop program: ' + data.message);
                      }
                  })
                  .catch(error => {
                      console.log(error);
                      alert('Error stopping program');
                  });
          }

          function startWhiteboard() {
              fetch('/start_whiteboard', { method: 'POST' })
                  .then(response => response.json())
                  .then(data => {
                      if (data.status === 'started') {
                          console.log('Whiteboard started successfully');
                      } else {
                          alert('Failed to start whiteboard: ' + data.message);
                      }
                  })
                  .catch(error => {
                      console.log(error);
                      alert('Error starting whiteboard');
                  });
          }






          function refreshMedia(type) {
              // Force browser to reload the media
              if (type === 'video') {
                  const videoSrc = document.getElementById('videoSrc');
                  videoSrc.src = `{{ url_for('static', filename='final_video.mp4') }}?t=${Date.now()}`;
                  document.getElementById('videoPlayer').load();
              } else if (type === 'image') {
                  const imgElement = document.getElementById('capturedImage');
                  imgElement.src = `{{ url_for('static', filename='latest_frame.jpg') }}?t=${Date.now()}`;
              }
          }




          function updateButtonState() {
              document.getElementById('startBtn').disabled = isMainRunning;
              document.getElementById('stopBtn').disabled = !isMainRunning;
              document.getElementById('whiteboardBtn').disabled = !isMainRunning;




              const statusText = document.getElementById('statusText');
              const statusBadge = document.getElementById('statusBadge');




              if (isMainRunning) {
                  statusText.innerText = 'Status:';
                  statusBadge.innerText = 'RUNNING';
                  statusBadge.style.backgroundColor = '#4CAF50';
              } else {
                  statusText.innerText = 'Status:';
                  statusBadge.innerText = 'STOPPED';
                  statusBadge.style.backgroundColor = '#F44336';
              }
          }




          // Poll transcript every second
          setInterval(fetchTranscript, 1000);




          // Check for media updates every second
          setInterval(checkMediaUpdate, 1000);




          // Check initial state when page loads
          window.onload = function() {
              fetchTranscript();
              updateButtonState();
              checkMediaUpdate();
          };
      </script>
  </head>
  <body>
      <div class="left-side">
          <div>
              <h1>LearnItLive</h1>
              <div>
                  <span id="statusText">Status:</span>
                  <span id="statusBadge" style="background-color: #F44336;">STOPPED</span>
              </div>
              <!-- Circle Wave Animation -->
              <div id="waveCircle" class="wave-circle">
            </div>
              <div class="controls">
                  <button id="startBtn" onclick="startMain()">Start Program</button>
                  <button id="stopBtn" onclick="stopMain()" disabled>Stop Program</button>
              </div>
              <div class="controls">
                  <button id="whiteboardBtn" class="whiteboard-btn" onclick="startWhiteboard()" disabled>Open Whiteboard</button>
              </div>
          </div>
      </div>
      <div class="right-side">
          <div class="top-right">
              <div class="media-container">
                  <video controls id="videoPlayer" style="display: {{ 'block' if has_video else 'none' }};">
                      <source id="videoSrc" src="{{ url_for('static', filename='final_video.mp4', t=current_time) }}"
                              type="video/mp4" onerror="this.style.display='none';">
                      Your browser does not support the video tag.
                  </video>
                  <img id="capturedImage" src="{{ url_for('static', filename='latest_frame.jpg', t=current_time) }}"
                       style="display: {{ 'block' if has_image and not has_video else 'none' }};"
                       onerror="this.style.display='none';">
                  <button class="refresh-btn" onclick="refreshMedia('video')">⟳ Refresh Video</button>
                  <div id="videoTimestamp" class="media-timestamp">-</div>
                  <div id="imageTimestamp" class="media-timestamp">-</div>
              </div>
          </div>
          <div class="bottom-right">
              <div id="transcript"><em>Waiting for AI response...</em></div>
          </div>
      </div>
  </body>
  </html>
  """
    return render_template_string(html, current_time=current_time)


@app.route('/check_media')
def check_media():
    """Check for media updates and return their status"""
    updates = check_for_file_updates()

    return jsonify({
        'hasVideo': os.path.exists(monitored_files['video']['path']),
        'hasImage': os.path.exists(monitored_files['image']['path']),
        'videoTimestamp': monitored_files['video']['last_modified'],
        'imageTimestamp': monitored_files['image']['last_modified'],
        'updates': updates
    })


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files with proper caching headers"""
    response = send_from_directory(STATIC_FOLDER, filename)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/transcript')
def get_transcript():
    global main_thread_running
    message = ''
    clear = False
    try:
        while not transcript_queue.empty():
            next_msg = transcript_queue.get_nowait()
            if "🤖 AI:" in next_msg:
                clear = True
            message += next_msg + "\n"
    except queue.Empty:
        pass
    return jsonify({
        'message': message.strip(),
        'clear': clear,
        'is_running': main_thread_running
    })


@app.route('/start_main', methods=['POST'])
def start_main():
    global main_thread, main_thread_running

    if main_thread_running:
        return jsonify({'status': 'already_running', 'message': 'Program is already running'})

    try:
        main_thread = threading.Thread(target=run_main, daemon=True)
        main_thread.start()
        # Wait a moment to ensure the thread starts properly
        time.sleep(0.5)
        return jsonify({'status': 'started', 'message': 'Program started successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to start program: {str(e)}'})


@app.route('/start_whiteboard', methods=['POST'])
def start_whiteboard():
    """Start the whiteboard in a separate process"""
    if not main_thread_running:
        return jsonify({'status': 'error', 'message': 'Main program must be running first'})

    success = run_whiteboard()
    if success:
        return jsonify({'status': 'started', 'message': 'Whiteboard started successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to start whiteboard'})


@app.route('/stop_main', methods=['POST'])
def stop_main():
    global main_thread_running, whiteboard_process

    if not main_thread_running:
        return jsonify({'status': 'not_running', 'message': 'Program is not running'})

    try:
        # Kill any existing whiteboard process
        if whiteboard_process and whiteboard_process.poll() is None:
            try:
                whiteboard_process.terminate()
            except:
                pass

        # Signal the main thread to stop
        main_thread_running = False
        # Give it some time to clean up
        time.sleep(1)
        return jsonify({'status': 'stopped', 'message': 'Program stopped successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to stop program: {str(e)}'})


@app.route('/refresh_video')
def refresh_video():
    """Force browser to reload the video by adding a timestamp parameter"""
    return jsonify({'status': 'success', 'timestamp': int(time.time())})


# Completely silence the Flask server output
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

if __name__ == '__main__':
    # Make sure the static folder exists
    os.makedirs('static', exist_ok=True)

    # Create a placeholder video if needed
    if not os.path.exists('static/placeholder.mp4'):
        with open('static/placeholder.mp4', 'w') as f:
            f.write('placeholder')

    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    signal.signal(signal.SIGTERM, lambda s, f: cleanup())

    # Use threaded=False to avoid more logging issues
    app.run(debug=False, host='0.0.0.0', port=8000, use_reloader=False, threaded=True)
