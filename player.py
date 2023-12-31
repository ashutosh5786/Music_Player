import os
import sys
import pygame
from tkinter import Tk, Label, Button, Listbox, filedialog, PhotoImage, ttk, Entry, Scale, StringVar, messagebox
from ttkthemes import ThemedTk
import requests
from io import BytesIO
from PIL import Image, ImageTk
import eyed3
import datetime
import threading
from random import shuffle
from urllib.parse import urlparse
import tempfile

# Create the music player


class MusicPlayer:
    def __init__(self, master):
        self.master = master
        master.title("Music Player")
        master.geometry("800x600")
        master.option_add("*Font", "SegoeUI 16")

        self.song_paused = False
        self.user_set_time = None
        self.offset_time = 0

        self.search_box = Entry(master, width=20)
        self.search_box.grid(row=1, column=1, padx=5, pady=5)
        self.search_box.bind("<KeyRelease>", self.search_song)

        # Add placeholder text to search box
        self.placeholder = "Search Song"
        self.search_box.insert(0, self.placeholder)

        # Set the default theme
        self.style = ttk.Style()
        self.style.theme_use('ubuntu')

        # Load the default album art
        img = Image.open(self.resource_path("default_album_art.png"))
        img = img.resize((100, 100))
        self.album_art = ImageTk.PhotoImage(img)

        self.album_art_label = ttk.Label(master, image=self.album_art)
        self.album_art_label.grid(row=2, column=0, padx=0, pady=0)

        self.song_name_label = Label(master, wraplength=250, justify="center")
        self.song_name_label.grid(row=3, column=0, padx=10, pady=10)
        self.song_name_label.grid_remove()  # Hide the song name label by default

        # Library Configuration
        self.song_library = []
        self.original_song_library = []
        self.song_details = []
        self.current_album_art = None
        self.playlist_listbox = None
        self.current_song_index = 0
        self.playing = False
        self.repeat = False

        # Playlist Configuration
        self.playlist_listbox = Listbox(master, selectmode="MULTIPLE")
        self.playlist_listbox.grid(row=2, column=1, padx=10, pady=10)
        self.playlist_listbox.bind(
            '<<ListboxSelect>>', self.play_selected_song)

        self.label = Label(master, text="Music Player", font=("Segoe UI", 16))
        self.label.grid(row=1, column=0, padx=10, pady=10)

        self.or_label = Label(master, text="or Stream it",
                              font=("Segoe UI", 12))
        self.or_label.grid(row=4, column=1, padx=10, pady=10)
        # Create the Entry widget
        self.url_entry = ttk.Entry(master, width=20)
        # Place the Entry widget
        self.url_entry.grid(row=5, column=1, padx=5, pady=5)
        # Bind the Return key to the Entry widget
        self.url_entry.bind("<Return>", self.add_url_library)

        # Add the songs to the library
        self.add_button = Button(
            master, text="Select Folder", command=self.add_to_library)
        self.add_button.grid(row=3, column=1, pady=10)

        # Create the buttons
        button_frame = ttk.Frame(master)
        button_frame.grid(row=7, column=0, padx=(50, 0))

        self.muted = False
        self.volume = 100
        self.volume_scale = Scale(
            button_frame, from_=0, to=100, orient="horizontal", command=self.set_volume, showvalue=False)
        self.volume_scale.set(self.volume)
        self.volume_scale.grid(row=0, column=7)
        self.volume_var = StringVar(value='')
        self.volume_label = Label(button_frame, textvariable=self.volume_var)
        self.volume_label.grid(row=0, column=8)
        self.volume_label.grid_remove()     # Hide the volume label by default

        # Resize factor for the icons
        resize_factor = 0.5
        # Load the icons

        self.shuffle_icon = PhotoImage(file=self.resource_path("shuffle.png"))
        self.shuffle_icon = self.shuffle_icon.subsample(
            int(resize_factor * 100))
        self.shuffle_button = ttk.Button(
            button_frame, image=self.shuffle_icon, command=self.shuffle_songs)
        self.shuffle_button.grid(row=0, column=0, padx=5)

        self.repeat_icon = PhotoImage(file=self.resource_path("repeat.png"))
        self.repeat_icon = self.repeat_icon.subsample(int(resize_factor * 60))
        self.repeat_once_icon = PhotoImage(
            file=self.resource_path("repeat_once.png"))
        self.repeat_once_icon = self.repeat_once_icon.subsample(
            int(resize_factor * 60))
        self.repeat_button = ttk.Button(
            button_frame, image=self.repeat_icon, command=self.toggle_repeat)
        self.repeat_button.grid(row=0, column=5, padx=5)

        self.play_icon = PhotoImage(file=self.resource_path("play.png"))
        self.play_icon = self.play_icon.subsample(int(resize_factor * 100))
        self.play_button = ttk.Button(
            button_frame, image=self.play_icon, command=self.play)
        self.play_button.grid(row=0, column=3, padx=5)

        self.pause_icon = PhotoImage(file=self.resource_path("pause.png"))
        self.pause_icon = self.pause_icon.subsample(int(resize_factor * 100))
        self.pause_button = ttk.Button(
            button_frame, image=self.pause_icon, command=self.pause)
        self.pause_button.grid(row=0, column=2, padx=5)
        self.pause_button.grid_remove()  # Hide the pause button by default

        self.forward_icon = PhotoImage(file=self.resource_path("forward.png"))
        self.forward_icon = self.forward_icon.subsample(
            int(resize_factor * 100))
        self.forward_button = ttk.Button(
            button_frame, image=self.forward_icon, command=self.forward)
        self.forward_button.grid(row=0, column=4, padx=5)

        self.backward_icon = PhotoImage(
            file=self.resource_path("backward.png"))
        self.backward_icon = self.backward_icon.subsample(
            int(resize_factor * 100))
        self.backward_button = ttk.Button(
            button_frame, image=self.backward_icon, command=self.backward)
        self.backward_button.grid(row=0, column=1, padx=5)

        button_frame2 = ttk.Frame(master)
        button_frame2.grid(row=4, column=0)

        self.total_time_label = Label(button_frame2)
        # This needs to be fixed and needs to be visible at the end of the progress bar
        self.total_time_label.grid(row=0, column=2)

        self.current_time_label = Label(button_frame2)
        self.current_time_label.grid(row=0, column=0, padx=(10, 0))

        self.mute_icon = PhotoImage(file=self.resource_path("mute.png"))
        self.mute_icon = self.mute_icon.subsample(int(resize_factor * 60))
        self.unmute_icon = PhotoImage(file=self.resource_path("unmute.png"))
        self.unmute_icon = self.unmute_icon.subsample(int(resize_factor * 60))
        self.mute_button = Button(
            button_frame, image=self.unmute_icon, command=self.toggle_mute)
        self.mute_button.grid(row=0, column=6, padx=5)

        # Create the progress bar
        self.progress_bar = ttk.Progressbar(
            button_frame2, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.grid(row=0, column=1, padx=10)
        self.progress_bar.bind("<Button-1>", self.set_progress_start)
        # self.progress_bar.bind("<B1-Motion>", self.set_progress_update)
        self.update_progress_bar()

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    @staticmethod
    def resource_path(relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(
            os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)

    # Volume slider working upon

    def set_volume(self, volume):
        pygame.mixer.init()
        self.volume = int(volume)
        pygame.mixer.music.set_volume(self.volume / 100)
        self.volume_var.set(f"{self.volume}%")
        self.volume_label.grid()  # Show the volume label
        if self.volume == 0:
            self.mute_button.configure(image=self.mute_icon)
            self.muted = True
        else:
            self.mute_button.configure(image=self.unmute_icon)
            self.muted = False
        # Hide the volume label after 2 seconds
        self.volume_label.after(2000, self.volume_label.grid_remove)

    def toggle_mute(self):
        if self.muted:
            pygame.mixer.music.set_volume(self.volume / 100)
            self.mute_button.configure(image=self.unmute_icon)
            self.muted = False
        else:
            pygame.mixer.music.set_volume(0)
            self.mute_button.configure(image=self.mute_icon)
            self.muted = True

    def toggle_repeat(self):
        if self.repeat:
            self.repeat = False
            self.repeat_button.configure(image=self.repeat_icon)
        else:
            self.repeat = True
            self.repeat_button.configure(image=self.repeat_once_icon)

    # Search the song
    def search_song(self, event):
        search_term = self.search_box.get()
        if search_term:
            matching_songs = [song for song in self.original_song_library if search_term.lower(
            ) in os.path.basename(song).lower()]
            if not matching_songs:
                # print(f"No songs found for search term '{search_term}'")
                messagebox.showinfo(
                    "No songs found", f"No songs found with the name '{search_term}'")
            else:
                self.song_library = matching_songs
        else:
            self.song_library = self.original_song_library.copy()
        self.playlist_listbox.delete(0, "end")
        for song in self.song_library:
            self.playlist_listbox.insert("end", os.path.basename(song))
        self.current_song_index = 0

# The Search is working here but after the search box is cleared the songs are not coming back to the original list

    # Change theme

    def change_theme(self, event):
        selected_theme = self.theme_var.get()
        self.master.set_theme(selected_theme)

    # Add Songs from the URL
    def add_url_library(self, event=None):
        try:
            url = self.url_entry.get()
            if url:
                response = requests.get(url)
                if response.status_code == 200:
                    file_path = urlparse(url).path
                    basename = os.path.basename(file_path)

                    temp_dir = tempfile.gettempdir()
                    temp_file_path = os.path.join(temp_dir, basename)

                    # .NamedTemporaryFile(delete=False, suffix=basename) as temp_file:
                    with open(temp_file_path, 'wb') as temp_file:

                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                temp_file.write(chunk)
                        temp_file.close()
                    # Append the path of the temporary file to the song library
                    self.song_library.append(temp_file_path)
                    self.url_entry.delete(0, "end")

                    self.playlist_listbox.insert(
                        "end", basename)
                    self.search_box.grid_remove()
        except Exception as e:
            messagebox.showerror("Invalid URL", "Please enter a valid URL")
            print(e)

    # Add songs to the library

    def add_to_library(self):
        try:
            # from local directory
            Tk().withdraw()
            self.search_box.grid()  # Show the search box
            directory_path = filedialog.askdirectory(
                title="Select Music Folder")
            if directory_path == "":
                raise ValueError("No folder selected")
            for file_name in os.listdir(directory_path):
                if file_name.endswith('.mp3') or file_name.endswith('.wav'):
                    file_path = os.path.join(directory_path, file_name)

                    # created to sort the songs by date added
                    date_added = datetime.datetime.fromtimestamp(
                        os.path.getctime(file_path))
                    self.song_details.append((file_path, date_added))

            # Sorting the songs by date added
            self.song_details.sort(key=lambda x: x[1], reverse=True)

            # Removing the date added from the list and populating the song_library list
            self.song_library = [song[0] for song in self.song_details]
            # Store the original song library for search box
            self.original_song_library = self.song_library.copy()
            for song in self.song_library:
                self.playlist_listbox.insert("end", os.path.basename(song))
        except ValueError as e:
            messagebox.showerror("No folder selected",
                                 "Please select a folder to add songs")

    # Get the album art from the song
    # Need to call this function before playing the songs with current index of that song

    def get_album_art(self, file_path):
        audio_file = eyed3.load(file_path)
        if audio_file.tag:
            if audio_file.tag.images:
                image_data = audio_file.tag.images[0].image_data
                img = Image.open(BytesIO(image_data))
                img = img.resize((350, 250))
                self.album_art = ImageTk.PhotoImage(img)
                self.album_art_label.configure(image=self.album_art)
            else:
                img = Image.open("default_album_art.png")
                img = img.resize((100, 100))
                self.album_art = ImageTk.PhotoImage(img)
                self.album_art_label.configure(image=self.album_art)
        else:
            img = Image.open("default_album_art.png")
            img = img.resize((100, 100))
            self.album_art = ImageTk.PhotoImage(img)
            self.album_art_label.configure(image=self.album_art)

    # Playing Selected Song from the List
    def play_selected_song(self, event):
        try:
            self.current_song_index = self.playlist_listbox.curselection()[0]
            song_data = self.song_library[self.current_song_index]
            self.offset_time = 0
            self.play(song_data)
            self.get_album_art(song_data)
        except IndexError:
            messagebox.showerror("No song selected",
                                 "Please select a song to play")


# Stop the music

    def stop(self):
        pygame.mixer.music.stop()
        self.playing = False
        self.progress_bar.stop()
        self.song_name_label.grid_remove()  # Hide the song name label

    # Play the music

    def play(self, song_data=None):  # The play function is playing from the start of the list and we cant play from the list due to this as the play function is not taking any index value from where tho play from the list I think we need to add the index value or pass it in function
        try:
            if self.song_paused:
                pygame.mixer.music.unpause()
                self.song_paused = False
                # self.update_progress_bar()
                self.play_button.grid_remove()  # Hide the play button when playing the song
                self.pause_button.grid()  # Show the pause button when playing the song
                self.playing = True
                self.update_progress_bar()

            else:
                self.stop()
                song_data = self.song_library[self.current_song_index]
                pygame.mixer.music.load(song_data)
                song_name = os.path.basename(song_data)
                self.song_name_label.configure(text=song_name)
                self.song_name_label.grid()
                song = pygame.mixer.Sound(song_data)
                length = song.get_length()
                minutes = int(length // 60)
                seconds = int(length % 60)
                self.total_time_label.configure(text=f"{minutes}:{seconds:02}")
                pygame.mixer.music.play()
                self.play_button.grid_remove()  # Hide the play button when playing the song
                self.pause_button.grid()  # Show the pause button when playing the song
                self.playing = True
                self.update_progress_bar()
                pygame.mixer.music.set_endevent(pygame.USEREVENT)
                threading.Thread(target=self.wait_for_song_end,
                                 args=(song_data,)).start()
        except IndexError:
            messagebox.showerror("No song selected",
                                 "Please select a song to play")

    def wait_for_song_end(self, song_data):
        self.offset_time = 0
        while pygame.event.wait().type != pygame.USEREVENT:
            pass
        if self.repeat:
            self.play(song_data)

# Pause the music
    def pause(self):
        if self.playing:
            pygame.mixer.music.pause()
            self.playing = False
            self.song_paused = True
            self.play_button.grid()  # Show the play button
            self.pause_button.grid_remove()

    # Go to the next song
    def forward(self):
        try:
            self.stop()
            self.offset_time = 0
            if self.current_song_index < len(self.song_library) - 1:
                self.current_song_index += 1
                song_data = self.song_library[self.current_song_index]
                self.play(song_data)
                self.get_album_art(song_data)
            else:
                raise ValueError("No Song in Playlist")
        except ValueError:
            messagebox.showerror("No song selected", "No Song in Playlist")
    # Go back to the previous song

    def backward(self):
        try:
            self.stop()
            self.offset_time = 0
            if self.current_song_index > 0:
                self.current_song_index -= 1
                song_data = self.song_library[self.current_song_index]
                self.play(song_data)
                self.get_album_art(song_data)
            else:
                raise ValueError("No Song in Playlist")
        except ValueError:
            messagebox.showerror("No song selected", "No Song in Playlist")

    # Update the progress bar as the song plays
    def update_progress_bar(self):
        if 0 <= self.current_song_index < len(self.song_library):
            total_time = pygame.mixer.Sound(
                self.song_library[self.current_song_index]).get_length() * 1000
            self.progress_bar["maximum"] = total_time

            def update():
                if self.playing:
                    if self.user_set_time is not None:
                        current_time = self.user_set_time
                        self.user_set_time = None  # Reset the user_set_time
                    else:
                        current_time = (pygame.mixer.music.get_pos(
                        ) + self.offset_time)  # + self.offset_time
                    current_time_for_label = current_time / 1000
                    minutes = int(current_time_for_label // 60)
                    seconds = int(current_time_for_label % 60)
                    self.current_time_label.configure(
                        text=f"{minutes}:{seconds:02}")
                    self.progress_bar["value"] = current_time
                    threading.Timer(0.1, update).start()

            update()

    # Set the progress bar to the clicked position
    def set_progress_start(self, event):
        if self.playing:
            clicked_x = event.x
            total_width = self.progress_bar.winfo_width()
            total_time = pygame.mixer.Sound(
                self.song_library[self.current_song_index]).get_length() * 1000
            new_time = (clicked_x / total_width) * \
                total_time  # Set new position in seconds
            # Dividing by 1000 to convert it into seconds
            pygame.mixer.music.set_pos(new_time / 1000)
            self.user_set_time = new_time  # Dividing by 1000 to convert it into seconds
            self.offset_time = new_time
            self.progress_bar["value"] = self.user_set_time
            print("this is new time: " + str(new_time / 1000))

    def shuffle_songs(self):
        shuffle(self.song_library)
        self.playlist_listbox.delete(0, "end")
        for song in self.song_library:
            self.playlist_listbox.insert("end", os.path.basename(song))
        self.current_song_index = 0

    def on_closing(self):
        self.stop()
        self.master.destroy()
        os._exit(0)


# Run the program
if __name__ == "__main__":
    pygame.init()
    root = ThemedTk()
    player = MusicPlayer(root)
    root.mainloop()
    pygame.quit()
