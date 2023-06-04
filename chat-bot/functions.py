import requests, re
import pyttsx3 as tts
import speech_recognition
from playsound import playsound as sound
import datetime
from music import *
import struct
import face_recognition
import cv2
import os
import numpy as np
import pickle
import csv
import random
import time

# Import for sound files
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

K9_TTS = None
weather_key = 'bf63b77834f1e14ad335ba6c23eea570'

local_recogniser = None
global_spotify = None
global_device_id = None

def play_sound(file_path, volume, blocking=True):
    pygame.mixer.init()
    sound = pygame.mixer.Sound(file_path)
    sound.set_volume(volume)
    if blocking:
        sound.play()
        while pygame.mixer.get_busy():  # Wait for the sound to finish playing
            pygame.time.Clock().tick(10)  # Control the loop speed
    else:
        sound.play()

# Initiliasing the Text to Speech engine
def initialise_tts():
    global K9_TTS
    K9_TTS = tts.init()
    K9_TTS.setProperty('rate', 200)

# Calibrates mic for 2 seconds (adjusts to ambient noise)
def calibrate_mic(recogniser):
     with speech_recognition.Microphone() as source:   
        print("Please wait. Calibrating microphone...")   
        recogniser.adjust_for_ambient_noise(source, duration=3)

# Recognises user input and converts to text
def recognise_input(recogniser):
    global local_recogniser
    local_recogniser = recogniser
    with speech_recognition.Microphone() as mic:
        audio = recogniser.listen(mic)
        play_sound("assets/prompt.mp3", 0.8, blocking=False)
        message = recogniser.recognize_google(audio)
        message = message.lower()
        return message

def listen_for_wake_word(porcupine, audio_stream):
    while True:
        pcm = audio_stream.read(porcupine.frame_length)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
        keyword_index = porcupine.process(pcm)
        if keyword_index >= 0:
            print("Custom Keyword Detected")
            break

# Text to speech
def speak(text):
    print('K9: ' + text)
    K9_TTS.say(text)
    K9_TTS.runAndWait()

def send_variables(spotify, device_id):
    global global_spotify
    global global_device_id

    global_spotify = spotify
    global_device_id = device_id

def extract_song_info(text):
    # Try to match the pattern 'play' followed by song name and artist
    match = re.search(r'play(?: me)?\s(.+?)(?:\sby\s(.+))?$', text, re.IGNORECASE)
    if match:
        song_name = match.group(1).strip()
        artist = match.group(2).strip() if match.group(2) is not None else ""
    else:
        # If the previous pattern fails, try to match 'listen to' followed by song name and artist, or just the song name if 'by' is not present
        match = re.search(r'listen to(?:\s(.+?))(?:\sby\s(.+))?$', text, re.IGNORECASE)
        if match:
            song_name = match.group(1).strip() if match.group(1) is not None else ""
            artist = match.group(2).strip() if match.group(2) is not None else ""
        else:
            song_name = ""
            artist = ""
    return song_name.title(), artist.title()


def extract_song_and_artist(text):
    # Extract the song name and artist from the user input
    match = re.search(r'(.+?)(?:\sby\s(.+))?$', text)
    song_name = match.group(1).strip() if match.group(1) is not None else ""
    artist = match.group(2).strip() if match.group(2) is not None else ""
    return song_name.title(), artist.title()

def extract_playlist_info(text):
    # Try to match the pattern 'playlist' followed by the playlist name
    match = re.search(r'playlist\s(.+)$', text, re.IGNORECASE)
    if match:
        playlist_name = match.group(1).strip()
    else:
        playlist_name = ""
    return playlist_name

def extract_podcast_info(text):
    match = re.search(r'podcast\s(.+)$', text, re.IGNORECASE)
    if match:
        podcast_name = match.group(1).strip()
    else:
        podcast_name = ""
    return podcast_name


# Local functions called by Watson (must take user_input even if not used)
def request_song(text):
    global local_recogniser
    speak("Sure, what song do you want to listen to?")
    done = False
    while not done:
        try:
            song = recognise_input(local_recogniser)
            song_name, artist = extract_song_and_artist(song)
            print("song", song_name)
            print("artist", artist)
            if artist == "":
                time.sleep(4)
                uri = get_track_uri(spotify=global_spotify, name=song_name)
                play_track(spotify=global_spotify, device_id=global_device_id, uri=uri)
                speak(f"Playing {song_name}.")
            # If song title + artist provided
            else:
                time.sleep(4)
                uri = get_track_uri(spotify=global_spotify, name=song_name, artist=artist)
                play_track(spotify=global_spotify, device_id=global_device_id, uri=uri)
                speak(f"Playing {song_name} by {artist}.")
            done = True
        except speech_recognition.UnknownValueError:
            local_recogniser = speech_recognition.Recognizer()
            speak("Please repeat...")

def request_specific_song(text):
    song_name, artist = extract_song_info(text)
    if (artist == "" and song_name == ""):
        speak(f"Search unsuccessful, please try again.")
        return
    # If only song title provided
    if artist == "":
        time.sleep(4)
        uri = get_track_uri(spotify=global_spotify, name=song_name)
        play_track(spotify=global_spotify, device_id=global_device_id, uri=uri)
        speak(f"Playing {song_name}.")
    # If song title + artist provided
    else:
        time.sleep(4)
        uri = get_track_uri(spotify=global_spotify, name=song_name, artist=artist)
        play_track(spotify=global_spotify, device_id=global_device_id, uri=uri)
        speak(f"Playing {song_name} by {artist}.")

def request_playlist(text):
    global local_recogniser  
    speak("Sure, what playlist do you want to listen to?")
    done = False
    while not done:
        try:
            playlist_name = recognise_input(local_recogniser).title()
            print("Playlist: ", playlist_name)
            time.sleep(4)
            uri = get_playlist_uri(spotify=global_spotify, name=playlist_name)
            play_playlist(spotify=global_spotify, device_id=global_device_id, uri=uri)
            speak(f"Playing {playlist_name}.")
            done = True
        except speech_recognition.UnknownValueError:
            local_recogniser = speech_recognition.Recognizer()
            speak("Please repeat...")

def request_specific_playlist(text):
    playlist_name = extract_playlist_info(text).title()
    if playlist_name == "":
        speak(f"Search unsuccessful, please try again.")
        return
    else:
        time.sleep(4)
        uri = get_playlist_uri(spotify=global_spotify, name=playlist_name)
        play_playlist(spotify=global_spotify, device_id=global_device_id, uri=uri)
        speak(f"Playing {playlist_name}.")

def request_podcast(text):
    global local_recogniser  
    speak("Sure, what podcast do you want to listen to?")
    done = False
    while not done:
        try:
            podcast_name = recognise_input(local_recogniser).title()
            print("Podcast: ", podcast_name)
            time.sleep(4)
            uri = get_podcast_uri(spotify=global_spotify, name=podcast_name)
            play_podcast(spotify=global_spotify, device_id=global_device_id, uri=uri)
            speak(f"Playing {podcast_name}.")
            done = True
        except speech_recognition.UnknownValueError:
            local_recogniser = speech_recognition.Recognizer()
            speak("Please repeat...")

def request_specific_podcast(text):
    podcast_name = extract_podcast_info(text).title()
    if podcast_name == "":
        speak(f"Search unsuccessful, please try again.")
        return
    else:
        time.sleep(4)
        uri = get_podcast_uri(spotify=global_spotify, name=podcast_name)
        play_podcast(spotify=global_spotify, device_id=global_device_id, uri=uri)
        speak(f"Playing {podcast_name}.")

def is_music_paused():
    return is_track_paused(spotify=global_spotify)

def pause_music(text):
    pause_track(spotify=global_spotify, device_id=global_device_id)

def play_music(text):
    resume_play(spotify=global_spotify, device_id=global_device_id)

def play_liked(text):
    liked_songs = get_liked_songs(spotify=global_spotify)
    play_liked_songs(spotify=global_spotify, device_id=global_device_id, liked_songs=liked_songs)

def play_next(text):
    next_track(spotify=global_spotify, device_id=global_device_id)

def play_previous(text):
    prev_track(spotify=global_spotify, device_id=global_device_id)

def extract_volume_percentage(text):
    # Try to find the pattern 'to' followed by a number, with or without '%'
    match = re.search(r'to\s+(\d+)%?', text, re.IGNORECASE)
    if match:
        volume_percentage = int(match.group(1))
        return volume_percentage
    else:
        return None
    
def set_vol(text):
    set_vol = extract_volume_percentage(text)
    set_volume(spotify=global_spotify, device_id=global_device_id, volume=set_vol)

def increase_vol(text):
    current_volume = get_current_volume(spotify=global_spotify, device_id=global_device_id)
    if current_volume is not None:
        new_volume = min(current_volume + 10, 100)
        set_volume(spotify=global_spotify, device_id=global_device_id, volume=new_volume)
        print(f"Volume increased to {new_volume}%")
    else:
        print("No active playback or device found.")

def decrease_vol(text):
    current_volume = get_current_volume(spotify=global_spotify, device_id=global_device_id)
    if current_volume is not None:
        new_volume = max(current_volume - 10, 0)
        set_volume(spotify=global_spotify, device_id=global_device_id, volume=new_volume)
        print(f"Volume decreased to {new_volume}%")
    else:
        print("No active playback or device found.")

def get_weather(user_input):
    pattern = r"(?<=\bin\s).*"
    matches = re.search(pattern, user_input)    
    if matches:
        location = matches.group(0).title()
    else:
        location = "London"
    weather_data = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={location}&units=metric&APPID={weather_key}")
    weather = weather_data.json()['weather'][0]['main']
    temp = round(weather_data.json()['main']['temp'])
    speak(f"In {location}, the temperature is {temp} degrees, it's {weather}.")

def get_day(user_input):
    day = datetime.datetime.now().strftime('%A')
    speak(f"Today is {day}.")


class SimpleFacerec:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.frame_resizing = 0.25

    def load_encoding_images(self, images_path, save_file=None):
        if save_file and os.path.exists(save_file):
            # Load pre-encoded face encodings from file
            with open(save_file, 'rb') as f:
                data = pickle.load(f)
            self.known_face_encodings = data['encodings']
            self.known_face_names = data['names']
        else:
            # Encode faces and save the encodings
            images_path = os.path.abspath(images_path)
            for filename in os.listdir(images_path):
                if filename.endswith('.jpg') or filename.endswith('.png'):
                    image_path = os.path.join(images_path, filename)
                    img = cv2.imread(image_path)
                    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    encoding = face_recognition.face_encodings(rgb_img)[0]
                    self.known_face_encodings.append(encoding)
                    self.known_face_names.append(os.path.splitext(filename)[0])

            if save_file:
                # Save the face encodings to file
                data = {'encodings': self.known_face_encodings, 'names': self.known_face_names}
                with open(save_file, 'wb') as f:
                    pickle.dump(data, f)

    def detect_known_faces(self, frame):
        small_frame = cv2.resize(frame, (0, 0), fx=self.frame_resizing, fy=self.frame_resizing)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Unknown"

            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = self.known_face_names[best_match_index]
            face_names.append(name)

        face_locations = np.array(face_locations)
        face_locations = face_locations / self.frame_resizing
        return face_locations.astype(int), face_names
    
def scan_face():
    # Encode faces from a folder and save the encodings
    save_file = 'face_encodings.pkl'
    sfr = SimpleFacerec()
    sfr.load_encoding_images("faces/", save_file=save_file)

    # Load Camera
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        recognized_names = []  # Initialize the list inside the loop

        # Detect Faces
        face_locations, face_names = sfr.detect_known_faces(frame)
        if len(face_locations) == 0:  # No face detected
            error_message = "N"
            return error_message
        for face_loc, name in zip(face_locations, face_names):
            y1, x2, y2, x1 = face_loc[0], face_loc[1], face_loc[2], face_loc[3]

            recognized_names.append(name)  # Add recognized name to the list

            cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 200), 2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 200), 4)


        if len(recognized_names) > 0:
            break

    cap.release()
    cv2.destroyAllWindows()
    return(recognized_names)

def add_face(text):
    global local_recogniser
    name = False
    speak("... Sure")
    while name == False:
        done = False
        while not done:
            speak("What's your name?")
            try:
                person = recognise_input(local_recogniser)
                done=True
            except speech_recognition.UnknownValueError:
                local_recogniser = speech_recognition.Recognizer()
                speak("Please repeat...")
        
        print("Name: ", person)
        finish = False
        while not finish:
            speak(f"Is your name {person}?")
            try:
                response = recognise_input(local_recogniser)
                print("[INPUT] ",response)
                finish = True
            except speech_recognition.UnknownValueError:
                local_recogniser = speech_recognition.Recognizer()
                speak("Please repeat...")

        if ('no' in response) or ('nope' in response):
            speak("Okay, Lets try again.")
            name = False
        else:
            if ('yes' in response) or ('yeah' in response):               
                name = True
            name = True #consider changing 
    cap = cv2.VideoCapture(0)
    speak("Get ready for a picture")
    speak("3")
    speak("2")
    speak("1")
    _, image = cap.read()
    speak("Smile!")
    image_path = f"faces/{person}.jpg"
    cv2.imwrite(image_path, image)
    speak(f"All done! Hello {person}")
    print(f"Face captured and saved as {image_path}")
    cap.release()
    cv2.destroyAllWindows()
    save_file = 'face_encodings.pkl'
    sfr = SimpleFacerec()
    sfr.load_encoding_images("faces/", save_file=save_file)



def be_positive(text):
    global local_recogniser
    categories = ["Exercise", "Gratitude", "Learning", "Reading", "Walking"]
    category = random.choice(categories)
    folder_path = os.path.join('assets', 'behaviours')
    file_path = os.path.join(folder_path, f'{category}.csv')
    location = "Chelsea"  # adjust to dog location

    def get_suggestions():
        suggestions = []

        closest_temperature_diff = float('inf')
        closest_temperature_activity = None

        with open(file_path, 'r') as options:
            reader = csv.reader(options)
            for row in reader:
                row_weather = row[1]
                row_temperature = int(row[2])
                temperature_diff = abs(row_temperature - temp)
                if temperature_diff <= 3.0 and weather == row_weather:
                    suggestions.append(row[3])
                elif temperature_diff < closest_temperature_diff and weather == row_weather:
                    closest_temperature_diff = temperature_diff
                    closest_temperature_activity = row[3]

        if len(suggestions) > 0:
            return suggestions
        elif closest_temperature_activity:
            return [closest_temperature_activity]

    while True:
        weather_data = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={location}&units=metric&APPID={weather_key}")
        weather_json = weather_data.json()
        weather = weather_json['weather'][0]['main']
        temp = round(weather_json['main']['temp'])
        suggestions = get_suggestions()
        motivation = random.choice(suggestions)
        prev_motivation = motivation
        prev_category = category

        speak("My suggestion is ...")
        speak(f"{motivation}")
        speak("Would you like a different suggestion?")

        attempt_counter = 0
        max_attempts = 3  # Set the maximum number of attempts

        while attempt_counter < max_attempts:
            category = random.choice(categories)
            try:
                response = recognise_input(local_recogniser)
                print("[INPUT] ", response)
                if 'yes' in response:
                    while prev_category == category:
                        category = random.choice(categories)
                    suggestions = get_suggestions()
                    if suggestions:
                        suggestions.remove(prev_motivation)  # Remove the previous suggestion from the available suggestions
                        if suggestions:
                            motivation = random.choice(suggestions)
                        else:
                            speak("I'm sorry, I couldn't find any more suggestions at the moment.")
                            break  # Exit the inner while loop
                        speak("Another suggestion is ...")
                        speak(f"{motivation}")
                    else:
                        speak("I'm sorry, I couldn't find any more suggestions at the moment.")
                        break  # Exit the inner while loop
                    break  # Exit the inner while loop
                elif 'no' in response:
                    speak("No problem!")
                    break  # Exit the inner while loop
                else:
                    speak("I didn't understand. Please respond with 'yes' or 'no'.")
                attempt_counter += 1
            except speech_recognition.UnknownValueError:
                local_recogniser = speech_recognition.Recognizer()
                speak("Please repeat...")

        if attempt_counter >= max_attempts:
            speak("Sorry, I couldn't find any more suggestions. If you need further assistance, feel free to ask.")
        break  # Exit the outer while loop




        
def greet_me(text):
    # Encode faces from a folder and save the encodings
    save_file = 'face_encodings.pkl'
    sfr = SimpleFacerec()
    sfr.load_encoding_images("faces/", save_file=save_file)
    # Load Camera
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        recognized_names = []  # Initialize the list inside the loop
        # Detect Faces
        face_locations, face_names = sfr.detect_known_faces(frame)
        if len(face_locations) == 0:  # No face detected
            error_message = "N"
            return error_message
        for face_loc, name in zip(face_locations, face_names):
            y1, x2, y2, x1 = face_loc[0], face_loc[1], face_loc[2], face_loc[3]
            recognized_names.append(name)  # Add recognized name to the list
            cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 200), 2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 200), 4)
        if len(recognized_names) > 0:
            break
    cap.release()
    cv2.destroyAllWindows()
    for name in recognized_names:
        if name == "N" or name == "Unknown":
            speak("Hi, I don't think we have met. I'm K9. If you want me to greet you by name, say Hey K9, Add me!")
        else:
            speak(f"Hey {name}. I'm K9.")

def extract_article_number(user_input):
    number_words = {
        'one': 1,
        'two': 2,
        'three': 3,
        'four': 4,
        'five': 5
    }
    match = re.search(r'\bnumber\s*(\w+)\b', user_input, re.IGNORECASE)
    if match:
        number_word = match.group(1)
        if number_word in number_words:
            return number_words[number_word]
    return None


def get_news(user_input):
    global local_recogniser
    news_data = requests.get('https://newsdata.io/api/1/news?apikey=pub_2224719bbcc10e32c3eaae46f288b9876718a&language=en&country=gb&domain=bbc')
    news = news_data.json()
    titles = ""
    for i in range(min(5, len(news["results"]))):
        titles += news["results"][i]["title"] + "\n"
    speak("Here's the latest news: \n" + titles)
    speak("Would you like me to read any of these articles? If so, simply say the article number. You can also say 'repeat' to hear the titles again.")
    done = False
    while not done:
        try:
            user_reply = recognise_input(local_recogniser)
            print("Reply: ", user_reply)
            if user_reply == "repeat":
                speak("Here are the latest news: \n" + titles)
                speak("Please provide a number from 1 to 5")
            elif user_reply == "no":
                speak("Alright!")
                done = True
            else:
                article_number = extract_article_number(user_reply)
                if article_number is not None:
                    article_index = article_number - 1
                    if 0 <= article_index < min(5, len(news["results"])):
                        speak(news["results"][article_index]["description"])
                        done = True
                    else:
                        speak("Sorry, the specified article number is out of range.")
                        done = True
                else:
                    speak("Please provide a number from 1 to 5")
        except speech_recognition.UnknownValueError:
            local_recogniser = speech_recognition.Recognizer()
            speak("Please repeat...")

def get_specific_news(user_input):
    global local_recogniser
    matches = [
        re.search(r'\bon\s(?P<substring>.+)', user_input),
        re.search(r'\babout\s(?P<substring>.+)', user_input),
        re.search(r'\bon the\s(?P<substring>.+)', user_input),
        re.search(r'\babout the\s(?P<substring>.+)', user_input)
    ]

    max_position = -1
    substring_max = ""

    for match in matches:
        if match:
            substring = match.group("substring")
            position = match.start("substring")
            if position > max_position:
                max_position = position
                substring_max = substring

    news_data = requests.get(f'https://newsdata.io/api/1/news?apikey=pub_2224719bbcc10e32c3eaae46f288b9876718a&language=en&country=gb&q={substring_max}')
    news = news_data.json()
    titles = ""
    for i in range(min(5, len(news["results"]))):
        titles += news["results"][i]["title"] + "\n"
    speak(f"These are the latest news on {substring_max}: \n" + titles)
    speak("Do you want me to read any of these? Say the number of the article if so. Or say repeat for me to repeat the titles.")
    done = False
    while not done:
        try:
            user_reply = recognise_input(local_recogniser)
            print("Reply: ", user_reply)
            article_number = extract_article_number(user_reply)
            if user_reply == "repeat":
                speak(f"These are the latest news on {substring_max}: \n" + titles)
            elif user_reply == "no":
                speak("Alright!")
                done = True
            elif article_number is not None and 1 <= article_number <= 5:
                speak(news["results"][article_number - 1]["description"])
                done = True
            else:
                speak("I didn't understand")
        except speech_recognition.UnknownValueError:
            local_recogniser = speech_recognition.Recognizer()
            speak("Please repeat...")

def get_random_joke(text):
    url = "https://v2.jokeapi.dev/joke/Any?type=twopart"
    response = requests.get(url)
    data = response.json()

    if data["type"] == "twopart":
        setup = data["setup"]
        punchline = data["delivery"]
        joke = f"{setup}\n{punchline}"
    else:
        joke = data["joke"]

    speak(joke)





        




