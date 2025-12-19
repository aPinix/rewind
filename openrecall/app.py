from threading import Thread

import numpy as np
from flask import Flask, render_template_string, request, send_from_directory
from jinja2 import BaseLoader

from openrecall.config import appdata_folder, screenshots_path
from openrecall.database import create_db, get_all_entries, get_timestamps
from openrecall.nlp import cosine_similarity, get_embedding
from openrecall.screenshot import record_screenshots_thread
from openrecall.utils import human_readable_time, timestamp_to_human_readable

app = Flask(__name__)

app.jinja_env.filters["human_readable_time"] = human_readable_time
app.jinja_env.filters["timestamp_to_human_readable"] = timestamp_to_human_readable

base_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OpenRecall</title>
  <!-- Bootstrap CSS -->
  <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.3.0/font/bootstrap-icons.css">
  <style>
    .slider-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px;
    }
    .slider {
      width: 80%;
    }
    .slider-value {
      margin-top: 10px;
      font-size: 1.2em;
    }
    .image-container {
      margin-top: 20px;
      text-align: center;
    }
    .image-container img {
      max-width: 100%;
      height: auto;
    }
    .text-block-icon {
      position: absolute;
      background: rgba(0, 123, 255, 0.9);
      color: white;
      border-radius: 50%;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      transition: all 0.2s;
      pointer-events: auto;
      z-index: 10;
    }
    .text-block-icon:hover {
      background: rgba(0, 123, 255, 1);
      transform: scale(1.1);
    }
    .text-popup {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: white;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      max-width: 600px;
      max-height: 80vh;
      overflow: hidden;
      z-index: 1000;
      display: none;
    }
    .text-popup.show {
      display: block;
    }
    .text-popup-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0,0,0,0.5);
      z-index: 999;
      display: none;
    }
    .text-popup-overlay.show {
      display: block;
    }
    .text-popup-header {
      padding: 15px;
      border-bottom: 1px solid #dee2e6;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .text-popup-body {
      padding: 15px;
      max-height: 60vh;
      overflow-y: auto;
    }
    .text-popup-footer {
      padding: 15px;
      border-top: 1px solid #dee2e6;
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }
  </style>
</head>
<body>
<nav class="navbar navbar-light bg-light">
  <div class="container">
    <form class="form-inline my-2 my-lg-0 w-100 d-flex" action="/search" method="get">
      <input class="form-control flex-grow-1 mr-sm-2" type="search" name="q" placeholder="Search" aria-label="Search">
      <button class="btn btn-outline-secondary my-2 my-sm-0" type="submit">
        <i class="bi bi-search"></i>
      </button>
    </form>
  </div>
</nav>
{% block content %}

{% endblock %}

  <!-- Bootstrap and jQuery JS -->
  <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.5.3/dist/umd/popper.min.js"></script>
  <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
  
</body>
</html>
"""


class StringLoader(BaseLoader):
    def get_source(self, environment, template):
        if template == "base_template":
            return base_template, None, lambda: True
        return None, None, None


app.jinja_env.loader = StringLoader()


@app.route("/")
def timeline():
    # connect to db
    timestamps = get_timestamps()
    entries = get_all_entries()
    entries_dict = {entry.timestamp: entry for entry in entries}
    return render_template_string(
        """
{% extends "base_template" %}
{% block content %}
{% if timestamps|length > 0 %}
  <div class="container-fluid" style="height: calc(100vh - 100px); display: flex; flex-direction: column;">
    <div class="slider-container">
      <input type="range" class="slider custom-range" id="discreteSlider" min="0" max="{{timestamps|length - 1}}" step="1" value="{{timestamps|length - 1}}">
      <div class="slider-value" id="sliderValue">{{timestamps[0] | timestamp_to_human_readable }}</div>
    </div>
    <div class="row flex-grow-1" style="overflow: hidden;">
      <div class="col-md-8" style="height: 100%; overflow-y: auto; display: flex; align-items: center; justify-content: center; position: relative;">
        <div id="imageWrapper" style="position: relative; display: inline-block;">
          <img id="timestampImage" src="/static/{{timestamps[0]}}.webp" alt="Image for timestamp" style="max-width: 100%; max-height: 100%; object-fit: contain; display: block;">
          <div id="textOverlay" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;"></div>
        </div>
      </div>
      <div class="col-md-4 p-3 bg-light border-left" style="height: 100%; overflow-y: auto;">
        <div class="mb-3">
          <label class="d-flex align-items-center">
            <input type="checkbox" id="showOverlay" checked class="mr-2">
            <span>Show text blocks on image</span>
          </label>
        </div>
        <div class="d-flex justify-content-between align-items-center mb-2">
          <strong>All Extracted Text:</strong>
          <button class="btn btn-sm btn-outline-primary" onclick="copyCurrentText()">
            <i class="bi bi-clipboard"></i> Copy All
          </button>
        </div>
        <pre id="extractedText" style="white-space: pre-wrap; word-wrap: break-word; margin: 0; font-size: 0.9em; user-select: text;"></pre>
      </div>
    </div>
    
    <div class="text-popup-overlay" id="textPopupOverlay" onclick="closeTextPopup()"></div>
    <div class="text-popup" id="textPopup">
      <div class="text-popup-header">
        <strong>Text Block</strong>
        <button type="button" class="close" onclick="closeTextPopup()">&times;</button>
      </div>
      <div class="text-popup-body">
        <pre id="popupText" style="white-space: pre-wrap; word-wrap: break-word; margin: 0; user-select: text;"></pre>
      </div>
      <div class="text-popup-footer">
        <button class="btn btn-sm btn-secondary" onclick="closeTextPopup()">Close</button>
        <button class="btn btn-sm btn-primary" onclick="copyPopupText()">
          <i class="bi bi-clipboard"></i> Copy Text
        </button>
      </div>
    </div>
  </div>
  <script>
    const timestamps = {{ timestamps|tojson }};
    const entriesData = {{ entries_dict|tojson }};
    const slider = document.getElementById('discreteSlider');
    const sliderValue = document.getElementById('sliderValue');
    const timestampImage = document.getElementById('timestampImage');
    const extractedText = document.getElementById('extractedText');
    const textOverlay = document.getElementById('textOverlay');
    const showOverlayCheckbox = document.getElementById('showOverlay');
    const textPopup = document.getElementById('textPopup');
    const textPopupOverlay = document.getElementById('textPopupOverlay');
    const popupText = document.getElementById('popupText');
    
    let currentEntry = null;

    function groupWordsIntoBlocks(words) {
      if (!words || words.length === 0) return [];
      
      const blocks = [];
      let currentBlock = [words[0]];
      
      for (let i = 1; i < words.length; i++) {
        const prev = words[i - 1];
        const curr = words[i];
        
        // Check if words are on similar Y position (same line) or close vertically
        const verticalDistance = Math.abs(curr.y1 - prev.y1);
        const avgHeight = (curr.y2 - curr.y1 + prev.y2 - prev.y1) / 2;
        
        if (verticalDistance < avgHeight * 0.5) {
          currentBlock.push(curr);
        } else {
          blocks.push(currentBlock);
          currentBlock = [curr];
        }
      }
      blocks.push(currentBlock);
      
      // Merge blocks into text regions
      return blocks.map(block => {
        const minX = Math.min(...block.map(w => w.x1));
        const minY = Math.min(...block.map(w => w.y1));
        const maxX = Math.max(...block.map(w => w.x2));
        const maxY = Math.max(...block.map(w => w.y2));
        const text = block.map(w => w.text).join(' ');
        
        return { x1: minX, y1: minY, x2: maxX, y2: maxY, text };
      });
    }

    function renderTextOverlay() {
      textOverlay.innerHTML = '';
      if (!showOverlayCheckbox.checked || !currentEntry || !currentEntry.words_coords) return;
      
      const img = timestampImage;
      const displayWidth = img.width;
      const displayHeight = img.height;
      
      const blocks = groupWordsIntoBlocks(currentEntry.words_coords);
      
      blocks.forEach((block, index) => {
        const icon = document.createElement('div');
        icon.className = 'text-block-icon';
        icon.innerHTML = '<i class="bi bi-file-text"></i>';
        icon.style.left = (block.x1 * displayWidth) + 'px';
        icon.style.top = (block.y1 * displayHeight) + 'px';
        icon.title = 'Click to view text';
        icon.onclick = () => showTextPopup(block.text);
        textOverlay.appendChild(icon);
      });
    }

    function showTextPopup(text) {
      popupText.textContent = text;
      textPopup.classList.add('show');
      textPopupOverlay.classList.add('show');
    }

    function closeTextPopup() {
      textPopup.classList.remove('show');
      textPopupOverlay.classList.remove('show');
    }

    function copyPopupText() {
      const text = popupText.textContent;
      navigator.clipboard.writeText(text).then(() => {
        alert('Text copied to clipboard!');
      });
    }

    function updateDisplay(timestamp) {
      sliderValue.textContent = new Date(timestamp / 1000).toLocaleString();
      timestampImage.src = `/static/${timestamp}.webp`;
      currentEntry = entriesData[timestamp];
      extractedText.textContent = currentEntry ? currentEntry.text : 'No text available';
      
      timestampImage.onload = renderTextOverlay;
    }

    slider.addEventListener('input', function() {
      const reversedIndex = timestamps.length - 1 - slider.value;
      const timestamp = timestamps[reversedIndex];
      updateDisplay(timestamp);
    });
    
    showOverlayCheckbox.addEventListener('change', renderTextOverlay);
    window.addEventListener('resize', renderTextOverlay);

    function copyCurrentText() {
      const text = extractedText.textContent;
      navigator.clipboard.writeText(text).then(() => {
        alert('Text copied to clipboard!');
      });
    }

    // Initialize the slider with a default value
    slider.value = timestamps.length - 1;
    updateDisplay(timestamps[0]);
  </script>
{% else %}
  <div class="container">
      <div class="alert alert-info" role="alert">
          Nothing recorded yet, wait a few seconds.
      </div>
  </div>
{% endif %}
{% endblock %}
""",
        timestamps=timestamps,
        entries_dict=entries_dict,
    )


@app.route("/search")
def search():
    q = request.args.get("q")
    entries = get_all_entries()
    embeddings = [np.frombuffer(entry.embedding, dtype=np.float32) for entry in entries]
    query_embedding = get_embedding(q)
    similarities = [cosine_similarity(query_embedding, emb) for emb in embeddings]
    indices = np.argsort(similarities)[::-1]
    sorted_entries = [entries[i] for i in indices]

    return render_template_string(
        """
{% extends "base_template" %}
{% block content %}
    <div class="container">
        <div class="row">
            {% for entry in entries %}
                <div class="col-md-3 mb-4">
                    <div class="card">
                        <a href="#" data-toggle="modal" data-target="#modal-{{ loop.index0 }}">
                            <img src="/static/{{ entry['timestamp'] }}.webp" alt="Image" class="card-img-top">
                        </a>
                    </div>
                </div>
                <div class="modal fade" id="modal-{{ loop.index0 }}" tabindex="-1" role="dialog" aria-labelledby="exampleModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-xl" role="document" style="max-width: none; width: 100vw; height: 100vh; padding: 20px;">
                        <div class="modal-content" style="height: calc(100vh - 40px); width: calc(100vw - 40px); padding: 0;">
                            <div class="modal-body" style="padding: 0; display: flex; height: 100%;">
                                <div style="flex: 2; display: flex; align-items: center; justify-content: center; overflow: auto; padding: 10px; position: relative;">
                                    <div style="position: relative; display: inline-block;">
                                        <img id="modalImg{{ loop.index0 }}" src="/static/{{ entry['timestamp'] }}.webp" alt="Image" style="max-width: 100%; max-height: 100%; object-fit: contain; display: block;">
                                        <div id="modalOverlay{{ loop.index0 }}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;"></div>
                                    </div>
                                    
                                    <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 2000; display: none;" id="modalPopupOverlay{{ loop.index0 }}" onclick="closeModalTextPopup{{ loop.index0 }}()"></div>
                                    <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); max-width: 600px; max-height: 80vh; overflow: hidden; z-index: 2001; display: none;" id="modalTextPopup{{ loop.index0 }}">
                                        <div style="padding: 15px; border-bottom: 1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center;">
                                            <strong>Text Block</strong>
                                            <button type="button" class="close" onclick="closeModalTextPopup{{ loop.index0 }}()">&times;</button>
                                        </div>
                                        <div style="padding: 15px; max-height: 60vh; overflow-y: auto;">
                                            <pre id="modalPopupText{{ loop.index0 }}" style="white-space: pre-wrap; word-wrap: break-word; margin: 0; user-select: text;"></pre>
                                        </div>
                                        <div style="padding: 15px; border-top: 1px solid #dee2e6; display: flex; justify-content: flex-end; gap: 10px;">
                                            <button class="btn btn-sm btn-secondary" onclick="closeModalTextPopup{{ loop.index0 }}()">Close</button>
                                            <button class="btn btn-sm btn-primary" onclick="copyModalPopupText{{ loop.index0 }}()">
                                                <i class="bi bi-clipboard"></i> Copy Text
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                {% if entry['text'] %}
                                <div class="p-3 bg-light border-left" style="flex: 1; overflow-y: auto; min-width: 300px;">
                                    <div class="mb-3">
                                        <label class="d-flex align-items-center">
                                            <input type="checkbox" id="showModalOverlay{{ loop.index0 }}" checked class="mr-2">
                                            <span>Show text overlay</span>
                                        </label>
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <strong>Extracted Text:</strong>
                                        <button class="btn btn-sm btn-outline-primary" onclick="copyText{{ loop.index0 }}()">
                                            <i class="bi bi-clipboard"></i> Copy
                                        </button>
                                    </div>
                                    <pre id="text-{{ loop.index0 }}" style="white-space: pre-wrap; word-wrap: break-word; margin: 0; font-size: 0.9em; user-select: text;">{{ entry['text'] }}</pre>
                                </div>
                                <script>
                                    (function() {
                                        const wordsCoords = {{ entry['words_coords']|tojson }};
                                        const img = document.getElementById('modalImg{{ loop.index0 }}');
                                        const overlay = document.getElementById('modalOverlay{{ loop.index0 }}');
                                        const checkbox = document.getElementById('showModalOverlay{{ loop.index0 }}');
                                        
                                        function groupWordsIntoBlocks(words) {
                                            if (!words || words.length === 0) return [];
                                            
                                            const blocks = [];
                                            let currentBlock = [words[0]];
                                            
                                            for (let i = 1; i < words.length; i++) {
                                                const prev = words[i - 1];
                                                const curr = words[i];
                                                
                                                const verticalDistance = Math.abs(curr.y1 - prev.y1);
                                                const avgHeight = (curr.y2 - curr.y1 + prev.y2 - prev.y1) / 2;
                                                
                                                if (verticalDistance < avgHeight * 0.5) {
                                                    currentBlock.push(curr);
                                                } else {
                                                    blocks.push(currentBlock);
                                                    currentBlock = [curr];
                                                }
                                            }
                                            blocks.push(currentBlock);
                                            
                                            return blocks.map(block => {
                                                const minX = Math.min(...block.map(w => w.x1));
                                                const minY = Math.min(...block.map(w => w.y1));
                                                const maxX = Math.max(...block.map(w => w.x2));
                                                const maxY = Math.max(...block.map(w => w.y2));
                                                const text = block.map(w => w.text).join(' ');
                                                
                                                return { x1: minX, y1: minY, x2: maxX, y2: maxY, text };
                                            });
                                        }
                                        
                                        function showModalTextPopup{{ loop.index0 }}(text) {
                                            const existingPopup = document.getElementById('modalTextPopup{{ loop.index0 }}');
                                            if (existingPopup) {
                                                document.getElementById('modalPopupText{{ loop.index0 }}').textContent = text;
                                                existingPopup.style.display = 'block';
                                                document.getElementById('modalPopupOverlay{{ loop.index0 }}').style.display = 'block';
                                            }
                                        }
                                        
                                        function closeModalTextPopup{{ loop.index0 }}() {
                                            document.getElementById('modalTextPopup{{ loop.index0 }}').style.display = 'none';
                                            document.getElementById('modalPopupOverlay{{ loop.index0 }}').style.display = 'none';
                                        }
                                        
                                        window.closeModalTextPopup{{ loop.index0 }} = closeModalTextPopup{{ loop.index0 }};
                                        
                                        function copyModalPopupText{{ loop.index0 }}() {
                                            const text = document.getElementById('modalPopupText{{ loop.index0 }}').textContent;
                                            navigator.clipboard.writeText(text).then(() => {
                                                alert('Text copied to clipboard!');
                                            });
                                        }
                                        
                                        window.copyModalPopupText{{ loop.index0 }} = copyModalPopupText{{ loop.index0 }};
                                        
                                        function renderModalOverlay() {
                                            overlay.innerHTML = '';
                                            if (!checkbox.checked || !wordsCoords) return;
                                            
                                            const displayWidth = img.width;
                                            const displayHeight = img.height;
                                            
                                            const blocks = groupWordsIntoBlocks(wordsCoords);
                                            
                                            blocks.forEach((block, index) => {
                                                const icon = document.createElement('div');
                                                icon.className = 'text-block-icon';
                                                icon.innerHTML = '<i class="bi bi-file-text"></i>';
                                                icon.style.left = (block.x1 * displayWidth) + 'px';
                                                icon.style.top = (block.y1 * displayHeight) + 'px';
                                                icon.title = 'Click to view text';
                                                icon.onclick = () => showModalTextPopup{{ loop.index0 }}(block.text);
                                                overlay.appendChild(icon);
                                            });
                                        }
                                        
                                        img.onload = renderModalOverlay;
                                        checkbox.addEventListener('change', renderModalOverlay);
                                        $('#modal-{{ loop.index0 }}').on('shown.bs.modal', renderModalOverlay);
                                    })();
                                    
                                    function copyText{{ loop.index0 }}() {
                                        const text = document.getElementById('text-{{ loop.index0 }}').textContent;
                                        navigator.clipboard.writeText(text).then(() => {
                                            alert('Text copied to clipboard!');
                                        });
                                    }
                                </script>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
            {% endfor %}
        </div>
    </div>
{% endblock %}
""",
        entries=sorted_entries,
    )


@app.route("/static/<filename>")
def serve_image(filename):
    return send_from_directory(screenshots_path, filename)


if __name__ == "__main__":
    create_db()

    print(f"Appdata folder: {appdata_folder}")

    # Start the thread to record screenshots
    t = Thread(target=record_screenshots_thread)
    t.start()

    app.run(port=8082)
