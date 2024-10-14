#!/usr/bin/python

import os
import random
import threading
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import asyncio
import tkinter as tk
from PIL import Image, ImageTk, ImageOps
from PIL import ImageDraw, ImageFont
from moviepy.editor import VideoFileClip
from time import sleep
import time
from datetime import datetime, timedelta, timezone
import subprocess

# Get the directory name of the current script
dirname = os.path.dirname(os.path.abspath(__file__))

# Replace with your own Telegram bot token
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
GIF_FOLDER = f"{dirname}/dl/"


# Create the folder to store the GIFs if it doesn't exist
if not os.path.exists(GIF_FOLDER):
    os.makedirs(GIF_FOLDER)

# Initialize the list of GIFs and frame handling variables
gifs = []
gif_frames = []
gif_frame_index = 0
default_delay = 100
delay = default_delay
window = None
label = None

# Function to download the GIF
async def download_gif(file_id, bot):
    file = await bot.get_file(file_id)
    file_path = os.path.join(GIF_FOLDER, f"{file_id}.gif")
    await file.download_to_drive(file_path)
    return file_path

# Function to update the displayed GIF frames
def update_gif_frame():
    global gif_frame_index, delay

    try:
        if gifs:
            gif_frame_index = (gif_frame_index + 1) % len(gif_frames)
            gif_tk = gif_frames[gif_frame_index]
            label.config(image=gif_tk)
            label.image = gif_tk  # Keep a reference to prevent garbage collection
    except:
        # In a middle of an update?
        sleep(1)

    window.after(delay, update_gif_frame)

# Function to load the current GIF's frames and start animation
def load_and_display_gif(gif_path):
    global gif_frames, gif_frame_index, delay

    gif_image = Image.open(gif_path)

    # Load all frames of the GIF
    gif_frames = []
    try:
        while True:
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            frame = ImageOps.fit(gif_image.copy(), (screen_width, screen_height), method=Image.Resampling.LANCZOS)
            gif_frames.append(ImageTk.PhotoImage(frame))
            gif_image.seek(len(gif_frames))
    except EOFError:
        pass  # End of GIF frames

    gif_frame_index = 0
    delay = gif_image.info.get('duration', default_delay)
    print(f"Delay: {delay}")

# Function to convert MP4 to GIF
def convert_mp4_to_gif(mp4_path, gif_path):
    # Assuming ImageMagick is installed and available in your PATH
    # subprocess.run(["convert", "output.gif", "-delay", "10", "output_with_delay.gif"])

    clip = VideoFileClip(mp4_path)

    print(f"Converting {mp4_path} to {gif_path}. FPS: {clip.fps}")

    clip.write_gif(gif_path, fps = clip.fps)

# Create a semi-transparent rounded background for the clock
def create_clock_image(time_text, size=(150, 50), radius=20, color=(128, 128, 128), transparency=160):
    width, height = size
    image = Image.new("RGBA", size, (0, 0, 0, 0))  # Fully transparent background
    draw = ImageDraw.Draw(image)

    # Draw the rounded rectangle
    draw.rounded_rectangle((0, 0, width, height), radius, fill=(color[0], color[1], color[2], transparency))

    # Draw the time text
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)  # Use the correct path for your system
    except IOError:
        font = ImageFont.load_default()  # Fallback to a default font if the .ttf font isn't found

    text_bbox = font.getbbox(time_text)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    text_position = ((width - text_width) / 2, (height - text_height) / 2 - 5)
    draw.text(text_position, time_text, font=font, fill="white")

    return image

# Update the time display
def update_time():
    current_time = datetime.now(timezone(timedelta(hours=3))).strftime("%H:%M")

    # Create an updated clock image with the current time
    clock_image = create_clock_image(current_time, radius = 0)
    clock_bg = ImageTk.PhotoImage(clock_image)

    # Update the label with the new clock image
    time_label.config(image=clock_bg)
    time_label.image = clock_bg  # Keep a reference to prevent garbage collection

    window.after(1000, update_time)  # Update every second


# Telegram bot handlers
async def start(update, context):
    await update.message.reply_text("Send me GIFs, and I'll display them!")


async def handle_gif(update, context):
    bot = context.bot
    print("Got gif:", update.message.video, update.message.document, update.message.photo)

    # Check if the GIF was sent as a document
    if update.message.document and (update.message.document.mime_type == 'image/gif' or update.message.document.mime_type == 'video/mp4'):
        print("It's a GIF!")
        gif_file = update.message.document
        await update.message.reply_text("Downloading and displaying your GIF...")
        gif_path = await download_gif(gif_file.file_id, bot)

        if update.message.document.mime_type == 'video/mp4':
            convert_mp4_to_gif(gif_path, gif_path + ".converted.gif")

            # Remove original file
            os.unlink(gif_path)

            # Use new path
            gif_path += ".converted.gif"

        gifs.append(gif_path)  # Add to the list of GIFs
        load_and_display_gif(gif_path)  # Display it immediately
    else:
        await update.message.reply_text("Please send me a valid GIF file.")

def run_telegram_bot():
    # Set up Telegram bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command and message handlers
    application.add_handler(CommandHandler("start", start))
    # application.add_handler(MessageHandler(filters.Document.MimeType("image/gif") | filters.VIDEO, handle_gif))
    application.add_handler(MessageHandler(filters.ALL, handle_gif))

    # Start polling and keep the bot running
    application.run_polling()

def pick_random(folder_path):
        # Get a list of all files in the given folder
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    # If the folder contains no files, return None
    if not files:
        return None

    # Choose a random file from the list
    random_file = random.choice(files)

    return os.path.join(folder_path, random_file)

def pick_first_image():
    sleep(2)

    chosen = pick_random(f"{dirname}/dl/")

    if chosen is not None:
        print(f"Chose {chosen}")
        gifs.append(chosen)
        load_and_display_gif(chosen)

        # Start the loop
        update_gif_frame()

def run_tkinter():
    global window, label
    global time_label

    # Set display info
    os.environ["DISPLAY"] = ":0"

    # Disable screen blanking on Linux
    os.system("xset s off")          # Disable screen saver
    os.system("xset -dpms")          # Disable DPMS (Energy Star) features
    os.system("xset s noblank")      # Disable blanking

    # Set up the tkinter window
    window = tk.Tk()
    window.title("GIF Display Bot")
    window.attributes('-fullscreen', True)
    window.configure(bg='black')
    window.bind("<Button-1>", lambda event: window.destroy())

    label = tk.Label(window, bg='black')
    label.pack(expand=True)

    first_image = threading.Thread(target = pick_first_image)
    first_image.start()

    # Set up the time label (initial image is blank)
    blank_image = Image.new("RGBA", (150, 50), (0, 0, 0, 0))
    blank_photo = ImageTk.PhotoImage(blank_image)
    time_label = tk.Label(window, image=blank_photo, bg='black')
    time_label.place(x=window.winfo_screenwidth() - 170, y=20)

    # Start the time update loop
    update_time()

    # Start the Tkinter main loop
    window.mainloop()

def main():
    # Run the Tkinter GUI in a separate thread
    tkinter_thread = threading.Thread(target=run_tkinter)
    tkinter_thread.start()

    # Run the Telegram bot in the main thread
    run_telegram_bot()

    # Wait for the Tkinter thread to finish
    tkinter_thread.join()


import socket
import time

def check_internet_connectivity(timeout=5, retry_interval=2):
    while True:
        try:
            # Try to connect to a reliable public host (Google DNS)
            socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            print("Connected to the internet!")
            return True
        except OSError:
            print("No internet connection, retrying...")
            time.sleep(retry_interval)  # Wait for a while before retrying

if __name__ == '__main__':
    # Make sure there's internet, so the telegram bot won't complain
    check_internet_connectivity()

    # Now start everything.
    main()
