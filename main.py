import os
import json
import time
import threading
from datetime import datetime
from pygame import mixer

# Global State
active_alarms = {}
last_trigger_times = {}
state_lock = threading.Lock()
music_playing_file = None
running = True

def load_config():
    """Loads settings from config.json, falling back to defaults if not found."""
    default_config = {
        "reminders": [
            {
                "name": "water",
                "interval_seconds": 1800,
                "music_file": "water.wav",
                "stop_code": "Drank",
                "log_message": "Water drank"
            },
            {
                "name": "eyes",
                "interval_seconds": 3600, 
                "music_file": "eyes.mp3",
                "stop_code": "Eye",
                "log_message": "Eyes movement"
            },
            {
                "name": "exercise",
                "interval_seconds": 7200,
                "music_file": "exer.mp3",
                "stop_code": "Exercise",
                "log_message": "Exercise"
            }
        ]
    }
    
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config.json: {e}. Using default settings.")
    return default_config

def log_now(msg):
    """Appends compliance record to record_store.txt."""
    log_path = os.path.join(os.path.dirname(__file__), "record_store.txt")
    try:
        with open(log_path, "a") as file:
            file.write(f"{msg} is done at {datetime.now()}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

def update_music():
    """Manages audio playback based on current active alarms."""
    global music_playing_file
    with state_lock:
        if not active_alarms:
            if music_playing_file is not None:
                try:
                    if mixer.get_init():
                        mixer.music.stop()
                except Exception:
                    pass
                music_playing_file = None
        else:
            # Play music of one of the active alarms
            first_alarm = list(active_alarms.values())[0]
            target_file = first_alarm["music_file"]
            if music_playing_file != target_file:
                try:
                    if not mixer.get_init():
                        mixer.init()
                    music_path = os.path.join(os.path.dirname(__file__), target_file)
                    mixer.music.load(music_path)
                    mixer.music.play(-1)
                    music_playing_file = target_file
                except Exception as e:
                    print(f"\n[Warning] Could not play audio file '{target_file}': {e}")
                    music_playing_file = None

def timer_thread_func(reminders):
    """Background loop that ticks once per second checking reminder intervals."""
    global running
    while running:
        current_time = time.time()
        any_triggered = False
        
        with state_lock:
            for reminder in reminders:
                name = reminder["name"]
                interval = reminder["interval_seconds"]
                
                # Check if this reminder is already active
                if name in active_alarms:
                    continue
                
                # If timer exceeded
                if current_time - last_trigger_times[name] > interval:
                    active_alarms[name] = reminder
                    print(f"\n[ALARM] Time for {name.capitalize()}! Enter '{reminder['stop_code']}' to stop: ", end="", flush=True)
                    any_triggered = True
        
        if any_triggered:
            update_music()
            
        time.sleep(1)

if __name__ == "__main__":
    config = load_config()
    reminders = config.get("reminders", [])
    
    # Initialize trigger times
    now = time.time()
    for reminder in reminders:
        last_trigger_times[reminder["name"]] = now
        
    print("Health Programmer Started.")
    print("Monitoring reminders...")
    print("Type 'exit' or '1' to quit the program at any time.\n")
    
    # Start background timer thread
    timer_thread = threading.Thread(target=timer_thread_func, args=(reminders,), daemon=True)
    timer_thread.start()
    
    try:
        while True:
            # Blocking input in the main thread (allows stopping alarms asynchronously)
            query = input().strip()
            
            if query.lower() in ["exit", "1"]:
                running = False
                break
                
            # Check if query matches any active alarm's stop code
            matched_name = None
            matched_msg = None
            with state_lock:
                for name, reminder in active_alarms.items():
                    if reminder["stop_code"] == query:
                        matched_name = name
                        matched_msg = reminder["log_message"]
                        break
                        
            if matched_name:
                with state_lock:
                    del active_alarms[matched_name]
                    # Update base trigger time so next reminder counts from compliance verification time
                    last_trigger_times[matched_name] = time.time()
                log_now(matched_msg)
                print(f"[SUCCESS] Stopped {matched_name} alarm. Logged task.")
                update_music()
            else:
                if active_alarms:
                    print("Invalid code. Active alarm codes: " + ", ".join(f"'{r['stop_code']}'" for r in active_alarms.values()))
                else:
                    print("No active alarms. Keep working!")
    except KeyboardInterrupt:
        print("\nExiting program...")
    finally:
        running = False
        try:
            if mixer.get_init():
                mixer.music.stop()
        except Exception:
            pass
        
        # Print final logs on exit as in the original code
        print("\n--- Compliance Logs ---")
        log_path = os.path.join(os.path.dirname(__file__), "record_store.txt")
        if os.path.exists(log_path):
            try:
                with open(log_path, "r") as f:
                    print(f.read())
            except Exception as e:
                print(f"Error reading log file: {e}")
        print("Goodbye!")
        