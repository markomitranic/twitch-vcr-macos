#! /bin/bash

echo "Select a username:"
echo "1) vinyljunkies"
echo "2) dj_nitey"
echo "3) djfrantic"
echo "4) vinylphilharmonic"
echo "Choose (1-6):"
read choice

case $choice in
1) username="vinyljunkies" ;;
2) username="dj_nitey" ;;
3) username="djfrantic" ;;
4) username="vinylphilharmonic" ;;
*)
    echo "Invalid choice"
    exit 1
    ;;
esac

echo "Starting recorder for: $username"
caffeinate -i -s /usr/bin/python3 twitch-recorder.py --username "$username"
