import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
from datetime import datetime
from scapy.all import *
from scapy.layers.inet import IP, TCP, UDP
import socket
from pathlib import Path
import json

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class PCAPPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PCAP Player (UDP Only)")
        self.geometry("1400x900")

        # Core state
        self.pcap_file = None
        self.all_packets = []

        # Timing state
        self.pcap_start_time = 0.0
        self.total_duration = 0.0  # seconds (pcap_end - pcap_start)
        self.current_playback_pos = 0.0  # seconds from pcap_start

        # Playback control
        self.is_playing = False
        self.playback_speed = 1.0
        self.play_thread = None
        self.stop_playback_event = None

        # DIS graph state
        self.dis_time_bins = []
        self.dis_counts = []
        self.dis_fig = None
        self.dis_ax = None
        self.dis_canvas = None
        self.dis_playhead = None

        self.setup_ui()
        self.update_ui()

    # -------------------------------------------------------------------------
    # UI setup
    # -------------------------------------------------------------------------
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_container = ctk.CTkFrame(self, corner_radius=10)
        self.main_container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self.main_container, height=80, corner_radius=10)
        self.header_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)

        title_label = ctk.CTkLabel(
            self.header_frame,
            text="PCAP Player (UDP Streams)",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Accurate UDP Traffic Replayer",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        subtitle_label.grid(row=0, column=1, padx=20, pady=20, sticky="w")

        # Main content area
        self.content_frame = ctk.CTkFrame(self.main_container, corner_radius=10)
        self.content_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=3)
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Left panel
        self.left_panel = ctk.CTkFrame(self.content_frame, corner_radius=10)
        self.left_panel.grid(row=0, column=0, padx=(0, 5), pady=10, sticky="nsew")
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(2, weight=1)

        # File section
        self.file_section = ctk.CTkFrame(self.left_panel, corner_radius=10)
        self.file_section.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.file_info_frame = ctk.CTkFrame(self.file_section, corner_radius=8)
        self.file_info_frame.pack(fill="x", padx=10, pady=10)

        self.file_path_label = ctk.CTkLabel(
            self.file_info_frame,
            text="No file selected",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.file_path_label.pack(fill="x", padx=10, pady=5)

        self.file_stats_label = ctk.CTkLabel(
            self.file_info_frame,
            text="Packets: 0 | Duration: 00:00:00.000",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w"
        )
        self.file_stats_label.pack(fill="x", padx=10, pady=(0, 10))

        file_buttons_frame = ctk.CTkFrame(self.file_section, fg_color="transparent")
        file_buttons_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.browse_btn = ctk.CTkButton(
            file_buttons_frame,
            text="Browse PCAP",
            command=self.browse_file,
            width=120,
            height=35
        )
        self.browse_btn.pack(side="left", padx=(0, 10))

        # Target configuration
        self.target_section = ctk.CTkFrame(self.left_panel, corner_radius=10)
        self.target_section.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        target_input_frame = ctk.CTkFrame(self.target_section, fg_color="transparent")
        target_input_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(target_input_frame, text="Target IP:", width=80).grid(
            row=0, column=0, padx=(0, 5), pady=5
        )
        self.target_ip = ctk.CTkEntry(target_input_frame, placeholder_text="127.0.0.1", width=150)
        self.target_ip.insert(0, "127.0.0.1")
        self.target_ip.grid(row=0, column=1, padx=(0, 20), pady=5)

        ctk.CTkLabel(target_input_frame, text="Port:", width=50).grid(
            row=0, column=2, padx=(0, 5), pady=5
        )
        self.target_port = ctk.CTkEntry(target_input_frame, placeholder_text="3001", width=100)
        self.target_port.insert(0, "3001")
        self.target_port.grid(row=0, column=3, pady=5)

        # Playback controls
        self.playback_section = ctk.CTkFrame(self.left_panel, corner_radius=10)
        self.playback_section.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.time_label = ctk.CTkLabel(
            self.playback_section,
            text="00:00:00.000 / 00:00:00.000",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#00b894"
        )
        self.time_label.pack(pady=(15, 5))

        self.progress_slider = ctk.CTkSlider(
            self.playback_section,
            from_=0,
            to=100,
            number_of_steps=1000,
            command=self.on_progress_change
        )
        self.progress_slider.set(0)
        self.progress_slider.pack(fill="x", padx=20, pady=10)

        control_buttons_frame = ctk.CTkFrame(self.playback_section, fg_color="transparent")
        control_buttons_frame.pack(pady=10)

        # Speed control
        speed_frame = ctk.CTkFrame(control_buttons_frame, fg_color="transparent")
        speed_frame.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(speed_frame, text="Speed:").pack(side="left", padx=(0, 5))
        self.speed_combo = ctk.CTkComboBox(
            speed_frame,
            values=["0.25x", "0.5x", "1.0x", "2.0x", "4.0x", "8.0x", "16.0x"],
            command=self.change_speed,
            width=80
        )
        self.speed_combo.set("1.0x")
        self.speed_combo.pack(side="left")

        # Control buttons
        self.play_btn = ctk.CTkButton(
            control_buttons_frame,
            text="Play",
            command=self.toggle_play,
            width=80,
            height=35,
            fg_color="#00b894",
            hover_color="#00a884"
        )
        self.play_btn.pack(side="left", padx=5)

        self.pause_btn = ctk.CTkButton(
            control_buttons_frame,
            text="Pause",
            command=self.pause,
            width=80,
            height=35,
            fg_color="#fdcb6e",
            hover_color="#edbb5e"
        )
        self.pause_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            control_buttons_frame,
            text="Stop",
            command=self.stop,
            width=80,
            height=35,
            fg_color="#e17055",
            hover_color="#d16045"
        )
        self.stop_btn.pack(side="left", padx=5)

        # Right panel - Stats and graph
        self.right_panel = ctk.CTkFrame(self.content_frame, corner_radius=10)
        self.right_panel.grid(row=0, column=1, padx=(5, 0), pady=10, sticky="nsew")
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)

        # Statistics section
        self.stats_section = ctk.CTkScrollableFrame(self.right_panel, corner_radius=10)
        self.stats_section.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        stats_title = ctk.CTkLabel(
            self.stats_section,
            text="Statistics",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        stats_title.pack(pady=(10, 15))

        self.stats_labels = {}
        stats_items = [
            ("Total Packets:", "total_packets", "0"),
            ("TCP Packets:", "tcp_packets", "0"),
            ("UDP Packets:", "udp_packets", "0"),
            ("DIS PDU Packets:", "dis_packets", "0"),
            ("ICMP Packets:", "icmp_packets", "0"),
            ("DNS Packets:", "dns_packets", "0"),
            ("HTTP Packets:", "http_packets", "0"),
            ("Unique Source IPs:", "src_ips", "0"),
            ("Unique Destination IPs:", "dst_ips", "0"),
            ("Total Bytes:", "total_bytes", "0"),
            ("Average Packet Size:", "avg_size", "0")
        ]

        for label_text, key, default_value in stats_items:
            frame = ctk.CTkFrame(self.stats_section, fg_color="transparent", height=30)
            frame.pack(fill="x", padx=10, pady=2)

            ctk.CTkLabel(frame, text=label_text, width=150, anchor="w").pack(side="left")
            self.stats_labels[key] = ctk.CTkLabel(frame, text=default_value, anchor="w")
            self.stats_labels[key].pack(side="left", fill="x", expand=True)

        # DIS Graph section
        self.graph_frame = ctk.CTkFrame(self.right_panel, corner_radius=10)
        self.graph_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        graph_title = ctk.CTkLabel(
            self.graph_frame,
            text="DIS PDU Timeline",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        graph_title.pack(pady=(10, 5))

        # Status bar
        self.status_bar = ctk.CTkFrame(self.main_container, height=40, corner_radius=10)
        self.status_bar.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color="white"
        )
        self.status_label.pack(side="left", padx=15, pady=10)

        self.progress_indicator = ctk.CTkProgressBar(self.status_bar, width=200, height=8)
        self.progress_indicator.pack(side="right", padx=15, pady=10)
        self.progress_indicator.set(0)

    # -------------------------------------------------------------------------
    # File loading / stats
    # -------------------------------------------------------------------------
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select PCAP file",
            filetypes=[("PCAP files", "*.pcap *.pcapng"), ("All files", "*.*")]
        )

        if filename:
            self.load_pcap(filename)

    def load_pcap(self, filename):
        try:
            self.status_label.configure(text=f"Loading {Path(filename).name}...")
            self.progress_indicator.set(0.3)
            self.update()

            self.pcap_file = filename
            self.all_packets = rdpcap(filename)

            if len(self.all_packets) > 1:
                self.pcap_start_time = float(self.all_packets[0].time)
                last_time = float(self.all_packets[-1].time)
                self.total_duration = last_time - self.pcap_start_time
            else:
                self.pcap_start_time = 0.0
                self.total_duration = 0.0

            self.file_path_label.configure(text=f"File: {Path(filename).name}")
            self.progress_slider.set(0)
            self.current_playback_pos = 0.0

            total_packets = len(self.all_packets)
            self.file_stats_label.configure(
                text=f"Packets: {total_packets:,} | Duration: {self.format_duration(self.total_duration)}"
            )

            self.update_statistics()

            self.progress_indicator.set(1.0)
            self.status_label.configure(
                text=f"Loaded {len(self.all_packets)} packets from {Path(filename).name}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load PCAP file: {str(e)}")
            self.status_label.configure(text="Error loading file")
            self.progress_indicator.set(0)

    def update_statistics(self):
        if not self.all_packets:
            return

        counters = {
            'tcp': 0, 'udp': 0, 'icmp': 0,
            'dns': 0, 'http': 0, 'other': 0
        }

        src_ips = set()
        dst_ips = set()
        total_bytes = 0
        dis_count = 0  # DIS PDUs

        # For DIS timeline
        dis_bins = {}

        for pkt in self.all_packets:
            if TCP in pkt:
                counters['tcp'] += 1
                if pkt[TCP].dport in [80, 443, 8080, 8000]:
                    counters['http'] += 1

            elif UDP in pkt:
                counters['udp'] += 1
                if pkt[UDP].dport == 53:
                    counters['dns'] += 1

                # DIS detection: UDP payload starting with protocol version 7
                payload = bytes(pkt[UDP].payload)
                if len(payload) >= 4 and payload[0] == 7:
                    dis_count += 1
                    if self.total_duration > 0:
                        offset = int(float(pkt.time) - self.pcap_start_time)
                    else:
                        offset = 0
                    dis_bins[offset] = dis_bins.get(offset, 0) + 1

            elif ICMP in pkt:
                counters['icmp'] += 1
            else:
                counters['other'] += 1

            if IP in pkt:
                src_ips.add(pkt[IP].src)
                dst_ips.add(pkt[IP].dst)

            total_bytes += len(pkt)

        self.stats_labels['total_packets'].configure(text=f"{len(self.all_packets):,}")
        self.stats_labels['tcp_packets'].configure(text=f"{counters['tcp']:,}")
        self.stats_labels['udp_packets'].configure(text=f"{counters['udp']:,}")
        self.stats_labels['dis_packets'].configure(text=f"{dis_count:,}")
        self.stats_labels['icmp_packets'].configure(text=f"{counters['icmp']:,}")
        self.stats_labels['dns_packets'].configure(text=f"{counters['dns']:,}")
        self.stats_labels['http_packets'].configure(text=f"{counters['http']:,}")
        self.stats_labels['src_ips'].configure(text=f"{len(src_ips):,}")
        self.stats_labels['dst_ips'].configure(text=f"{len(dst_ips):,}")
        self.stats_labels['total_bytes'].configure(text=f"{total_bytes:,}")

        avg_size = total_bytes / len(self.all_packets) if self.all_packets else 0
        self.stats_labels['avg_size'].configure(text=f"{avg_size:.1f} bytes")

        # Build DIS time series and update graph
        self.dis_time_bins = sorted(dis_bins.keys())
        self.dis_counts = [dis_bins[t] for t in self.dis_time_bins] if self.dis_time_bins else []
        self.update_dis_graph()

    # -------------------------------------------------------------------------
    # DIS graph helpers
    # -------------------------------------------------------------------------
    def update_dis_graph(self):
        bg_color = "#2b2b2b"
        axis_color = "#dfe6e9"
        grid_color = "#444444"
        bar_color = "#00b894"
        playhead_color = "#e17055"

        if self.dis_fig is None:
            # Create figure and canvas once
            self.dis_fig = Figure(figsize=(4, 2), dpi=100, facecolor=bg_color)
            self.dis_ax = self.dis_fig.add_subplot(111)
            self.dis_canvas = FigureCanvasTkAgg(self.dis_fig, master=self.graph_frame)
            self.dis_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.dis_ax.clear()

        # Background and axes styling
        self.dis_ax.set_facecolor(bg_color)
        for spine in self.dis_ax.spines.values():
            spine.set_color(axis_color)

        self.dis_ax.tick_params(colors=axis_color)
        self.dis_ax.xaxis.label.set_color(axis_color)
        self.dis_ax.yaxis.label.set_color(axis_color)

        self.dis_ax.set_xlabel("Time (s)")
        self.dis_ax.set_ylabel("DIS PDUs")
        self.dis_ax.grid(True, linestyle="--", linewidth=0.5, color=grid_color)

        if self.dis_time_bins and self.dis_counts:
            self.dis_ax.bar(
                self.dis_time_bins,
                self.dis_counts,
                width=0.8,
                align="center",
                color=bar_color
            )
            if self.total_duration > 0:
                self.dis_ax.set_xlim(0, max(self.total_duration, max(self.dis_time_bins) + 1))
        else:
            self.dis_ax.text(
                0.5, 0.5, "No DIS PDUs",
                ha="center", va="center",
                transform=self.dis_ax.transAxes,
                color=axis_color
            )

        # Create playhead line at x=0
        self.dis_playhead = self.dis_ax.axvline(
            x=0, color=playhead_color, linestyle="--", linewidth=1
        )

        self.dis_canvas.draw()

    def update_dis_playhead(self):
        if (
            self.dis_ax is None or
            self.dis_canvas is None or
            self.dis_playhead is None
        ):
            return

        x = self.current_playback_pos
        self.dis_playhead.set_xdata([x, x])
        self.dis_canvas.draw_idle()

    # -------------------------------------------------------------------------
    # Playback control
    # -------------------------------------------------------------------------
    def toggle_play(self):
        if not self.pcap_file:
            messagebox.showwarning("No File", "Please load a PCAP file first")
            return

        if not self.is_playing:
            self.start_playback()
        else:
            self.pause()

    def start_playback(self):
        if not self.all_packets:
            messagebox.showwarning("No Packets", "No packets loaded")
            return

        # Only play UDP packets
        udp_packets = [p for p in self.all_packets if UDP in p]
        if not udp_packets:
            messagebox.showwarning("No UDP Packets", "This capture contains no UDP packets")
            return

        # Stop any existing playback thread
        if self.stop_playback_event is not None:
            self.stop_playback_event.set()

        self.stop_playback_event = threading.Event()
        self.is_playing = True

        # Determine starting offset from slider (0..total_duration)
        start_progress = self.progress_slider.get() / 100.0
        start_offset = start_progress * self.total_duration if self.total_duration > 0 else 0.0
        self.current_playback_pos = start_offset

        self.play_btn.configure(text="Pause", fg_color="#fdcb6e", hover_color="#edbb5e")
        self.status_label.configure(text="Playing UDP streams...")

        self.play_thread = threading.Thread(
            target=self.udp_playback_thread,
            args=(start_offset,),
            daemon=True
        )
        self.play_thread.start()

    def pause(self):
        if not self.is_playing:
            return

        self.is_playing = False
        if self.stop_playback_event is not None:
            self.stop_playback_event.set()

        self.play_btn.configure(text="Resume", fg_color="#00b894", hover_color="#00a884")
        self.status_label.configure(text="Paused")

    def stop(self):
        self.is_playing = False
        if self.stop_playback_event is not None:
            self.stop_playback_event.set()

        self.current_playback_pos = 0.0
        self.progress_slider.set(0)
        self.progress_indicator.set(0)
        self.play_btn.configure(text="Play", fg_color="#00b894", hover_color="#00a884")
        self.status_label.configure(text="Stopped")
        self.update_time_display()

    def change_speed(self, choice):
        speed_map = {
            "0.25x": 0.25,
            "0.5x": 0.5,
            "1.0x": 1.0,
            "2.0x": 2.0,
            "4.0x": 4.0,
            "8.0x": 8.0,
            "16.0x": 16.0
        }

        new_speed = speed_map.get(choice, 1.0)
        self.playback_speed = new_speed
        self.status_label.configure(text=f"Speed: {choice}")

        # If currently playing, restart from current position with new speed
        if self.is_playing:
            current_progress = self.progress_slider.get() / 100.0
            self.current_playback_pos = current_progress * self.total_duration if self.total_duration > 0 else 0.0

            if self.stop_playback_event is not None:
                self.stop_playback_event.set()

            self.stop_playback_event = threading.Event()
            self.play_thread = threading.Thread(
                target=self.udp_playback_thread,
                args=(self.current_playback_pos,),
                daemon=True
            )
            self.play_thread.start()

    # -------------------------------------------------------------------------
    # UDP playback thread (payload-only)
    # -------------------------------------------------------------------------
    def udp_playback_thread(self, start_offset):
        """
        Accurate UDP replay based on original pcap timestamps.
        Sends only the UDP payload via a normal UDP socket.
        start_offset: seconds from pcap_start_time where playback begins.
        """
        try:
            udp_packets = [p for p in self.all_packets if UDP in p]
            if not udp_packets:
                self.status_label.configure(text="No UDP packets to play")
                self.is_playing = False
                return

            target_ip = self.target_ip.get()
            target_port = int(self.target_port.get())
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            base_time = self.pcap_start_time
            real_start = time.time()

            total_udp = len(udp_packets)
            sent_count = 0

            for pkt in udp_packets:
                if self.stop_playback_event.is_set():
                    break

                pkt_time = float(pkt.time)
                rel_time = pkt_time - base_time  # time from capture start

                if rel_time < start_offset:
                    continue

                # When should this packet be sent (wall-clock)?
                send_at = real_start + (rel_time - start_offset) / max(self.playback_speed, 0.0001)

                while not self.stop_playback_event.is_set() and time.time() < send_at:
                    time.sleep(0.0005)  # 0.5 ms resolution

                if self.stop_playback_event.is_set():
                    break

                # Extract ONLY the UDP payload (no IP/UDP headers)
                try:
                    if UDP not in pkt:
                        continue

                    payload = bytes(pkt[UDP].payload)

                    # Skip empty payloads
                    if not payload:
                        continue

                    sock.sendto(payload, (target_ip, target_port))
                except Exception as e:
                    print(f"Error sending UDP payload: {e}")
                    continue

                # Update playback position and UI-related counters
                self.current_playback_pos = rel_time
                sent_count += 1
                self.progress_indicator.set(sent_count / total_udp)

            sock.close()

        finally:
            # Only reset play state if this thread wasn't interrupted mid-stream
            if not self.stop_playback_event.is_set():
                self.is_playing = False
                self.play_btn.configure(text="Play", fg_color="#00b894", hover_color="#00a884")
                self.status_label.configure(text="Playback finished")

    # -------------------------------------------------------------------------
    # UI / time formatting
    # -------------------------------------------------------------------------
    def on_progress_change(self, value):
        # Only allow manual seeking when not actively playing
        if not self.is_playing and self.total_duration > 0:
            progress = float(value) / 100.0
            self.current_playback_pos = progress * self.total_duration
            self.update_time_display()
            self.update_dis_playhead()

    def format_duration(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    def update_time_display(self):
        if self.total_duration > 0:
            if self.is_playing:
                current = self.current_playback_pos
            else:
                progress = self.progress_slider.get() / 100.0
                current = progress * self.total_duration
            current_str = self.format_duration(current)
            total_str = self.format_duration(self.total_duration)
            self.time_label.configure(text=f"{current_str} / {total_str}")
        else:
            self.time_label.configure(text="00:00:00.000 / 00:00:00.000")

    def update_ui(self):
        """
        Periodic UI update – does NOT drive timing, only reflects it.
        """
        if self.total_duration > 0:
            if self.is_playing:
                # slider follows playback position
                progress = (self.current_playback_pos / self.total_duration) * 100.0
                progress = max(0.0, min(100.0, progress))
                self.progress_slider.set(progress)

        self.update_time_display()
        self.update_dis_playhead()

        # Schedule next update in 50 ms
        self.after(50, self.update_ui)


def main():
    app = PCAPPlayer()
    app.mainloop()


if __name__ == "__main__":
    try:
        import scapy  # noqa: F401
    except ImportError:
        print("Installing required dependencies...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "scapy"])

    try:
        import customtkinter  # noqa: F401
    except ImportError:
        print("Installing CustomTkinter...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])

    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print("Installing matplotlib...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib"])

    main()
