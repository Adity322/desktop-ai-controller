"""
Jarvis Cross-Platform AI Voice Assistant
Author: Aditya Singh
Description:
Built a modular voice assistant with plugin-based architecture supporting system control, web search, news updates, YouTube playback, and app launching.
Designed cross-platform compatibility (Windows & macOS) with voice + keyboard fallbacks for reliability.
Integrated NLP (spaCy), API-based news fetching, and error-handling for smooth conversational interaction.
Implemented custom confirmation logic, API integrations, and extensible plugin manager, making the system scalable for future enhancements.
"""

# -------------------- Imports --------------------
import os                        #used for system control
import pyttsx3
import datetime                  #used for telling the date and time
import webbrowser                #used for browser controls
import pyautogui                 #used for youtube controls like mute unmute forward
import pywhatkit as kit          #used for playing videos on youtube by just speaking the tittle of that video
import speech_recognition as sr  #used for speech-to-text means that for jarvis to listen 
import spacy                     #used for nlp understanding
from serpapi import GoogleSearch #used for google search and for opening any link you want to open by just asking it to open that link
import platform                      #used for using jarvis on linux or macos also
from dotenv import load_dotenv    
import time
import urllib.parse  
import json  
import struct  
from sentence_transformers import SentenceTransformer
from intents import detect_intent, INTENT_THRESHOLD
import threading
from indexer import run_indexer
from searcher import search_file
from opener import open_file
from prep import AudioManager
from modules.brightness import increase_brightness, decrease_brightness
# -------------------- Core Config --------------------
WAKE_WORD = "jarvis"
with open("contacts.json", "r") as f:
    CONTACTS = json.load(f)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

intent_model = SentenceTransformer("all-MiniLM-L6-v2")
# Load memory
with open("memory.json", "r") as f:
    MEMORY = json.load(f)


# Load environment variables from .env
load_dotenv()

# Fetch keys
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
PORCUPINE_KEY = os.getenv("PORCUPINE_KEY")
KEYWORD_PATH = "/Users/adityakumarsingh/Downloads/jarvis_en_mac_v3_0_0/jarvis_en_mac_v3_0_0.ppn"
audio_manager = AudioManager(PORCUPINE_KEY, KEYWORD_PATH)
# Global search results memory
SEARCH_RESULTS = []

# NLP
nlp = spacy.load("en_core_web_sm")

# -------------------- Core Speaking --------------------
def speak(text):
    print(f"Jarvis: {text}")

    system = platform.system()

    # --- macOS: Use native TTS (fast, reliable, no audio conflicts)
    if system == "Darwin":
        os.system(f'say "{text}"')

    # --- Windows/Linux: Use pyttsx3
    else:
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception:
            # fallback if something breaks
            os.system(f'say "{text}"')
#-------ACK Function-----
def ack(prefix=None, suffix=None):
    text = ""

    if prefix:
        text += prefix + " "
    if suffix:
        text += suffix

    text = text.strip()

    if text:
        speak(text)

# -------------------- Voice Confirmation --------------------

def confirm_action(prompt: str) -> bool:
    # 1️⃣ Ask for confirmation
    speak(prompt)
    speak("Please say yes or no.")

    # 2️⃣ macOS TTS release delay (critical)
    time.sleep(2.0)

    # 3️⃣ Clear user cue
    speak("Listening now.")
    print(">>> CONFIRMATION LISTENING NOW <<<")

    # 4️⃣ Voice confirmation
    response = audio_manager.listen_once(
        timeout=10,
        phrase_time_limit=6
    )

    print(">>> RAW CONFIRMATION RESPONSE:", response)

    # 5️⃣ If voice failed → keyboard fallback
    if not response:
        speak("I did not hear you.")
        speak("Please confirm using the keyboard.")

        key = input("⚡ Confirm action? (y / n): ").strip().lower()
        return key in ("y", "yes")

    response = response.lower()

    # 6️⃣ Positive confirmations
    if any(word in response for word in ["yes", "yeah", "yep", "confirm"]):
        return True

    # 7️⃣ Negative confirmations
    if any(word in response for word in ["no", "not", "cancel", "stop", "don't"]):
        return False

    # 8️⃣ Unclear response → keyboard fallback
    speak("I couldn't clearly understand your response.")
    key = input("⚡ Confirm action? (y / n): ").strip().lower()
    return key in ("y", "yes")


def save_memory():
    with open("memory.json", "w") as f:
        json.dump(MEMORY, f, indent=4)

# -------------------- Plugin Manager --------------------
class PluginManager:
    def __init__(self):
        self.plugins = {}

    def register(self, name, func):
        self.plugins[name] = func

    def execute(self, name, *args, **kwargs):
        if name in self.plugins:
            try:
                return self.plugins[name](*args, **kwargs)
            except Exception as e:
                speak(f"Error in plugin {name}: {e}")
        else:
            speak(f"I don't know how to handle {name}.")

plugin_manager = PluginManager()

# -------------------- Plugins --------------------
def plugin_time():
    now = datetime.datetime.now()
    ack(prefix="Sure.", suffix=f"The time is {now.strftime('%I:%M %p')}.")

def plugin_date():
    today = datetime.date.today()
    ack(prefix="On it.", suffix=f"Today's date is {today.strftime('%B %d, %Y')}.")

def plugin_open_app(app_name):
    APPS = {
        "notepad": "notepad",
        "calculator": "calc",
        "command prompt": "start cmd",
        "chrome": "start chrome",
    }
    cmd = APPS.get(app_name)
    if cmd:
        ack(prefix="Okay.", suffix=f"Opening {app_name}.")
        os.system(cmd)
    else:
        ack(prefix="Hmm.", suffix=f"I couldn't find the app {app_name}.")

def plugin_open_website(site_name):
    WEBSITES = {
        "google": "https://google.com",
        "facebook": "https://facebook.com",
        "youtube": "https://youtube.com",
        "instagram": "https://instagram.com",
        "hotstar": "https://hotstar.com/in/mypage",
        "chatgpt": "https://chatgpt.com/?model=auto",
        "chat gpt": "https://chatgpt.com/?model=auto",
    }
    url = WEBSITES.get(site_name)
    if url:
        ack(prefix="Got it.", suffix=f"Opening {site_name}.")
        webbrowser.open(url)
    else:
        ack(prefix="Oops.", suffix=f"I couldn't find a website named {site_name}.")

# Store last search results globally
last_search_results = []


def plugin_search(query):
    MEMORY["last_search"] = query
    save_memory()

    global last_search_results
    ack(prefix="Searching.", suffix=f"Here are the top results for {query}.")
    last_search_results = []

    try:
        params = {
            "q": query,
            "hl": "en",
            "gl": "in",
            "api_key": SERPAPI_KEY  # 👈 get from serpapi.com
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        links = []
        if "organic_results" in results:
            for res in results["organic_results"][:10]:
                link = res.get("link")
                title = res.get("title")
                if link:
                    links.append((title, link))

        last_search_results = links

        if last_search_results:
            for i, (title, link) in enumerate(last_search_results[:3], 1):
                speak(f"Result {i}: {title}")
        else:
            speak("Sorry, I couldn’t fetch results.")

        # also open Google search page
        webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")

    except Exception as e:
        speak(f"Search failed: {e}")

def plugin_open_search_result(index: int):
    global last_search_results
    if not last_search_results:
        speak("Please perform a search first before opening a link.")
        return
    if 1 <= index <= len(last_search_results):
        title, url = last_search_results[index - 1]
        ack(prefix="Opening.", suffix=f"{title}")
        webbrowser.open(url)
    else:
        speak("I couldn’t find that result number.")


def plugin_youtube(song):
    MEMORY["last_song"] = song
    save_memory()

    speak(f"Playing {song} on YouTube.")

    try:
        # Get YouTube video URL (does NOT auto open)
        video_url = kit.playonyt(song, open_video=False)

        # Open the video directly in browser
        webbrowser.open(video_url)

        # That's it — YouTube auto-plays the video
        # No pyautogui
        # No key press
        # No cursor dependency

    except Exception as e:
        speak(f"There was an issue playing the video: {e}")



def plugin_youtube_control(action: str):
    if "pause" in action or "resume" in action:
        pyautogui.press("k")
        ack("Done.", "Toggled play/pause on YouTube.")
    elif "mute" in action:
        pyautogui.press("m")
        ack("Done.", "Muted or unmuted video.")
    elif "forward" in action or "skip" in action:
        pyautogui.press("l")
        ack("Skipped forward.", "10 seconds ahead.")
    elif "back" in action or "rewind" in action:
        pyautogui.press("j")
        ack("Rewinding.", "10 seconds back.")
    elif "full screen" in action:
        pyautogui.press("f")
        ack("Okay.", "Toggled fullscreen mode.")
    elif "unmute" in action:
        pyautogui.press("m")
    elif "half screen" in action:
        pyautogui.press("f") 
    else:
        ack("Sorry.", "I didn’t recognize that YouTube control command.")

def plugin_close_tab():
        pyautogui.hotkey("command","w")
        ack(prefix="Done.", suffix="Closed the current tab.")
def plugin_system(command: str):
    if "shutdown" in command:
        speak("Shutting down your system.")
        if platform.system() == "Windows":
            os.system("shutdown /s /t 1")
        elif platform.system() == "Darwin":
            os.system("sudo shutdown -h now")
        else:
            os.system("shutdown now")

    elif "restart" in command:
        speak("Restarting your system.")
        if platform.system() == "Windows":
            os.system("shutdown /r /t 1")
        elif platform.system() == "Darwin":
            os.system("sudo shutdown -r now")
        else:
            os.system("reboot")

    elif "sleep" in command:
        speak("Putting system to sleep.")
        if platform.system() == "Windows":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif platform.system() == "Darwin":
            os.system("pmset sleepnow")
        else:
            os.system("systemctl suspend")

def plugin_help():
    lines = [
        "You can say things like:",
        " - open youtube / open chrome / open notepad",
        " - play shape of you",
        " - pause youtube / play youtube / mute youtube",
        " - skip youtube / rewind youtube / fullscreen youtube",
        " - who is Elon Musk / search python decorators",
        " - open first link / open second link",
        " - time / date",
        " - close tab",
        " - shutdown / restart / sleep (requires confirmation)",
        f" - say '{WAKE_WORD}' to activate, 'stop listening' to sleep",
    ]
    speak("\n".join(lines))

from serpapi import GoogleSearch

def plugin_news(query=None):
    """Fetch top Google News headlines using SerpApi."""
    try:
        # Default: show top news if no topic is given
        if not query or query.strip() == "":
            query = "latest news"

        speak(f"Fetching top news about {query}...")

        params = {
            "engine": "google_news",
            "q": query,  # topic or keyword
            "gl": "in",  # country
            "hl": "en",  # language
            "api_key": SERPAPI_KEY # ⚠️ replace with your key
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        
        news_items = results.get("news_results", [])

        if not news_items:
            speak(f"Sorry, I couldn't find any {query} news.")
            return

        speak(f"Here are the top {min(3, len(news_items))} headlines.")
        for i, article in enumerate(news_items[:3], 1):
            title = article.get("title", "No title")
            source = article.get("source", {}).get("name", "Unknown source")
            date = article.get("date", "")
            print(f"{i}. {title} ({source}, {date})")
            speak(f"{i}. {title} from {source}.")

    except Exception as e:
        speak(f"I faced an error fetching news: {e}")
        print("DEBUG:", str(e))



def plugin_send_whatsapp(contact_name, message):
    """Send WhatsApp message via installed WhatsApp Desktop app (auto-presses Enter)."""
    try:
        contact_name = contact_name.lower().strip()
        number = CONTACTS.get(contact_name)

        if not number:
            speak(f"I don't have a contact saved as {contact_name}. Please add them first.")
            return

        encoded_message = urllib.parse.quote(message)
        whatsapp_url = f"whatsapp://send?phone={number}&text={encoded_message}"

        system = platform.system()

        speak(f"Opening WhatsApp chat with {contact_name}...")

        if system == "Windows":
            os.system(f'start "" "{whatsapp_url}"')
        elif system == "Darwin":
            os.system(f'open "{whatsapp_url}"')
        else:
            webbrowser.open(whatsapp_url)

        # Wait a few seconds for WhatsApp to open
        time.sleep(5)

        # Press 'Enter' to send message automatically
        pyautogui.press("enter")
        speak(f"Message sent successfully to {contact_name}.")

    except Exception as e:
        speak(f"Something went wrong while sending the message: {e}")
        print("DEBUG:", e)

def plugin_macos_control(action: str):

    action = action.lower().strip()

    # ---- VOLUME ----
    if "volume up" in action:
        os.system('osascript -e "set volume output volume ((output volume of (get volume settings)) + 10)"')
        speak("Volume increased.")

    elif "volume down" in action:
        os.system('osascript -e "set volume output volume ((output volume of (get volume settings)) - 10)"')
        speak("Volume decreased.")

    elif "mute" in action:
        os.system('osascript -e "set volume with output muted"')
        speak("Muted.")

    elif "unmute" in action:
        os.system('osascript -e "set volume without output muted"')
        speak("Unmuted.")

    # ---- BRIGHTNESS ----
    elif "brightness up" in command:
        increase_brightness()
        speak("Brightness increased")

    elif "brightness down" in command:
        decrease_brightness()
        speak("Brightness decreased")
    # ---- WIFI ----
    elif "wifi on" in action:
        os.system('osascript -e "do shell script \\"networksetup -setairportpower en0 on\\""')
        speak("Wi-Fi turned on.")

    elif "wifi off" in action:
        os.system('osascript -e "do shell script \\"networksetup -setairportpower en0 off\\""')
        speak("Wi-Fi turned off.")

    # ---- BLUETOOTH ----
    elif "bluetooth on" in action:
        os.system('osascript -e "do shell script \\"blueutil --power 1\\""')
        speak("Bluetooth turned on.")

    elif "bluetooth off" in action:
        os.system('osascript -e "do shell script \\"blueutil --power 0\\""')
        speak("Bluetooth turned off.")

    # ---- SCREENSHOT ----
    elif "screenshot" in action:
        os.system("screencapture ~/Desktop/screenshot.jpg")
        speak("Screenshot saved on Desktop.")

    # ---- LOCK SCREEN ----
    elif "lock screen" in action or "lock mac" in action:
        os.system('/System/Library/CoreServices/Menu\\ Extras/User.menu/Contents/Resources/CGSession -suspend')
        speak("Locking your Mac.")

    # ---- BATTERY STATUS ----
    elif "battery" in action or "battery status" in action:
        os.system('pmset -g batt > battery_info.txt')
        with open("battery_info.txt") as f:
            info = f.read()
        speak("Here is your battery information.")
        print(info)

    # ---- OPEN SETTINGS ----
    elif "open settings" in action or "system settings" in action:
        os.system('open /System/Applications/System\\ Settings.app')
        speak("Opening system settings.")

    # ---- EMPTY TRASH ----
    elif "empty trash" in action or "clear trash" in action:
        os.system('osascript -e "empty the trash"')
        speak("Trash emptied.")

    else:
        speak("Sorry, I couldn't understand the mac control command.")

def plugin_open_file(query):
    results = search_file(query)

    if not results:
        speak(f"I couldn't find any file related to {query}.")
        return

    file_path = results[0]
    speak(f"Opening {os.path.basename(file_path)}.")
    open_file(file_path)


  
# -------------------- Register Plugins --------------------
plugin_manager.register("time", plugin_time)
plugin_manager.register("date", plugin_date)
plugin_manager.register("open_app", plugin_open_app)
plugin_manager.register("open_website", plugin_open_website)
plugin_manager.register("search", plugin_search)
plugin_manager.register("open_search_result", plugin_open_search_result)
plugin_manager.register("youtube", plugin_youtube)
plugin_manager.register("youtube_control", plugin_youtube_control)
plugin_manager.register("close_tab", plugin_close_tab)
plugin_manager.register("system", plugin_system)
plugin_manager.register("help", plugin_help)
plugin_manager.register("news", plugin_news)
plugin_manager.register("send_whatsapp", plugin_send_whatsapp)
plugin_manager.register("macos_control", plugin_macos_control)
plugin_manager.register("open_file", plugin_open_file)
# -------------------- NLP Parsing --------------------
def nlp_understand(command: str):
    doc = nlp(command)
    intent, target = None, None
    cleaned = command

    if any(w in command for w in ("open first link", "open second link", "open third link", "open fourth link", "open fifth link","open six link")):
        intent = "open_search_result"
    elif any(w in command for w in ("open", "launch", "start")):
        intent = "open"
    elif "play" in command:
        intent = "play"
    elif any(w in command for w in ("pause youtube", "resume youtube", "mute youtube","unmute youtube","forward youtube", "rewind youtube", "full screen youtube","half screen youtube".strip())):
        intent = "youtube_control"
        target = command
    elif "time" in command:
        intent = "time"
    elif "date" in command:
        intent = "date"
    elif any(w in command for w in ("shutdown", "reopen", "sleep")):
        intent = "system"
    elif "close tab" in command:
        intent = "close"
    elif any(w in command for w in ("news", "headlines", "latest news")):
        intent = "news"
    elif any (w in command for w in ("send message", "send whatsapp", "message", "text")):
        intent = "send_whatsapp"
    elif any(w in command for w in ("search", "find","how", "who is", "what is", "tell me about")):
        intent = "search"
        target = command
    elif any(w in command for w in ("brightness", "volume", "wifi", "bluetooth", 
                                "screenshot", "lock screen", "battery", "system settings", 
                                "empty trash")):
        intent = "macos_control"
        target = command

    if intent in ("open", "play"):
        cleaned = command
        for w in ("open", "launch", "start", "play"):
            cleaned = cleaned.replace(w, "").strip()
    target = cleaned

    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT", "WORK_OF_ART", "GPE") and len(ent.text.split()) > 1:
            target = ent.text.lower()
            break
    if not target and doc.noun_chunks:
        target = list(doc.noun_chunks)[-1].text.lower()
    if target:
        for f in ["please", "could you", "would you", "can you", "will you"]:
            target = target.replace(f, "")
        target = target.strip()
    return intent, target

#--------NLP HELPERS--------------#
def extract_entities(text: str):
    doc = nlp(text)
    entities = {}
    for ent in doc.ents:
        entities.setdefault(ent.label_, []).append(ent.text)
    return entities


def handle_semantic_intent(intent, command, entities):
    if intent == "PLAY_MEDIA":
        return plugin_manager.execute("youtube", command)

    elif intent == "OPEN_APP":
        return plugin_manager.execute("open_app", command)

    elif intent == "SEARCH":
        return plugin_manager.execute("search", command)

    elif intent == "SYSTEM_CONTROL":
        return plugin_manager.execute("system", command)
    elif intent == "MEDIA_CONTROL":
        return plugin_manager.execute("youtube_control", command)


    else:
        speak("I understood your request, but I can't do that yet.")

# -------------------- Command Processor --------------------

def process_command(command: str):
    cmd = command.lower().strip()

    # -------- help --------
    if "help" in cmd:
        return plugin_manager.execute("help")

    # -------- exit --------
    if any(x in cmd for x in ("exit", "quit")):
        ack(prefix="Goodbye.", suffix="Exiting now.")
        raise SystemExit

    # -------- MEMORY FEATURE --------
    if any(p in cmd for p in ["last song", "play last song", "repeat last song"]):
        last_song = MEMORY.get("last_song")
        if last_song:
            return plugin_manager.execute("youtube", last_song)

    # ================= PHASE 4 =================
    semantic_intent, confidence = detect_intent(cmd)

    # ================= PHASE 5 =================
    if confidence >= INTENT_THRESHOLD:

        # ================= PHASE 7 =================
        entities = extract_entities(cmd)

        # ================= PHASE 8 =================
        MEMORY["last_intent"] = semantic_intent
        MEMORY["last_command"] = cmd
        MEMORY["last_entities"] = entities
        save_memory()

        return handle_semantic_intent(semantic_intent, cmd, entities)

    # ================= PHASE 6 (FALLBACK) =================
    intent, target = nlp_understand(cmd)

    # -------- LEGACY ROUTING (UNCHANGED) --------
    if intent == "open":

    # websites
        if target in ["google", "facebook", "youtube", "instagram", "hotstar", "chatgpt", "chat gpt"]:
            return plugin_manager.execute("open_website", target)

    # known apps
        KNOWN_APPS = ["notepad", "calculator", "chrome", "terminal"]
        if target in KNOWN_APPS:
            return plugin_manager.execute("open_app", target)

    # everything else → FILE SEARCH
        return plugin_manager.execute("open_file", target)


    elif intent == "play":
        return plugin_manager.execute("youtube", target)

    elif intent == "youtube_control":
        return plugin_manager.execute("youtube_control", target)

    elif intent == "search":
        return plugin_manager.execute("search", command)
    
    elif intent == "open_search_result":
        if "first" in cmd: return plugin_manager.execute("open_search_result", 1)
        if "second" in cmd: return plugin_manager.execute("open_search_result", 2)
        if "third" in cmd: return plugin_manager.execute("open_search_result", 3)
        if "fourth" in cmd: return plugin_manager.execute("open_search_result", 4)
        if "fifth" in cmd: return plugin_manager.execute("open_search_result", 5)


    elif intent == "time":
        return plugin_manager.execute("time")

    elif intent == "date":
        return plugin_manager.execute("date")

    elif intent == "system":
        return plugin_manager.execute("system", cmd)

    elif intent == "close":
        return plugin_manager.execute("close_tab")

    elif intent == "news":
        return plugin_manager.execute("news")
    
    elif intent == "send_whatsapp":
        try:
            text = command.lower()

        # Step 1: detect contact name
            contact = None
            for c in CONTACTS.keys():
                if c in text:
                    contact = c
                    break

            if not contact:
                return speak("I couldn't detect the contact name. Please say, send message to someone.")

        # Step 2: Ask user for the message
            speak(f"What message do you want to send to {contact}?")
            recognizer = sr.Recognizer()

            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                print("Listening for message...")
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=8)

            message = recognizer.recognize_google(audio).lower()
            print(f"Message captured: {message}")

        # Final: Send the message
            plugin_manager.execute("send_whatsapp", contact, message)
            return speak(f"Message sent to {contact}.")

        except Exception as e:
            return speak(f"Error while processing WhatsApp command: {e}")


    elif intent == "macos_control":
        return plugin_manager.execute("macos_control", target)
    speak("Sorry, I couldn't understand that. Can you rephrase?")

def start_file_indexing_background():
    t = threading.Thread(target=run_indexer, daemon=True)
    t.start()


# -------------------- Main Program --------------------
# -------------------- Main Program --------------------
if __name__ == "__main__":

    speak("Jarvis initialized and ready. Say 'Jarvis' to wake me.")
    start_file_indexing_background()

    # 🔊 Start wake-word engine via prep.py
    audio_manager.start_wake_word()

    try:
        while True:
            pcm = audio_manager.audio_stream.read(
                audio_manager.porcupine.frame_length,
                exception_on_overflow=False
            )

            pcm = struct.unpack_from(
                "h" * audio_manager.porcupine.frame_length,
                pcm
            )

            if audio_manager.porcupine.process(pcm) >= 0:
                print("Wake word detected")

                # 🔥 RELEASE MIC FROM PORCUPINE
                audio_manager.stop_wake_word()

                speak("Yes?")
                command = audio_manager.listen_once()

                if not command:
                    speak("I didn't catch that.")
                    audio_manager.start_wake_word()
                    continue

                print("User command:", command)

                # ---- SHUTDOWN ----
                if "shutdown" in command:
                    if confirm_action("Do you want to shut down?"):
                        plugin_manager.execute("system", "shutdown")
                    else:
                        speak("Shutdown cancelled.")

                # ---- RESTART ----
                elif "restart" in command:
                    if confirm_action("Do you want to restart?"):
                        plugin_manager.execute("system", "restart")
                    else:
                        speak("Restart cancelled.")

                # ---- WHATSAPP ----
                elif "send whatsapp" in command or "send message" in command:
                    contact = None
                    for c in CONTACTS:
                        if c in command:
                            contact = c
                            break

                    if not contact:
                        speak("I couldn't detect the contact name.")
                    else:
                        speak(f"What message do you want to send to {contact}?")
                        message = audio_manager.listen_once(
                            timeout=8,
                            phrase_time_limit=8
                        )

                        if not message:
                            speak("Message cancelled.")
                        elif confirm_action(
                            f"Do you want me to send '{message}'?"
                        ):
                            plugin_manager.execute(
                                "send_whatsapp",
                                contact,
                                message
                            )
                        else:
                            speak("Message cancelled.")

                # ---- EVERYTHING ELSE ----
                else:
                    process_command(command)

                # 🔁 GIVE MIC BACK TO PORCUPINE
                audio_manager.start_wake_word()

    except KeyboardInterrupt:
        print("Exiting Jarvis...")
