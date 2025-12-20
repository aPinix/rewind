from threading import Thread
import os
import base64

import numpy as np
from flask import Flask, render_template_string, request, send_from_directory, jsonify
from jinja2 import BaseLoader
from PIL import Image

from openrecall.config import appdata_folder, screenshots_path
from openrecall.database import create_db, get_all_entries, get_timestamps, update_ai_ocr
from openrecall.nlp import cosine_similarity, get_embedding
from openrecall.screenshot import record_screenshots_thread
from openrecall.utils import human_readable_time, timestamp_to_human_readable
from openrecall.ai_ocr import get_ai_provider

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
    * {
      overscroll-behavior-x: none;
      overscroll-behavior-y: contain;
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body, html {
      overscroll-behavior-x: none;
      height: 100vh;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #000;
      color: #fff;
    }
    
    /* Fullscreen layout */
    .fullscreen-container {
      width: 100vw;
      height: 100vh;
      display: flex;
      flex-direction: column;
      position: relative;
    }
    
    /* Search bar - top right */
    .search-container {
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 1000;
    }
    .search-input {
      width: 400px;
      padding: 12px 20px;
      padding-right: 45px;
      border-radius: 24px;
      border: 1px solid rgba(255, 255, 255, 0.2);
      background: rgba(30, 30, 30, 0.9);
      backdrop-filter: blur(20px);
      color: #fff;
      font-size: 15px;
      transition: all 0.2s;
    }
    .search-input:focus {
      outline: none;
      border-color: rgba(0, 123, 255, 0.6);
      background: rgba(40, 40, 40, 0.95);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    .search-icon {
      position: absolute;
      right: 15px;
      top: 50%;
      transform: translateY(-50%);
      color: rgba(255, 255, 255, 0.5);
      pointer-events: none;
    }
    
    /* Search results modal */
    .search-results-modal {
      position: fixed;
      top: 80px;
      right: 20px;
      width: 800px;
      max-height: calc(100vh - 120px);
      background: rgba(30, 30, 30, 0.98);
      backdrop-filter: blur(40px);
      border-radius: 16px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
      padding: 20px;
      overflow-y: auto;
      display: none;
      z-index: 999;
    }
    .search-results-modal.show {
      display: block;
    }
    .search-results-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 16px;
    }
    .search-result-card {
      background: rgba(50, 50, 50, 0.6);
      border-radius: 12px;
      overflow: hidden;
      cursor: pointer;
      transition: all 0.2s;
      border: 2px solid transparent;
    }
    .search-result-card:hover {
      transform: scale(1.05);
      border-color: rgba(0, 123, 255, 0.6);
      box-shadow: 0 8px 24px rgba(0, 123, 255, 0.3);
    }
    .search-result-card img {
      width: 100%;
      height: 120px;
      object-fit: cover;
    }
    .search-result-time {
      padding: 8px 12px;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.6);
      text-align: center;
    }
    
    /* Main screenshot area */
    .screenshot-area {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 60px 40px 120px;
      position: relative;
    }
    .screenshot-wrapper {
      position: relative;
      max-width: 100%;
      max-height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .screenshot-wrapper img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      border-radius: 8px;
      box-shadow: 0 20px 80px rgba(0, 0, 0, 0.5);
    }
    
    /* Text overlay icons */
    .text-block-icon {
      position: absolute;
      background: rgba(0, 123, 255, 0.15);
      color: rgba(255, 255, 255, 0.4);
      border-radius: 50%;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 16px;
      transition: all 0.2s;
      pointer-events: auto;
      z-index: 10;
    }
    .text-block-icon:hover {
      background: rgba(0, 123, 255, 0.9);
      color: white;
      transform: scale(1.2);
      box-shadow: 0 4px 12px rgba(0, 123, 255, 0.4);
    }
    
    /* Timeline - bottom center */
    .timeline-container {
      position: fixed;
      bottom: 30px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 1000;
    }
    .timeline-pill {
      background: rgba(30, 30, 30, 0.95);
      backdrop-filter: blur(40px);
      border-radius: 32px;
      padding: 16px 32px;
      border: 1px solid rgba(255, 255, 255, 0.15);
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      min-width: 400px;
    }
    .timeline-date {
      font-size: 14px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.9);
      letter-spacing: 0.3px;
    }
    .timeline-slider {
      width: 100%;
      height: 4px;
      -webkit-appearance: none;
      appearance: none;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 2px;
      outline: none;
    }
    .timeline-slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #007bff;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0, 123, 255, 0.4);
    }
    .timeline-slider::-moz-range-thumb {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #007bff;
      cursor: pointer;
      border: none;
      box-shadow: 0 2px 8px rgba(0, 123, 255, 0.4);
    }
    
    /* Text popup */
      z-index: 1100;
      background: white;
      border-radius: 50%;
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 10px rgba(0,0,0,0.2);
      cursor: pointer;
      transition: all 0.2s;
    }
    .home-icon:hover {
      transform: scale(1.1);
      box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .toggle-sidebar-btn {
      position: fixed;
      top: 75px;
      right: 15px;
      z-index: 1100;
      background: white;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 10px rgba(0,0,0,0.2);
      cursor: pointer;
      transition: all 0.2s;
      border: 2px solid #007bff;
    }
    .toggle-sidebar-btn:hover {
      transform: scale(1.1);
      background: #007bff;
      color: white;
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
<a href="/" class="home-icon" title="Home">
  <i class="bi bi-house-fill" style="font-size: 1.5rem; color: #007bff;"></i>
</a>
<a href="/timeline-v2" class="fullscreen-link" title="Fullscreen View">
  <i class="bi bi-fullscreen"></i>
</a>
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
@app.route("/timeline-v2")
def timeline_v2():
    """New Rewind.ai style interface"""
    timestamps = get_timestamps()
    entries = get_all_entries()
    entries_dict = {
        entry.timestamp: {
            'id': entry.id,
            'text': entry.text,
            'timestamp': entry.timestamp,
            'words_coords': entry.words_coords,
            'ai_text': entry.ai_text,
            'ai_words_coords': entry.ai_words_coords if entry.ai_words_coords else []
        }
        for entry in entries
    }
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OpenRecall</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.3.0/font/bootstrap-icons.css">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; overscroll-behavior-x: none; }
    body, html {
      height: 100vh; overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #000; color: #fff;
    }
    .fullscreen-container { width: 100vw; height: 100vh; position: relative; }
    
    /* Search bar */
    .search-container { position: fixed; top: 20px; right: 20px; z-index: 1000; }
    .search-wrapper { position: relative; }
    .search-input {
      width: min(400px, calc(100vw - 100px)); padding: 12px 45px 12px 20px; border-radius: 24px;
      border: 1px solid rgba(255,255,255,0.15); background: rgba(20,20,20,0.75);
      backdrop-filter: blur(30px); color: #fff; font-size: 15px; transition: all 0.2s;
    }
    .search-input:focus {
      outline: none; border-color: rgba(0,123,255,0.5);
      background: rgba(30,30,30,0.85); box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    .search-icon { position: absolute; right: 15px; top: 50%; transform: translateY(-50%); color: rgba(255,255,255,0.4); }
    
    /* Search results */
    .search-results {
      position: fixed; top: 80px; right: 20px; 
      width: min(850px, calc(100vw - 40px)); max-height: calc(100vh - 120px);
      background: rgba(30,30,30,0.98); backdrop-filter: blur(40px); border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 20px 60px rgba(0,0,0,0.6);
      padding: 20px; overflow-y: auto; display: none; z-index: 999;
    }
    .search-results.show { display: block; }
    .results-grid {
      display: grid; 
      grid-template-columns: repeat(auto-fill, minmax(min(180px, 100%), 1fr)); 
      gap: 16px;
    }
    .result-card {
      background: rgba(50,50,50,0.6); border-radius: 12px; overflow: hidden;
      cursor: pointer; transition: all 0.2s; border: 2px solid transparent;
    }
    .result-card:hover {
      transform: scale(1.05); border-color: rgba(0,123,255,0.6);
      box-shadow: 0 8px 24px rgba(0,123,255,0.3);
    }
    .result-card img { width: 100%; height: 120px; object-fit: cover; }
    .result-time { padding: 8px 12px; font-size: 11px; color: rgba(255,255,255,0.6); text-align: center; }
    
    /* Screenshot area */
    .screenshot-area {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
    }
    .screenshot-wrapper { 
      position: relative; 
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .screenshot-wrapper img {
      width: 100%;
      height: 100%;
      object-fit: contain; 
      border-radius: 8px;
      box-shadow: 0 20px 80px rgba(0,0,0,0.5);
    }
    .text-overlay { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); pointer-events: none; }
    
    /* Text icons */
    .text-icon {
      position: absolute; background: rgba(0,123,255,0.15); color: rgba(255,255,255,0.4);
      border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center;
      justify-content: center; cursor: pointer; transition: all 0.2s; pointer-events: auto; z-index: 10;
    }
    .text-icon:hover {
      background: rgba(0,123,255,0.9); color: white; transform: scale(1.2);
      box-shadow: 0 4px 12px rgba(0,123,255,0.4);
    }
    
    /* Timeline */
    .timeline {
      position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); z-index: 1000;
    }
    .timeline-pill {
      background: rgba(20,20,20,0.75); backdrop-filter: blur(30px); border-radius: 32px;
      padding: 16px 32px; border: 1px solid rgba(255,255,255,0.12);
      box-shadow: 0 10px 40px rgba(0,0,0,0.5); display: flex; flex-direction: column;
      align-items: center; gap: 12px; min-width: 400px;
    }
    .timeline-date {
      font-size: 14px; font-weight: 500; color: rgba(255,255,255,0.85); letter-spacing: 0.3px;
    }
    .timeline-slider {
      width: 100%; height: 4px; -webkit-appearance: none; appearance: none;
      background: rgba(255,255,255,0.2); border-radius: 2px; outline: none;
    }
    .timeline-slider::-webkit-slider-thumb {
      -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%;
      background: #007bff; cursor: pointer; box-shadow: 0 2px 8px rgba(0,123,255,0.4);
    }
    .timeline-slider::-moz-range-thumb {
      width: 16px; height: 16px; border-radius: 50%; background: #007bff;
      cursor: pointer; border: none; box-shadow: 0 2px 8px rgba(0,123,255,0.4);
    }
    
    /* Text popup */
    .text-popup-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 2000; display: none; }
    .text-popup-overlay.show { display: block; }
    .text-popup {
      position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
      background: rgba(30,30,30,0.98); backdrop-filter: blur(40px); border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 20px 60px rgba(0,0,0,0.8);
      max-width: 600px; max-height: 80vh; overflow: hidden; z-index: 2001; display: none;
    }
    .text-popup.show { display: block; }
    .popup-header {
      padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.1);
      display: flex; justify-content: space-between; align-items: center;
    }
    .popup-body { padding: 20px; max-height: 60vh; overflow-y: auto; }
    .popup-body pre {
      white-space: pre-wrap; word-wrap: break-word; margin: 0;
      color: rgba(255,255,255,0.9); font-size: 14px; user-select: text;
    }
    .popup-footer {
      padding: 20px; border-top: 1px solid rgba(255,255,255,0.1);
      display: flex; justify-content: flex-end; gap: 12px;
    }
    .btn {
      padding: 8px 16px; border-radius: 8px; border: none; cursor: pointer;
      font-size: 14px; transition: all 0.2s;
    }
    .btn-primary {
      background: #007bff; color: white;
    }
    .btn-primary:hover { background: #0056b3; }
    .btn-secondary {
      background: rgba(255,255,255,0.1); color: white;
    }
    .btn-secondary:hover { background: rgba(255,255,255,0.2); }
    .close-btn {
      background: none; border: none; color: rgba(255,255,255,0.6);
      font-size: 24px; cursor: pointer; padding: 0; line-height: 1;
    }
    .close-btn:hover { color: #fff; }
    
    /* Sidebar toggle button */
    .sidebar-toggle {
      position: fixed; top: 20px; left: 20px; z-index: 1000;
      background: rgba(20,20,20,0.75); backdrop-filter: blur(30px);
      border: 1px solid rgba(255,255,255,0.15); border-radius: 12px;
      width: 44px; height: 44px; display: flex; align-items: center; justify-content: center;
      cursor: pointer; transition: all 0.2s; color: rgba(255,255,255,0.6);
    }
    .sidebar-toggle:hover {
      background: rgba(30,30,30,0.85); border-color: rgba(0,123,255,0.5);
      color: #fff; box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    }
    
    /* Sidebar */
    .sidebar {
      position: fixed; top: 0; left: -400px; width: 400px; height: 100vh;
      background: rgba(20,20,20,0.98); backdrop-filter: blur(40px);
      border-right: 1px solid rgba(255,255,255,0.1); box-shadow: 0 0 60px rgba(0,0,0,0.8);
      z-index: 1100; transition: left 0.3s ease; padding: 80px 24px 24px;
      overflow-y: auto;
    }
    .sidebar.open { left: 0; }
    .sidebar-close {
      position: absolute; top: 20px; right: 20px; background: none; border: none;
      color: rgba(255,255,255,0.6); font-size: 24px; cursor: pointer; padding: 0;
    }
    .sidebar-close:hover { color: #fff; }
    .sidebar-section {
      margin-bottom: 24px; padding: 16px; background: rgba(255,255,255,0.03);
      border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);
    }
    .sidebar-section h3 {
      font-size: 14px; font-weight: 600; margin-bottom: 12px;
      color: rgba(255,255,255,0.7); text-transform: uppercase; letter-spacing: 0.5px;
    }
    .sidebar-section pre {
      white-space: pre-wrap; word-wrap: break-word; margin: 0;
      font-size: 13px; color: rgba(255,255,255,0.8); line-height: 1.5;
    }
    .sidebar-btn {
      width: 100%; padding: 10px 16px; margin-bottom: 8px; border-radius: 8px;
      border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05);
      color: rgba(255,255,255,0.9); cursor: pointer; font-size: 14px;
      transition: all 0.2s; display: flex; align-items: center; gap: 8px;
    }
    .sidebar-btn:hover {
      background: rgba(255,255,255,0.1); border-color: rgba(0,123,255,0.6);
    }
    .sidebar-btn.primary {
      background: rgba(0,123,255,0.8); border-color: rgba(0,123,255,1);
    }
    .sidebar-btn.primary:hover { background: rgba(0,123,255,1); }
    
    /* Toggle switch */
    .toggle-switch {
      position: relative; display: inline-block; width: 48px; height: 26px;
    }
    .toggle-switch input { opacity: 0; width: 0; height: 0; }
    .toggle-slider {
      position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
      background-color: rgba(255,255,255,0.2); transition: 0.3s; border-radius: 26px;
    }
    .toggle-slider:before {
      position: absolute; content: ""; height: 18px; width: 18px; left: 4px; bottom: 4px;
      background-color: white; transition: 0.3s; border-radius: 50%;
    }
    input:checked + .toggle-slider { background-color: #007bff; }
    input:checked + .toggle-slider:before { transform: translateX(22px); }
    
    .ocr-mode-selector {
      display: flex; align-items: center; justify-content: space-between;
      padding: 12px 16px; background: rgba(255,255,255,0.05);
      border-radius: 8px; margin-bottom: 16px;
    }
    .ocr-mode-label {
      font-size: 13px; color: rgba(255,255,255,0.8);
    }
    
    /* AI Config Modal */
    .config-modal-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 3000;
      display: none; align-items: center; justify-content: center;
    }
    .config-modal-overlay.show { display: flex; }
    .config-modal {
      background: rgba(30,30,30,0.98); backdrop-filter: blur(40px);
      border-radius: 16px; border: 1px solid rgba(255,255,255,0.1);
      box-shadow: 0 20px 60px rgba(0,0,0,0.8); width: 500px; max-width: 90vw;
    }
    .config-modal-header {
      padding: 24px; border-bottom: 1px solid rgba(255,255,255,0.1);
      display: flex; justify-content: space-between; align-items: center;
    }
    .config-modal-header h2 {
      font-size: 18px; font-weight: 600; margin: 0; color: #fff;
    }
    .config-modal-body { padding: 24px; }
    .form-group {
      margin-bottom: 20px;
    }
    .form-group label {
      display: block; margin-bottom: 8px; font-size: 13px;
      color: rgba(255,255,255,0.7); font-weight: 500;
    }
    .form-group select, .form-group input {
      width: 100%; padding: 12px 16px; border-radius: 8px;
      border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.05);
      color: #fff; font-size: 14px; transition: all 0.2s;
    }
    .form-group select:focus, .form-group input:focus {
      outline: none; border-color: rgba(0,123,255,0.6);
      background: rgba(255,255,255,0.08);
    }
    .form-group small {
      display: block; margin-top: 6px; font-size: 12px;
      color: rgba(255,255,255,0.5);
    }
    .config-modal-footer {
      padding: 20px 24px; border-top: 1px solid rgba(255,255,255,0.1);
      display: flex; justify-content: flex-end; gap: 12px;
    }
    
    /* Toast notifications */
    .toast-container {
      position: fixed; top: 80px; right: 20px; z-index: 4000;
      display: flex; flex-direction: column; gap: 12px; pointer-events: none;
    }
    .toast {
      background: rgba(30,30,30,0.98); backdrop-filter: blur(40px);
      border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);
      box-shadow: 0 8px 32px rgba(0,0,0,0.6); padding: 16px 20px;
      display: flex; align-items: center; gap: 12px; min-width: 300px;
      animation: slideIn 0.3s ease-out; pointer-events: auto;
    }
    .toast.success { border-left: 3px solid #28a745; }
    .toast.error { border-left: 3px solid #dc3545; }
    .toast.info { border-left: 3px solid #007bff; }
    .toast-icon {
      font-size: 20px; flex-shrink: 0;
    }
    .toast.success .toast-icon { color: #28a745; }
    .toast.error .toast-icon { color: #dc3545; }
    .toast.info .toast-icon { color: #007bff; }
    .toast-content {
      flex: 1; font-size: 14px; color: rgba(255,255,255,0.9);
    }
    .toast-close {
      background: none; border: none; color: rgba(255,255,255,0.5);
      cursor: pointer; font-size: 18px; padding: 0; line-height: 1;
    }
    .toast-close:hover { color: #fff; }
    @keyframes slideIn {
      from { transform: translateX(400px); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
      .sidebar {
        width: 90vw;
        left: -90vw;
      }
      .sidebar.open { left: 0; }
      
      .search-input {
        width: calc(100vw - 80px);
        font-size: 14px;
        padding: 10px 40px 10px 16px;
      }
      
      .search-results {
        top: 70px;
        left: 10px;
        right: 10px;
        width: auto;
        padding: 12px;
      }
      
      .results-grid {
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 12px;
      }
      
      .timeline-pill {
        min-width: calc(100vw - 40px);
        padding: 12px 20px;
      }
      
      .timeline-date {
        font-size: 12px;
      }
      
      .screenshot-area {
        padding: max(60px, 8vh) 10px max(100px, 12vh);
      }
      
      .sidebar-toggle {
        top: 15px;
        left: 15px;
        width: 40px;
        height: 40px;
      }
      
      .config-modal {
        width: 90vw;
      }
    }
    
    @media (max-width: 480px) {
      .search-container {
        top: 10px;
        right: 10px;
        left: 60px;
      }
      
      .search-input {
        width: 100%;
      }
      
      .timeline-pill {
        padding: 10px 16px;
      }
      
      .timeline-date {
        font-size: 11px;
      }
      
      .text-icon {
        width: 28px;
        height: 28px;
        font-size: 14px;
      }
    }
  </style>
</head>
<body>
  <div class="fullscreen-container">
    <!-- Sidebar toggle -->
    <div class="sidebar-toggle" onclick="toggleSidebar()">
      <i class="bi bi-list" style="font-size: 24px;"></i>
    </div>
    
    <!-- Sidebar -->
    <div class="sidebar" id="sidebar">
      <button class="sidebar-close" onclick="toggleSidebar()">&times;</button>
      
      <div class="sidebar-section">
        <h3>OCR Settings</h3>
        
        <div class="ocr-mode-selector">
          <span class="ocr-mode-label">Basic OCR</span>
          <label class="toggle-switch">
            <input type="checkbox" id="ocrToggle" onchange="toggleOCRMode()">
            <span class="toggle-slider"></span>
          </label>
          <span class="ocr-mode-label">AI OCR</span>
        </div>
        
        <button class="sidebar-btn primary" onclick="runAIOCR()" id="btnRunAI">
          <i class="bi bi-stars"></i> Run AI Text
        </button>
        <button class="sidebar-btn" onclick="showAIConfig()">
          <i class="bi bi-gear"></i> Configure AI Provider
        </button>
      </div>
      
      <div class="sidebar-section">
        <h3>Extracted Text</h3>
        <button class="sidebar-btn" onclick="copyExtractedText()" style="margin-bottom: 12px;">
          <i class="bi bi-clipboard"></i> Copy All
        </button>
        <pre id="extractedText"></pre>
      </div>
    </div>
    
    <!-- Search bar -->
    <div class="search-container">
      <div class="search-wrapper">
        <input type="text" class="search-input" id="searchInput" placeholder="Search your history...">
        <i class="bi bi-search search-icon"></i>
      </div>
    </div>
    
    <!-- Search results -->
    <div class="search-results" id="searchResults"></div>
    
    <!-- Screenshot area -->
    <div class="screenshot-area" id="screenshotArea">
      <div class="screenshot-wrapper">
        <img id="screenshot" src="/static/{{timestamps[0]}}.webp" alt="Screenshot">
        <div class="text-overlay" id="textOverlay"></div>
      </div>
    </div>
    
    <!-- Timeline -->
    <div class="timeline">
      <div class="timeline-pill">
        <div class="timeline-date" id="timelineDate">{{timestamps[0] | timestamp_to_human_readable}}</div>
        <input type="range" class="timeline-slider" id="timelineSlider" 
               min="0" max="{{timestamps|length - 1}}" value="{{timestamps|length - 1}}">
      </div>
    </div>
  </div>
  
  <!-- AI Config Modal -->
  <div class="config-modal-overlay" id="configModalOverlay" onclick="if(event.target===this) closeAIConfig()">
    <div class="config-modal">
      <div class="config-modal-header">
        <h2>AI Provider Settings</h2>
        <button class="close-btn" onclick="closeAIConfig()">&times;</button>
      </div>
      <div class="config-modal-body">
        <div class="form-group">
          <label>AI Provider</label>
          <select id="aiProvider">
            <option value="gemini">Google Gemini</option>
            <option value="openai">OpenAI (GPT-4o)</option>
            <option value="claude">Anthropic Claude</option>
          </select>
          <small>Choose your preferred AI provider for enhanced OCR</small>
        </div>
        <div class="form-group">
          <label>API Key</label>
          <input type="password" id="aiApiKey" placeholder="Enter your API key">
          <small>Your API key is stored locally and never sent to our servers</small>
        </div>
      </div>
      <div class="config-modal-footer">
        <button class="btn btn-secondary" onclick="closeAIConfig()">Cancel</button>
        <button class="btn btn-primary" onclick="saveAIConfig()">
          <i class="bi bi-check-lg"></i> Save Settings
        </button>
      </div>
    </div>
  </div>
  
  <!-- Toast container -->
  <div class="toast-container" id="toastContainer"></div>
  
  <!-- Text popup -->
  <div class="text-popup-overlay" id="textPopupOverlay" onclick="closeTextPopup()"></div>
  <div class="text-popup" id="textPopup">
    <div class="popup-header">
      <strong>Text Block</strong>
      <button class="close-btn" onclick="closeTextPopup()">&times;</button>
    </div>
    <div class="popup-body">
      <pre id="popupText"></pre>
    </div>
    <div class="popup-footer">
      <button class="btn btn-secondary" onclick="closeTextPopup()">Close</button>
      <button class="btn btn-primary" onclick="copyPopupText()">
        <i class="bi bi-clipboard"></i> Copy
      </button>
    </div>
  </div>

  <script>
    const timestamps = {{timestamps|tojson}};
    const entriesData = {{entries_dict|tojson}};
    const slider = document.getElementById('timelineSlider');
    const dateEl = document.getElementById('timelineDate');
    const screenshot = document.getElementById('screenshot');
    const textOverlay = document.getElementById('textOverlay');
    const screenshotArea = document.getElementById('screenshotArea');
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    
    let currentEntry = null;
    let searchTimeout = null;
    
    // Update display
    function updateDisplay(timestamp) {
      screenshot.src = `/static/${timestamp}.webp`;
      dateEl.textContent = new Date(timestamp / 1000).toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: 'numeric', minute: '2-digit', hour12: true
      });
      currentEntry = entriesData[timestamp];
      screenshot.onload = renderOverlay;
      updateExtractedText();
    }
    
    // Slider
    slider.addEventListener('input', () => {
      const idx = timestamps.length - 1 - parseInt(slider.value);
      updateDisplay(timestamps[idx]);
    });
    
    // Trackpad scrubbing
    let accDelta = 0, isScrolling = false, scrollTimeout = null;
    document.addEventListener('wheel', e => {
      if (Math.abs(e.deltaX) > 0) e.preventDefault();
    }, {passive: false, capture: true});
    
    screenshotArea.addEventListener('wheel', e => {
      if (Math.abs(e.deltaX) > Math.abs(e.deltaY) && Math.abs(e.deltaX) > 0) {
        e.preventDefault();
        e.stopPropagation();
        
        accDelta += e.deltaX * 0.5;
        const frames = Math.floor(Math.abs(accDelta));
        
        if (frames >= 1) {
          const dir = accDelta > 0 ? 1 : -1;
          let newVal = parseInt(slider.value) + (dir * frames);
          accDelta = accDelta % 1;
          newVal = Math.max(0, Math.min(timestamps.length - 1, newVal));
          
          if (newVal !== parseInt(slider.value)) {
            slider.value = newVal;
            const idx = timestamps.length - 1 - slider.value;
            const ts = timestamps[idx];
            
            if (!isScrolling) isScrolling = true;
            
            dateEl.textContent = new Date(ts / 1000).toLocaleString('en-US', {
              month: 'short', day: 'numeric', year: 'numeric',
              hour: 'numeric', minute: '2-digit', hour12: true
            });
            screenshot.src = `/static/${ts}.webp`;
            currentEntry = entriesData[ts];
          }
          
          clearTimeout(scrollTimeout);
          scrollTimeout = setTimeout(() => {
            isScrolling = false;
            renderOverlay();
          }, 300);
        }
      }
    }, {passive: false});
    
    // Arrow keys
    document.addEventListener('keydown', e => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        const dir = e.key === 'ArrowRight' ? 1 : -1;
        let newVal = parseInt(slider.value) + dir;
        newVal = Math.max(0, Math.min(timestamps.length - 1, newVal));
        if (newVal !== parseInt(slider.value)) {
          slider.value = newVal;
          const idx = timestamps.length - 1 - slider.value;
          updateDisplay(timestamps[idx]);
        }
      } else if (e.key === 'Escape') {
        closeTextPopup();
        searchResults.classList.remove('show');
      }
    });
    
    // Render overlay
    function groupWords(words) {
      if (!words || words.length === 0) return [];
      const lines = [];
      let line = [words[0]];
      for (let i = 1; i < words.length; i++) {
        const p = words[i-1], c = words[i];
        const vd = Math.abs(c.y1 - p.y1);
        const ah = (c.y2 - c.y1 + p.y2 - p.y1) / 2;
        if (vd < ah * 0.5) line.push(c);
        else { lines.push(line); line = [c]; }
      }
      lines.push(line);
      
      const blocks = [];
      let block = [lines[0]];
      for (let i = 1; i < lines.length; i++) {
        const pl = lines[i-1], cl = lines[i];
        const pmy = Math.max(...pl.map(w => w.y2));
        const cmy = Math.min(...cl.map(w => w.y1));
        const gap = cmy - pmy;
        const alh = ((Math.max(...pl.map(w => w.y2)) - Math.min(...pl.map(w => w.y1))) +
                     (Math.max(...cl.map(w => w.y2)) - Math.min(...cl.map(w => w.y1)))) / 2;
        if (gap < alh * 1.5) block.push(cl);
        else { blocks.push(block); block = [cl]; }
      }
      blocks.push(block);
      
      return blocks.map(b => {
        const all = b.flat();
        return {
          x1: Math.min(...all.map(w => w.x1)),
          y1: Math.min(...all.map(w => w.y1)),
          x2: Math.max(...all.map(w => w.x2)),
          y2: Math.max(...all.map(w => w.y2)),
          text: b.map(l => l.map(w => w.text).join(' ')).join('\\n')
        };
      });
    }
    
    function renderOverlay() {
      textOverlay.innerHTML = '';
      if (!currentEntry || !currentEntry.words_coords) return;
      
      const w = screenshot.clientWidth;
      const h = screenshot.clientHeight;
      textOverlay.style.width = w + 'px';
      textOverlay.style.height = h + 'px';
      
      const blocks = groupWords(currentEntry.words_coords);
      const positions = [];
      const minDist = 40;
      
      blocks.forEach(block => {
        const bw = (block.x2 - block.x1) * w;
        const bh = (block.y2 - block.y1) * h;
        let left = block.x1 * w + bw/2 - 16;
        let top = block.y1 * h + bh/2 - 16;
        
        let overlapping = true, attempts = 0;
        while (overlapping && attempts < 10) {
          overlapping = false;
          for (const pos of positions) {
            const dist = Math.sqrt(Math.pow(left - pos.left, 2) + Math.pow(top - pos.top, 2));
            if (dist < minDist) {
              overlapping = true;
              if (attempts === 0) { left = block.x1 * w; top = block.y1 * h; }
              else if (attempts === 1) { left = block.x2 * w - 32; top = block.y1 * h; }
              else if (attempts === 2) { left = block.x1 * w; top = block.y2 * h - 32; }
              else if (attempts === 3) { left = block.x2 * w - 32; top = block.y2 * h - 32; }
              else { left += (Math.random() - 0.5) * 20; top += (Math.random() - 0.5) * 20; }
              break;
            }
          }
          attempts++;
        }
        
        positions.push({left, top});
        const icon = document.createElement('div');
        icon.className = 'text-icon';
        icon.innerHTML = '<i class="bi bi-file-text"></i>';
        icon.style.left = left + 'px';
        icon.style.top = top + 'px';
        icon.onclick = () => showTextPopup(block.text);
        textOverlay.appendChild(icon);
      });
    }
    
    // Text popup
    function showTextPopup(text) {
      document.getElementById('popupText').textContent = text;
      document.getElementById('textPopup').classList.add('show');
      document.getElementById('textPopupOverlay').classList.add('show');
    }
    
    function closeTextPopup() {
      document.getElementById('textPopup').classList.remove('show');
      document.getElementById('textPopupOverlay').classList.remove('show');
    }
    
    function copyPopupText() {
      const text = document.getElementById('popupText').textContent;
      navigator.clipboard.writeText(text).then(() => alert('Copied!'));
    }
    
    // Search
    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      const q = searchInput.value.trim();
      
      if (!q) {
        searchResults.classList.remove('show');
        return;
      }
      
      searchTimeout = setTimeout(() => performSearch(q), 300);
    });
    
    async function performSearch(q) {
      const response = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      const results = await response.json();
      
      if (results.length === 0) {
        searchResults.innerHTML = '<p style="color: rgba(255,255,255,0.5); text-align: center;">No results found</p>';
      } else {
        searchResults.innerHTML = '<div class="results-grid">' + 
          results.map(r => `
            <div class="result-card" onclick="goToTimestamp(${r.timestamp})">
              <img src="/static/${r.timestamp}.webp" alt="">
              <div class="result-time">${new Date(r.timestamp/1000).toLocaleString('en-US', {
                month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
              })}</div>
            </div>
          `).join('') + '</div>';
      }
      searchResults.classList.add('show');
    }
    
    function goToTimestamp(ts) {
      const idx = timestamps.indexOf(ts);
      if (idx !== -1) {
        slider.value = timestamps.length - 1 - idx;
        updateDisplay(ts);
        searchResults.classList.remove('show');
        searchInput.value = '';
      }
    }
    
    // Sidebar
    function toggleSidebar() {
      document.getElementById('sidebar').classList.toggle('open');
    }
    
    let currentOCRMode = 'basic';
    let aiConfig = null;
    
    fetch('/api/config').then(r => r.json()).then(c => aiConfig = c);
    
    function toggleOCRMode() {
      const toggle = document.getElementById('ocrToggle');
      currentOCRMode = toggle.checked ? 'ai' : 'basic';
      updateExtractedText();
    }
    
    function showOCRMode(mode) {
      currentOCRMode = mode;
      document.getElementById('ocrToggle').checked = (mode === 'ai');
      updateExtractedText();
    }
    
    async function runAIOCR() {
      if (!currentEntry) {
        showToast('No screenshot selected', 'error');
        return;
      }
      
      const btn = document.getElementById('btnRunAI');
      btn.disabled = true;
      btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Processing...';
      
      // Show info toast about processing time
      showToast('AI OCR is processing... This may take 10-30 seconds as the AI analyzes the entire screenshot.', 'info');
      
      try {
        const configResp = await fetch('/api/config?full=true');
        const fullConfig = await configResp.json();
        
        if (!fullConfig.api_key || fullConfig.api_key === '***' || fullConfig.api_key === '') {
          showToast('Please configure AI settings first', 'error');
          showAIConfig();
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-stars"></i> Run AI Text';
          return;
        }
        
        const response = await fetch('/api/ai-ocr', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            timestamp: currentEntry.timestamp,
            provider: fullConfig.provider || 'gemini',
            api_key: fullConfig.api_key
          })
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || 'AI OCR failed');
        }
        
        const result = await response.json();
        currentEntry.ai_text = result.text;
        currentEntry.ai_words_coords = result.words_coords;
        entriesData[currentEntry.timestamp].ai_text = result.text;
        entriesData[currentEntry.timestamp].ai_words_coords = result.words_coords;
        
        showOCRMode('ai');
        showToast('AI OCR completed successfully! ✨', 'success');
      } catch (error) {
        showToast('AI OCR error: ' + error.message, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-stars"></i> Run AI Text';
      }
    }
    
    // Toast notifications
    function showToast(message, type = 'info') {
      const container = document.getElementById('toastContainer');
      const toast = document.createElement('div');
      toast.className = `toast ${type}`;
      
      const iconMap = {
        success: 'bi-check-circle-fill',
        error: 'bi-x-circle-fill',
        info: 'bi-info-circle-fill'
      };
      
      toast.innerHTML = `
        <i class="bi ${iconMap[type]} toast-icon"></i>
        <div class="toast-content">${message}</div>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
      `;
      
      container.appendChild(toast);
      setTimeout(() => toast.remove(), 4000);
    }
    
    // AI Config Modal
    function showAIConfig() {
      const modal = document.getElementById('configModalOverlay');
      
      // Load current config
      if (aiConfig) {
        document.getElementById('aiProvider').value = aiConfig.provider || 'gemini';
      }
      
      modal.classList.add('show');
    }
    
    function closeAIConfig() {
      document.getElementById('configModalOverlay').classList.remove('show');
      document.getElementById('aiApiKey').value = '';
    }
    
    async function saveAIConfig() {
      const provider = document.getElementById('aiProvider').value;
      const apiKey = document.getElementById('aiApiKey').value;
      
      if (!apiKey) {
        showToast('Please enter an API key', 'error');
        return;
      }
      
      try {
        const response = await fetch('/api/config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({provider, api_key: apiKey})
        });
        
        if (response.ok) {
          aiConfig = {provider, api_key: '***'};
          closeAIConfig();
          showToast('AI settings saved successfully!', 'success');
        } else {
          showToast('Failed to save settings', 'error');
        }
      } catch (error) {
        showToast('Error: ' + error.message, 'error');
      }
    }
    
    function copyExtractedText() {
      const text = document.getElementById('extractedText').textContent;
      navigator.clipboard.writeText(text).then(() => {
        showToast('Text copied to clipboard!', 'success');
      }).catch(() => {
        showToast('Failed to copy text', 'error');
      });
    }
    
    function copyPopupText() {
      const text = document.getElementById('popupText').textContent;
      navigator.clipboard.writeText(text).then(() => {
        showToast('Text copied to clipboard!', 'success');
      }).catch(() => {
        showToast('Failed to copy text', 'error');
      });
    }
    
    // Update extracted text on change
    function updateExtractedText() {
      if (currentEntry) {
        const text = currentOCRMode === 'ai' && currentEntry.ai_text ? currentEntry.ai_text : currentEntry.text;
        document.getElementById('extractedText').textContent = text || 'No text available';
      }
    }
    
    // Init
    updateDisplay(timestamps[0]);
    updateExtractedText();
  </script>
</body>
</html>
    """, timestamps=timestamps, entries_dict=entries_dict)


@app.route("/api/search")
def api_search():
    """API endpoint for search"""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    
    entries = get_all_entries()
    embeddings = [entry.embedding for entry in entries]
    query_embedding = get_embedding(q)
    similarities = [cosine_similarity(query_embedding, emb) for emb in embeddings]
    
    query_lower = q.lower()
    scores = []
    for i, entry in enumerate(entries):
        semantic_score = similarities[i]
        text_lower = entry.text.lower()
        keyword_boost = 0
        
        if query_lower in text_lower:
            keyword_boost = 0.5
        else:
            query_words = query_lower.split()
            matched = sum(1 for word in query_words if word in text_lower)
            if matched > 0:
                keyword_boost = 0.3 * (matched / len(query_words))
        
        scores.append((i, semantic_score + keyword_boost, keyword_boost > 0))
    
    scores.sort(key=lambda x: (x[2], x[1]), reverse=True)
    
    results = [
        {
            'timestamp': entries[idx].timestamp,
            'text': entries[idx].text[:200]
        }
        for idx, score, has_keyword in scores[:20]
    ]
    
    return jsonify(results)


@app.route("/classic")
def timeline():
    # connect to db
    timestamps = get_timestamps()
    entries = get_all_entries()
    # Convert entries to dict without embedding (numpy array)
    entries_dict = {
        entry.timestamp: {
            'id': entry.id,
            'app': entry.app,
            'title': entry.title,
            'text': entry.text,
            'timestamp': entry.timestamp,
            'words_coords': entry.words_coords,
            'ai_text': entry.ai_text,
            'ai_words_coords': entry.ai_words_coords if entry.ai_words_coords else []
        }
        for entry in entries
    }
    return render_template_string(
        """
{% extends "base_template" %}
{% block content %}
{% if timestamps|length > 0 %}
  <div class="toggle-sidebar-btn" onclick="toggleSidebar()" title="Toggle sidebar">
    <i id="sidebarToggleIcon" class="bi bi-chevron-left"></i>
  </div>
  <div class="container-fluid" style="height: calc(100vh - 100px); display: flex; flex-direction: column;">
    <div class="slider-container">
      <input type="range" class="slider custom-range" id="discreteSlider" min="0" max="{{timestamps|length - 1}}" step="1" value="{{timestamps|length - 1}}">
      <div class="slider-value" id="sliderValue">{{timestamps[0] | timestamp_to_human_readable }}</div>
    </div>
    <div class="row flex-grow-1" style="overflow: hidden; margin: 0;">
      <div id="imageColumn" class="col-md-8" style="height: 100%; display: flex; align-items: center; justify-content: center; position: relative; transition: width 0.3s; overscroll-behavior-x: none; padding: 20px;">
        <div id="imageWrapper" style="position: relative; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;">
          <img id="timestampImage" src="/static/{{timestamps[0]}}.webp" alt="Image for timestamp" style="max-width: 100%; max-height: 100%; width: auto; height: auto; object-fit: contain; display: block;">
          <div id="textOverlay" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); pointer-events: none;"></div>
        </div>
      </div>
      <div id="sidebarColumn" class="col-md-4 p-3 bg-light border-left" style="height: 100%; overflow-y: auto; display: flex; flex-direction: column; transition: all 0.3s;">
        <div class="mb-3">
          <label class="d-flex align-items-center">
            <input type="checkbox" id="showOverlay" checked class="mr-2">
            <span>Show text blocks on image</span>
          </label>
        </div>
        
        <div class="mb-3">
          <div class="btn-group btn-group-sm w-100" role="group">
            <button type="button" class="btn btn-outline-secondary" id="btnBasicOCR" onclick="switchOCRMode('basic')">
              Basic OCR
            </button>
            <button type="button" class="btn btn-outline-primary" id="btnAIOCR" onclick="switchOCRMode('ai')">
              AI OCR
            </button>
          </div>
          <button class="btn btn-sm btn-success w-100 mt-2" onclick="runAIOCR()" id="btnRunAI">
            <i class="bi bi-robot"></i> Run AI Text
          </button>
          <button class="btn btn-sm btn-secondary w-100 mt-1" onclick="showAIConfig()">
            <i class="bi bi-gear"></i> AI Settings
          </button>
        </div>
        
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center" style="cursor: pointer; user-select: none;" onclick="toggleTextPanel()">
            <strong>All Extracted Text</strong>
            <i id="toggleIcon" class="bi bi-chevron-up"></i>
          </div>
          <div id="textPanel" class="card-body" style="max-height: 300px; overflow-y: auto;">
            <div class="d-flex justify-content-end mb-2">
              <button class="btn btn-sm btn-outline-primary" onclick="copyCurrentText()">
                <i class="bi bi-clipboard"></i> Copy All
              </button>
            </div>
            <pre id="extractedText" style="white-space: pre-wrap; word-wrap: break-word; margin: 0; font-size: 0.9em; user-select: text;"></pre>
          </div>
        </div>
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
    
    <!-- AI Config Modal -->
    <div class="text-popup-overlay" id="aiConfigOverlay" onclick="closeAIConfig()"></div>
    <div class="text-popup" id="aiConfigModal">
      <div class="text-popup-header">
        <strong>AI OCR Settings</strong>
        <button type="button" class="close" onclick="closeAIConfig()">&times;</button>
      </div>
      <div class="text-popup-body">
        <div class="form-group">
          <label>AI Provider</label>
          <select class="form-control" id="aiProvider">
            <option value="gemini">Google Gemini</option>
            <option value="openai">OpenAI (GPT-4o)</option>
            <option value="claude">Anthropic Claude</option>
          </select>
        </div>
        <div class="form-group">
          <label>API Key</label>
          <input type="password" class="form-control" id="aiApiKey" placeholder="Enter your API key">
          <small class="form-text text-muted">Your API key is stored locally and never sent to our servers.</small>
        </div>
      </div>
      <div class="text-popup-footer">
        <button class="btn btn-sm btn-secondary" onclick="closeAIConfig()">Cancel</button>
        <button class="btn btn-sm btn-primary" onclick="saveAIConfig()">
          <i class="bi bi-save"></i> Save
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
      if (!showOverlayCheckbox.checked || !currentEntry || !currentEntry.words_coords || currentEntry.words_coords.length === 0) {
        return;
      }
      
      const img = timestampImage;
      
      // Get actual rendered dimensions of the image
      const displayWidth = img.clientWidth;
      const displayHeight = img.clientHeight;
      
      // Make overlay match image size exactly
      textOverlay.style.width = displayWidth + 'px';
      textOverlay.style.height = displayHeight + 'px';
      
      const blocks = groupWordsIntoBlocks(currentEntry.words_coords);
      
      blocks.forEach((block, index) => {
        const icon = document.createElement('div');
        icon.className = 'text-block-icon';
        icon.innerHTML = '<i class="bi bi-file-text"></i>';
        
        // Center the icon on the block
        const blockWidth = (block.x2 - block.x1) * displayWidth;
        const blockHeight = (block.y2 - block.y1) * displayHeight;
        const iconSize = 32;
        
        const left = block.x1 * displayWidth + blockWidth / 2 - iconSize / 2;
        const top = block.y1 * displayHeight + blockHeight / 2 - iconSize / 2;
        
        icon.style.left = left + 'px';
        icon.style.top = top + 'px';
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

    // Video-like scrubbing with trackpad - prevent ALL horizontal scroll from triggering back
    const imageColumn = document.getElementById('imageColumn');
    let accumulatedDelta = 0;
    let isScrolling = false;
    let scrollTimeout = null;
    const sensitivity = 0.5;
    
    // Block back gesture at document level
    document.addEventListener('wheel', function(e) {
      if (Math.abs(e.deltaX) > 0) {
        e.preventDefault();
      }
    }, { passive: false, capture: true });
    
    imageColumn.addEventListener('wheel', function(e) {
      // Only handle horizontal scroll, ignore vertical
      if (Math.abs(e.deltaX) > Math.abs(e.deltaY) && Math.abs(e.deltaX) > 0) {
        e.preventDefault();
        e.stopPropagation();
        
        // Accumulate scroll delta for smooth scrubbing
        accumulatedDelta += e.deltaX * sensitivity;
        
        // Calculate how many frames to move
        const framesToMove = Math.floor(Math.abs(accumulatedDelta));
        
        if (framesToMove >= 1) {
          const direction = accumulatedDelta > 0 ? 1 : -1;
          let newValue = parseInt(slider.value) + (direction * framesToMove);
          
          // Reset accumulated delta
          accumulatedDelta = accumulatedDelta % 1;
          
          // Clamp to valid range
          const oldValue = parseInt(slider.value);
          newValue = Math.max(0, Math.min(timestamps.length - 1, newValue));
          
          // Update even if at boundaries to consume the scroll
          if (newValue !== oldValue) {
            slider.value = newValue;
            const reversedIndex = timestamps.length - 1 - slider.value;
            const timestamp = timestamps[reversedIndex];
            
            // Fast update without overlay during scrubbing
            if (!isScrolling) {
              isScrolling = true;
              showOverlayCheckbox.checked = false;
            }
            
            sliderValue.textContent = new Date(timestamp / 1000).toLocaleString();
            timestampImage.src = `/static/${timestamp}.webp`;
            currentEntry = entriesData[timestamp];
            extractedText.textContent = currentEntry ? currentEntry.text : 'No text available';
          }
          
          // Clear and restart timeout even if we're at boundaries
          clearTimeout(scrollTimeout);
          scrollTimeout = setTimeout(() => {
            isScrolling = false;
            showOverlayCheckbox.checked = true;
            renderTextOverlay();
          }, 300);
        }
      }
    }, { passive: false });
    
    // Arrow keys for precise navigation
    document.addEventListener('keydown', function(e) {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        const direction = e.key === 'ArrowRight' ? 1 : -1;
        let newValue = parseInt(slider.value) + direction;
        
        newValue = Math.max(0, Math.min(timestamps.length - 1, newValue));
        
        if (newValue !== parseInt(slider.value)) {
          slider.value = newValue;
          const reversedIndex = timestamps.length - 1 - slider.value;
          const timestamp = timestamps[reversedIndex];
          updateDisplay(timestamp);
        }
      }
    });

    function toggleSidebar() {
      const sidebar = document.getElementById('sidebarColumn');
      const imageCol = document.getElementById('imageColumn');
      const icon = document.getElementById('sidebarToggleIcon');
      
      if (sidebar.style.display === 'none') {
        sidebar.style.display = 'flex';
        imageCol.classList.remove('col-md-12');
        imageCol.classList.add('col-md-8');
        icon.className = 'bi bi-chevron-left';
      } else {
        sidebar.style.display = 'none';
        imageCol.classList.remove('col-md-8');
        imageCol.classList.add('col-md-12');
        icon.className = 'bi bi-chevron-right';
      }
      
      // Wait for transition and re-render
      setTimeout(() => {
        renderTextOverlay();
      }, 350);
    }

    function toggleTextPanel() {
      const panel = document.getElementById('textPanel');
      const icon = document.getElementById('toggleIcon');
      
      if (panel.style.display === 'none') {
        panel.style.display = 'block';
        icon.className = 'bi bi-chevron-up';
      } else {
        panel.style.display = 'none';
        icon.className = 'bi bi-chevron-down';
      }
    }

    function copyCurrentText() {
      const text = extractedText.textContent;
      navigator.clipboard.writeText(text).then(() => {
        alert('Text copied to clipboard!');
      });
    }

    // AI OCR functionality
    let currentOCRMode = 'basic';
    let aiConfig = null;
    
    // Load AI config on startup
    fetch('/api/config')
      .then(r => r.json())
      .then(config => {
        aiConfig = config;
      });
    
    function switchOCRMode(mode) {
      currentOCRMode = mode;
      document.getElementById('btnBasicOCR').classList.toggle('btn-secondary', mode !== 'basic');
      document.getElementById('btnBasicOCR').classList.toggle('btn-primary', mode === 'basic');
      document.getElementById('btnAIOCR').classList.toggle('btn-secondary', mode !== 'ai');
      document.getElementById('btnAIOCR').classList.toggle('btn-primary', mode === 'ai');
      
      if (currentEntry) {
        const original = entriesData[currentEntry.timestamp];
        
        if (mode === 'ai' && currentEntry.ai_text) {
          extractedText.textContent = currentEntry.ai_text;
          // Use AI coordinates if available, otherwise fallback to basic
          currentEntry.words_coords = (currentEntry.ai_words_coords && currentEntry.ai_words_coords.length > 0) 
            ? currentEntry.ai_words_coords 
            : original.words_coords;
        } else {
          extractedText.textContent = currentEntry.text;
          currentEntry.words_coords = original.words_coords;
        }
        renderTextOverlay();
      }
    }
    
    async function runAIOCR() {
      if (!currentEntry) {
        alert('No screenshot selected');
        return;
      }
      
      const btn = document.getElementById('btnRunAI');
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm mr-1"></span> Processing...';
      
      try {
        // Load real API key from backend
        const configResp = await fetch('/api/config?full=true');
        const fullConfig = await configResp.json();
        
        if (!fullConfig.api_key || fullConfig.api_key === '***' || fullConfig.api_key === '') {
          alert('Please configure AI settings first');
          showAIConfig();
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-robot"></i> Run AI Text';
          return;
        }
        
        const response = await fetch('/api/ai-ocr', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            timestamp: currentEntry.timestamp,
            provider: fullConfig.provider || 'gemini',
            api_key: fullConfig.api_key
          })
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || 'AI OCR failed');
        }
        
        const result = await response.json();
        
        // Update current entry
        currentEntry.ai_text = result.text;
        currentEntry.ai_words_coords = result.words_coords;
        entriesData[currentEntry.timestamp].ai_text = result.text;
        entriesData[currentEntry.timestamp].ai_words_coords = result.words_coords;
        
        // Switch to AI mode
        switchOCRMode('ai');
        
        alert('AI OCR completed successfully!');
      } catch (error) {
        alert('AI OCR error: ' + error.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-robot"></i> Run AI Text';
      }
    }
    
    function showAIConfig() {
      const modal = document.getElementById('aiConfigModal');
      const overlay = document.getElementById('aiConfigOverlay');
      
      if (aiConfig) {
        document.getElementById('aiProvider').value = aiConfig.provider || 'gemini';
        // Don't show the masked key
        document.getElementById('aiApiKey').value = '';
        document.getElementById('aiApiKey').placeholder = aiConfig.api_key === '***' ? 'Enter new API key' : 'Enter your API key';
      }
      
      modal.classList.add('show');
      overlay.classList.add('show');
    }
    
    function closeAIConfig() {
      const modal = document.getElementById('aiConfigModal');
      const overlay = document.getElementById('aiConfigOverlay');
      modal.classList.remove('show');
      overlay.classList.remove('show');
    }
    
    async function saveAIConfig() {
      const provider = document.getElementById('aiProvider').value;
      const apiKey = document.getElementById('aiApiKey').value;
      
      if (!apiKey) {
        alert('Please enter an API key');
        return;
      }
      
      try {
        const response = await fetch('/api/config', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({provider, api_key: apiKey})
        });
        
        if (response.ok) {
          aiConfig = {provider, api_key: '***'};
          alert('AI settings saved successfully!');
          closeAIConfig();
        } else {
          alert('Failed to save settings');
        }
      } catch (error) {
        alert('Error saving settings: ' + error.message);
      }
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
    if not q or not q.strip():
        return render_template_string(
            """
{% extends "base_template" %}
{% block content %}
    <div class="container mt-4">
        <div class="alert alert-info">Please enter a search query</div>
    </div>
{% endblock %}
""")
    
    entries = get_all_entries()
    embeddings = [entry.embedding for entry in entries]
    query_embedding = get_embedding(q)
    similarities = [cosine_similarity(query_embedding, emb) for emb in embeddings]
    
    # Create a hybrid score: semantic similarity + keyword match boost
    query_lower = q.lower()
    scores = []
    for i, entry in enumerate(entries):
        semantic_score = similarities[i]
        
        # Boost score if query keywords are found in text
        text_lower = entry.text.lower()
        keyword_boost = 0
        
        # Exact phrase match gets highest boost
        if query_lower in text_lower:
            keyword_boost = 0.5
        else:
            # Check individual words
            query_words = query_lower.split()
            matched_words = sum(1 for word in query_words if word in text_lower)
            if matched_words > 0:
                keyword_boost = 0.3 * (matched_words / len(query_words))
        
        # Combined score
        final_score = semantic_score + keyword_boost
        scores.append((i, final_score, keyword_boost > 0))
    
    # Sort by score, prioritizing entries with keyword matches
    scores.sort(key=lambda x: (x[2], x[1]), reverse=True)
    
    # Convert entries to dict without embedding (numpy array)
    sorted_entries = [
        {
            'id': entries[idx].id,
            'app': entries[idx].app,
            'title': entries[idx].title,
            'text': entries[idx].text,
            'timestamp': entries[idx].timestamp,
            'words_coords': entries[idx].words_coords,
            'ai_text': entries[idx].ai_text,
            'ai_words_coords': entries[idx].ai_words_coords if entries[idx].ai_words_coords else []
        }
        for idx, score, has_keyword in scores
    ]

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
                                                
                                                // Center the icon on the block
                                                const blockWidth = (block.x2 - block.x1) * displayWidth;
                                                const blockHeight = (block.y2 - block.y1) * displayHeight;
                                                const iconSize = 32;
                                                
                                                icon.style.left = (block.x1 * displayWidth + blockWidth / 2 - iconSize / 2) + 'px';
                                                icon.style.top = (block.y1 * displayHeight + blockHeight / 2 - iconSize / 2) + 'px';
                                                icon.title = 'Click to view text';
                                                icon.onclick = () => showModalTextPopup{{ loop.index0 }}(block.text);
                                                overlay.appendChild(icon);
                                            });
                                        }
                                        
                                        img.onload = renderModalOverlay;
                                        checkbox.addEventListener('change', renderModalOverlay);
                                        document.getElementById('modal-{{ loop.index0 }}').addEventListener('shown.bs.modal', renderModalOverlay);
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


@app.route("/api/ai-ocr", methods=["POST"])
def ai_ocr():
    """Endpoint to perform AI OCR on a screenshot"""
    try:
        data = request.json
        timestamp = data.get('timestamp')
        provider = data.get('provider', 'gemini')
        api_key = data.get('api_key')
        
        if not timestamp or not api_key:
            return jsonify({'error': 'Missing timestamp or api_key'}), 400
        
        # Find the entry
        entries = get_all_entries()
        entry = next((e for e in entries if e.timestamp == timestamp), None)
        
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404
        
        # Load the screenshot image
        image_path = os.path.join(screenshots_path, f"{timestamp}.webp")
        if not os.path.exists(image_path):
            return jsonify({'error': 'Screenshot file not found'}), 404
        
        # Convert image to base64
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to bytes
            import io
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=95)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Get AI provider
        ai_provider = get_ai_provider(provider, api_key)
        
        # Perform AI OCR
        ai_text, ai_words_coords = ai_provider.ocr_with_positions(
            image_base64,
            entry.text
        )
        
        # Update database
        update_ai_ocr(timestamp, ai_text, ai_words_coords)
        
        return jsonify({
            'success': True,
            'text': ai_text,
            'words_coords': ai_words_coords
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/config", methods=["GET", "POST"])
def ai_config():
    """Endpoint to manage AI OCR configuration"""
    config_path = os.path.join(appdata_folder, "ai_config.json")
    
    if request.method == "GET":
        full = request.args.get('full') == 'true'
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                import json
                config = json.load(f)
                # Mask API key unless full=true
                if not full:
                    config['api_key'] = '***' if config.get('api_key') else ''
                return jsonify(config)
        return jsonify({'provider': 'gemini', 'api_key': ''})
    
    elif request.method == "POST":
        data = request.json
        import json
        with open(config_path, 'w') as f:
            json.dump(data, f)
        return jsonify({'success': True})


if __name__ == "__main__":
    create_db()

    print(f"Appdata folder: {appdata_folder}")

    # Start the thread to record screenshots
    t = Thread(target=record_screenshots_thread)
    t.start()

    app.run(port=8082)
