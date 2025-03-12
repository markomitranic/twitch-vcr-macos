import datetime
import enum
import getopt
import logging
import os
import subprocess
import sys
import shutil
import time
import signal
import requests
import config


class TwitchResponseStatus(enum.Enum):
    ONLINE = 0
    OFFLINE = 1
    NOT_FOUND = 2
    UNAUTHORIZED = 3
    ERROR = 4


class TwitchRecorder:
    def __init__(self):
        # global configuration
        self.ffmpeg_path = "ffmpeg"
        self.disable_ffmpeg = False
        self.refresh = 60
        # Use the current directory where the app is running instead of config
        self.root_path = os.path.dirname(os.path.abspath(__file__))

        # user configuration
        self.username = None  # Will be set via CLI
        self.quality = "best"

        # twitch configuration
        self.client_id = config.client_id
        self.client_secret = config.client_secret
        self.token_url = "https://id.twitch.tv/oauth2/token?client_id=" + self.client_id + "&client_secret=" \
                         + self.client_secret + "&grant_type=client_credentials"
        self.url = "https://api.twitch.tv/helix/streams"
        self.access_token = self.fetch_access_token()
        
        # process tracking
        self.current_process = None
        self.recorded_filename = None
        self.processed_filename = None
        self.audio_filename = None
        self.is_recording = False

    def fetch_access_token(self):
        token_response = requests.post(self.token_url, timeout=15)
        token_response.raise_for_status()
        token = token_response.json()
        return token["access_token"]

    def run(self):
        # path to recorded stream
        recorded_path = os.path.join(self.root_path, "recordings", self.username)
        # path to finished video, errors removed
        processed_path = os.path.join(self.root_path, "processed", self.username)

        # create directory for recordedPath and processedPath if not exist
        if os.path.isdir(recorded_path) is False:
            os.makedirs(recorded_path)
        if os.path.isdir(processed_path) is False:
            os.makedirs(processed_path)

        # make sure the interval to check user availability is not less than 15 seconds
        if self.refresh < 15:
            logging.warning("check interval should not be lower than 15 seconds")
            self.refresh = 15
            logging.info("system set check interval to 15 seconds")

        # fix videos from previous recording session
        try:
            video_list = [f for f in os.listdir(recorded_path) if os.path.isfile(os.path.join(recorded_path, f))]
            if len(video_list) > 0:
                logging.info("processing previously recorded files")
            for f in video_list:
                recorded_filename = os.path.join(recorded_path, f)
                processed_filename = os.path.join(processed_path, f)
                self.process_recorded_file(recorded_filename, processed_filename)
        except Exception as e:
            logging.error(e)

        logging.info("checking for %s every %s seconds, recording with %s quality",
                     self.username, self.refresh, self.quality)
        self.loop_check(recorded_path, processed_path)

    def process_recorded_file(self, recorded_filename, processed_filename):
        if self.disable_ffmpeg:
            logging.info("moving: %s", recorded_filename)
            shutil.move(recorded_filename, processed_filename)
        else:
            logging.info("fixing %s", recorded_filename)
            self.ffmpeg_copy_and_fix_errors(recorded_filename, processed_filename)
            
        # Extract MP3 after processing the video
        if os.path.exists(processed_filename):
            self.audio_filename = self.extract_mp3(processed_filename)

    def ffmpeg_copy_and_fix_errors(self, recorded_filename, processed_filename):
        try:
            subprocess.call(
                [self.ffmpeg_path, "-err_detect", "ignore_err", "-i", recorded_filename, "-c", "copy",
                 processed_filename])
            os.remove(recorded_filename)
        except Exception as e:
            logging.error(e)

    def reveal_in_finder(self, file_path):
        """Open the containing folder in Finder and select the file"""
        try:
            if os.path.exists(file_path):
                logging.info(f"Opening file location in Finder: {file_path}")
                subprocess.call(["open", "-R", file_path])
            else:
                logging.warning(f"Cannot reveal file in Finder: File does not exist at {file_path}")
        except Exception as e:
            logging.error(f"Error opening Finder: {e}")

    def check_user(self):
        info = None
        status = TwitchResponseStatus.ERROR
        try:
            headers = {"Client-ID": self.client_id, "Authorization": "Bearer " + self.access_token}
            r = requests.get(self.url + "?user_login=" + self.username, headers=headers, timeout=15)
            r.raise_for_status()
            info = r.json()
            if info is None or not info["data"]:
                status = TwitchResponseStatus.OFFLINE
            else:
                status = TwitchResponseStatus.ONLINE
        except requests.exceptions.RequestException as e:
            if e.response:
                if e.response.status_code == 401:
                    status = TwitchResponseStatus.UNAUTHORIZED
                if e.response.status_code == 404:
                    status = TwitchResponseStatus.NOT_FOUND
        return status, info

    def graceful_shutdown(self):
        """Handle shutdown gracefully by processing any current recording"""
        if self.is_recording and self.current_process:
            logging.info("Graceful shutdown initiated. Terminating recording...")
            # Terminate the streamlink process
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=5)
            except Exception as e:
                logging.error(f"Error terminating process: {e}")
            
            # Process the recording if it exists
            if self.recorded_filename and self.processed_filename and os.path.exists(self.recorded_filename):
                logging.info("Processing recording before exit...")
                self.process_recorded_file(self.recorded_filename, self.processed_filename)
                # Reveal the processed file in Finder after processing
                if os.path.exists(self.processed_filename):
                    self.reveal_in_finder(self.processed_filename)
            
            logging.info("Graceful shutdown complete")
        else:
            logging.info("No active recording to process. Shutting down...")

    def loop_check(self, recorded_path, processed_path):
        while True:
            try:
                status, info = self.check_user()
                if status == TwitchResponseStatus.NOT_FOUND:
                    logging.error("username not found, invalid username or typo")
                    time.sleep(self.refresh)
                elif status == TwitchResponseStatus.ERROR:
                    logging.error("%s unexpected error. will try again in 5 minutes",
                                  datetime.datetime.now().strftime("%Hh%Mm%Ss"))
                    time.sleep(300)
                elif status == TwitchResponseStatus.OFFLINE:
                    logging.info("%s currently offline, checking again in %s seconds", self.username, self.refresh)
                    time.sleep(self.refresh)
                elif status == TwitchResponseStatus.UNAUTHORIZED:
                    logging.info("unauthorized, will attempt to log back in immediately")
                    self.access_token = self.fetch_access_token()
                elif status == TwitchResponseStatus.ONLINE:
                    logging.info("%s online, stream recording in session", self.username)

                    channels = info["data"]
                    channel = next(iter(channels), None)
                    now = datetime.datetime.now()
                    filename = now.strftime("%Y-%m-%d - %A - ") + channel.get("title") + ".mp4"

                    # clean filename from unnecessary characters
                    filename = "".join(x for x in filename if x.isalnum() or x in [" ", "-", "_", "."])

                    self.recorded_filename = os.path.join(recorded_path, filename)
                    self.processed_filename = os.path.join(processed_path, filename)

                    # start streamlink process
                    self.is_recording = True
                    self.current_process = subprocess.Popen(
                        ["streamlink", "--twitch-disable-ads", "twitch.tv/" + self.username, self.quality,
                         "-o", self.recorded_filename])
                    
                    self.current_process.wait()
                    self.is_recording = False

                    logging.info("recording stream is done, processing video file")
                    if os.path.exists(self.recorded_filename) is True:
                        self.process_recorded_file(self.recorded_filename, self.processed_filename)
                        # Reveal the processed file in Finder after processing
                        if os.path.exists(self.processed_filename):
                            self.reveal_in_finder(self.processed_filename)
                    else:
                        logging.info("skip fixing, file not found")

                    # Reset tracking variables
                    self.current_process = None
                    self.recorded_filename = None
                    self.processed_filename = None
                    self.audio_filename = None

                    logging.info("processing is done, going back to checking...")
                    time.sleep(self.refresh)
            except KeyboardInterrupt:
                logging.info("KeyboardInterrupt received, shutting down gracefully...")
                self.graceful_shutdown()
                sys.exit(0)

    def extract_mp3(self, video_path):
        """Extract MP3 audio from the processed video file"""
        if self.disable_ffmpeg:
            logging.info("ffmpeg disabled, skipping MP3 extraction")
            return None
            
        try:
            # Generate audio filename in the same directory as the video
            audio_filename = os.path.splitext(video_path)[0] + ".mp3"
            
            logging.info("Extracting MP3 from video: %s", video_path)
            subprocess.call([
                self.ffmpeg_path,
                "-i", video_path,
                "-q:a", "0",
                "-map", "a",
                audio_filename
            ])
            
            if os.path.exists(audio_filename):
                logging.info("MP3 extraction complete: %s", audio_filename)
                return audio_filename
            return None
        except Exception as e:
            logging.error("Error extracting MP3: %s", e)
            return None


def signal_handler(sig, frame):
    logging.info(f"Signal {sig} received, initiating graceful shutdown")
    if recorder:
        recorder.graceful_shutdown()
    sys.exit(0)


def main(argv):
    global recorder
    recorder = TwitchRecorder()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    usage_message = "twitch-recorder.py -u <username> -q <quality>"
    logging.basicConfig(filename="twitch-recorder.log", level=logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler())

    try:
        opts, args = getopt.getopt(argv, "hu:q:l:", ["username=", "quality=", "log=", "logging=", "disable-ffmpeg"])
    except getopt.GetoptError:
        print(usage_message)
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print(usage_message)
            sys.exit()
        elif opt in ("-u", "--username"):
            recorder.username = arg
        elif opt in ("-q", "--quality"):
            recorder.quality = arg
        elif opt in ("-l", "--log", "--logging"):
            logging_level = getattr(logging, arg.upper(), None)
            if not isinstance(logging_level, int):
                raise ValueError("invalid log level: %s" % logging_level)
            logging.basicConfig(level=logging_level)
            logging.info("logging configured to %s", arg.upper())
        elif opt == "--disable-ffmpeg":
            recorder.disable_ffmpeg = True
            logging.info("ffmpeg disabled")

    # Validate that username was provided
    if not recorder.username:
        print("Error: Username is required. Use -u or --username to specify the Twitch username.")
        print(usage_message)
        sys.exit(1)

    recorder.run()


if __name__ == "__main__":
    recorder = None
    main(sys.argv[1:])
