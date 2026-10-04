"""
User-Friendly GUI Interface
Modern and intuitive interface for the Smart Home Automation System
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import cv2
from PIL import Image, ImageTk
import threading
from typing import Dict, Optional
from datetime import datetime


class SmartHomeGUI:
    """Main GUI application for Smart Home Automation"""
    
    def __init__(self, root, video_callback, data_callback):
        """
        Initialize GUI
        
        Args:
            root: Tkinter root window
            video_callback: Function to call for video processing
            data_callback: Function to get current sensor/analysis data
        """
        self.root = root
        self.video_callback = video_callback
        self.data_callback = data_callback
        self.is_running = False
        
        # Configure window
        self.root.title("Smart Home Automation - Energy Efficient System")
        # Start with a safe default size for laptop screens
        self.root.geometry("1100x750")
        self.root.configure(bg='#2b2b2b')
        
        # Attempt to maximize the window for better screen utilization
        try:
            self.root.state('zoomed')
        except Exception:
            pass
        
        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._configure_styles()
        
        # Create main layout
        self._create_layout()
        
        # Start update loop
        self.update_interval = 100  # milliseconds
        self.update_display()
    
    def _configure_styles(self):
        """Configure ttk styles"""
        self.style.configure('Title.TLabel', 
                           background='#2b2b2b', 
                           foreground='#ffffff',
                           font=('Arial', 16, 'bold'))
        self.style.configure('Heading.TLabel',
                           background='#2b2b2b',
                           foreground='#4CAF50',
                           font=('Arial', 12, 'bold'))
        self.style.configure('Info.TLabel',
                           background='#2b2b2b',
                           foreground='#ffffff',
                           font=('Arial', 10))
        self.style.configure('Status.TLabel',
                           background='#2b2b2b',
                           foreground='#FFC107',
                           font=('Arial', 10, 'bold'))
    
    def _create_layout(self):
        """Create the main GUI layout"""
        # Title bar
        title_frame = tk.Frame(self.root, bg='#1e1e1e', height=60)
        title_frame.pack(fill=tk.X, padx=0, pady=0)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text="🏠 Smart Home Automation System",
                              bg='#1e1e1e',
                              fg='#4CAF50',
                              font=('Arial', 18, 'bold'))
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Control buttons
        button_frame = tk.Frame(title_frame, bg='#1e1e1e')
        button_frame.pack(side=tk.RIGHT, padx=20, pady=10)
        
        self.start_btn = tk.Button(button_frame,
                                   text="▶ Start",
                                   command=self.start_system,
                                   bg='#4CAF50',
                                   fg='white',
                                   font=('Arial', 10, 'bold'),
                                   padx=15,
                                   pady=5,
                                   relief=tk.FLAT)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(button_frame,
                                  text="⏹ Stop",
                                  command=self.stop_system,
                                  bg='#f44336',
                                  fg='white',
                                  font=('Arial', 10, 'bold'),
                                  padx=15,
                                  pady=5,
                                  relief=tk.FLAT,
                                  state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.dash_btn = tk.Button(button_frame,
                                   text="📊 Dashboard",
                                   command=self.open_dashboard,
                                   bg='#2196F3',
                                   fg='white',
                                   font=('Arial', 10, 'bold'),
                                   padx=15,
                                   pady=5,
                                   relief=tk.FLAT)
        self.dash_btn.pack(side=tk.LEFT, padx=5)
        
        # Domain Selector
        domain_frame = tk.Frame(title_frame, bg='#1e1e1e')
        domain_frame.pack(side=tk.RIGHT, padx=40, pady=10)
        tk.Label(domain_frame, text="Profile:", bg='#1e1e1e', fg='#aaaaaa', font=('Arial', 9)).pack(side='left')
        self.domain_var = tk.StringVar(value="home")
        self.domain_menu = ttk.Combobox(domain_frame, textvariable=self.domain_var, 
                                        values=["home", "office", "industrial"], width=10, state="readonly")
        self.domain_menu.pack(side='left', padx=5)
        self.domain_menu.bind("<<ComboboxSelected>>", self.on_domain_change)
        
        # Main content area - Responsive Grid
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure grid columns: Video gets more weight (4/5) than Info (1/5)
        main_frame.grid_columnconfigure(0, weight=4)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        
        # Left panel - Video feed
        left_panel = tk.Frame(main_frame, bg='#2b2b2b')
        left_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # Video display
        video_frame = tk.Frame(left_panel, bg='#1e1e1e', relief=tk.RAISED, bd=2)
        video_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        video_label_frame = tk.Label(video_frame, 
                                    text="📹 Live Camera Feed",
                                    bg='#1e1e1e',
                                    fg='#4CAF50',
                                    font=('Arial', 12, 'bold'))
        video_label_frame.pack(pady=5)
        
        self.video_label = tk.Label(video_frame, 
                                    bg='#000000',
                                    text="Camera feed will appear here...")
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status panel
        status_panel = tk.Frame(left_panel, bg='#1e1e1e', relief=tk.RAISED, bd=2)
        status_panel.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(status_panel,
                text="⚡ System Status",
                bg='#1e1e1e',
                fg='#4CAF50',
                font=('Arial', 11, 'bold')).pack(pady=5)
        
        self.status_text = tk.Label(status_panel,
                                   text="System Ready",
                                   bg='#1e1e1e',
                                   fg='#ffffff',
                                   font=('Arial', 10))
        self.status_text.pack(pady=2)
        
        self.camera_status_label = tk.Label(status_panel,
                                            text="Camera: Checking...",
                                            bg='#1e1e1e',
                                            fg='#FFC107',
                                            font=('Arial', 9))
        self.camera_status_label.pack(pady=2)
        
        # Right panel - Information dashboard
        right_panel = tk.Frame(main_frame, bg='#2b2b2b')
        right_panel.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(right_panel)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Detection tab
        detection_tab = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(detection_tab, text="👥 Detection")
        self._create_detection_tab(detection_tab)
        
        # Environment tab
        env_tab = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(env_tab, text="🌡️ Environment")
        self._create_environment_tab(env_tab)
        
        # Energy tab
        energy_tab = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(energy_tab, text="⚡ Energy")
        self._create_energy_tab(energy_tab)
        
        # Appliances tab
        appliances_tab = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(appliances_tab, text="🔌 Appliances")
        self._create_appliances_tab(appliances_tab)
        
        # Logs tab
        logs_tab = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(logs_tab, text="📋 Logs")
        self._create_logs_tab(logs_tab)
    
    def _create_detection_tab(self, parent):
        """Create detection information tab"""
        # Human detection
        human_frame = tk.LabelFrame(parent, text="Human Detection", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        human_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.human_count_label = tk.Label(human_frame,
                                          text="Count: 0",
                                          bg='#2b2b2b',
                                          fg='#4CAF50',
                                          font=('Arial', 12, 'bold'))
        self.human_count_label.pack(pady=5)
        
        # Animal detection
        animal_frame = tk.LabelFrame(parent, text="Animal Detection", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        animal_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.animal_count_label = tk.Label(animal_frame,
                                           text="Count: 0",
                                           bg='#2b2b2b',
                                           fg='#2196F3',
                                           font=('Arial', 12, 'bold'))
        self.animal_count_label.pack(pady=5)
        
        # Pose analysis
        pose_frame = tk.LabelFrame(parent, text="Pose & Motion", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        pose_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.motion_label = tk.Label(pose_frame,
                                     text="Motion Level: 0.0",
                                     bg='#2b2b2b',
                                     fg='#ffffff',
                                     font=('Arial', 10))
        self.motion_label.pack(pady=2)
        
        self.activity_label = tk.Label(pose_frame,
                                       text="Activity: None",
                                       bg='#2b2b2b',
                                       fg='#ffffff',
                                       font=('Arial', 10))
        self.activity_label.pack(pady=2)

        # Audio Detection
        audio_frame = tk.LabelFrame(parent, text="Audio Analysis", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        audio_frame.pack(fill=tk.X, padx=10, pady=5)
        self.sound_label = tk.Label(audio_frame, text="Sound Level: 0.0 dB", bg='#2b2b2b', fg='#00BCD4', font=('Arial', 10))
        self.sound_label.pack(pady=5)
        
        # Occupancy status
        occupancy_frame = tk.LabelFrame(parent, text="Occupancy", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        occupancy_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.occupancy_label = tk.Label(occupancy_frame,
                                        text="Status: Unoccupied",
                                        bg='#2b2b2b',
                                        fg='#FFC107',
                                        font=('Arial', 11, 'bold'))
        self.occupancy_label.pack(pady=10) # Increased padding
    
    def _create_environment_tab(self, parent):
        """Create environment monitoring tab"""
        # Brightness
        brightness_frame = tk.LabelFrame(parent, text="Brightness", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        brightness_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.brightness_value_label = tk.Label(brightness_frame,
                                               text="Level: 0",
                                               bg='#2b2b2b',
                                               fg='#FFC107',
                                               font=('Arial', 11, 'bold'))
        self.brightness_value_label.pack(pady=(10, 5))
        
        self.brightness_status_label = tk.Label(brightness_frame,
                                                text="Status: Optimal",
                                                bg='#2b2b2b',
                                                fg='#ffffff',
                                                font=('Arial', 10))
        self.brightness_status_label.pack(pady=(0, 10))
        
        # Airflow
        airflow_frame = tk.LabelFrame(parent, text="Airflow", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        airflow_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.airflow_value_label = tk.Label(airflow_frame,
                                            text="Value: 0.0 m/s",
                                            bg='#2b2b2b',
                                            fg='#00BCD4',
                                            font=('Arial', 11, 'bold'))
        self.airflow_value_label.pack(pady=(10, 5))
        
        self.airflow_status_label = tk.Label(airflow_frame,
                                             text="Status: Optimal",
                                             bg='#2b2b2b',
                                             fg='#ffffff',
                                             font=('Arial', 10))
        self.airflow_status_label.pack(pady=(0, 10))
    
    def _create_energy_tab(self, parent):
        """Create energy management tab"""
        # Energy consumption
        energy_frame = tk.LabelFrame(parent, text="Energy Consumption", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        energy_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.total_energy_label = tk.Label(energy_frame,
                                           text="Total: 0.0 kWh",
                                           bg='#2b2b2b',
                                           fg='#4CAF50',
                                           font=('Arial', 11, 'bold'))
        self.total_energy_label.pack(pady=2)
        
        self.cost_label = tk.Label(energy_frame,
                                   text="Cost: $0.00",
                                   bg='#2b2b2b',
                                   fg='#ffffff',
                                   font=('Arial', 10))
        self.cost_label.pack(pady=2)
        
        self.savings_label = tk.Label(energy_frame,
                                      text="Savings: $0.00",
                                      bg='#2b2b2b',
                                      fg='#4CAF50',
                                      font=('Arial', 10))
        self.savings_label.pack(pady=2)
        
        # Device controls
        controls_frame = tk.LabelFrame(parent, text="Device Controls", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.lights_label = tk.Label(controls_frame,
                                     text="Lights: Off",
                                     bg='#2b2b2b',
                                     fg='#ffffff',
                                     font=('Arial', 10))
        self.lights_label.pack(pady=2)
        
        self.ventilation_label = tk.Label(controls_frame,
                                          text="Ventilation: Off",
                                          bg='#2b2b2b',
                                          fg='#ffffff',
                                          font=('Arial', 10))
        self.ventilation_label.pack(pady=2)
        
        # Recommendations
        recommendations_frame = tk.LabelFrame(parent, text="Recommendations", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        recommendations_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.recommendations_text = scrolledtext.ScrolledText(recommendations_frame,
                                                              bg='#1e1e1e',
                                                              fg='#ffffff',
                                                              font=('Arial', 9),
                                                              wrap=tk.WORD,
                                                              height=8)
        self.recommendations_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _create_appliances_tab(self, parent):
        """Create appliances status tab"""
        # Light
        light_frame = tk.LabelFrame(parent, text="Light", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        light_frame.pack(fill=tk.X, padx=10, pady=5)
        self.appliance_light_label = tk.Label(light_frame, text="Status: Off", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10))
        self.appliance_light_label.pack(pady=5)
        
        # Fan
        fan_frame = tk.LabelFrame(parent, text="Fan", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        fan_frame.pack(fill=tk.X, padx=10, pady=5)
        self.appliance_fan_label = tk.Label(fan_frame, text="Status: Off", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10))
        self.appliance_fan_label.pack(pady=5)
        
        # AC
        ac_frame = tk.LabelFrame(parent, text="AC", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10, 'bold'))
        ac_frame.pack(fill=tk.X, padx=10, pady=5)
        self.appliance_ac_label = tk.Label(ac_frame, text="Status: Off", bg='#2b2b2b', fg='#ffffff', font=('Arial', 10))
        self.appliance_ac_label.pack(pady=5)
    
    def _create_logs_tab(self, parent):
        """Create logs tab"""
        logs_text = scrolledtext.ScrolledText(parent,
                                              bg='#1e1e1e',
                                              fg='#00ff00',
                                              font=('Consolas', 9),
                                              wrap=tk.WORD)
        logs_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.logs_text = logs_text
    
    def open_dashboard(self):
        """Open a premium dashboard window with custom charts and modern styling"""
        dash_win = tk.Toplevel(self.root)
        dash_win.title("Smart Home | Executive Overview")
        dash_win.geometry("850x700")
        dash_win.configure(bg='#121212') # Deep midnight background
        dash_win.transient(self.root)
        
        # Premium Colors
        colors = {
            'bg': '#121212',
            'card': '#1e1e1e',
            'accent': '#10B981', # Emerald
            'blue': '#3B82F6',   # Sapphire
            'amber': '#F59E0B',  # Amber
            'rose': '#EF4444',   # Rose
            'text': '#E5E7EB',
            'dim': '#9CA3AF'
        }

        # Header with Gradient-like effect label
        header_frame = tk.Frame(dash_win, bg=colors['bg'])
        header_frame.pack(fill='x', pady=(30, 10))
        
        tk.Label(header_frame, text="SYSTEM INTELLIGENCE OVERVIEW", 
                 bg=colors['bg'], fg=colors['accent'], font=('Arial', 18, 'bold')).pack()
        
        # Main Dashboard Grid
        grid_container = tk.Frame(dash_win, bg=colors['bg'])
        grid_container.pack(expand=True, fill='both', padx=30, pady=20)
        
        # Define 4 quadrants (Cards)
        # 1. Detection Card
        det_card = self._create_premium_card(grid_container, "DETECTION ENGINE", 0, 0, colors['blue'])
        # 2. Environment Card
        env_card = self._create_premium_card(grid_container, "CLIMATE & LIGHT", 0, 1, colors['amber'])
        # 3. Energy Card
        nrg_card = self._create_premium_card(grid_container, "POWER EFFICIENCY", 1, 0, colors['accent'])
        # 4. Analytics Card (Chart Area)
        chart_card = self._create_premium_card(grid_container, "LIVE ANALYTICS", 1, 1, colors['rose'])

        # Populate Detection
        self.dash_elements = {}
        self.dash_elements['humans'] = self._add_stat(det_card, "People Identified", "0", colors)
        self.dash_elements['animals'] = self._add_stat(det_card, "Animals Spotted", "0", colors)
        self.dash_elements['sound'] = self._add_stat(det_card, "Audio Presence", "QUIET", colors)
        
        # Populate Environment
        self.dash_elements['bright_val'] = self._add_stat(env_card, "Lumen Intensity", "0", colors)
        self.dash_elements['airflow'] = self._add_stat(env_card, "Air Velocity", "0.0 m/s", colors)
        
        # SUSTAINABILITY REPORT inside Environment
        tk.Frame(env_card, bg=colors['dim'], height=1).pack(fill='x', pady=10)
        tk.Label(env_card, text="SUSTAINABILITY REPORT", bg=colors['card'], fg=colors['dim'], font=('Arial', 8, 'bold')).pack(anchor='w')
        self.dash_elements['carbon'] = self._add_stat(env_card, "CO2 Emission", "0.0 kg", colors)

        # Populate Energy
        self.dash_elements['energy'] = self._add_stat(nrg_card, "Net Consumption", "0 kWh", colors)
        self.dash_elements['cost'] = self._add_stat(nrg_card, "Projected Cost", "$0.00", colors)
        self.dash_elements['savings'] = self._add_stat(nrg_card, "Green Savings", "$0.00", colors)

        # Populate Chart Card - Custom Canvas Bars
        tk.Label(chart_card, text="Motion vs Energy Ratio", bg=colors['card'], fg=colors['dim'], font=('Arial', 9)).pack(pady=(0, 5))
        self.chart_canvas = tk.Canvas(chart_card, width=300, height=120, bg=colors['card'], highlightthickness=0)
        self.chart_canvas.pack(pady=10)
        
        # Footer
        footer = tk.Label(dash_win, text="Data points refreshed in real-time", 
                         bg=colors['bg'], fg=colors['dim'], font=('Arial', 8, 'italic'))
        footer.pack(side='bottom', pady=10)

        def safe_update():
            if not dash_win.winfo_exists():
                return
            try:
                self._update_premium_dash_data()
                self._draw_luxury_charts(colors)
                dash_win.after(1000, safe_update)
            except Exception:
                pass # Window probably closed during process
                
        safe_update()

    def _create_premium_card(self, parent, title, row, col, accent):
        """Create a stylish card container for the dashboard"""
        card = tk.Frame(parent, bg='#1e1e1e', padx=15, pady=15, relief='flat', highlightbackground='#333333', highlightthickness=1)
        card.grid(row=row, column=col, sticky='nsew', padx=10, pady=10)
        parent.grid_columnconfigure(col, weight=1)
        parent.grid_rowconfigure(row, weight=1)
        
        # Card Header
        header = tk.Frame(card, bg='#1e1e1e')
        header.pack(fill='x', pady=(0, 10))
        tk.Frame(header, bg=accent, width=4, height=15).pack(side='left', padx=(0, 8))
        tk.Label(header, text=title, bg='#1e1e1e', fg=accent, font=('Arial', 10, 'bold')).pack(side='left')
        
        return card

    def _add_stat(self, card, label, default, colors):
        """Add a stat row to a card"""
        row = tk.Frame(card, bg='#1e1e1e')
        row.pack(fill='x', pady=4)
        tk.Label(row, text=label, bg='#1e1e1e', fg=colors['dim'], font=('Arial', 9)).pack(side='left')
        val_lbl = tk.Label(row, text=default, bg='#1e1e1e', fg=colors['text'], font=('Arial', 11, 'bold'))
        val_lbl.pack(side='right')
        return val_lbl

    def _draw_luxury_charts(self, colors):
        """Draw animated bars on canvas"""
        if not hasattr(self, 'chart_canvas'): return
        canv = self.chart_canvas
        canv.delete("all")
        
        # Sample data derived from GUI states
        try:
            motion_val = float(self.motion_label.cget("text").split(":")[1].strip())
            # Normalize to 0-1
            motion_h = int(motion_val * 100)
        except: motion_h = 10
            
        try:
            # Simple heuristic for "load" bar
            energy_val = float(self.total_energy_label.cget("text").split(":")[1].split(" ")[0].strip())
            energy_h = min(100, int(energy_val * 500)) # Scaled for visibility
        except: energy_h = 30

        # Motion Bar
        self._draw_fancy_bar(canv, 50, 110, motion_h, colors['blue'], "MOTION")
        # Energy Bar
        self._draw_fancy_bar(canv, 150, 110, energy_h, colors['accent'], "POWER")
        # Savings Indicator
        self._draw_fancy_bar(canv, 250, 110, 80 if "ON" in self._get_entire_status_text() else 20, colors['amber'], "EFFICIENCY")

    def _draw_fancy_bar(self, canvas, x, y_base, height, color, label):
        """Draw a single stylized bar on canvas"""
        h = max(5, height) # min height
        # Neon Glow Effect (simulated with shadow)
        canvas.create_rectangle(x-12, y_base-h+2, x+12, y_base, fill='#000000', outline='')
        # Main bar
        canvas.create_rectangle(x-10, y_base-h, x+10, y_base, fill=color, outline='', width=0)
        # Top cap
        canvas.create_rectangle(x-10, y_base-h, x+10, y_base-h+4, fill='#ffffff', stipple='gray50', outline='')
        # Label
        canvas.create_text(x, y_base + 10, text=label, fill='#9CA3AF', font=('Arial', 7, 'bold'))

    def _update_premium_dash_data(self):
        """Sync main app data to dashboard labels"""
        if not hasattr(self, 'dash_elements'): return
        
        # Mapping from GUI labels to Dashboard keys
        mappings = {
            'humans': (self.human_count_label, ""),
            'animals': (self.animal_count_label, ""),
            'sound': (self.sound_label, "QUIET"),
            'bright_val': (self.brightness_value_label, "0"),
            'airflow': (self.airflow_value_label, "0.0 m/s"),
            'energy': (self.total_energy_label, "0.00 kWh"),
            'cost': (self.cost_label, "$0.00"),
            'savings': (self.savings_label, "$0.00")
        }
        
        # Special handling for carbon and audio
        data = self.data_callback()
        if 'energy_stats' in data:
            self.dash_elements['carbon'].config(text=f"{data['energy_stats'].get('carbon_footprint_kg', 0):.2f} KG")
        
        if 'audio_analysis' in data:
            status = data['audio_analysis'].get('status', 'QUIET')
            self.dash_elements['sound'].config(text=status.upper(), fg=('#EF4444' if status == 'Elevated' else '#9CA3AF'))
        
        status_info = self._get_entire_status_text()
        
        for key, (gui_lbl, default) in mappings.items():
            if key in self.dash_elements:
                try:
                    raw_text = gui_lbl.cget("text")
                    # Extract value part
                    if ":" in raw_text:
                        val = raw_text.split(":")[1].strip()
                        if not val: val = default
                    else:
                        val = raw_text if raw_text else default
                        
                    # Clean up common strings
                    if val.lower() == "occupied":
                        self.dash_elements[key].config(fg='#10B981')
                    elif val.lower() == "unoccupied":
                        self.dash_elements[key].config(fg='#EF4444')
                        
                    self.dash_elements[key].config(text=val.upper())
                except: pass

    def _get_entire_status_text(self):
        """Check status text for specific keywords"""
        try:
            return self.status_text.cget("text")
        except: return ""

    def on_domain_change(self, event=None):
        """Handle domain mode change"""
        new_mode = self.domain_var.get()
        # This will be picked up by main.py in the next update cycle
        # We'll pass it back via a custom field in data if needed, 
        # or main.py can check gui.domain_var.get()
        self.log_message(f"Profile switched to {new_mode.upper()}")

    def start_system(self):
        """Start the system"""
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_text.config(text="System Running", fg='#4CAF50')
        self.log_message("System started")
    
    def stop_system(self):
        """Stop the system"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_text.config(text="System Stopped", fg='#f44336')
        self.log_message("System stopped")
    
    def update_video_frame(self, frame):
        """Update video display with dynamic resizing to fit available space"""
        if frame is None:
            return
        
        # Get actual available space in the label
        # Use update_idletasks to get current dimensions if window just opened/resized
        try:
            display_width = self.video_label.winfo_width()
            display_height = self.video_label.winfo_height()
            
            # Fallback for initial load if dimensions are 1x1
            if display_width < 100 or display_height < 100:
                display_width, display_height = 640, 480
                
            # Maintain aspect ratio of the input frame
            h, w = frame.shape[:2]
            aspect_ratio = w / h
            
            if display_width / display_height > aspect_ratio:
                # Height is the limiting factor
                target_h = display_height - 10
                target_w = int(target_h * aspect_ratio)
            else:
                # Width is the limiting factor
                target_w = display_width - 10
                target_h = int(target_w / aspect_ratio)
            
            if target_w <= 0 or target_h <= 0:
                return
                
            frame_resized = cv2.resize(frame, (target_w, target_h))
        except Exception:
            # Simple fallback if sizing logic fails
            frame_resized = cv2.resize(frame, (640, 480))
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        
        self.video_label.config(image=imgtk)
        self.video_label.image = imgtk
    
    def update_display(self):
        """Update all display elements"""
        # Get current data
        data = self.data_callback()
        
        # Update camera status
        camera_available = data.get('camera_available', True)
        if camera_available:
            self.camera_status_label.config(text="Camera: ✓ Connected", fg='#4CAF50')
        else:
            self.camera_status_label.config(text="Camera: ✗ Not Available", fg='#f44336')
        
        if self.is_running:
            # Update detection info
            if 'detections' in data:
                human_count = len(data['detections'].get('humans', []))
                animal_count = len(data['detections'].get('animals', []))
                self.human_count_label.config(text=f"Count: {human_count}")
                self.animal_count_label.config(text=f"Count: {animal_count}")
            
            # Update pose/motion
            if 'pose_analysis' in data:
                motion = data['pose_analysis'].get('motion_level', 0.0)
                activity = data['pose_analysis'].get('activity_type', 'none')
                self.motion_label.config(text=f"Motion Level: {motion:.2f}")
                self.activity_label.config(text=f"Activity: {activity}")
            
            # Update brightness
            if 'brightness_analysis' in data:
                brightness = data['brightness_analysis'].get('mean_brightness', 0)
                status = data['brightness_analysis'].get('status', 'unknown')
                self.brightness_value_label.config(text=f"Level: {brightness:.0f}")
                self.brightness_status_label.config(text=f"Status: {status}")
            
            # Update airflow
            if 'airflow_analysis' in data:
                airflow = data['airflow_analysis'].get('airflow_value', 0.0)
                status = data['airflow_analysis'].get('status', 'unknown')
                self.airflow_value_label.config(text=f"Value: {airflow:.2f} m/s")
                self.airflow_status_label.config(text=f"Status: {status}")

            # Update sound
            if 'audio_analysis' in data:
                level = data['audio_analysis'].get('sound_level', 0)
                self.sound_label.config(text=f"Sound Level: {level:.1f} dB")
            
            # Update energy
            if 'energy_stats' in data:
                stats = data['energy_stats']
                self.total_energy_label.config(text=f"Total: {stats.get('total_energy_kwh', 0):.4f} kWh")
                self.cost_label.config(text=f"Cost: ${stats.get('total_cost_usd', 0):.2f}")
                self.savings_label.config(text=f"Savings: ${stats.get('estimated_savings_usd', 0):.2f}")
            
            # Update device controls
            if 'decisions' in data:
                decisions = data['decisions']
                self.lights_label.config(text=f"Lights: {decisions.get('lights', 'off')}")
                self.ventilation_label.config(text=f"Ventilation: {decisions.get('ventilation', 'off')}")
                occupancy = decisions.get('occupancy_status', 'unknown')
                self.occupancy_label.config(text=f"Status: {occupancy.title()}")
                
                # Update appliance tab labels
                if hasattr(self, 'appliance_light_label'):
                    self.appliance_light_label.config(text=f"Status: {str(decisions.get('lights', 'off')).title()}")
                if hasattr(self, 'appliance_fan_label'):
                    self.appliance_fan_label.config(text=f"Status: {str(decisions.get('ventilation', 'off')).title()}")
                if hasattr(self, 'appliance_ac_label'):
                    self.appliance_ac_label.config(text=f"Status: {str(decisions.get('ac', 'off')).title()}")
            
            # Update recommendations
            if 'recommendations' in data:
                self.recommendations_text.delete(1.0, tk.END)
                for rec in data['recommendations']:
                    self.recommendations_text.insert(tk.END, f"• {rec}\n")
        
        # Schedule next update
        self.root.after(self.update_interval, self.update_display)
    
    def log_message(self, message):
        """Add message to logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.logs_text.see(tk.END)

