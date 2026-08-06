import os
import re
import io
import shutil
import urllib.request
import threading
from datetime import datetime
from PIL import Image

import customtkinter as ctk
from tkinter import filedialog, messagebox

from styles import *
from youtube_downloader import download_youtube_media
from instagram_downloader import download_instagram_carousel

class Velocity(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Velocity")
        self.geometry("680x780")
        self.configure(fg_color=BG_VOID)
        
        # Load theme setting defaults
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Downloader states
        self.download_folder = ""
        self.current_video_title = "Unknown Media"
        self.current_thumbnail_data = None
        self.picker_checkboxes = []

        self.build_ui()

    def build_ui(self):
        # ----------------------------------------------------
        # TOP HEADER
        # ----------------------------------------------------
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=24, pady=(16, 8))

        self.logo_lbl = ctk.CTkLabel(
            self.header_frame,
            text="Velocity",
            font=FONT_TITLE,
            text_color=LIME_ACCENT
        )
        self.logo_lbl.pack(anchor="w")

        # ----------------------------------------------------
        # MAIN TABVIEW
        # ----------------------------------------------------
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="transparent",
            segmented_button_selected_color=LIME_ACCENT,
            segmented_button_selected_hover_color=LIME_HOVER,
            segmented_button_unselected_color=MUTED_BG,
            segmented_button_unselected_hover_color="#4F4F5F",
            text_color=WHITE_TEXT
        )
        self.tabview.pack(fill="both", expand=True, padx=24, pady=(8, 16))

        self.tab_download = self.tabview.add("📥 Downloader")
        self.tab_settings = self.tabview.add("⚙️ Settings")
        self.tab_console = self.tabview.add("📊 Activity Log")

        self.tabview._segmented_button.configure(font=FONT_LABEL)
        
        # Enforce selected/unselected color requirements at runtime
        import types
        def patch_segmented_button(seg_btn):
            orig_select = seg_btn._select_button_by_value
            orig_unselect = seg_btn._unselect_button_by_value
            
            def custom_select(self_widget, value):
                orig_select(value)
                if value in self_widget._buttons_dict:
                    self_widget._buttons_dict[value].configure(text_color="#0D0D12")
            
            def custom_unselect(self_widget, value):
                orig_unselect(value)
                if value in self_widget._buttons_dict:
                    self_widget._buttons_dict[value].configure(text_color="#FFFFFF")
            
            seg_btn._select_button_by_value = types.MethodType(custom_select, seg_btn)
            seg_btn._unselect_button_by_value = types.MethodType(custom_unselect, seg_btn)
            
            # Initial styling configuration
            for val, btn in seg_btn._buttons_dict.items():
                if val == seg_btn._current_value:
                    btn.configure(text_color="#0D0D12")
                else:
                    btn.configure(text_color="#FFFFFF")

        patch_segmented_button(self.tabview._segmented_button)

        # ----------------------------------------------------
        # TAB 1: Downloader Section
        # ----------------------------------------------------
        # Subnav Layer 1: Platform Mode Selector (identical width/height alignment)
        self.platform_sec_frame = ctk.CTkFrame(self.tab_download, fg_color="transparent")
        self.platform_sec_frame.pack(fill="x", pady=(8, 8))

        self.platform_selector = ctk.CTkSegmentedButton(
            self.platform_sec_frame,
            values=["🔴 YouTube Mode", "📸 Instagram Mode"],
            command=self.on_platform_switch,
            font=FONT_LABEL,
            fg_color=MUTED_BG,
            selected_color=LIME_ACCENT,
            selected_hover_color=LIME_HOVER,
            text_color=WHITE_TEXT,
            height=36
        )
        self.platform_selector.pack(fill="x", expand=True)
        self.platform_selector.set("🔴 YouTube Mode")
        patch_segmented_button(self.platform_selector)

        # Subnav Layer 2: Adaptive Category Selector
        self.category_sec_frame = ctk.CTkFrame(self.tab_download, fg_color="transparent")
        self.category_sec_frame.pack(fill="x", pady=(0, 16))

        self.category_selector = ctk.CTkSegmentedButton(
            self.category_sec_frame,
            values=["📹 Video/Audio Only", "🖼️ Cover Thumbnail"],
            command=self.on_category_switch,
            font=FONT_LABEL,
            fg_color=MUTED_BG,
            selected_color=LIME_ACCENT,
            selected_hover_color=LIME_HOVER,
            text_color=WHITE_TEXT,
            height=36
        )
        self.category_selector.pack(fill="x", expand=True)
        self.category_selector.set("📹 Video/Audio Only")
        patch_segmented_button(self.category_selector)

        # URL Input Row Card
        self.input_card = ctk.CTkFrame(
            self.tab_download,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR
        )
        self.input_card.pack(fill="x", pady=(0, 16))

        self.input_inner = ctk.CTkFrame(self.input_card, fg_color="transparent")
        self.input_inner.pack(padx=16, pady=16, fill="x")

        self.url_entry = ctk.CTkEntry(
            self.input_inner,
            placeholder_text="Paste YouTube link here...",
            height=40,
            font=FONT_BODY,
            fg_color="#0D0D12",
            border_color=BORDER_COLOR,
            border_width=1.5,
            text_color=WHITE_TEXT,
            placeholder_text_color=MUTED_TEXT,
            corner_radius=12
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<KeyRelease>", self.on_url_key_release)
        self.url_entry.bind("<FocusIn>", lambda e: self.url_entry.configure(border_color=LIME_ACCENT))
        self.url_entry.bind("<FocusOut>", lambda e: self.url_entry.configure(border_color=BORDER_COLOR))

        self.analyze_btn = ctk.CTkButton(
            self.input_inner,
            text="Analyze URL",
            height=40,
            width=130,
            font=FONT_LABEL,
            fg_color=LIME_ACCENT,
            hover_color=LIME_HOVER,
            text_color="#0D0D12",
            corner_radius=12,
            command=self.analyze
        )
        self.analyze_btn.pack(side="right")
        
        # Click animations bindings for Analyze
        self.analyze_btn.bind("<Button-1>", lambda e: self.after(0, self.analyze_btn_click_down))
        self.analyze_btn.bind("<ButtonRelease-1>", lambda e: self.after(0, self.analyze_btn_click_up))

        # Dynamic Metadata Card Frame
        self.info_frame = ctk.CTkFrame(
            self.tab_download,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR
        )

        self.info_inner = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.info_inner.pack(padx=16, pady=16, fill="x")

        # Grid splits: Left (Thumbnail/Folder), Right (Formats/Title/Btn)
        self.left_col = ctk.CTkFrame(self.info_inner, fg_color="transparent")
        self.left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.right_col = ctk.CTkFrame(self.info_inner, fg_color="transparent")
        self.right_col.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self.thumbnail = ctk.CTkLabel(
            self.left_col,
            text="Metadata Preview",
            fg_color="#0D0D12",
            text_color=MUTED_TEXT,
            font=FONT_SMALL,
            height=140,
            corner_radius=12
        )
        self.thumbnail.pack(fill="x", pady=(0, 8))

        self.folder_box = ctk.CTkFrame(self.left_col, fg_color="transparent")
        self.folder_box.pack(fill="x")

        self.folder_lbl = ctk.CTkLabel(
            self.folder_box,
            text="Save path: Downloads (Default)",
            font=FONT_SMALL,
            text_color=MUTED_TEXT,
            anchor="w"
        )
        self.folder_lbl.pack(fill="x", pady=(0, 4))

        self.choose_folder_btn = ctk.CTkButton(
            self.folder_box,
            text="Choose folder",
            height=34,
            font=FONT_SMALL_BOLD,
            fg_color=MUTED_BG,
            hover_color="#4F4F5F",
            text_color=WHITE_TEXT,
            corner_radius=12,
            command=self.choose_folder
        )
        self.choose_folder_btn.pack(fill="x")

        self.title_lbl = ctk.CTkLabel(
            self.right_col,
            text="Title",
            font=FONT_LABEL,
            text_color=WHITE_TEXT,
            anchor="w",
            justify="left"
        )
        self.title_lbl.pack(fill="x", pady=(0, 8), anchor="w")

        self.channel_lbl = ctk.CTkLabel(
            self.right_col,
            text="Channel",
            font=FONT_BODY,
            text_color=MUTED_TEXT,
            anchor="w"
        )
        self.channel_lbl.pack(fill="x", pady=(0, 8), anchor="w")

        self.duration_lbl = ctk.CTkLabel(
            self.right_col,
            text="Duration",
            font=FONT_BODY,
            text_color=MUTED_TEXT,
            anchor="w"
        )
        self.duration_lbl.pack(fill="x", pady=(0, 8), anchor="w")

        # Format selector panel (packed dynamically but defined here)
        self.format_frame = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.format_frame.pack(fill="x", pady=(0, 8))

        fmt_lbl = ctk.CTkLabel(self.format_frame, text="Format:", font=FONT_BODY, text_color=WHITE_TEXT)
        fmt_lbl.pack(side="left", padx=(0, 8))

        self.format_box = ctk.CTkComboBox(
            self.format_frame,
            values=["MP4", "MP3"],
            width=80,
            height=32,
            corner_radius=12,
            fg_color="#0D0D12",
            border_color=BORDER_COLOR,
            button_color=BORDER_COLOR,
            button_hover_color=MUTED_BG
        )
        self.format_box.pack(side="left", padx=(0, 12))

        quality_lbl = ctk.CTkLabel(self.format_frame, text="Res:", font=FONT_BODY, text_color=WHITE_TEXT)
        quality_lbl.pack(side="left", padx=(0, 8))

        self.quality_box = ctk.CTkComboBox(
            self.format_frame,
            values=["1080p", "720p", "480p", "360p", "Best Audio"],
            width=110,
            height=32,
            corner_radius=12,
            fg_color="#0D0D12",
            border_color=BORDER_COLOR,
            button_color=BORDER_COLOR,
            button_hover_color=MUTED_BG
        )
        self.quality_box.set("720p")
        self.quality_box.pack(side="left")

        # Central download button action triggers
        self.action_frame = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.action_frame.pack(fill="x", pady=(0, 8))

        self.download_btn = ctk.CTkButton(
            self.action_frame,
            text="Download Video",
            height=40,
            font=FONT_LABEL,
            fg_color=LIME_ACCENT,
            hover_color=LIME_HOVER,
            text_color="#08080C",
            corner_radius=12,
            command=self.download
        )
        self.download_btn.pack(side="left", fill="x", expand=True)

        # Legacy redundant thumbnail button (hidden entirely to fit separated layout rules)
        self.thumbnail_btn = ctk.CTkButton(
            self.action_frame,
            text="Cover JPG",
            command=self.download_thumbnail
        )

        self.progress_frame = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.progress_frame.pack(fill="x", pady=(0, 8))

        self.progress = ctk.CTkProgressBar(
            self.progress_frame,
            height=8,
            progress_color=LIME_ACCENT,
            fg_color="#21212B",
            corner_radius=4
        )
        self.progress.pack(fill="x", pady=(0, 6))
        self.progress.set(0)

        self.metrics_frame = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.metrics_frame.pack(fill="x")

        self.metric_pct = ctk.CTkLabel(self.metrics_frame, text="0%", font=FONT_LABEL, text_color=LIME_ACCENT)
        self.metric_pct.pack(side="left", padx=(0, 8))

        self.metric_speed = ctk.CTkLabel(self.metrics_frame, text="Speed: -", font=FONT_SMALL, text_color=MUTED_TEXT)
        self.metric_speed.pack(side="left", padx=(0, 8))

        self.metric_eta = ctk.CTkLabel(self.metrics_frame, text="ETA: -", font=FONT_SMALL, text_color=MUTED_TEXT)
        self.metric_eta.pack(side="left", padx=(0, 8))

        self.metric_size = ctk.CTkLabel(self.metrics_frame, text="Size: -", font=FONT_SMALL, text_color=MUTED_TEXT)
        self.metric_size.pack(side="right")

        # Multi-Item Picker Card Frame (styled cyberpunk)
        self.picker_card = ctk.CTkFrame(
            self.tab_download,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR
        )

        self.picker_inner = ctk.CTkFrame(self.picker_card, fg_color="transparent")
        self.picker_inner.pack(padx=16, pady=16, fill="both", expand=True)

        picker_header = ctk.CTkFrame(self.picker_inner, fg_color="transparent")
        picker_header.pack(fill="x", pady=(0, 8))

        picker_title = ctk.CTkLabel(
            picker_header,
            text="Detected Media Slides",
            font=FONT_HEADER,
            text_color=WHITE_TEXT
        )
        picker_title.pack(side="left")

        self.select_all_btn = ctk.CTkButton(
            picker_header,
            text="Select All",
            width=80,
            height=30,
            font=FONT_SMALL_BOLD,
            fg_color=MUTED_BG,
            hover_color="#4F4F5F",
            text_color=WHITE_TEXT,
            corner_radius=12,
            command=self.select_all_slides
        )
        self.select_all_btn.pack(side="right", padx=(4, 0))

        self.deselect_all_btn = ctk.CTkButton(
            picker_header,
            text="Deselect All",
            width=80,
            height=30,
            font=FONT_SMALL_BOLD,
            fg_color=MUTED_BG,
            hover_color="#4F4F5F",
            text_color=WHITE_TEXT,
            corner_radius=12,
            command=self.deselect_all_slides
        )
        self.deselect_all_btn.pack(side="right")

        self.picker_scroll = ctk.CTkScrollableFrame(
            self.picker_inner,
            height=130,
            fg_color="#0D0D12",
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=12
        )
        self.picker_scroll.pack(fill="x", pady=(0, 8))

        self.zip_option_frame = ctk.CTkFrame(self.picker_inner, fg_color="transparent")
        self.zip_option_frame.pack(fill="x")

        zip_lbl = ctk.CTkLabel(
            self.zip_option_frame,
            text="Download Method:",
            font=FONT_BODY,
            text_color=WHITE_TEXT
        )
        zip_lbl.pack(side="left")

        self.zip_choice = ctk.CTkComboBox(
            self.zip_option_frame,
            values=["Save as Separate Files", "Pack into single ZIP Archive"],
            width=220,
            height=30,
            corner_radius=12,
            fg_color=MUTED_BG,
            border_color=BORDER_COLOR,
            button_color=BORDER_COLOR,
            button_hover_color=MUTED_BG
        )
        self.zip_choice.set("Save as Separate Files")
        self.zip_choice.pack(side="left", padx=8)

        # ----------------------------------------------------
        # TAB 2: System Settings
        # ----------------------------------------------------
        self.settings_card = ctk.CTkFrame(
            self.tab_settings,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR
        )
        self.settings_card.pack(fill="both", expand=True, padx=24, pady=16)

        self.settings_inner = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        self.settings_inner.pack(padx=24, pady=24, fill="both", expand=True)

        theme_head = ctk.CTkLabel(
            self.settings_inner,
            text="Diagnostics & Options",
            font=FONT_TITLE,
            text_color=WHITE_TEXT
        )
        theme_head.pack(anchor="w", pady=(0, 16))

        self.ffmpeg_frame = ctk.CTkFrame(self.settings_inner, fg_color="transparent")
        self.ffmpeg_frame.pack(fill="x", pady=8)

        ffmpeg_lbl = ctk.CTkLabel(
            self.ffmpeg_frame,
            text="FFmpeg Encoder Status:",
            font=FONT_LABEL,
            text_color=WHITE_TEXT
        )
        ffmpeg_lbl.pack(side="left")

        ffmpeg_installed = shutil.which("ffmpeg") is not None
        ffmpeg_text = "Installed (High Quality Merging Active)" if ffmpeg_installed else "Missing (Progressive Fallback Active)"
        ffmpeg_color = COLOR_SUCCESS if ffmpeg_installed else COLOR_ERROR

        self.ffmpeg_status = ctk.CTkLabel(
            self.ffmpeg_frame,
            text=ffmpeg_text,
            font=FONT_LABEL,
            text_color=ffmpeg_color
        )
        self.ffmpeg_status.pack(side="left", padx=8)

        self.theme_frame = ctk.CTkFrame(self.settings_inner, fg_color="transparent")
        self.theme_frame.pack(fill="x", pady=8)

        theme_lbl = ctk.CTkLabel(
            self.theme_frame,
            text="Interface Appearance Theme:",
            font=FONT_LABEL,
            text_color=WHITE_TEXT
        )
        theme_lbl.pack(side="left")

        self.theme_option = ctk.CTkOptionMenu(
            self.theme_frame,
            values=["Dark", "Light", "System"],
            fg_color=MUTED_BG,
            button_color=BORDER_COLOR,
            button_hover_color=MUTED_BG,
            dropdown_fg_color=CARD_BG,
            dropdown_text_color=WHITE_TEXT,
            dropdown_hover_color=MUTED_BG,
            corner_radius=12,
            command=self.change_theme
        )
        self.theme_option.set("Dark")
        self.theme_option.pack(side="left", padx=8)

        self.path_frame = ctk.CTkFrame(self.settings_inner, fg_color="transparent")
        self.path_frame.pack(fill="x", pady=8)

        path_title_lbl = ctk.CTkLabel(
            self.path_frame,
            text="Configuration Folder Path:",
            font=FONT_LABEL,
            text_color=WHITE_TEXT
        )
        path_title_lbl.pack(anchor="w", pady=(0, 4))

        self.path_setting_inner = ctk.CTkFrame(self.path_frame, fg_color="transparent")
        self.path_setting_inner.pack(fill="x")

        self.path_setting_lbl = ctk.CTkLabel(
            self.path_setting_inner,
            text="No folder custom configured",
            font=FONT_BODY,
            text_color=MUTED_TEXT,
            anchor="w"
        )
        self.path_setting_lbl.pack(side="left", fill="x", expand=True)

        self.path_setting_btn = ctk.CTkButton(
            self.path_setting_inner,
            text="Change Path",
            width=100,
            height=34,
            fg_color=MUTED_BG,
            hover_color="#4F4F5F",
            text_color=WHITE_TEXT,
            corner_radius=12,
            command=self.choose_folder
        )
        self.path_setting_btn.pack(side="right")

        # ----------------------------------------------------
        # TAB 3: Activity Logging Tab
        # ----------------------------------------------------
        self.console_card = ctk.CTkFrame(
            self.tab_console,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR
        )
        self.console_card.pack(fill="both", expand=True, padx=24, pady=16)

        self.console_inner = ctk.CTkFrame(self.console_card, fg_color="transparent")
        self.console_inner.pack(padx=16, pady=16, fill="both", expand=True)

        log_lbl = ctk.CTkLabel(
            self.console_inner,
            text="Activity Debug Logs",
            font=FONT_HEADER,
            text_color=WHITE_TEXT
        )
        log_lbl.pack(anchor="w", pady=(0, 8))

        self.console_textbox = ctk.CTkTextbox(
            self.console_inner,
            fg_color="#0D0D12",
            border_color=BORDER_COLOR,
            border_width=1.5,
            text_color=LIME_ACCENT,
            font=FONT_CONSOLE,
            corner_radius=12
        )
        self.console_textbox.pack(fill="both", expand=True)
        self.console_textbox.configure(state="disabled")

        # ----------------------------------------------------
        # STATUS FOOTER BAR
        # ----------------------------------------------------
        self.status_bar = ctk.CTkFrame(self, height=35, fg_color=CARD_BG, corner_radius=0)
        self.status_bar.pack(side="bottom", fill="x")

        self.status_inner = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        self.status_inner.pack(side="left", padx=24, fill="y")

        self.status_dot = ctk.CTkLabel(
            self.status_inner,
            text="●",
            font=("Inter", 14),
            text_color=MUTED_TEXT
        )
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_lbl = ctk.CTkLabel(
            self.status_inner,
            text="System Online | Awaiting Pipeline Target...",
            font=FONT_SMALL,
            text_color=WHITE_TEXT
        )
        self.status_lbl.pack(side="left")

        # Initialize visibility configuration
        self.on_category_switch(self.category_selector.get())
        self.log("Velocity premium pipeline initialized.")

    def analyze_btn_click_down(self):
        self.analyze_btn.configure(width=127, height=39)

    def analyze_btn_click_up(self):
        self.analyze_btn.configure(width=130, height=40)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}\n"
        self.after(0, lambda: self._write_log_ui(formatted))

    def _write_log_ui(self, formatted):
        if hasattr(self, 'console_textbox'):
            self.console_textbox.configure(state="normal")
            self.console_textbox.insert("end", formatted)
            self.console_textbox.see("end")
            self.console_textbox.configure(state="disabled")
        print(formatted.strip())

    def update_status(self, message, dot_color):
        if hasattr(self, 'status_lbl'):
            self.status_lbl.configure(text=message)
            self.status_dot.configure(text_color=dot_color)

    def change_theme(self, choice):
        ctk.set_appearance_mode(choice.lower())
        self.log(f"Theme mode altered. Config updated to: {choice}")

    def on_platform_switch(self, mode):
        if not hasattr(self, 'category_selector'):
            return

        if mode == "🔴 YouTube Mode":
            yt_cats = ["📹 Video/Audio Only", "🖼️ Cover Thumbnail"]
            self.category_selector.configure(values=yt_cats)
            self.category_selector.set(yt_cats[0])
            self.on_category_switch(yt_cats[0])
        else:
            ig_cats = ["📹 Video/Reel", "🖼️ Photo/Carousel", "📱 Story", "👤 Profile Pic"]
            self.category_selector.configure(values=ig_cats)
            self.category_selector.set(ig_cats[0])
            self.on_category_switch(ig_cats[0])

        self.log(f"Switched download channel mode context to: {mode}")

    def on_category_switch(self, category):
        placeholders = {
            "📹 Video/Audio Only": "Paste YouTube link here...",
            "🖼️ Cover Thumbnail": "Paste YouTube link here...",
            "📹 Video/Reel": "Paste Instagram Reel or Video link...",
            "🖼️ Photo/Carousel": "Paste Instagram Carousel Post link...",
            "📱 Story": "Paste Instagram Story link...",
            "👤 Profile Pic": "Paste Instagram Profile URL or @username..."
        }
        placeholder = placeholders.get(category, "Paste link here...")
        if hasattr(self, 'url_entry') and self.url_entry:
            self.url_entry.configure(placeholder_text=placeholder)

        # Update download button text dynamically
        if hasattr(self, 'download_btn') and self.download_btn:
            btn_labels = {
                "📱 Story": "Download Slides",
                "🖼️ Photo/Carousel": "Download Selected",
                "👤 Profile Pic": "Download Profile Pic",
                "🖼️ Cover Thumbnail": "Download Thumbnail"
            }
            lbl = btn_labels.get(category, "Download Video")
            self.download_btn.configure(text=lbl)

        # Split categories: hide format box when not downloading reels/youtube video format
        if hasattr(self, 'format_frame') and self.format_frame:
            if category in ["📹 Video/Audio Only", "📹 Video/Reel"]:
                self.format_frame.pack(before=self.action_frame, fill="x", pady=(0, 12))
            else:
                self.format_frame.pack_forget()

        # Hide picker checklist elements conditionally
        if hasattr(self, 'picker_card') and self.picker_card:
            self.picker_card.pack_forget()
        if hasattr(self, 'picker_checkboxes'):
            self.picker_checkboxes = []

    def on_url_key_release(self, event):
        url = self.url_entry.get().strip().lower()
        if "youtube.com" in url or "youtu.be" in url:
            if self.platform_selector.get() != "🔴 YouTube Mode":
                self.platform_selector.set("🔴 YouTube Mode")
                self.on_platform_switch("🔴 YouTube Mode")
        elif "instagram.com" in url:
            if self.platform_selector.get() != "📸 Instagram Mode":
                self.platform_selector.set("📸 Instagram Mode")
                self.on_platform_switch("📸 Instagram Mode")

    def select_all_slides(self):
        for var, _ in self.picker_checkboxes:
            var.set("on")

    def deselect_all_slides(self):
        for var, _ in self.picker_checkboxes:
            var.set("off")

    def analyze(self):
        url = self.url_entry.get().strip()
        if url == "":
            self.update_status("Enter a URL first.", COLOR_ERROR)
            self.log("Analysis error: Input URL is empty.")
            return

        self.log(f"Initiated parsing pipeline: url = {url}")
        self.update_status("Parsing media meta details...", COLOR_PROCESSING)
        self.analyze_btn.configure(state="disabled")
        
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        
        self.metric_pct.configure(text="--%")
        self.metric_speed.configure(text="Speed: -")
        self.metric_eta.configure(text="ETA: -")
        self.metric_size.configure(text="Size: -")

        threading.Thread(target=self._analyze_thread, args=(url,), daemon=True).start()

    def _analyze_thread(self, url):
        try:
            category = self.category_selector.get()
            
            # Instagram @username normalizations
            if category == "👤 Profile Pic" and not url.startswith("http"):
                username = url.lstrip("@").strip()
                url = f"https://www.instagram.com/{username}/"

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',
                'skip_download': True,
                'check_formats': False,
                'youtube_include_dash_manifest': False,
                'youtube_include_hls_manifest': False,
            }
            
            try:
                import yt_dlp
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as extract_err:
                # Custom bypass failover logic for Instagram urls (to handle login wall blockings)
                if "instagram.com" in url or self.platform_selector.get() == "📸 Instagram Mode":
                    self.log(f"Instagram backend details parsing warning: {extract_err}. Proceeding with manual fallbacks.")
                    info = {
                        'title': "Instagram Media Asset",
                        'uploader': "instagram.com",
                        'duration': None,
                        'thumbnail': None
                    }
                else:
                    raise extract_err

            title = info.get('title', 'Unknown Title')
            channel = info.get('uploader')
            if not channel:
                channel = info.get('uploader_id') or info.get('webpage_url_domain', 'Generic')

            duration = info.get('duration')
            thumbnail_url = info.get('thumbnail')

            if duration:
                mins, secs = divmod(duration, 60)
                hours, mins = divmod(mins, 60)
                duration_str = f"{hours}h {mins}m {secs}s" if hours else f"{mins}m {secs}s"
            else:
                duration_str = "Unknown"

            ctk_image = None
            raw_thumbnail_bytes = None
            if thumbnail_url:
                try:
                    self.log("Retrieving cover image raw bytes...")
                    req = urllib.request.Request(thumbnail_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        raw_thumbnail_bytes = response.read()
                    img = Image.open(io.BytesIO(raw_thumbnail_bytes))
                    ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=(220, 140))
                except Exception as thumb_err:
                    self.log(f"Image cover extract error: {thumb_err}")

            # Collect multiple slides if available (playlist/stories/carousel info)
            is_playlist = 'entries' in info or '_type' in info and info['_type'] == 'playlist'
            entries_list = []
            if is_playlist:
                raw_entries = info.get('entries', [])
                for idx, entry in enumerate(raw_entries):
                    if entry:
                        url_entry = entry.get('url') or entry.get('thumbnail')
                        if url_entry:
                            entries_list.append({
                                'index': idx + 1,
                                'url': url_entry,
                                'title': entry.get('title') or f"Slide #{idx+1}"
                            })

            self.after(0, lambda: self._update_analysis_ui(title, channel, duration_str, ctk_image, raw_thumbnail_bytes, entries_list))

        except Exception as e:
            self.after(0, lambda: self._analysis_failed(str(e)))

    def _update_analysis_ui(self, title, channel, duration_str, ctk_image, raw_thumbnail_bytes, entries_list=None):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(0)

        self.analyze_btn.configure(state="normal")
        self.update_status("Ready to download.", COLOR_READY)
        
        self.current_video_title = title
        self.current_thumbnail_data = raw_thumbnail_bytes
        
        display_title = title if len(title) <= 50 else title[:47] + "..."
        self.title_lbl.configure(text=display_title)
        self.channel_lbl.configure(text=f"Channel: {channel}")
        self.duration_lbl.configure(text=f"Duration: {duration_str}")

        if ctk_image:
            self.thumbnail.configure(image=ctk_image, text="")
            self.thumbnail.image = ctk_image
        else:
            self.thumbnail.configure(image=None, text="Metadata Preview")

        self.log(f"Metadata extracted successfully: '{title[:40]}...'")
        self.info_frame.pack(fill="x", pady=10)

        # Setup checkboxes slide items picker card conditional on types match
        self.picker_card.pack_forget()
        if entries_list and self.category_selector.get() in ["🖼️ Photo/Carousel", "📱 Story"]:
            self.log(f"Parsing item slider checklists details ({len(entries_list)} elements).")
            
            for widget in self.picker_scroll.winfo_children():
                widget.destroy()
                
            self.picker_checkboxes = []
            for item in entries_list:
                var = ctk.StringVar(value="on")
                item_row = ctk.CTkFrame(self.picker_scroll, fg_color="transparent")
                item_row.pack(fill="x", pady=2)
                
                chk = ctk.CTkCheckBox(
                    item_row,
                    text=item['title'],
                    variable=var,
                    onvalue="on",
                    offvalue="off",
                    font=FONT_SMALL,
                    fg_color=LIME_ACCENT,
                    hover_color=LIME_HOVER,
                    text_color=WHITE_TEXT
                )
                chk.pack(side="left", padx=15, pady=5)
                self.picker_checkboxes.append((var, item))
                
            self.picker_card.pack(fill="x", pady=10)

    def _analysis_failed(self, error_msg):
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(0)
        self.analyze_btn.configure(state="normal")
        
        self.update_status("Analysis failed.", COLOR_ERROR)
        self.log(f"Extraction failed: {error_msg}")

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_folder = folder
            self.folder_lbl.configure(text=f"Save path: {folder}")
            self.path_setting_lbl.configure(text=folder)
            self.log(f"Save directory updated to: {folder}")

    def download(self):
        url = self.url_entry.get().strip()
        if url == "":
            self.update_status("Enter a URL first.", COLOR_ERROR)
            self.log("Download failed: URL parameter empty.")
            return

        if not self.download_folder:
            default_path = os.path.join(os.path.expanduser('~'), 'Downloads')
            self.download_folder = default_path if os.path.exists(default_path) else os.getcwd()
            self.folder_lbl.configure(text=f"Save path: {self.download_folder}")
            self.path_setting_lbl.configure(text=self.download_folder)

        category = self.category_selector.get()
        
        # If slides selector is packed and selection exists
        if category in ["🖼️ Photo/Carousel", "📱 Story"] and hasattr(self, 'picker_checkboxes') and self.picker_checkboxes and self.picker_card.winfo_manager() != "":
            selected = [item for var, item in self.picker_checkboxes if var.get() == "on"]
            if not selected:
                self.update_status("No slides selected.", COLOR_ERROR)
                self.log("Failed: Checklist slide selectors empty.")
                return

            self.download_btn.configure(state="disabled")
            self.update_status("Downloading selections...", "#3B82F6")
            
            zipped = self.zip_choice.get() == "Pack into single ZIP Archive"
            self.log(f"Starting Instagram slides batch extract. Selections count: {len(selected)}")
            
            threading.Thread(
                target=self._download_carousel_thread,
                args=(selected, self.download_folder, zipped, self.current_video_title),
                daemon=True
            ).start()
            return

        # Profile/Thumbnail covers downloads
        if category in ["👤 Profile Pic", "🖼️ Cover Thumbnail"] and self.current_thumbnail_data:
            self.download_thumbnail()
            return

        # General stream media downloads
        self.log(f"Starting downloader thread. Directory save target: {self.download_folder}")
        self.update_status("Starting download...", "#3B82F6")
        
        self.progress.set(0)
        self.metric_pct.configure(text="0%")
        self.metric_speed.configure(text="Speed: -")
        self.metric_eta.configure(text="ETA: -")
        self.metric_size.configure(text="Size: -")
        
        self.download_btn.configure(state="disabled")
        
        fmt = self.format_box.get()
        quality = self.quality_box.get()

        threading.Thread(
            target=self._download_thread,
            args=(url, self.download_folder, fmt, quality),
            daemon=True
        ).start()

    def _download_carousel_thread(self, items, folder, zip_it, title):
        try:
            res_path = download_instagram_carousel(
                items=items,
                folder=folder,
                zip_it=zip_it,
                title=title,
                log_callback=self.log,
                progress_callback=lambda p, cur, tot: self.after(0, lambda: self._update_carousel_progress(p, cur, tot))
            )
            self.after(0, lambda: self._carousel_done(res_path))
        except Exception as e:
            self.after(0, lambda: self._carousel_failed(str(e)))

    def _update_carousel_progress(self, percent, current, total):
        self.progress.set(percent)
        self.metric_pct.configure(text=f"{int(percent * 100)}%")
        self.metric_speed.configure(text="Urllib downloader active")
        self.metric_eta.configure(text=f"Item {current}/{total}")
        self.metric_size.configure(text=f"Total: {total}")
        self.update_status(f"Downloading selection ({current}/{total})...", "#3B82F6")

    def _carousel_done(self, path):
        self.progress.set(1.0)
        self.metric_pct.configure(text="100%")
        self.update_status("Download completed successfully!", COLOR_SUCCESS)
        self.download_btn.configure(state="normal")
        self.log(f"Instagram extraction cycle complete. Target: {path}")

    def _carousel_failed(self, err):
        self.progress.set(0)
        self.metric_pct.configure(text="Error")
        self.update_status("Download failed.", COLOR_ERROR)
        self.download_btn.configure(state="normal")
        self.log(f"Instagram Extraction Error detail: {err}")

    def _download_thread(self, url, folder, fmt, quality):
        try:
            download_youtube_media(
                url=url,
                folder=folder,
                fmt=fmt,
                quality=quality,
                progress_hook=self._progress_hook,
                log_callback=self.log
            )
            # Default yt-dlp triggers completed status on finished hook, but we guard here
        except Exception as e:
            self.after(0, lambda: self._download_failed(str(e)))

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            
            percent = downloaded / total if total > 0 else 0
            speed_str = d.get('_speed_str', 'N/A')
            eta_str = d.get('_eta_str', 'N/A')
            
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            size_str = f"{downloaded_mb:.1f}MB / {total_mb:.1f}MB" if total > 0 else f"{downloaded_mb:.1f}MB"

            self.after(
                0,
                lambda p=percent, s=speed_str, e=eta_str, sz=size_str: self._update_download_progress(p, s, e, sz)
            )
        elif d['status'] == 'finished':
            self.after(0, self._download_finished)

    def _update_download_progress(self, percent, speed_str, eta_str, size_str):
        self.progress.set(percent)
        percent_display = int(percent * 100)
        self.metric_pct.configure(text=f"{percent_display}%")
        self.metric_speed.configure(text=f"Speed: {speed_str.strip()}")
        self.metric_eta.configure(text=f"ETA: {eta_str.strip()}")
        self.metric_size.configure(text=f"Size: {size_str}")
        self.update_status(f"Downloading... {percent_display}%", "#3B82F6")

    def _download_finished(self):
        self.progress.set(1.0)
        self.metric_pct.configure(text="100%")
        self.update_status("Download completed successfully!", COLOR_SUCCESS)
        self.download_btn.configure(state="normal")
        self.log("Download completed. Media details saved successfully.")

    def _download_failed(self, error_msg):
        self.progress.set(0)
        self.metric_pct.configure(text="Error")
        self.update_status("Download failed.", COLOR_ERROR)
        self.download_btn.configure(state="normal")
        self.log(f"Media download failed: {error_msg[:120]}")

    def download_thumbnail(self):
        if not self.current_thumbnail_data:
            self.update_status("No cover data.", COLOR_ERROR)
            self.log("Save cover failed: Empty preview stream.")
            return

        if not self.download_folder:
            default_path = os.path.join(os.path.expanduser('~'), 'Downloads')
            self.download_folder = default_path if os.path.exists(default_path) else os.getcwd()
            self.folder_lbl.configure(text=f"Save path: {self.download_folder}")
            self.path_setting_lbl.configure(text=self.download_folder)

        safe_title = re.sub(r'[\\/*?:"<>|]', "", self.current_video_title)
        filename = f"{safe_title}_cover.jpg"
        save_path = os.path.join(self.download_folder, filename)

        try:
            with open(save_path, "wb") as f:
                f.write(self.current_thumbnail_data)
            self.update_status("Cover images saved successfully!", COLOR_SUCCESS)
            self.log(f"JPG cover image file committed: {filename}")
        except Exception as e:
            self.update_status("Save failed.", COLOR_ERROR)
            self.log(f"File writing cover image error: {str(e)[:50]}")

if __name__ == "__main__":
    app = Velocity()
    app.mainloop()
