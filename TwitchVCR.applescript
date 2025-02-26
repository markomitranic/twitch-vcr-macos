tell application "Terminal"
    set current_path to POSIX path of (path to me as text)
    set dir_path to do shell script "dirname " & quoted form of current_path
    do script "cd " & quoted form of dir_path & "; ./start.sh"
    activate
end tell
