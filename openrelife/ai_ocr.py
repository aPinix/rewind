import os
import json
import base64
from typing import Dict, List, Optional, Tuple
import requests


class AIProvider:
    """Base class for AI OCR providers"""
    
    def ocr_with_positions(self, image_base64: str, basic_ocr_text: str) -> Tuple[str, List[Dict]]:
        """
        Perform OCR with position mapping
        Returns: (text, words_with_coords)
        """
        raise NotImplementedError


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Use gemini-3-flash-preview as requested
        self.model = "gemini-3-flash-preview"
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
    
    def ocr_with_positions(self, image_base64: str, basic_ocr_text: str) -> Tuple[str, List[Dict]]:
        prompt = f"""You are an expert OCR system. Analyze this screenshot and extract all visible text accurately.

The basic OCR detected this text (may contain errors):
{basic_ocr_text[:1000]}{"..." if len(basic_ocr_text) > 1000 else ""}

Please:
1. Extract ALL visible text from the image
2. Fix any OCR errors you see
3. Maintain the original layout and line breaks
4. Return ONLY the corrected text, nothing else

Do not add any comments or explanations - just the text."""

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 8192  # Reduced since we're not asking for coordinates
            }
        }
        
        print(f"Calling Gemini API: {self.endpoint}")
        response = requests.post(
            f"{self.endpoint}?key={self.api_key}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Gemini response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Gemini error response: {response.text}")
            raise Exception(f"Gemini API error: {response.text}")
        
        result = response.json()
        ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
        
        print(f"AI returned text length: {len(ai_text)}")
        
        # Since we don't have coordinates from AI, return empty list
        # The UI will still use basic OCR coordinates for the overlay
        return ai_text, []


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.openai.com/v1/chat/completions"
    
    def ocr_with_positions(self, image_base64: str, basic_ocr_text: str) -> Tuple[str, List[Dict]]:
        prompt = f"""You are an expert OCR system. Analyze this screenshot and extract all visible text with precise positions.

The basic OCR detected this text:
{basic_ocr_text}

Please:
1. Perform a more accurate OCR, fixing any errors
2. For each word, provide its position as normalized coordinates (0-1 range) in format: x1, y1, x2, y2
3. Return the result as JSON in this exact format:
{{
  "words": [
    {{"text": "word", "x1": 0.1, "y1": 0.2, "x2": 0.15, "y2": 0.25}},
    ...
  ]
}}

Important: 
- x1,y1 is top-left corner, x2,y2 is bottom-right corner
- Coordinates must be normalized (0 to 1)
- Include ALL visible text
- Return ONLY valid JSON, no other text"""

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1
        }
        
        response = requests.post(
            self.endpoint,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.text}")
        
        result = response.json()
        text_response = result['choices'][0]['message']['content']
        
        # Extract JSON from response
        json_str = text_response.strip()
        
        # Remove markdown code blocks
        if '```json' in json_str:
            json_str = json_str.split('```json')[1].split('```')[0]
        elif '```' in json_str:
            json_str = json_str.split('```')[1].split('```')[0]
        
        json_str = json_str.strip()
        
        # Try to find JSON object if wrapped in other text
        if not json_str.startswith('{'):
            start = json_str.find('{')
            end = json_str.rfind('}')
            if start != -1 and end != -1:
                json_str = json_str[start:end+1]
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse OpenAI response as JSON: {e}")
        
        words = data.get('words', [])
        text = ' '.join(w['text'] for w in words)
        
        return text, words


class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.anthropic.com/v1/messages"
    
    def ocr_with_positions(self, image_base64: str, basic_ocr_text: str) -> Tuple[str, List[Dict]]:
        prompt = f"""You are an expert OCR system. Analyze this screenshot and extract all visible text with precise positions.

The basic OCR detected this text:
{basic_ocr_text}

Please:
1. Perform a more accurate OCR, fixing any errors
2. For each word, provide its position as normalized coordinates (0-1 range) in format: x1, y1, x2, y2
3. Return the result as JSON in this exact format:
{{
  "words": [
    {{"text": "word", "x1": 0.1, "y1": 0.2, "x2": 0.15, "y2": 0.25}},
    ...
  ]
}}

Important: 
- x1,y1 is top-left corner, x2,y2 is bottom-right corner
- Coordinates must be normalized (0 to 1)
- Include ALL visible text
- Return ONLY valid JSON, no other text"""

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4096,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(
            self.endpoint,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Claude API error: {response.text}")
        
        result = response.json()
        text_response = result['content'][0]['text']
        
        # Extract JSON from response
        json_str = text_response.strip()
        
        # Remove markdown code blocks
        if '```json' in json_str:
            json_str = json_str.split('```json')[1].split('```')[0]
        elif '```' in json_str:
            json_str = json_str.split('```')[1].split('```')[0]
        
        json_str = json_str.strip()
        
        # Try to find JSON object if wrapped in other text
        if not json_str.startswith('{'):
            start = json_str.find('{')
            end = json_str.rfind('}')
            if start != -1 and end != -1:
                json_str = json_str[start:end+1]
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Claude response as JSON: {e}")
        
        words = data.get('words', [])
        text = ' '.join(w['text'] for w in words)
        
        return text, words


def get_ai_provider(provider_name: str, api_key: str) -> AIProvider:
    """Factory function to get the appropriate AI provider"""
    providers = {
        'gemini': GeminiProvider,
        'openai': OpenAIProvider,
        'claude': ClaudeProvider
    }
    
    if provider_name.lower() not in providers:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(providers.keys())}")
    
    return providers[provider_name.lower()](api_key)
