import subprocess
import tkinter as tk
import socket
from tkinter import ttk

class VLCApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Control VLC with Tkinter")
        
        # VLC command. Note the use of rc interface for control.
        command = [
            "vlc",
            "--intf", "rc",
            "--rc-host", "localhost:12345",
            "jenni.mp4"
        ]
        self.vlc_process = subprocess.Popen(command)
        
        # Control buttons
        self.play_button = ttk.Button(self, text="Play", command=self.play_video)
        self.play_button.pack()
        self.pause_button = ttk.Button(self, text="Pause", command=self.pause_video)
        self.pause_button.pack()

    def send_vlc_command(self, command):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("localhost", 12345))
            s.sendall(command.encode('utf-8'))

    def play_video(self):
        self.send_vlc_command("play\n")

    def pause_video(self):
        self.send_vlc_command("pause\n")

app = VLCApp()
app.mainloop()
