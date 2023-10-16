import tkinter as tk
import customtkinter as ctk

def show_content_1():
    # Clear the frame
    for widget in content_frame.winfo_children():
        widget.destroy()

    # Set the window size for Content 1
    root.geometry("300x200")
    
    ctk.CTkLabel(content_frame, text="This is Content 1").pack()
    ctk.CTkButton(content_frame, text="Switch to Content 2", command=show_content_2).pack()

def show_content_2():
    # Clear the frame
    for widget in content_frame.winfo_children():
        widget.destroy()

    # Set the window size for Content 2
    root.geometry("500x300")
    
    ctk.CTkLabel(content_frame, text="This is Content 2").pack()
    ctk.CTkButton(content_frame, text="Switch to Content 1", command=show_content_1).pack()

root = tk.Tk()
root.geometry("300x200")

# This frame will contain the content
content_frame = tk.Frame(root)
content_frame.pack(pady=20)

show_content_1()

root.mainloop()
