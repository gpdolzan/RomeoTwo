import os
import cv2
import vlc
import tkinter as tk
from tkinter import filedialog

if os.name == 'nt':
    os.add_dll_directory(r'C:\Program Files\VideoLAN\VLC')

def open_webcam():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Couldn't open the camera.")
        return

    while True:
        ret, frame = cap.read()
        if ret:
            cv2.imshow('Webcam Feed', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("Error: Couldn't read a frame from the camera.")
            break

    cap.release()
    cv2.destroyAllWindows()

def play_video():
    filepath = filedialog.askopenfilename(initialdir=".", title="Select Video File", filetypes=[("Video Files", "*.mp4;*.avi;*.mkv;*.mov;*.flv")])
    if not filepath:
        return

    vlc_instance = vlc.Instance()
    player = vlc_instance.media_player_new()
    media = vlc_instance.media_new(filepath)
    player.set_media(media)
    player.play()

root = tk.Tk()
root.title("Select")

# Define size
root.geometry("200x140")

btn_webcam = tk.Button(root, text="Open Webcam", command=open_webcam)
btn_webcam.pack(pady=20)

btn_video = tk.Button(root, text="Play Video", command=play_video)
btn_video.pack(pady=20)

root.mainloop()
