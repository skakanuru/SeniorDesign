
Sathvik Kakanuru <kakanuru.sathvik@gmail.com>
Wed, Dec 6, 2023, 7:56 PM
to me

import io
import socketserver
from threading import Condition, Thread
from http import server
import picamera2
import time
from PIL import Image, ImageEnhance
import numpy as np

PAGE = """\
<html>
<head>
<title>Cystoscope Stream</title>
<style>
    /* Your existing styles */
</style>
</head>
<body>
    <h1>Cystoscope View</h1>
    <div class="container">
        <div class="image-container">
            <img id="stream" src="stream.mjpg" width="640" height="480" />
        </div>
        <div class="controls-container">
            <button id="screenshotButton">Take Screenshot</button>
            <button id="zoomInButton">Zoom In</button>
            <button id="zoomOutButton">Zoom Out</button>
            <label for="brightnessSlider">Brightness:</label>
            <input type="range" id="brightnessSlider" min="0.5" max="1.5" step="0.01" value="1.0">
            <label for="contrastSlider">Contrast:</label>
            <input type="range" id="contrastSlider" min="0.5" max="1.5" step="0.01" value="1.0">
           
        </div>
    </div>
    <script>
        // Your existing JavaScript code

        // Voice command functionality
        var SpeechRecognition = SpeechRecognition || webkitSpeechRecognition;
        var recognition = new SpeechRecognition();

        recognition.continuous = true;
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onresult = function(event) {
            var last = event.results.length - 1;
            var command = event.results[last][0].transcript.trim().toLowerCase();

            if (command.includes('zoom in')) {
                apply_digital_zoom(1.1);
            } else if (command.includes('zoom out')) {
                apply_digital_zoom(0.9);
            } else if (command.includes('increase brightness')) {
                var brightnessSlider = document.getElementById('brightnessSlider');
                brightnessSlider.value = parseFloat(brightnessSlider.value) + 0.1;
                brightnessSlider.dispatchEvent(new Event('input'));
                current_brightness = current_brightness + 0.1
            } else if (command.includes('decrease brightness')) {        
                var brightnessSlider = document.getElementById('brightnessSlider');
                brightnessSlider.value = parseFloat(brightnessSlider.value) - 0.1;
                brightnessSlider.dispatchEvent(new Event('input'));
                current_brightness = current_brightness - 0.1
            } else if (command.includes('increase contrast')) {
                var contrastSlider = document.getElementById('contrastSlider');
                contrastSlider.value = parseFloat(contrastSlider.value) + 0.1;
                contrastSlider.dispatchEvent(new Event('input'));
                current_contrast = current_contrast + 0.1;
            } else if (command.includes('decrease contrast')) {
                var contrastSlider = document.getElementById('contrastSlider');
                contrastSlider.value = parseFloat(contrastSlider.value) - 0.1;
                contrastSlider.dispatchEvent(new Event('input'));
                current_contrast = current_contrast - 0.1;
            } else if (command.includes('take screenshot')) {
                takeScreenshot();
            }
        };

        recognition.start();

        function takeScreenshot() {
            var stream = document.getElementById('stream');
                var canvas = document.createElement('canvas');
            canvas.width = stream.width;
            canvas.height = stream.height;
            var ctx = canvas.getContext('2d');
            ctx.drawImage(stream, 0, 0, canvas.width, canvas.height);
            var dataURL = canvas.toDataURL('image/png');
            var link = document.createElement('a');
            link.download = 'screenshot.png';
            link.href = dataURL;
            link.click();
        }
    </script>
</body>
</html>
"""



current_zoom_level = 1.0
current_brightness = 1.0
current_contrast = 1.0    

class StreamingOutput:
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def update(self, frame):
        with self.condition:
            self.frame = frame
            self.condition.notify_all()

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        global current_zoom_level, current_brightness, current_contrast
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            while True:
                with output.condition:
                    output.condition.wait()
                    frame = output.frame
                self.wfile.write(b'--FRAME\r\n')
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', len(frame))
                self.end_headers()
                self.wfile.write(frame)
                self.wfile.write(b'\r\n')
        elif self.path.startswith('/zoom'):
            zoom_level = float(self.path.split('=')[1])
            current_zoom_level = zoom_level
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Zoom adjusted")
        elif self.path.startswith('/adjust'):
            query = self.path.split('?')[1]
            params = query.split('&')
            setting = params[0].split('=')[1]
            value = float(params[1].split('=')[1])

            if setting == 'brightness':
                current_brightness = value
                print(f"Updated brightness: {current_brightness}")
            elif setting == 'contrast':
                current_contrast = value
                print(f"Updated contrast: {current_contrast}")
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Setting adjusted")

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def convert_to_jpeg(np_image):
    if np_image.shape[2] == 4:
        np_image = np_image[:, :, :3]

    image = Image.fromarray(np_image)
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()
import numpy as np

def adjust_brightness_contrast(image, brightness, contrast):
   
    img_array = np.array(image, dtype=np.float64)

   
    img_array = img_array * brightness

 
    mean = np.mean(img_array)
    img_array = (1 - contrast) * mean + contrast * img_array

    img_array = np.clip(img_array, 0, 255).astype(np.uint8)

    new_image = Image.fromarray(img_array)

    return new_image


def apply_digital_zoom(image, zoom_level):
    if zoom_level <= 1.0:
        image = adjust_brightness_contrast(image, current_brightness, current_contrast)
        return image

    center_x, center_y = image.size[0] // 2, image.size[1] // 2
    width, height = image.size[0] / zoom_level, image.size[1] / zoom_level
    left = center_x - width // 2
    top = center_y - height // 2
    right = center_x + width // 2
    bottom = center_y + height // 2
   
    cropped_image = image.crop((left, top, right, bottom))
    resized_image = cropped_image.resize(image.size)
   
    image = adjust_brightness_contrast(resized_image, current_brightness, current_contrast)

    return image

camera = picamera2.Picamera2()
config = camera.create_preview_configuration()
camera.configure(config)

output = StreamingOutput()

def capture_frames():
    global current_zoom_level
    camera.start()
    while True:
        frame = camera.capture_array()
        pil_image = Image.fromarray(frame)
        zoomed_frame = apply_digital_zoom(pil_image, current_zoom_level)
        jpeg_frame = convert_to_jpeg(np.array(zoomed_frame))
        output.update(jpeg_frame)
        time.sleep(1.0 / 30)

try:
    capture_thread = Thread(target=capture_frames)
    capture_thread.start()

    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()
finally:
    camera.close()
