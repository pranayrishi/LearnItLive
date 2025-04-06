import cv2
import openai
import base64
import requests
import time
import numpy as np
import speech_recognition as sr
import pyttsx3  # Text-to-Speech
import os
from gtts import gTTS
from manim import *
from moviepy.editor import VideoFileClip, AudioFileClip
import glob
from WhiteBoardFeature import VirtualPainter as VP
import threading


# OpenAI API Key (Replace with your actual API key)
openai.api_key = "OPEN_AI_API_KEY"


# Initialize Text-to-Speech - moved outside functions to be a global instance
engine = None
speech_engine_lock = threading.Lock()


'''
def initialize_engine():
   """Initialize the TTS engine with a thread lock to prevent multiple initializations"""
   global engine
   with speech_engine_lock:
       if engine is None:
'''
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[80].id)  # Changed from 80 to 0 for default voice




def speak(text):
   """ Speak out loud and print text for debugging """
   print(f"🤖 AI: {text}")


   # Use thread-safe approach for TTS
   with speech_engine_lock:
       try:
           #initialize_engine()
           engine.say(text)
           engine.runAndWait()
       except RuntimeError:
           # Fallback method if engine is busy
           print("TTS engine busy, using alternative method")
           # Use gTTS as a fallback
           tts = gTTS(text=text, lang='en')
           tts.save("temp_speech.mp3")
           os.system("afplay temp_speech.mp3")  # For macOS, use appropriate command for your OS




def get_voice_input():
   """ Capture and process user speech input """
   recognizer = sr.Recognizer()
   with sr.Microphone() as source:
       recognizer.adjust_for_ambient_noise(source)
       print("🎤 Listening...")  # Print instead of speak to avoid recursive calls
       try:
           audio = recognizer.listen(source, timeout=10)
           user_input = recognizer.recognize_google(audio)
           print(f"🗣️ You said: {user_input}")
           return user_input.lower()
       except sr.UnknownValueError:
           print("Sorry, I didn't catch that. Could you repeat?")
           return None
       except sr.RequestError:
           print("I can't connect to the speech recognition service. Check your internet.")
           return None




def capture_frame():
   """ Capture an image from the webcam """
   cap = cv2.VideoCapture(0)
   time.sleep(1)
   if not cap.isOpened():
       speak("Oops! I can't access the webcam.")
       return None
   ret, frame = cap.read()
   cap.release()
   if ret and isinstance(frame, np.ndarray):
       img_path = "latest_frame.jpg"
       cv2.imwrite(img_path, frame)
       return img_path
   else:
       speak("Hmm, I couldn't capture a valid image. Let's try again.")
       return None




def encode_image(image_path):
   """ Encode image to base64 for API submission """
   with open(image_path, "rb") as image_file:
       return base64.b64encode(image_file.read()).decode("utf-8")




def analyze_image_with_gpt(image_path, user_prompt="What do you see?"):
   """ Analyze an image using GPT-4 Vision """
   base64_image = encode_image(image_path)
   headers = {"Authorization": f"Bearer {openai.api_key}"}
   payload = {
       "model": "gpt-4-turbo",
       "messages": [
           {"role": "system", "content": "You analyze images and assist users."},
           {"role": "user", "content": [
               {"type": "text", "text": user_prompt},
               {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
           ]}
       ],
       "max_tokens": 500
   }
   try:
       response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
       if response.status_code == 200:
           return response.json()["choices"][0]["message"]["content"]
       else:
           print(f"Error: {response.status_code}, {response.text}")
           return "Error analyzing image."
   except Exception as e:
       print(f"Exception: {e}")
       return "Error connecting to OpenAI service."




def generate_manim_script(topic):
   """ Generate a Manim script using GPT """
   prompt = f"Using the Manim library, create a valid and self-contained Python script that produces a clear, beginner-friendly animation explaining {topic}. Only use built-in Manim shapes, vector drawings, and text—do not reference or use any external images or files. All components and labels should be spaced out to avoid text overlap and ensure readability. The animation should be structured, visually engaging, and educational for a beginner audience. Return only the final Python Manim code with no markdown or explanation."
   response = openai.ChatCompletion.create(
       model="gpt-3.5-turbo",
       messages=[{"role": "system", "content": "Generate valid Manim code."},
                     {"role": "user", "content": prompt}]
   )
   return response['choices'][0]['message']['content'].strip().replace("```python", "").replace("```", "")




def generate_voiceover_script(topic):
   """ Generate a short educational voiceover for the math topic """
   prompt = f"Provide a 10-second explanation about '{topic}'."
   response = openai.ChatCompletion.create(
       model="gpt-3.5-turbo",
       messages=[{"role": "system", "content": "Generate educational explanations."},
                 {"role": "user", "content": prompt}]
   )
   return response['choices'][0]['message']['content'].strip()




def create_manim_video(manim_script):
   """ Create the Manim animation video """
   with open("generated_manim_script.py", "w") as f:
       f.write(manim_script)
   os.system("manim -pql generated_manim_script.py")




def get_latest_manim_video():
   """ Find the latest Manim-generated video file """
   video_files = glob.glob("media/videos/generated_manim_script/480p15/*.mp4")
   return max(video_files, key=os.path.getctime) if video_files else None




def generate_voiceover(text):
   """ Create a voiceover MP3 using gTTS """
   tts = gTTS(text=text, lang='en')
   tts.save("voiceover.mp3")




def combine_video_audio(video_path):
   """ Combine Manim video with generated voiceover """
   video = VideoFileClip(video_path)
   audio = AudioFileClip("voiceover.mp3")
   final_video = video.set_audio(audio)
   final_video.write_videofile("final_video.mp4", codec="libx264")






def generate_raspberrypi_video(topic):
   """ Generate a short educational voiceover for the math topic """
   prompt = f"Provide a clear and thoughtful description about '{topic}'."
   response = openai.ChatCompletion.create(
       model="gpt-3.5-turbo",
       messages=[{"role": "system", "content": "Generate educational explanations."},
                 {"role": "user", "content": prompt}]
   )
   return response['choices'][0]['message']['content'].strip()






def main():
   """ Main AI assistant loop """
   speak("Hello! I'm your AI assistant. How can I help you?")
   while True:
       user_input = get_voice_input()
       if not user_input:
           continue
       if "quit" in user_input:
           speak("Goodbye! Have a great day.")
           break


       # Detecting intent
       if "holding" in user_input or "look at" in user_input or "analyze" in user_input:
           speak("Alright, I'll analyze what you're holding. Give me a moment.")
           image_path = capture_frame()
           if image_path:
               observation = analyze_image_with_gpt(image_path, user_input)
               speak(f"Here's what I see: {observation}")
           else:
               speak("I couldn't get a clear image. Try again.")


       elif "teach me" in user_input or "learn" in user_input:
           topic = user_input.replace("teach me about", "").strip()
           speak(f"Got it! I'll create a Manim video about {topic}.")
           #VP.VirtualPainter()
           manim_script = generate_manim_script(topic)
           create_manim_video(manim_script)
           voiceover_script = generate_voiceover_script(topic)
           generate_voiceover(voiceover_script)
           latest_video = get_latest_manim_video()
           if latest_video:
               combine_video_audio(latest_video)
               speak("Your educational video is ready!")


       elif "set up" in user_input:
           topic = user_input.replace("set up the", "").strip()
           os.system("manim -pql RaspberryPi.py")
           speak("Alright, I'll help you set up the Raspberry Pi. Give me a moment.")
           raspberrypi_script = generate_raspberrypi_video(topic)
           speak(f"Here's what I see: {raspberrypi_script}")


       else:
           speak("I didn't quite understand. Could you rephrase?")




if __name__ == "__main__":
   try:
       main()
   except Exception as e:
       print(f"Program terminated with error: {e}")
       # Clean shutdown of any resources
       if 'engine' in globals() and engine is not None:
           engine.stop()
