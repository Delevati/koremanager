import os
import re
import subprocess
import threading
import psutil
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
from datetime import datetime
import logging
import queue
from collections import defaultdict

class BotManager:
    def __init__(self):
        self.start_time = time.time()
        self.BASE_DIR = ""
        self.BOT_FOLDERS = []
        self.bot_start_times = {}
        self.bot_last_uptimes = {}
        self.config_file = "bot_config.json"
        self.log_file = "bot_manager.log"
        self.log_regex_pattern = r"(Weight|card)"
        
        # Default settings
        self.config = {
            "base_directory": self.BASE_DIR,
            "bot_folders": self.BOT_FOLDERS.copy(),
            "restart_interval": 7200,
            "auto_restart": True,
            "start_minimized": False,
            "log_level": "INFO",
            "all_bots": self.BOT_FOLDERS.copy(),
            "capture_output": True
        }
        
        self.load_config()
        self.setup_logging()
        self.bot_processes = {}
        self.bot_outputs = defaultdict(list)  # Store bot outputs
        self.output_queues = {}  # Queues for bot outputs
        self.restart_timers = {}
        self.system_tray = None
        self.main_window = None
        self.selected_bot = None  # Currently selected bot in treeview
        self.bot_folder_entries = {}  # For setup tab
        self.tree_selection = []  # For multiple selection in treeview
        self.bot_process_objs = {}
        
    def setup_logging(self):
        logging.basicConfig(
            filename=self.log_file,
            filemode='w',
            level=getattr(logging, self.config["log_level"]),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
                    # Update class variables from config
                    self.BASE_DIR = self.config.get("base_directory", self.BASE_DIR)
                    self.BOT_FOLDERS = self.config.get("bot_folders", self.BOT_FOLDERS)
        except Exception as e:
            print(f"Error loading config: {e}")
            
    def save_config(self):
        try:
            # Update config with current values
            self.config["base_directory"] = self.BASE_DIR
            self.config["bot_folders"] = self.BOT_FOLDERS
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_exe_path(self, bot_folder):
        return os.path.join(self.BASE_DIR, bot_folder, f"start_{bot_folder}.exe")

    def get_start_path(self, bot_folder):
        return os.path.join(self.BASE_DIR, bot_folder, "start.exe")

    def capture_bot_output(self, bot_folder, process):
        """Capture bot output in a separate thread"""
        def read_output():
            try:
                while process.poll() is None:
                    output = process.stdout.readline()
                    if output:
                        decoded_output = output.strip()
                        if decoded_output:
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            formatted_output = f"[{timestamp}] {decoded_output}"
                            self.bot_outputs[bot_folder].append(formatted_output)
                            
                            # Keep only last 100 lines per bot
                            if len(self.bot_outputs[bot_folder]) > 100:
                                self.bot_outputs[bot_folder] = self.bot_outputs[bot_folder][-100:]
                            
                            # Add to queue for UI update
                            if bot_folder in self.output_queues:
                                try:
                                    self.output_queues[bot_folder].put(formatted_output, block=False)
                                except queue.Full:
                                    pass
            except Exception as e:
                self.logger.error(f"Error capturing output for {bot_folder}: {e}")
        
        if self.config.get("capture_output", True):
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()

    def start_log_tail(self, bot_folder, text_widget, regex_pattern=None):
        if regex_pattern is None:
            regex_pattern = self.log_regex_pattern
        log_path = os.path.join(self.BASE_DIR, bot_folder, "logs", "console.txt")
        def tail():
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    f.seek(0, os.SEEK_END)  # Começa do final do arquivo!
                    while text_widget.winfo_exists():
                        where = f.tell()
                        line = f.readline()
                        if not line:
                            time.sleep(1)
                            f.seek(where)
                        else:
                            if re.search(regex_pattern, line, re.IGNORECASE):
                                text_widget.insert("end", line)
                                text_widget.see("end")
            except Exception as e:
                self.logger.error(f"Error tailing log for {bot_folder}: {e}")

        t = threading.Thread(target=tail, daemon=True)
        t.start()

    def reset_bot_log(self, bot_folder, text_widget):
        log_path = os.path.join(self.BASE_DIR, bot_folder, "logs", "console.txt")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.truncate(0)
            text_widget.delete(1.0, "end")
            self.logger.info(f"Log reset for {bot_folder}")
        except Exception as e:
            self.logger.error(f"Error resetting log for {bot_folder}: {e}")

    def is_bot_running(self, bot_folder):
        exe_name = f"start_{bot_folder}.exe"
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == exe_name.lower():
                    self.bot_processes[bot_folder] = proc.info['pid']
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def start_bot(self, bot_folder, visible=False):
        try:
            if self.is_bot_running(bot_folder):
                self.logger.info(f"Bot {bot_folder} is already running")
                return False

            exe_path = self.get_exe_path(bot_folder)
            start_path = self.get_start_path(bot_folder)

            # Renomeia start.exe para start_<bot_folder>.exe se necessário
            if os.path.exists(start_path):
                if os.path.exists(exe_path):
                    os.remove(exe_path)  # Remove se já existir
                os.rename(start_path, exe_path)

            if not os.path.exists(exe_path):
                self.logger.error(f"Executable not found: {exe_path}")
                return False

            cwd = os.path.join(self.BASE_DIR, bot_folder)

            if visible:
                process = subprocess.Popen(
                    [exe_path],
                    cwd=cwd,
                    creationflags=0
                )
                self.bot_process_objs[bot_folder] = process
                console_mode = 'WINDOW'
            else:
                process = subprocess.Popen(
                    [exe_path],
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    text=True,
                    bufsize=1
                )
                self.bot_process_objs[bot_folder] = process
                self.capture_bot_output(bot_folder, process)
                console_mode = 'NO_WINDOW'

            self.bot_processes[bot_folder] = process.pid
            if not hasattr(self, 'bot_console_mode'):
                self.bot_console_mode = {}
            self.bot_console_mode[bot_folder] = console_mode
            self.output_queues[bot_folder] = queue.Queue(maxsize=50)
            # Renomeia de volta após 5 segundos
            threading.Timer(5, lambda: self.rename_back(exe_path, start_path)).start()
            self.logger.info(f"Bot {bot_folder} started with PID {process.pid}")

            # UPTIME: marca início e zera uptime congelado
            self.bot_start_times[bot_folder] = time.time()
            self.bot_last_uptimes[bot_folder] = 0

            if self.config["auto_restart"]:
                self.schedule_restart(bot_folder)

            return True

        except Exception as e:
            self.logger.error(f"Error starting bot {bot_folder}: {e}")
            return False

    def rename_back(self, exe_path, start_path):
        try:
            if os.path.exists(exe_path):
                os.rename(exe_path, start_path)
        except Exception as e:
            self.logger.error(f"Error renaming file: {e}")

    def kill_bot(self, bot_folder):
        try:
            exe_name = f"start_{bot_folder}.exe"
            killed = False

            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == exe_name.lower():
                        proc.kill()
                        killed = True
                        self.logger.info(f"Bot {bot_folder} terminated")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if bot_folder in self.bot_processes:
                del self.bot_processes[bot_folder]
            if bot_folder in self.restart_timers:
                self.restart_timers[bot_folder].cancel()
                del self.restart_timers[bot_folder]
            if bot_folder in self.output_queues:
                del self.output_queues[bot_folder]
            # Zera o modo do console ao parar o bot
            if hasattr(self, 'bot_console_mode') and bot_folder in self.bot_console_mode:
                del self.bot_console_mode[bot_folder]
            # UPTIME: congela o uptime ao parar
            if bot_folder in self.bot_start_times:
                self.bot_last_uptimes[bot_folder] = int(time.time() - self.bot_start_times[bot_folder])
                del self.bot_start_times[bot_folder]
            return killed

        except Exception as e:
            self.logger.error(f"Error terminating bot {bot_folder}: {e}")
            return False

    def kill_all_bots(self):
        killed_count = 0
        for bot_folder in self.config["all_bots"]:
            if self.kill_bot(bot_folder):
                killed_count += 1
        
        self.logger.info(f"{killed_count} bots terminated")
        return killed_count

    def restart_bot(self, bot_folder):
        self.kill_bot(bot_folder)
        time.sleep(2)
        return self.start_bot(bot_folder)

    def restart_all_bots(self):
        # Kill all bots first
        for bot_folder in self.config["all_bots"]:
            self.kill_bot(bot_folder)
        
        time.sleep(5)
        started_count = 0
        
        for bot_folder in self.config["all_bots"]:
            if self.start_bot(bot_folder):
                started_count += 1
                
        self.logger.info(f"{started_count} bots restarted")
        return started_count

    def schedule_restart(self, bot_folder):
        if not self.config["auto_restart"]:
            return
            
        if bot_folder in self.restart_timers:
            self.restart_timers[bot_folder].cancel()
            
        timer = threading.Timer(self.config["restart_interval"], 
                              lambda: self.restart_bot(bot_folder))
        timer.daemon = True
        timer.start()
        self.restart_timers[bot_folder] = timer

    def get_bot_status(self):
        status = {}
        for bot_folder in self.BOT_FOLDERS:
            running = self.is_bot_running(bot_folder)
            pid = self.bot_processes.get(bot_folder, None) if running else None
            mem = "-"
            cpu = "-"
            if running and pid:
                try:
                    proc = psutil.Process(pid)
                    mem = f"{proc.memory_info().rss // (1024*1024)} MB"
                    cpu = f"{proc.cpu_percent(interval=0.1):.1f}%"
                except Exception:
                    pass
            status[bot_folder] = {
                'running': running,
                'pid': pid,
                'selected': bot_folder in self.config["all_bots"],
                'mem': mem,
                'cpu': cpu
            }
        return status


    def create_tray_icon(self):
        # Create system tray icon
        img = Image.new('RGB', (64, 64), color='white')
        d = ImageDraw.Draw(img)
        d.ellipse((8, 8, 56, 56), fill='blue')
        d.text((20, 25), "BOT", fill='white')
        return img

    def show_main_window(self, icon=None, item=None):
        if self.main_window is None or not self.main_window.winfo_exists():
            self.create_main_window()
        else:
            self.main_window.deiconify()
            self.main_window.lift()

    def hide_to_tray(self):
        if self.main_window:
            self.main_window.withdraw()

    def on_closing(self):
        """Handle window closing properly"""
        try:
            # Kill all running bots
            self.kill_all_bots()
            
            # Stop system tray
            if self.system_tray:
                self.system_tray.stop()
            
            # Destroy main window
            if self.main_window:
                self.main_window.quit()
                self.main_window.destroy()
                
            # Force exit
            os._exit(0)
        except:
            os._exit(0)

    def update_timer(self):
        elapsed = int(time.time() - self.start_time)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        self.timer_label.config(text=f"Uptime: {h:02d}:{m:02d}:{s:02d}")
        if self.main_window and self.main_window.winfo_exists():
            self.main_window.after(1000, self.update_timer)

    def create_main_window(self):
        self.main_window = tk.Tk()
        self.main_window.title("Bot Manager")
        self.main_window.geometry("900x600")
        self.main_window.configure(bg='#2b2b2b')

        try:
            import sys
            if getattr(sys, 'frozen', False):
                # Executando como .exe
                icon_path = os.path.join(sys._MEIPASS, "emblem_2855.ico")
            else:
                # Executando como script
                icon_path = "emblem_2855.ico"
            self.main_window.iconbitmap(icon_path)
        except Exception as e:
            print(f"Erro ao definir ícone: {e}")

        self.timer_label = tk.Label(
            self.main_window,
            text="Uptime: 00:00:00",
            font=('Arial', 10, 'bold'),
            bg='#2b2b2b',
            fg='#ffffff'
        )
        self.timer_label.place(relx=1.0, rely=0.0, anchor='ne', x=-10, y=10)


        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'))
        
        # Main frame
        main_frame = ttk.Frame(self.main_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create tabs
        self.create_setup_tab()
        self.create_control_tab()
        self.create_terminals_tab()

        # Configure resizing
        self.main_window.columnconfigure(0, weight=1)
        self.main_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Bind events
        self.main_window.protocol("WM_DELETE_WINDOW", self.on_closing) 

        self.update_timer()

    def update_terminal_bots(self):
        running_bots = [b for b, mode in getattr(self, 'bot_console_mode', {}).items() if mode == 'NO_WINDOW' and self.is_bot_running(b)]
        for idx, var in enumerate(self.terminal_selectors):
            current = var.get()
            combo = self.terminal_combos[idx]
            combo['values'] = running_bots
            if current in running_bots:
                var.set(current)
            else:
                var.set('')

    def update_terminal_output(self, idx):
        pass

    def update_all_terminal_outputs(self):
        for i in range(3):
            self.update_terminal_output(i)
        self.update_terminal_bots()
        if self.main_window and self.main_window.winfo_exists():
            self.main_window.after(1000, self.update_all_terminal_outputs)

    def create_terminals_tab(self):
        terminals_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(terminals_frame, text="🖥️ Terminais")

        self.terminal_selectors = []
        self.terminal_texts = []
        self.terminal_combos = []

        for i in range(3):
            frame = ttk.LabelFrame(terminals_frame, text=f"Terminal {i+1}", padding="5")
            frame.grid(row=i, column=0, sticky=tk.N+tk.S+tk.E+tk.W, padx=5, pady=5)
            bot_var = tk.StringVar()
            combo = ttk.Combobox(frame, textvariable=bot_var, state="readonly", width=25)
            combo.pack(fill=tk.X, pady=2)
            self.terminal_selectors.append(bot_var)
            self.terminal_combos.append(combo)

            reset_btn = ttk.Button(frame, text="⟳", width=2, command=lambda idx=i: self.reset_bot_log(self.terminal_selectors[idx].get(), self.terminal_texts[idx]))
            reset_btn.place(relx=1.0, rely=0.0, anchor='ne', x=-5, y=5)

            text = tk.Text(frame, height=8, width=120, bg='#1e1e1e', fg='#00ff00', font=('Consolas', 9))
            text.pack(fill=tk.BOTH, expand=True)
            self.terminal_texts.append(text)

            # Conecte o callback ao evento de mudança do combobox
            def make_update_func(idx):
                def update_output(*args):
                    bot_name = self.terminal_selectors[idx].get()
                    text_widget = self.terminal_texts[idx]
                    if bot_name:
                        self.start_log_tail(bot_name, text_widget)
                return update_output
            bot_var.trace_add('write', make_update_func(i))

        terminals_frame.columnconfigure(0, weight=1)
        for i in range(3):
            terminals_frame.rowconfigure(i, weight=1)

        self.update_terminal_bots()
        self.update_all_terminal_outputs()

    def create_setup_tab(self):
        """Create setup/configuration tab"""
        setup_frame = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(setup_frame, text="🔧 Setup & Configuration")
        
        # Directory section - more compact layout
        dir_frame = ttk.Frame(setup_frame)
        dir_frame.grid(row=0, column=0, sticky=tk.W+tk.E, pady=(0, 10))
        
        ttk.Label(dir_frame, text="Main Directory:").grid(row=0, column=0, sticky=tk.W)
        
        self.base_dir_var = tk.StringVar(value=self.BASE_DIR)
        base_dir_entry = ttk.Entry(dir_frame, textvariable=self.base_dir_var, width=60)
        base_dir_entry.grid(row=0, column=1, padx=5, sticky=tk.W+tk.E)
        
        ttk.Button(dir_frame, text="Browse", 
                  command=self.browse_base_directory).grid(row=0, column=2, padx=5)
        
        ttk.Button(dir_frame, text="Scan", 
                  command=self.scan_bot_folders).grid(row=0, column=3, padx=5)
        
        ttk.Button(dir_frame, text="Save", 
                  command=self.save_base_directory).grid(row=0, column=4, padx=5)
        
        # Bot folders section
        bots_frame = ttk.LabelFrame(setup_frame, text="Bot Folders", padding="10")
        bots_frame.grid(row=1, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        
        # Header
        header = ttk.Frame(bots_frame)
        header.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(header, text="Folder Name", width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(header, text="Status", width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(header, text="Actions", width=10).pack(side=tk.LEFT, padx=5)
        
        # Scrollable area for bot entries
        bot_container = ttk.Frame(bots_frame)
        bot_container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(bot_container)
        scrollbar = ttk.Scrollbar(bot_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons
        btn_frame = ttk.Frame(bots_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="Add Bot", command=self.add_bot_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save Config", command=self.save_bot_configuration).pack(side=tk.LEFT, padx=5)
        
        # Load existing folders
        self.refresh_bot_folder_list()
        
        # Configure resizing
        setup_frame.columnconfigure(0, weight=1)
        setup_frame.rowconfigure(1, weight=1)
        bots_frame.columnconfigure(0, weight=1)

    def create_control_tab(self):
        control_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(control_frame, text="🎮 Bot Control")

        ctrl_frame = ttk.Frame(control_frame)
        ctrl_frame.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        ttk.Button(ctrl_frame, text="Start All", command=self.start_all_bots).grid(row=0, column=0, padx=5)
        ttk.Button(ctrl_frame, text="Stop All", command=self.stop_all_bots).grid(row=0, column=1, padx=5)
        ttk.Button(ctrl_frame, text="Restart All", command=self.restart_all_bots_ui).grid(row=0, column=2, padx=5)

        ttk.Label(ctrl_frame, text="Restart Interval (min):").grid(row=0, column=3, padx=5)
        self.restart_interval_var = tk.StringVar(value=str(self.config["restart_interval"] // 60))
        ttk.Entry(ctrl_frame, textvariable=self.restart_interval_var, width=8).grid(row=0, column=4, padx=2)

        self.auto_restart_var = tk.BooleanVar(value=self.config["auto_restart"])
        ttk.Checkbutton(ctrl_frame, text="Auto-restart", variable=self.auto_restart_var).grid(row=0, column=5, padx=5)

        self.capture_output_var = tk.BooleanVar(value=self.config.get("capture_output", True))
        ttk.Checkbutton(ctrl_frame, text="Capture Output", variable=self.capture_output_var).grid(row=0, column=6, padx=5)

        self.visible_bots_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl_frame, text="WINDOW", variable=self.visible_bots_var).grid(row=0, column=8, padx=5)

        ttk.Button(ctrl_frame, text="Save Settings", command=self.save_settings).grid(row=0, column=7, padx=5)

        tree_frame = ttk.LabelFrame(control_frame, text="Bot Status", padding="10")
        tree_frame.grid(row=1, column=0, sticky=tk.W+tk.E+tk.N+tk.S, columnspan=2)

        columns = ('Bot', 'Status', 'PID', 'Console', 'Memory', 'CPU', 'Uptime')
        self.bot_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=10)
        self.bot_tree.heading('Bot', text='Bot Name')
        self.bot_tree.heading('Status', text='Status')
        self.bot_tree.heading('PID', text='Process ID')
        self.bot_tree.heading('Console', text='Console')
        self.bot_tree.heading('Memory', text='Memory')
        self.bot_tree.heading('CPU', text='CPU')
        self.bot_tree.heading('Uptime', text='Uptime')

        self.bot_tree.column('Bot', width=120)
        self.bot_tree.column('Status', width=100)
        self.bot_tree.column('PID', width=80)
        self.bot_tree.column('Console', width=80)
        self.bot_tree.column('Memory', width=70)
        self.bot_tree.column('CPU', width=60)
        self.bot_tree.column('Uptime', width=90)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.bot_tree.yview)
        self.bot_tree.configure(yscrollcommand=scrollbar.set)
        self.bot_tree.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        action_frame = ttk.Frame(control_frame)
        action_frame.grid(row=2, column=0, sticky=tk.W, pady=(10, 0), columnspan=2)
        ttk.Button(action_frame, text="Start", command=self.start_selected_bot).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Stop", command=self.stop_selected_bot).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Restart", command=self.restart_selected_bot).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="View Output", command=self.view_bot_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Select All", command=self.select_all_bots).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Deselect All", command=self.deselect_all_bots).pack(side=tk.LEFT, padx=5)

        log_frame = ttk.LabelFrame(control_frame, text="System Logs", padding="10")
        log_frame.grid(row=3, column=0, sticky=tk.W+tk.E+tk.N+tk.S, pady=(10, 0), columnspan=2)
        self.log_text = tk.Text(log_frame, height=6, width=80, bg='#1e1e1e', fg='#ffffff')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        control_frame.columnconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.bot_tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.bot_tree.bind('<Control-Button-1>', self.on_ctrl_click)

        style = ttk.Style()
        style.map('Treeview', background=[('selected', '#347083')])

        self.update_bot_status()
        self.update_logs()
        self.schedule_status_update()
        self.enable_treeview_drag_and_drop()

    def enable_treeview_drag_and_drop(self):
        self.bot_tree.bind('<ButtonPress-1>', self.on_treeview_drag_start)
        self.bot_tree.bind('<B1-Motion>', self.on_treeview_drag_motion)
        self.bot_tree.bind('<ButtonRelease-1>', self.on_treeview_drag_release)
        self._dragging_item = None

    def on_treeview_drag_start(self, event):
        item = self.bot_tree.identify_row(event.y)
        if item:
            self._dragging_item = item

    def on_treeview_drag_motion(self, event):
        if not self._dragging_item:
            return
        target = self.bot_tree.identify_row(event.y)
        if target and target != self._dragging_item:
            idx_drag = self.bot_tree.index(self._dragging_item)
            idx_target = self.bot_tree.index(target)
            self.bot_tree.move(self._dragging_item, '', idx_target)
            # Atualize a ordem na lista BOT_FOLDERS também!
            bot_names = [self.bot_tree.item(i)['values'][0] for i in self.bot_tree.get_children()]
            self.BOT_FOLDERS = bot_names

    def on_treeview_drag_release(self, event):
        self._dragging_item = None
        self.save_config()  # Salva a nova ordem se quiser

    def browse_base_directory(self):
        """Browse for base directory"""
        directory = filedialog.askdirectory(initialdir=self.BASE_DIR)
        if directory:
            self.base_dir_var.set(directory)
            self.BASE_DIR = directory

    def scan_bot_folders(self):
        """Scan base directory and add found folders to list"""
        base_dir = self.base_dir_var.get()
        if not os.path.exists(base_dir):
            messagebox.showerror("Error", "Directory does not exist!")
            return

        self.BASE_DIR = base_dir
        
        try:
            # Clear current list
            self.BOT_FOLDERS = []
            
            # Find valid bot folders
            for folder in os.listdir(base_dir):
                folder_path = os.path.join(base_dir, folder)
                if os.path.isdir(folder_path):
                    exe_path = os.path.join(folder_path, f"start.exe")
                    if os.path.exists(exe_path):
                        self.BOT_FOLDERS.append(folder)
            
            # Refresh UI
            self.refresh_bot_folder_list()
            messagebox.showinfo("Scan Complete", f"Found {len(self.BOT_FOLDERS)} bot folders")
            
        except Exception as e:
            messagebox.showerror("Error", f"Scan failed: {str(e)}")

    def save_base_directory(self):
        """Save the base directory"""
        new_dir = self.base_dir_var.get()
        if not os.path.exists(new_dir):
            messagebox.showerror("Error", "Directory does not exist!")
            return
        
        self.BASE_DIR = new_dir
        self.save_config()
        messagebox.showinfo("Success", "Base directory saved successfully!")

    def refresh_bot_folder_list(self):
        """Refresh the bot folder configuration list"""
        # Clear existing entries
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.bot_folder_entries = {}
        
        # Add bot folder entries
        for i, bot_folder in enumerate(self.BOT_FOLDERS):
            self.add_bot_folder_row(i, bot_folder)
            
        self.enable_drag_and_drop()

    def enable_drag_and_drop(self):
        """Habilita drag and drop nos bot folders da aba de configuração"""
        for frame in self.scrollable_frame.winfo_children():
            frame.bind("<Button-1>", self.on_drag_start)
            frame.bind("<B1-Motion>", self.on_drag_motion)
            frame.bind("<ButtonRelease-1>", self.on_drag_release)

        self._drag_data = {"widget": None, "y": 0}

    def on_drag_start(self, event):
        widget = event.widget
        self._drag_data["widget"] = widget
        self._drag_data["y"] = event.y_root

    def on_drag_motion(self, event):
        widget = self._drag_data["widget"]
        if widget:
            dy = event.y_root - self._drag_data["y"]
            widget.place_configure(y=widget.winfo_y() + dy)
            self._drag_data["y"] = event.y_root

    def on_drag_release(self, event):
        widget = self._drag_data["widget"]
        if widget:
            # Descobre a nova posição
            widgets = list(self.scrollable_frame.winfo_children())
            widgets.sort(key=lambda w: w.winfo_y())
            new_order = []
            for w in widgets:
                entry = w.winfo_children()[0]
                folder_name = entry.get()
                if folder_name:
                    new_order.append(folder_name)
            self.BOT_FOLDERS = new_order
            self.refresh_bot_folder_list()
            self.enable_drag_and_drop()
        self._drag_data = {"widget": None, "y": 0}

    def add_bot_folder_row(self, row, bot_folder=""):
        frame = ttk.Frame(self.scrollable_frame)
        frame.grid(row=row, column=0, sticky=tk.W+tk.E, pady=2)

        entry_var = tk.StringVar(value=bot_folder)
        entry = ttk.Entry(frame, textvariable=entry_var, width=20)
        entry.grid(row=0, column=0, padx=5)

        status_label = ttk.Label(frame, text="", width=15)
        status_label.grid(row=0, column=1, padx=5)

        def update_status(*args):
            folder_name = entry_var.get()
            if folder_name:
                path = os.path.join(self.BASE_DIR, folder_name)
                if os.path.exists(path):
                    status_label.config(text="✅ Exists", foreground="green")
                else:
                    status_label.config(text="❌ Not Found", foreground="red")
            else:
                status_label.config(text="", foreground="black")
        entry_var.trace('w', update_status)
        update_status()

        action_frame = ttk.Frame(frame)
        action_frame.grid(row=0, column=2, padx=5)

        edit_btn = ttk.Button(action_frame, text="✏️", width=3,
            command=lambda: self.edit_bot_folder(entry_var))
        edit_btn.grid(row=0, column=2, padx=2)

        delete_btn = ttk.Button(action_frame, text="🗑️", width=3,
            command=lambda f=frame, bf=bot_folder: self.delete_bot_folder(f, bf))
        delete_btn.grid(row=0, column=3, padx=2)

        self.bot_folder_entries[bot_folder] = {
            'frame': frame,
            'entry': entry,
            'var': entry_var,
            'status': status_label
        }

    def edit_bot_folder(self, entry_var):
        """Edit bot folder name"""
        current_name = entry_var.get()
        new_name = simpledialog.askstring("Edit Bot Folder", 
                                         "Enter new folder name:", 
                                         initialvalue=current_name)
        if new_name and new_name != current_name:
            entry_var.set(new_name)

    def delete_bot_folder(self, frame, bot_folder):
        """Delete bot folder from configuration"""
        frame.destroy()
        if bot_folder in self.BOT_FOLDERS:
            self.BOT_FOLDERS.remove(bot_folder)
        if bot_folder in self.bot_folder_entries:
            del self.bot_folder_entries[bot_folder]

    def add_bot_folder(self):
        """Add a new bot folder entry"""
        new_row = len(self.scrollable_frame.winfo_children())
        self.add_bot_folder_row(new_row, "")

    def save_bot_configuration(self):
        """Save bot folder configuration"""
        # Collect all folder names from entries
        new_bot_folders = []
        for bot_folder, entry_data in self.bot_folder_entries.items():
            folder_name = entry_data['var'].get().strip()
            if folder_name and folder_name not in new_bot_folders:
                new_bot_folders.append(folder_name)
        
        # Add any new entries from empty rows
        for widget in self.scrollable_frame.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Entry):
                        folder_name = child.get().strip()
                        if folder_name and folder_name not in new_bot_folders:
                            new_bot_folders.append(folder_name)
        
        if not new_bot_folders:
            messagebox.showwarning("Warning", "No bot folders configured!")
            return
        
        self.BOT_FOLDERS = new_bot_folders
        self.config["all_bots"] = [bot for bot in new_bot_folders 
                                       if bot in self.config.get("all_bots", [])]
        self.save_config()
        
        # Refresh the control tab
        if hasattr(self, 'bot_tree'):
            self.update_bot_status()
        
        messagebox.showinfo("Success", f"Saved {len(new_bot_folders)} bot folders!")

    def on_tree_select(self, event):
        """Handle treeview selection"""
        self.tree_selection = []
        for item in self.bot_tree.selection():
            bot_name = self.bot_tree.item(item)['values'][0]
            self.tree_selection.append(bot_name)
            
        # Update button states
        self.update_action_buttons()

    def on_ctrl_click(self, event):
        """Handle Ctrl+click for multiple selection"""
        region = self.bot_tree.identify("region", event.x, event.y)
        if region == "cell":
            item = self.bot_tree.identify_row(event.y)
            if item in self.bot_tree.selection():
                self.bot_tree.selection_remove(item)
            else:
                self.bot_tree.selection_add(item)
            return "break"
        return None

    def update_action_buttons(self):
        """Update button states based on selection"""
        if not self.tree_selection:
            # No selection
            return
            
        # Check status of first selected bot
        bot_name = self.tree_selection[0]
        is_running = self.is_bot_running(bot_name)
        
        # Enable/disable buttons appropriately
        # (In a real implementation, you might want to handle multiple states)

    def select_all_bots(self):
        """Select all bots in treeview"""
        self.bot_tree.selection_set(self.bot_tree.get_children())
        self.tree_selection = [self.bot_tree.item(item)['values'][0] 
                              for item in self.bot_tree.get_children()]
        self.update_action_buttons()

    def deselect_all_bots(self):
        """Deselect all bots in treeview"""
        self.bot_tree.selection_remove(self.bot_tree.selection())
        self.tree_selection = []
        self.update_action_buttons()

    def start_selected_bot(self):
        if not self.tree_selection:
            return
        for bot_name in self.tree_selection:
            self.start_bot(bot_name, visible=self.visible_bots_var.get())
        self.update_bot_status()

    def stop_selected_bot(self):
        if not self.tree_selection:
            return
            
        for bot_name in self.tree_selection:
            self.kill_bot(bot_name)
        self.update_bot_status()

    def restart_selected_bot(self):
        if not self.tree_selection:
            return
            
        for bot_name in self.tree_selection:
            self.restart_bot(bot_name)
        self.update_bot_status()

    def view_bot_output(self):
        """Show bot output for the first selected bot"""
        if not self.tree_selection:
            return
            
        bot_name = self.tree_selection[0]
        output_window = tk.Toplevel(self.main_window)
        output_window.title(f"Bot Output: {bot_name}")
        output_window.geometry("500x400")
        output_window.transient(self.main_window)
        
        frame = ttk.Frame(output_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"Output for Bot: {bot_name}", 
                 font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Text widget for output
        output_text = tk.Text(frame, bg='#1e1e1e', fg='#00ff00', font=('Consolas', 9))
        output_text.pack(fill=tk.BOTH, expand=True)
        
        output_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=output_text.yview)
        output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        output_text.configure(yscrollcommand=output_scrollbar.set)
        
        # Load existing output
        if bot_name in self.bot_outputs:
            for line in self.bot_outputs[bot_name]:
                output_text.insert(tk.END, line + '\n')
        
        output_text.see(tk.END)
        
        # Real-time update function
        def update_output():
            if bot_name in self.output_queues:
                try:
                    while True:
                        line = self.output_queues[bot_name].get_nowait()
                        output_text.insert(tk.END, line + '\n')
                        output_text.see(tk.END)
                except queue.Empty:
                    pass
            
            if output_window.winfo_exists():
                output_window.after(1000, update_output)
        
        # Start real-time updates
        update_output()

    def start_all_bots(self):
        if not self.BOT_FOLDERS:
            messagebox.showwarning("Warning", "No bots found!")
            return
        started = 0
        for bot_name in self.BOT_FOLDERS:
            if self.start_bot(bot_name, visible=self.visible_bots_var.get()):
                started += 1
        self.update_bot_status()

    def stop_all_bots(self):
        if not self.BOT_FOLDERS:
            messagebox.showwarning("Warning", "No bots found!")
            return
        killed = 0
        for bot_name in self.BOT_FOLDERS:
            if self.kill_bot(bot_name):
                killed += 1
        messagebox.showinfo("Result", f"{killed} out of {len(self.BOT_FOLDERS)} bots stopped!")
        self.update_bot_status()

    def restart_all_bots_ui(self):
        if not self.BOT_FOLDERS:
            messagebox.showwarning("Warning", "No bots found!")
            return
        restarted = 0
        for bot_name in self.BOT_FOLDERS:
            if self.restart_bot(bot_name):
                restarted += 1
        messagebox.showinfo("Result", f"{restarted} out of {len(self.BOT_FOLDERS)} bots restarted successfully!")
        self.update_bot_status()

    def save_settings(self):
        try:
            # Converte minutos para segundos
            self.config["restart_interval"] = int(self.restart_interval_var.get()) * 60
            self.config["auto_restart"] = self.auto_restart_var.get()
            self.config["capture_output"] = self.capture_output_var.get()
            self.save_config()
            messagebox.showinfo("Success", "Settings saved successfully!")
        except ValueError:
            messagebox.showerror("Error", "Restart interval must be a number!")

    def update_bot_status(self):
        if not hasattr(self, 'bot_tree'):
            return

        selected_items = self.bot_tree.selection()
        all_bots = [self.bot_tree.item(item)['values'][0] for item in selected_items]

        for bot_folder in list(self.bot_process_objs.keys()):
            process = self.bot_process_objs.get(bot_folder)
            if process and process.poll() is not None:
                # Processo já morreu, remova do dict
                del self.bot_process_objs[bot_folder]
                if bot_folder in self.bot_processes:
                    del self.bot_processes[bot_folder]
                if hasattr(self, 'bot_console_mode') and bot_folder in self.bot_console_mode:
                    del self.bot_console_mode[bot_folder]
                # UPTIME: congela o uptime ao morrer
                if bot_folder in self.bot_start_times:
                    self.bot_last_uptimes[bot_folder] = int(time.time() - self.bot_start_times[bot_folder])
                    del self.bot_start_times[bot_folder]

        for item in self.bot_tree.get_children():
            self.bot_tree.delete(item)

        status = self.get_bot_status()
        for bot_name, info in status.items():
            status_text = "🟢 Running" if info['running'] else "🔴 Stopped"
            pid_text = str(info['pid']) if info['pid'] else "-"
            console_mode = getattr(self, 'bot_console_mode', {}).get(bot_name, '-')
            mem = info.get('mem', '-')
            cpu = info.get('cpu', '-')
            # UPTIME: calcula ao vivo se rodando, senão mostra congelado
            if info['running'] and bot_name in self.bot_start_times:
                elapsed = int(time.time() - self.bot_start_times[bot_name])
                uptime = elapsed
                self.bot_last_uptimes[bot_name] = uptime  # Atualiza o uptime congelado
            else:
                uptime = self.bot_last_uptimes.get(bot_name, 0)
            h = uptime // 3600
            m = (uptime % 3600) // 60
            s = uptime % 60
            uptime_str = f"{h:02d}:{m:02d}:{s:02d}" if uptime > 0 else "-"
            item = self.bot_tree.insert('', 'end', values=(bot_name, status_text, pid_text, console_mode, mem, cpu, uptime_str))
            if bot_name in all_bots:
                self.bot_tree.selection_add(item)

        self.update_action_buttons()

    def update_logs(self):
        if not hasattr(self, 'log_text'):
            return
            
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    # Show only last 50 lines
                    recent_lines = lines[-50:] if len(lines) > 50 else lines
                    
                    self.log_text.delete(1.0, tk.END)
                    self.log_text.insert(tk.END, ''.join(recent_lines))
                    self.log_text.see(tk.END)
        except Exception as e:
            pass

    def schedule_status_update(self):
        if self.main_window and self.main_window.winfo_exists():
            self.update_bot_status()
            self.update_logs()
            self.main_window.after(1000, self.schedule_status_update)

    def create_system_tray(self):
        menu = pystray.Menu(
            item('Open Interface', self.show_main_window),
            pystray.Menu.SEPARATOR,
            item('Start All Bots', lambda: self.start_all_bots()),
            item('Stop All Bots', lambda: self.stop_all_bots()),
            item('Restart All Bots', lambda: self.restart_all_bots_ui()),
            pystray.Menu.SEPARATOR,
            item('Exit', self.quit_application)
        )
        
        icon = pystray.Icon("BotManager", self.create_tray_icon(), "Bot Manager", menu)
        return icon

    def quit_application(self, icon=None, item=None):
        try:
            self.kill_all_bots()
            if self.system_tray:
                self.system_tray.stop()
            if self.main_window:
                self.main_window.quit()
                self.main_window.destroy()
            os._exit(0)
        except:
            os._exit(0)

    def run(self):
        # # Start selected bots if not configured to start minimized
        # if not self.config.get("start_minimized", False):
        #     for bot_folder in self.config["all_bots"]:
        #         if not self.is_bot_running(bot_folder):
        #             self.start_bot(bot_folder)
        
        # # Configure auto-restart if enabled
        # if self.config["auto_restart"]:
        #     for bot_folder in self.config["all_bots"]:
        #         self.schedule_restart(bot_folder)
        
        # Create and run interface
        if not self.config.get("start_minimized", False):
            self.create_main_window()
        
        # Create system tray icon
        self.system_tray = self.create_system_tray()
        
        # Run in separate thread if main window is visible
        if self.main_window:
            tray_thread = threading.Thread(target=self.system_tray.run, daemon=True)
            tray_thread.start()
            self.main_window.mainloop()
        else:
            self.system_tray.run()

def main():
    manager = BotManager()
    manager.run()

if __name__ == "__main__":
    main()