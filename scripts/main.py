if __name__ == "__main__":
    import os
    import threading
    import pygame
    import pygame.camera
    import time
    from datetime import datetime, date, timedelta
    import io
    from typing import Literal
    from gemini_ai import GeminiAI, SerializableFile
    from voice_recognition import VoiceRecognition
    from text_to_speech import TextToSpeech
    from extern_api import *
    import sched
    import queue
    import keyboard
    from pathlib import Path
    import sys
    from PIL import ImageGrab, Image
    import cv2
    import numpy as np
    from queue import Queue
    from app_watchdog import ApplicationWatchdog, CHECK_INTERVAL

    print("Usage: Modify the config.json to change parameters")

    SOUNDS_PATH = 'sounds/'
    USER_VOICE_PATH = 'sounds/users'
    TEMP_PATH = 'temp/'
    CHATLOG_PATH = TEMP_PATH+'chatlog/'
    IMAGE_PATH = TEMP_PATH+'images/'
    CONFIG_FILE = 'config.json'
    HISTORY_FILE = 'history.txt'
    MEMORY_FILE = 'memory.txt'

    context = {
        'talk': [],
        'upload_file': None,
        'vision_mode': False,
        'system_message_in_a_row': 0,   # This and the following is to prevent system message trigger infinite system message loop. Sometimes the AI will post system_message in a response to system_message and loop it forever.
        'upload_in_a_row': 0,
        'freetalk': True,
        'sleep': False,
        'memory': [],
        'memory_str': '',
        'vision_mode_camrea_is_screen' : False    # This will work with Discord video call to capture the video screen as the AI's vision, in this case you are on the other end of discord chat holding the phone camera
    }

    pygame.init()
    pygame.camera.init()
    scheduler = sched.scheduler(time.time, time.sleep)
    alarm_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}alarm.mp3")
    code_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}code.mp3")
    code_sound.set_volume(0.2)
    analyze_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}analyze.mp3")
    analyze_sound.set_volume(0.2)
    fail_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}failed.mp3")
    event_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}event.mp3")
    event_sound.set_volume(0.5)
    voice_on_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}sonar.mp3")
    voice_on_sound.set_volume(0.5)
    voice_off_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}confirm.mp3")
    voice_off_sound.set_volume(0.5)
    recording_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}recording.mp3")
    recording_sound.set_volume(0.2)
    start_up_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}startup.mp3")
    shutter_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}shutter.mp3")
    shutter_sound.set_volume(0.5)
    recurring_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}recurring.mp3")
    power_off_sound = pygame.mixer.Sound(f"{SOUNDS_PATH}poweroff.mp3")
    today = str(date.today())
    evt_enter = threading.Event()
    wdt_feed_lock1 = threading.Lock()
    wdt_feed_lock2 = threading.Lock()

    # Create the folder if it doesn't exist
    os.makedirs(TEMP_PATH, exist_ok=True)
    os.makedirs(CHATLOG_PATH, exist_ok=True)
    os.makedirs(IMAGE_PATH, exist_ok=True)

    if len(sys.argv) >= 2:
        CONFIG_FILE = sys.argv[1]

    def check_config():
        global config

        # The default values
        MAX_HISTORY = 20 
        MAX_MEMORY = 10
        AI_NAME = 'Jarvis'
        TARGET_CAMERA = 'DroidCam Video'
        USER_CHROME_DATA_PATH = 'C:\\Users\\Zhenya\\AppData\\Local\\Google\\Chrome\\User Data'
        RECORDER_DEVICE = None
        SPEAKER_DEVICE = None

        default_config = {
            'ai_name': AI_NAME,
            'model_name': 'gemini-1.5-flash',
            'user_chrome_data_path': USER_CHROME_DATA_PATH,
            'max_history' : MAX_HISTORY,
            'max_memory' : MAX_MEMORY,
            'target_camera': TARGET_CAMERA,
            'recorder_device': RECORDER_DEVICE,
            'speaker_device': SPEAKER_DEVICE,
            'voice_similarity_threshold': 0.72,
            'allow_record_during_speaking' : True
        }
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            print('-----')
            for key in default_config.keys():
                print(key, config[key])
            print('-----')

        except Exception as e:
            print('Load config error! Create new.')

            config = default_config
            print(json.dumps(config, indent = 2))
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)

    check_config()
    set_browser_data_path(config['user_chrome_data_path'])

    class UnifiedRecorder:
        def __init__(self, camera:pygame.camera.Camera):
            """
            Initialize unified recorder for both screen and camera recording
            
            Args:
                camera_resolution (tuple): Resolution for camera recording
                camera_index (int): Camera device index (usually 0 for built-in webcam)
            """
            self.is_recording = False
            self.frame_queue = Queue()
            self.recording_thread = None
            self.recording_type = None
            self.camera = camera
            # unfortunately gemini samples video in 1 frame per second. We can however sample more frames per second and output in 1 fps so it is in slow motion
            self.fps = 4
            
        def capture_screen_frames(self):
            """Background thread function to capture screen frames"""
            while self.is_recording:
                frame = ImageGrab.grab()
                frame = np.array(frame)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                self.frame_queue.put(frame)
                time.sleep(1/self.fps)
                
        def capture_camera_frames(self):
            """Background thread function to capture camera frames"""
            #self.camera.start()
            while self.is_recording:
                frame = self.camera.get_image()
                frame_buffer = pygame.surfarray.array3d(frame)
                frame_buffer = frame_buffer.transpose([1, 0, 2])
                frame_array = np.array(frame_buffer)
                frame_array = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
                self.frame_queue.put(frame_array)
                time.sleep(1/self.fps)
            #self.camera.stop()

        def start_recording(self, record_type='screen'):
            """
            Start recording
            
            Args:
                record_type (str): Type of recording ('screen' or 'camera')
            
            Returns:
                bool: True if recording started successfully
            """
            if self.is_recording:
                print("Recording is already in progress")
                return False
                
            if record_type not in ['screen', 'camera']:
                print("Invalid record type. Use 'screen' or 'camera'")
                return False
                
            if record_type == 'camera' and self.camera is None:
                print("Camera is not available")
                return False
            
            self.is_recording = True
            self.recording_type = record_type
            
            if record_type == 'screen':
                self.recording_thread = threading.Thread(target=self.capture_screen_frames)
            else:
                self.recording_thread = threading.Thread(target=self.capture_camera_frames)
                
            self.recording_thread.start()
            print(f"Started {record_type} recording...")
            return True

        def stop_recording(self, output_filename, resize_width=640):
            """
            Stop recording and save the video
            
            Args:
                output_filename (str): Name for the output file (should end with .mp4)
                resize_width (int): Resize the frame
            
            Returns:
                str: Path to the saved video file
            """
            if not self.is_recording:
                print("No recording in progress")
                return None

            # Stop the recording thread
            self.is_recording = False
            self.recording_thread.join()

            # Get initial frame to determine dimensions
            if self.frame_queue.empty():
                print("No frames captured")
                return None
            
            if(output_filename):
                first_frame = self.frame_queue.queue[0]
                height, width = first_frame.shape[:2]
                new_width = int(resize_width)
                new_height = int(resize_width / width * height)

                # Initialize video writer
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(
                    output_filename,
                    fourcc,
                    1,  # Gemini sample video in 1 FPS, so higher FPS is useless in output
                    (new_width, new_height),
                    True
                )

                print("Processing and saving video...")
                
                frame_count = 0
                while not self.frame_queue.empty():
                    frame = self.frame_queue.get()
                    
                    # Apply basic compression
                    frame = cv2.GaussianBlur(frame, (3, 3), 0)

                    # Resize frame
                    frame = cv2.resize(frame, (new_width, new_height), 
                                    interpolation=cv2.INTER_AREA)
                    
                    frame = np.uint8(frame)
                    
                    out.write(frame)
                    frame_count += 1

                out.release()
                print(f"Video saved to: {output_filename} ({frame_count} frames)")
            self.frame_queue.queue.clear()
            return output_filename

    instruction = [
        f'''Remember, your name is {config['ai_name']}.
        You are a well educated and professional assistant, have great knowledge on everything. You make most suitable decision for the users.
        Keep in mind that there can be multiple users speaking. If it is a main master user, his/her name will be as prefix. If it is a guest, there will be a **Guest:** prefix, attached at the beginning of request. 
        If the request message is with prefix **System:** then it means this message is from the system, not the user. 
        You have the interface on physical world through python code, there are several python function APIs to interact with the physical world. The list of which is in the uploaded text list file. 
        To execute the python code, put the code as python snippet at the end of the response, then any code in the snippet in response will be executed. Only one code snippet per response is allowed.
        In that case, if you just want to show me the python code rather than execute it, do not put it in the python snippet form. 
        Variables scope in python snippet is limited to that snippet. If you want to store variable and so can be accessed in another snippet, store it using context['temp_key'] = value, then you can access context['temp_key'] in another snippet.
        Be aware, you will not respond to the guest for the requests about operating the house, unless you get authorization from the users that are not with guest prefix. For other kinds of requests, you should help with the guest. 
        To operate with the PC, use the python code execution with necessary library. But do not do potentially harmful operations, like deleting files, unless get the non guest users' permission. 
        You are to answer questions in a concise and always humorous way, and talk more casual and use more expressive words that talks more lively, like haha, oh, wow, hmmm.'''
    ]

    def append2log(text:str):
        fname = CHATLOG_PATH + 'chatlog-' + today + '.txt'
        with open(fname, "a", encoding='utf8') as f:
            f.write(text.strip() + "\n")

    def save_history():
        with open(f'{TEMP_PATH}{HISTORY_FILE}', "w", encoding='utf8') as f:
            f.write(json.dumps(context['talk']))

    def load_history():
        try:
            with open(f'{TEMP_PATH}{HISTORY_FILE}', "r", encoding='utf8') as f:
                text = f.read()
                context['talk'] = json.loads(text)
                for item in context['talk']:
                    for idx, part in enumerate(item['parts']):
                        if part.startswith('+') and part.endswith('+'):
                            # this is a gemini file
                            filename = part[1:-1]
                            item['parts'][idx] = gemini_ai.get_file(filename)

        except Exception as e:
            print(e)
            context['talk'] = []

    def system_message(*value: object,
            sep: str | None = " ",
            end: str | None = "\n",
            flush: Literal[False] = False):
        string_output = io.StringIO()
        print(*value, file=string_output, sep=sep, end=end, flush=flush)
        response = string_output.getvalue().strip()
        if context['system_message_in_a_row'] < 3 and context['upload_in_a_row'] < 2:
            context['system_message_in_a_row'] += 1
            if response.startswith('file:'):
                filename = response.split(':', maxsplit=1)[1]
                if response.endswith('.jpg'):
                    context['upload_file'] = gemini_ai.upload_file(filename, display_name='Photo')
                    response = 'This is the photo.'
                    context['upload_in_a_row'] += 1
                elif response.endswith('.txt'):
                    context['upload_file'] = gemini_ai.upload_file(filename, display_name='Text')
                    response = 'This is the content.'
                    context['upload_in_a_row'] += 1
                else:
                    context['upload_file'] = gemini_ai.upload_file(filename, display_name='File')
                    response = 'This is the content.'
                    context['upload_in_a_row'] += 1
            response = f"**System:**{response}"
            mInputQueue.put(response)
            string_output.close()
            analyze_sound.play()
        else:
            print("Too many system message call in a row!")

    def vision_mode(on:bool, type:str):
        if type == 'camera':
            context['vision_mode_camrea_is_screen'] = False
        else:
            context['vision_mode_camrea_is_screen'] = True

        if(on):
            if not context['vision_mode_camrea_is_screen']:
                cam.start()
            context['vision_mode'] = True
        else:
            context['vision_mode'] = False
            cam.stop()
            
    def camera_shot()->str:
        # opening the camera, in case it is not open
        cam.start()
        # might need to adjust this value
        time.sleep(0.5)
        img = cam.get_image()
        shutter_sound.play()
        timestr = time.strftime("%Y%m%d-%H%M%S")
        photo_path = f"{IMAGE_PATH}camera-{timestr}.jpg"
        # saving the image 
        pygame.image.save(img, photo_path)
        return 'file:'+photo_path
    
    def screenshot() -> str:
        # Capture the screenshot
        screenshot = ImageGrab.grab()
        shutter_sound.play()

        # Half the resolution to minimize tokens used and increase speed
        width, height = screenshot.size

        # Calculate the new dimensions (half of the original)
        new_width = width // 2
        new_height = height // 2

        # Resize the image to half resolution
        screenshot = screenshot.resize((new_width, new_height), Image.LANCZOS)

        timestr = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{IMAGE_PATH}screenshot-{timestr}.jpg"

        # Save the screenshot as JPG
        screenshot.save(filename, "JPEG")
        return 'file:'+filename
    
    def capture_upload_photo():
        if context['vision_mode_camrea_is_screen']:
            filename = screenshot()
        else:
            filename = camera_shot()

        previous = context['upload_file']
        context['upload_file'] = gemini_ai.upload_file(path=filename,
                            display_name="Photo")
        if previous:
            # A previously unused photo file
            gemini_ai.delete_file(previous)


    def exec_code(code:str):
        try:
            d = dict(locals(), **globals())
            code_sound.play()
            exec(code, d, d)
        except Exception as e:
            fail_sound.play()
            err_msg = f'Code exec exception: {e}'
            print(err_msg)
            system_message(err_msg)

    def event_thread():
        clock = pygame.time.Clock()

        while True:
            try:
                clock.tick(10)
                scheduler.run(blocking=False)
            except Exception as e:
                print(e)

    def callback_wrapper(cb, arg=()):
        print('Event')
        event_sound.play()
        cb(*arg)
    
    def recurring_wrapper(interval_sec, cb, arg=()):
        print('Recurring event')
        recurring_sound.play()
        # Might resulting a request from recurring event, clear some flags
        context['system_message_in_a_row'] = 0
        context['upload_in_a_row'] = 0
        cb(*arg)
        scheduler.enter(interval_sec, 1, recurring_wrapper, argument=(interval_sec, cb, arg))

    def schedule_recurring(interval_sec, cb, arg=()):
        if not type(arg) is tuple:
            arg = (arg,)
        scheduler.enter(interval_sec, 1, recurring_wrapper, argument=(interval_sec, cb, arg))

    def schedule(dt:datetime, cb, arg=()):
        if not type(arg) is tuple:
            arg = (arg,)
        secs = (dt - datetime.now()).total_seconds()
        scheduler.enter(secs, 1, callback_wrapper, argument=(cb, arg))

    def clear_schedule():
        list(map(scheduler.cancel, scheduler.queue))

    def switch_user_voice():
        text_to_speech.switch_user_voice(voice_recognition.recorder.audio)

    def switch_default_mode():
        text_to_speech.switch_default_mode()

    def switch_trump_mode():
        text_to_speech.switch_trump_mode()

    def switch_biden_mode():
        text_to_speech.switch_biden_mode()

    def switch_vader_mode():
        text_to_speech.switch_vader_mode()

    def switch_robot_mode():
        text_to_speech.switch_robot_mode()
    
    def switch_female_mode():
        text_to_speech.switch_female_mode()

    def play_alarm_sound():
        alarm_sound.play(2)
    
    def play_text_voice(text:str):
        text_to_speech.speak(text)

    def freetalk_mode(on:bool):
        previous = context['freetalk']
        if previous == False and on == True:
            context['freetalk'] = on
            # The voice recognition thread might stuck on the event waiting for key input, we cancel that first
            evt_enter.set()
        elif previous == True and on == False:
            # hack to bypass the wait for audio in voice recorder
            voice_recognition.recorder.start()
            voice_recognition.recorder.stop()
            context['freetalk'] = on

    def get_today_conversation() -> str:
        fname = CHATLOG_PATH + 'chatlog-' + today + '.txt'
        return fname    
    def start_new_conversation(summary:str):
        start_up_sound.play()
        context['talk'] = []
        context['talk'].append({'role': 'user', 'parts': [f'This is our previous talk summary from your perspective: {summary}']})
        context['talk'].append({'role': 'model', 'parts': ['All right, I will reference that information as part of the context.']})
        clear_schedule()
    
    def go_sleep():
        print('Enter sleep')
        power_off_sound.play()
        context['sleep'] = True

    def save_memory():
        with open(f'{TEMP_PATH}{MEMORY_FILE}', "w") as file:
            for item in context['memory']:
                file.write(item + "\n")

    def update_memory_str():
        if len(context['memory']) > 0:
            context['memory_str'] = f"You remember these things: {",".join(context['memory'])}"
        else:
            context['memory_str'] = 'You have no memory of the users yet.'

    def add_memory(item:str):
        context['memory'].append(item)
        if len(context['memory']) > config['max_memory']:
            context['memory'] = context['memory'][-config['max_memory']:]
        update_memory_str()
        save_memory()

    def load_memory():
        try:
            with open(f'{TEMP_PATH}{MEMORY_FILE}', "r") as file:
                context['memory'] = file.read().splitlines()
        except Exception as e:
            print("Memory load error, skip")
        update_memory_str()

    def clear_memory():
        context['memory'].clear()
        update_memory_str()
        save_memory()

    def main():
        global context, gemini_ai, voice_recognition, text_to_speech, cam, mInputQueue, photo_upload_thread, upload_handle, gemini_ai

        from json import JSONEncoder
        # for gemini file serialization
        def _default(self, obj):
            return getattr(obj.__class__, "to_json", _default.default)(obj)

        _default.default = JSONEncoder().default
        JSONEncoder.default = _default

        mInputQueue = queue.Queue()

        # Initialize camera
        camlist = pygame.camera.list_cameras()
        img_size = (640, 360)
        cam = None
        if camlist:
            if config['target_camera'] in camlist:
                cam = pygame.camera.Camera(config['target_camera'], img_size)
            else:
                cam = pygame.camera.Camera(camlist[0], img_size)

        recorder = UnifiedRecorder(cam)

        # Start event thread
        threading.Thread(target=event_thread).start()

        talk_header = [
            {'role': 'user', 'parts': [None, 'This is the list of python APIs you can execute. To execute them, put them in python code snippet at the end of your response. Now start a new conversation.', '']},
            {'role': 'model', 'parts': ['''Alright, I'm ready to execute some Python code! Starting a fresh new talk!\n```python\nstart_new_conversation("""We had some fun talks over various topics.""")\n```''']}
        ]

        gemini_ai = GeminiAI(model_name=config['model_name'], system_instruction=instruction)

        def check_function_file():
            needUpload = False
            if not talk_header[0]['parts'][0]:
                needUpload = True
            else:
                try:
                    test = gemini_ai.get_file(talk_header[0]['parts'][0].name)
                except Exception as e:
                    needUpload = True

            if needUpload:
                try:
                    if not talk_header[0]['parts'][0]:
                        function_file = gemini_ai.upload_file(path="api_list.txt", display_name="Python API")
                        talk_header[0]['parts'][0] = function_file
                except Exception as e:
                    print(e)
                    with wdt_feed_lock2:
                        text_to_speech.speak('Hmm, looks like some connection issues out there.')

        def check_history_files():
            for item in context['talk']:
                for i, part in enumerate(item['parts']):
                    if part is SerializableFile:
                        try:
                            test = gemini_ai.get_file(part.name)
                        except Exception as e:
                            print(e)
                            print('Some of the files are invald, clear the file reference')
                            # some of the file might be invalid already(might due to TTL in the server), just clear the reference for now
                            item['parts'][i] = ' '

        def on_record_start():
            if not context['freetalk']:
                text_to_speech.stop()
            if context['vision_mode']:
                if context['vision_mode_camrea_is_screen']:
                    recorder.start_recording('screen')
                else:
                    recorder.start_recording('camera')

        text_to_speech = TextToSpeech(SOUNDS_PATH, device_name=config['speaker_device'])
        voice_recognition = VoiceRecognition(on_recording_start=on_record_start, device_name=config['recorder_device'])
        voice_recognition.recorder.set_recording_judger(lambda: not text_to_speech.stream.is_playing())
        if not config['allow_record_during_speaking']:
            voice_recognition.recorder.set_use_record_judger_for_recording(True)

        def trigger_button(e):
            evt_enter.set()

        def input_thread():
            while True:
                text = input()
                text = f'**Master:**{text}'
                if context['vision_mode']:
                    if context['vision_mode_camrea_is_screen']:
                        recorder.start_recording('screen')
                    else:
                        recorder.start_recording('camera')
                    time.sleep(5)
                    timestr = time.strftime("%Y%m%d-%H%M%S")
                    file_name = f"{IMAGE_PATH}video-{timestr}.mp4"
                    recorder.stop_recording(file_name)
                    recording_sound.play()
                    context['upload_file'] = gemini_ai.upload_file(path=file_name,
                        display_name="Video")

                # Request is from keyboard, clear some flags
                context['system_message_in_a_row'] = 0
                context['upload_in_a_row'] = 0
                mInputQueue.put(text)

        def voice_thread():
            new_speaker_recorded = False
            verify_threshold = config['voice_similarity_threshold']
            
            user_lists = []
            for root, _, files in os.walk(USER_VOICE_PATH):
                for file in files:
                    if file.endswith('.wav'):
                        file_path = os.path.join(root, file)
                        user = os.path.splitext(file)[0]
                        
                        # Generate embedding
                        embedding = voice_recognition.generate_embed(Path(file_path))
                        
                        user_lists.append({
                            "user": user,
                            "embedding": embedding
                        })

            if(len(user_lists) == 0):
                print("Warning: No user voice sample registered! Run record_master_wave.py to register a user first!")
                print(f"You can still talk by saying the AI name {config['ai_name']} in your phrase, or 'Nice to meet your'.")

            exceptionCounter = 0
            while True:
                try:
                    text = None
                    temp_text = None
                    if not context['freetalk']:
                        # -179 is the play/pause media key
                        keyboard.on_press_key(-179, trigger_button, suppress=True)
                        keyboard.on_press_key('tab', trigger_button, suppress=True)

                        evt_enter.clear()
                        evt_enter.wait()
                        evt_enter.clear()
                        print("Listening ...")
                            
                        # In case change in the middle
                        if not context['freetalk']:
                            voice_on_sound.play()
                            with wdt_feed_lock1:
                                voice_recognition.start_listen()

                                evt_enter.wait()
                                evt_enter.clear()
                                
                                voice_off_sound.play()

                                temp_text = voice_recognition.stop_listen()

                            voice_embed = voice_recognition.generate_embed(voice_recognition.recorder.audio)
                            closest_similarity = 0
                            closest_user = None
                            for item in user_lists:
                                user_similarity = voice_recognition.verify_speaker(item['embedding'], voice_embed)
                                print(f"{item['user']} similarity:", user_similarity)
                                if user_similarity > closest_similarity:
                                    closest_similarity = user_similarity
                                    closest_user = item['user']

                            if closest_similarity > verify_threshold:
                                text = f'**{closest_user}:**{temp_text}'
                            else:
                                text = f'**Guest:**{temp_text}'

                            if(recorder.is_recording):
                                recording_sound.play()
                                timestr = time.strftime("%Y%m%d-%H%M%S")
                                file_name = f"{IMAGE_PATH}video-{timestr}.mp4"
                                recorder.stop_recording(file_name)
                                context['upload_file'] = gemini_ai.upload_file(path=file_name,
                                    display_name="Video")
                                
                            keyboard.unhook_all()
                        else:
                            keyboard.unhook_all()

                    else:
                        evt_enter.clear()
                        voice_recognition.listen()
                        print(len(voice_recognition.recorder.audio)/voice_recognition.recorder.sample_rate, 'sec')
                        if context['sleep']:
                            # It is sleeping, we detect if the name appears in the text to exit sleep
                            if not temp_text:
                                with wdt_feed_lock1:
                                    temp_text = voice_recognition.transcribe_voice()
                                print('Sleeping:', temp_text)
                            if config['ai_name'] in temp_text:
                                print('Exit sleep')
                                context['sleep'] = False
                        if not context['sleep']:
                            # in free talk mode, we verify the speaker
                            voice_embed = voice_recognition.generate_embed(voice_recognition.recorder.audio)

                            closest_similarity = 0
                            closest_user = None
                            for item in user_lists:
                                user_similarity = voice_recognition.verify_speaker(item['embedding'], voice_embed)
                                print(f"{item['user']} similarity:", user_similarity)
                                if user_similarity > closest_similarity:
                                    closest_similarity = user_similarity
                                    closest_user = item['user']

                            if (closest_similarity > verify_threshold) and (not text_to_speech.stream.is_playing() or  (text_to_speech.stream.is_playing() and len(voice_recognition.recorder.audio) > voice_recognition.recorder.sample_rate * 2)):    # Only transcribe sentence which is > 2 seconds long when it is talking, ignore small fragments
                                if not temp_text:
                                    with wdt_feed_lock1:
                                        temp_text = voice_recognition.transcribe_voice()

                                text = f'**{closest_user}:**{temp_text}'
                                voice_off_sound.play()
                            else:
                                # do the AI_NAME match only when it is not talking and record length > 2sec, as this consumes GPU resource
                                if not text_to_speech.stream.is_playing() and len(voice_recognition.recorder.audio) > voice_recognition.recorder.sample_rate * 2:
                                    if not temp_text:
                                        with wdt_feed_lock1:
                                            temp_text = voice_recognition.transcribe_voice()
                                    print(temp_text)
                                    if (config['ai_name'] in temp_text) or ('to meet you' in temp_text):
                                        print('Update guest embedding')
                                        current_guest_embed = voice_embed
                                        new_speaker_recorded = True
                                        text = f'**Guest:**{temp_text}'
                                        voice_off_sound.play()

                                if not text and new_speaker_recorded:
                                    guest_similarity = voice_recognition.verify_speaker(current_guest_embed, voice_embed)
                                    print('guest similarity:', guest_similarity)
                                    if guest_similarity > verify_threshold:
                                        if not temp_text:
                                            with wdt_feed_lock1:
                                                temp_text = voice_recognition.transcribe_voice()
                                        text = f'**Guest:**{temp_text}'
                                        voice_off_sound.play()
                    if text:
                        # backdoor for updating main embedding
                        if config['ai_name'] in text and 'master' in temp_text:
                            print('Update master embedding')
                            item = {
                                "user": 'Master',
                                "embedding": voice_embed
                            }

                            text = f'**{item['user']}:**{temp_text}'
                            
                            master_exists = False
                            for item in user_lists:
                                if item['user'] == 'Master':
                                    item['embedding'] = voice_embed
                                    master_exists = True
                                    break
                            
                            if not master_exists:
                                user_lists.append({'user': 'Master', 'embedding': voice_embed})
                            # sound
                            print('\a')

                        if(recorder.is_recording):
                            recording_sound.play()
                            timestr = time.strftime("%Y%m%d-%H%M%S")
                            file_name = f"{IMAGE_PATH}video-{timestr}.mp4"
                            recorder.stop_recording(file_name)
                            context['upload_file'] = gemini_ai.upload_file(path=file_name,
                                display_name="Video")
                        # Request is from voice, clear some flags
                        context['system_message_in_a_row'] = 0
                        context['upload_in_a_row'] = 0
                        mInputQueue.put(text)
                    else:
                        if(recorder.is_recording):
                            recorder.stop_recording(None)
                except Exception as e:
                    exceptionCounter += 1
                    print(e)
                    if(exceptionCounter > 20):
                        with wdt_feed_lock1:
                            # wait for watchdog to restart
                            while True:
                                pass

        def wdt_feed_thread():
            while True:
                with wdt_feed_lock1:
                    with wdt_feed_lock2:
                        ApplicationWatchdog.Feed()
                time.sleep(CHECK_INTERVAL)

        load_history()
        load_memory()

        threading.Thread(target=input_thread).start()
        threading.Thread(target=voice_thread).start()
        threading.Thread(target=wdt_feed_thread).start()
        
        # Main loop
        start_up_sound.play()
        text_to_speech.speak(f"{config['ai_name']}, online. How can I help you?")
        append2log('==================New=====================')
        check_function_file()

        exceptionCounter = 0
        while True:
            try:
                check_function_file()
                check_history_files()

                # only fetch the latest text msg
                if mInputQueue.qsize() > 0:
                    while(not (mInputQueue.qsize() == 0)):
                        text = mInputQueue.get()
                else:
                    text = mInputQueue.get()
                if text == '':
                    continue

                parts = []
                if context['upload_file']:
                    gemini_ai.wait_file(context['upload_file'])
                    parts.append(context['upload_file'])
                    context['upload_file'] = None
                parts.append(text)
                timestamp = datetime.now().strftime("%H:%M:%S")
                parts.append(f'**System:**{timestamp}')

                talk_header[0]['parts'][2] = context['memory_str']
                temp = talk_header + context['talk']
                temp.append({'role': 'user', 'parts': parts})
                print(f"You: {text}, {timestamp}")

                # Process user's request
                try:
                    response = gemini_ai.generate_response(temp).strip()
                except Exception as e:
                    print(e)
                    with wdt_feed_lock2:
                        text_to_speech.speak("Well, looks like I can't get a response from the server.")
                    continue
                print(f"AI: {response}")
                
                pythoncode = gemini_ai.extract_code(response)
                voice_text = gemini_ai.strip_code(response).strip()
                if voice_text != '':
                    with wdt_feed_lock2:
                        text_to_speech.stop()
                # Update context
                context['talk'].append({'role': 'user', 'parts': parts})
                context['talk'].append({'role': 'model', 'parts': [response]})
                if len(context['talk']) > config['max_history']:
                    context['talk'] = context['talk'][-config['max_history']:]
                # Handle any code execution from the response
                # sometimes the AI generate code with comment only, strip this comment line to avoid trigger code sound effect
                def remove_comment_lines(s):
                    return "\n".join([line for line in s.split('\n') if not line.strip().startswith('#')])
                pythoncode = remove_comment_lines(pythoncode).strip()
                thread = None
                if(pythoncode != ''):
                    print(f'code: {pythoncode}')
                    thread = threading.Thread(target=exec_code, args=(pythoncode,))
                    # Start the thread
                    thread.start()
                else:
                    # no code this round, clear some flags
                    context['system_message_in_a_row'] = 0
                    context['upload_in_a_row'] = 0
                # Speak the response
                if voice_text != '':
                    with wdt_feed_lock2:
                        text_to_speech.speak(voice_text)
                append2log(f"You: {parts}")
                append2log(f"AI: {response}")
                save_history()
                if thread:
                    thread.join()
                
                # conserve energy
                if not context['vision_mode']:
                    cam.stop()

            except Exception as e:
                print(e)
                print('\a')
                exceptionCounter += 1
                if exceptionCounter > 20:
                    with wdt_feed_lock2:
                        #wait for watchdog to restart
                        while True:
                            pass
                continue
    main()