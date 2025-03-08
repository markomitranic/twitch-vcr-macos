# Ancalentari Twitch Stream Recorder
This script allows you to record twitch streams live to .mp4 files.  
It is an improved version of [junian's twitch-recorder](https://gist.github.com/junian/b41dd8e544bf0e3980c971b0d015f5f6), migrated to [**helix**](https://dev.twitch.tv/docs/api) - the new twitch API. It uses OAuth2.

## Usage

```ts
caffeinate -i -s /usr/bin/python3 twitch-recorder.py
```

OR

```ts
./start.sh
```

## Requirements
1. [python3.8](https://www.python.org/downloads/release/python-380/) or higher  
2. [streamlink](https://streamlink.github.io/)  
3. [ffmpeg](https://ffmpeg.org/)

## Setting up
1) Check if you have latest version of streamlink:
    * `streamlink --version` shows current version
    * `streamlink --version-check` shows available upgrade
    * `sudo pip install --upgrade streamlink` do upgrade

2) Install `requests` module [if you don't have it](https://pypi.org/project/requests/)  
   * Windows:    ```python -m pip install requests```  
   * Linux:      ```python3.8 -m pip install requests```
3) Create `config.py` file: `cp config.py.example config.py`
   `root_path` - path to a folder where you want your VODs to be saved to  
   `username` - name of the streamer you want to record by default  
   `client_id` - you can grab this from [here](https://dev.twitch.tv/console/apps) once you register your application  
   `client_secret` - you generate this [here](https://dev.twitch.tv/console/apps) as well, for your registered application

## Running script
The script will be logging to a console and to a file `twitch-recorder.log`

### On linux
Run the script
```shell script
python3.8 twitch-recorder.py
```
To record a specific streamer use `-u` or `--username`
```shell script
python3.8 twitch-recorder.py --username forsen
```
To specify quality use `-q` or `--quality`
```shell script
python3.8 twitch-recorder.py --quality 720p
```
To change default logging use `-l`, `--log` or `--logging`
```shell script
python3.8 twitch-recorder.py --log warn
```
To disable ffmpeg processing (fixing errors in recorded file) use `--disable-ffmpeg`
```shell script
python3.8 twitch-recorder.py --disable-ffmpeg
```
If you want to run the script as a job in the background and be able to close the terminal:
```shell script
nohup python3.8 twitch-recorder.py >/dev/null 2>&1 &
```
In order to kill the job, you first list them all:
```shell script
jobs
```
The output should show something like this:
```shell script
[1]+  Running                 nohup python3.8 twitch-recorder > /dev/null 2>&1 &
```
And now you can just kill the job:
```shell script
kill %1
```
### On Windows
You can run the scipt from `cmd` or [terminal](https://www.microsoft.com/en-us/p/windows-terminal/9n0dx20hk701?activetab=pivot:overviewtab), by simply going to the directory where the script is located at and using command:
```shell script
python twitch-recorder.py
```
The optional parameters should work exactly the same as on Linux.

## macOS Integration

### Using the TwitchRecorder.app
On macOS, you can use the TwitchRecorder.app to launch the script like a native macOS application. This allows you to:
1. Launch the recorder by double-clicking the app icon
2. See the app in your Dock while it's running
3. Easily stop the recorder by closing the app's dialog window

### Recompiling the TwitchRecorder.app
If you make changes to the AppleScript or need to recreate the app, follow these steps:

1. Edit the `TwitchRecorder.applescript` file if needed
2. Open Terminal and navigate to the directory containing the files:
   ```
   cd /path/to/your/twitch/recorder/directory
   ```
3. Compile the AppleScript into an application:
   ```
   osacompile -o TwitchRecorder.app TwitchRecorder.applescript
   ```
4. If you want to use a custom icon, copy it to the app bundle:
   ```
   cp your-icon-file.icns TwitchRecorder.app/Contents/Resources/applet.icns
   ```
5. To make the app work with Gatekeeper on newer macOS versions, you may need to codesign it (optional):
   ```
   codesign --force --deep --sign - TwitchRecorder.app
   ```

The compiled app can be moved to your Applications folder or kept in the same directory as the script.

P.S. You can convert it into mp3 with:
```bash
ffmpeg -i "/Users/markomitranic/Sites/twitch-vcr-macos/processed/vinyljunkies/vinyljunkies - 2025-03-03 21h12m13s - METAL MÖNDAY HEAVY VINYL SPINS ALL DAY   11k LPS   Music Talk  socialradio  BROADCAST 1667.mp4" -q:a 0 -map a "output.mp3"

# Crop the mp3
ffmpeg -i "output.mp3" -ss 02:13:00 -acodec copy "output_trimmed.mp3"
```

