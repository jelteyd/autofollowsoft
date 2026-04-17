# start.py — Modernized Edition
import os
import sys
import subprocess

# Определяем базовый путь (для EXE и обычного режима)
if getattr(sys, 'frozen', False):
    # Запуск из EXE
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    APPLICATION_DIR = os.path.dirname(sys.executable)
    # Используем СИСТЕМНУЮ папку с браузерами (не временную)
    PLAYWRIGHT_BROWSERS_PATH = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ms-playwright')
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = PLAYWRIGHT_BROWSERS_PATH
else:
    # Обычный запуск
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APPLICATION_DIR = BASE_DIR
    PLAYWRIGHT_BROWSERS_PATH = ''

if os.name == 'nt':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import nest_asyncio
nest_asyncio.apply()

# НЕ импортируем playwright здесь - сделаем это ПОСЛЕ проверки браузеров!

# Функция для проверки и установки браузеров
def setup_playwright():
    """Проверяет и устанавливает Playwright браузеры"""
    browsers_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '')
    
    # Проверяем есть ли браузеры
    has_browsers = False
    if os.path.exists(browsers_path):
        try:
            for item in os.listdir(browsers_path):
                if 'chromium' in item.lower():
                    has_browsers = True
                    break
        except:
            pass
    
    if not has_browsers:
        print(f"⚠️ Playwright browsers not found")
        print("📍 Expected location:", browsers_path)
        print("🔧 You need to install them manually.\n")
        return False
    
    print(f"✅ Found browsers at: {browsers_path}")
    return True

# Проверяем браузеры при старте
browsers_ready = setup_playwright()

# ТЕПЕРЬ импортируем playwright (браузеры должны быть установлены)
import customtkinter as ctk
from tkinter import filedialog, messagebox
import logging

# Проверяем готовы ли браузеры и показываем окно если нет
if not browsers_ready:
    root_tmp = ctk.CTk()
    root_tmp.withdraw()
    messagebox.showerror(
        "❌ Браузеры не найдены",
        "❌ Playwright браузеры не установлены!\n\n"
        "Откройте Command Prompt (cmd) и выполните:\n"
        "  python -m playwright install chromium\n\n"
        "Или запустите файл: install-browsers-and-build.bat\n\n"
        "После установки перезапустите приложение."
    )
    root_tmp.destroy()
    sys.exit(1)

import json
import time
import random
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError
import threading
import shutil

from telegram_bot import TelegramBot

# ====================== ЦВЕТНЫЕ ЛОГИ ======================
class ColoredTextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        # Цветные теги
        self.text_widget.tag_config("success", foreground="#10b981")
        self.text_widget.tag_config("skip",    foreground="#f59e0b")
        self.text_widget.tag_config("error",   foreground="#ef4444")
        self.text_widget.tag_config("info",    foreground="#60a5fa")
        self.text_widget.tag_config("warning", foreground="#f97316")

    def emit(self, record):
        msg = self.format(record)
        tag = "info"
        lower = msg.lower()
        if any(k in lower for k in ["выполнен", "успех", "ok", "лайк", "follow выполнен", "поставлен", "✅"]):
            tag = "success"
        elif any(k in lower for k in ["пропуск", "уже followed", "слишком много", "удалена", "неактивен", "до 2025", "⛔"]):
            tag = "skip"
        elif any(k in lower for k in ["ошибка", "не работает", "не найдена", "failed", "timeout", "❌"]):
            tag = "error"
        elif any(k in lower for k in ["предупреждение", "warning", "⚠️"]):
            tag = "warning"

        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", msg + "\n", tag)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")


# ====================== НАСТРОЙКА ЛОГГИРОВАНИЯ ======================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PROCESSED_FILE = os.path.join(APPLICATION_DIR, 'processed.txt')
CONFIG_FILE = os.path.join(APPLICATION_DIR, 'config.json')
DAILY_STATS_FILE = os.path.join(APPLICATION_DIR, 'daily_stats.json')
BACKUP_DIR = os.path.join(APPLICATION_DIR, 'backups')

INVALID_COUNTRIES = [
    'Russia', 'Ukraine', 'Belarus', 'Kazakhstan', 'Armenia', 'Azerbaijan',
    'Kyrgyzstan', 'Moldova', 'Tajikistan', 'Turkmenistan', 'Uzbekistan', 'Georgia', 'Spain'
]

TELEGRAM_TOKEN = '8785779877:AAGItvylOnm3c_1WfJLkrK72Kbz-2j0d1pc'


class AutoFollowApp:
    def __init__(self):
        # Настройки темы
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("🚀 AutoFollow X — Premium Edition")
        self.root.geometry("1000x1100")
        self.root.resizable(True, True)
        
        # Современный градиентный фон
        self.root.configure(fg_color="#0f172a")

        # НАСТРОЙКИ
        self.likes_enabled = ctk.BooleanVar(value=True)
        self.country_check = ctk.BooleanVar(value=True)
        self.auto_backup = ctk.BooleanVar(value=True)

        # Создаемtabs
        self.tabview = ctk.CTkTabview(
            self.root,
            fg_color="#1e293b",
            segmented_button_fg_color="#334155",
            segmented_button_selected_color="#3b82f6",
            segmented_button_selected_hover_color="#2563eb"
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self.tabview.add("🏠 Главная")
        self.create_main_tab()

        self.tabview.add("⚙️ Настройки")
        self.create_settings_tab()

        self.tabview.add("📊 Статистика")
        self.create_stats_tab()

        # ПЕРЕМЕННЫЕ
        self.processed = self.load_processed()
        self.input_lines = []
        self.input_file_path = None
        self.cookies_path = None
        self.cookies_valid = False
        self.proxy = None
        self.browser = None
        self.context = None
        self.page = None

        self.session_processed_count = 0
        self.session_followed_count = 0

        self.is_running = False
        self.is_paused = False
        self.process_thread = None

        self.load_config()
        self.telegram_bot = TelegramBot(self, TELEGRAM_TOKEN)

        self.root.mainloop()

    def create_main_tab(self):
        tab = self.tabview.tab("🏠 Главная")
        
        # Главный контейнер с прокруткой
        main_frame = ctk.CTkScrollableFrame(tab, fg_color="#0f172a")
        main_frame.pack(fill="both", expand=True)

        # ЗАГОЛОВОК С ЛОГОТИПОМ
        header_frame = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=20)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title = ctk.CTkLabel(
            header_frame,
            text="🚀 AutoFollow X",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="#60a5fa"
        )
        title.pack(pady=(25, 5))
        
        subtitle = ctk.CTkLabel(
            header_frame,
            text="✨ Premium Automation Suite • 2025 Edition",
            font=ctk.CTkFont(size=16),
            text_color="#94a3b8"
        )
        subtitle.pack(pady=(0, 20))

        # СТАТУС-БАР (компактный)
        status_frame = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=15)
        status_frame.pack(fill="x", padx=20, pady=10)
        
        self.status_bar = ctk.CTkLabel(
            status_frame,
            text="🌐 Прокси: ✗  |  🍪 Cookies: ✗  |  🌍 Браузер: ✗",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ef4444",
            height=50
        )
        self.status_bar.pack(fill="x", padx=15, pady=10)

        # ИНДИКАТОР СТАТУСА (большой)
        self.big_status = ctk.CTkLabel(
            main_frame,
            text="⚡ Готов к запуску\nЗагрузите файл со строками",
            font=ctk.CTkFont(size=20, weight="bold"),
            justify="center",
            text_color="#cbd5e1",
            height=80
        )
        self.big_status.pack(pady=15)

        # ПРОГРЕСС-БАР
        prog_frame = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=15)
        prog_frame.pack(fill="x", padx=20, pady=10)
        
        self.progress = ctk.CTkProgressBar(prog_frame, height=30, corner_radius=10, fg_color="#334155", progress_color="#3b82f6")
        self.progress.pack(fill="x", padx=15, pady=(15, 5))
        self.progress.set(0)
        
        self.progress_label = ctk.CTkLabel(
            prog_frame,
            text="📊 0 / 0 (0%)",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.progress_label.pack(pady=(0, 15))

        # НАСТРОЙКИ (горизонтальная сетка)
        settings_frame = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=15)
        settings_frame.pack(fill="x", padx=20, pady=10)
        
        settings_title = ctk.CTkLabel(
            settings_frame,
            text="⚙️ Параметры",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#60a5fa"
        )
        settings_title.grid(row=0, column=0, columnspan=4, sticky="w", padx=20, pady=(15, 10))

        # Строка 1
        ctk.CTkLabel(settings_frame, text="⏱ Задержка (мин)", font=ctk.CTkFont(size=13)).grid(row=1, column=0, sticky="w", padx=20, pady=8)
        self.delay_entry = ctk.CTkEntry(settings_frame, width=100, height=35, corner_radius=8)
        self.delay_entry.insert(0, "3")
        self.delay_entry.grid(row=1, column=1, padx=10, pady=8)

        ctk.CTkLabel(settings_frame, text="👥 Макс. фолловеров", font=ctk.CTkFont(size=13)).grid(row=1, column=2, sticky="w", padx=10, pady=8)
        self.max_followers_entry = ctk.CTkEntry(settings_frame, width=100, height=35, corner_radius=8)
        self.max_followers_entry.insert(0, "5000")
        self.max_followers_entry.grid(row=1, column=3, padx=10, pady=8)

        # Строка 2
        ctk.CTkLabel(settings_frame, text="🔄 Follow перед отдыхом", font=ctk.CTkFont(size=13)).grid(row=2, column=0, sticky="w", padx=20, pady=8)
        self.follows_before_rest_entry = ctk.CTkEntry(settings_frame, width=100, height=35, corner_radius=8)
        self.follows_before_rest_entry.insert(0, "50")
        self.follows_before_rest_entry.grid(row=2, column=1, padx=10, pady=8)

        ctk.CTkLabel(settings_frame, text="😴 Время отдыха (мин)", font=ctk.CTkFont(size=13)).grid(row=2, column=2, sticky="w", padx=10, pady=8)
        self.rest_entry = ctk.CTkEntry(settings_frame, width=100, height=35, corner_radius=8)
        self.rest_entry.insert(0, "60")
        self.rest_entry.grid(row=2, column=3, padx=10, pady=8)

        # Строка 3
        ctk.CTkLabel(settings_frame, text="❤️ Мин. лайков", font=ctk.CTkFont(size=13)).grid(row=3, column=0, sticky="w", padx=20, pady=8)
        self.min_likes_entry = ctk.CTkEntry(settings_frame, width=100, height=35, corner_radius=8)
        self.min_likes_entry.insert(0, "0")
        self.min_likes_entry.grid(row=3, column=1, padx=10, pady=8)

        ctk.CTkLabel(settings_frame, text="❤️ Макс. лайков", font=ctk.CTkFont(size=13)).grid(row=3, column=2, sticky="w", padx=10, pady=8)
        self.max_likes_entry = ctk.CTkEntry(settings_frame, width=100, height=35, corner_radius=8)
        self.max_likes_entry.insert(0, "3")
        self.max_likes_entry.grid(row=3, column=3, padx=10, pady=8)

        # ПРОКСИ И COOKIES
        connection_frame = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=15)
        connection_frame.pack(fill="x", padx=20, pady=10)
        
        conn_title = ctk.CTkLabel(
            connection_frame,
            text="🔌 Подключения",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#60a5fa"
        )
        conn_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        ctk.CTkLabel(connection_frame, text="🌐 Прокси (http://user:pass@ip:port)", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(0, 5))
        self.proxy_entry = ctk.CTkEntry(connection_frame, height=40, corner_radius=8)
        self.proxy_entry.pack(fill="x", padx=20, pady=(0, 10))

        btn_row = ctk.CTkFrame(connection_frame, fg_color="transparent")
        btn_row.pack(pady=(0, 15))
        
        ctk.CTkButton(
            btn_row,
            text="✅ Проверить прокси",
            command=self.check_proxy,
            height=40,
            corner_radius=10,
            fg_color="#3b82f6",
            hover_color="#2563eb"
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_row,
            text="🍪 Проверить cookies",
            command=self.check_cookies,
            height=40,
            corner_radius=10,
            fg_color="#8b5cf6",
            hover_color="#7c3aed"
        ).pack(side="left", padx=10)

        # ГЛАВНЫЕ КНОПКИ
        controls_frame = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=15)
        controls_frame.pack(fill="x", padx=20, pady=10)
        
        ctrl_title = ctk.CTkLabel(
            controls_frame,
            text="🎮 Управление",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#60a5fa"
        )
        ctrl_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        btn_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        self.file_button = ctk.CTkButton(
            btn_frame,
            text="📂 Выбрать файл",
            command=self.load_file,
            height=50,
            width=180,
            corner_radius=12,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#6366f1",
            hover_color="#4f46e5"
        )
        self.file_button.grid(row=0, column=0, padx=10, pady=10)

        self.start_button = ctk.CTkButton(
            btn_frame,
            text="▶️ Старт",
            fg_color="#10b981",
            hover_color="#059669",
            command=self.start_process,
            height=50,
            width=160,
            corner_radius=12,
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.start_button.grid(row=0, column=1, padx=10, pady=10)

        self.pause_button = ctk.CTkButton(
            btn_frame,
            text="⏸ Пауза",
            fg_color="#f59e0b",
            hover_color="#d97706",
            command=self.toggle_pause,
            height=50,
            width=160,
            corner_radius=12,
            font=ctk.CTkFont(size=15, weight="bold"),
            state="disabled"
        )
        self.pause_button.grid(row=0, column=2, padx=10, pady=10)

        self.stop_button = ctk.CTkButton(
            btn_frame,
            text="⏹ Стоп",
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self.stop_process,
            height=50,
            width=160,
            corner_radius=12,
            font=ctk.CTkFont(size=15, weight="bold"),
            state="disabled"
        )
        self.stop_button.grid(row=0, column=3, padx=10, pady=10)

        # ЛОГИ
        log_frame = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=15)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        ctk.CTkLabel(
            log_frame,
            text="📜 Логи в реальном времени",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#60a5fa"
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.log_text = ctk.CTkTextbox(
            log_frame,
            height=250,
            corner_radius=10,
            fg_color="#0f172a",
            border_color="#334155",
            border_width=2
        )
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.log_text.configure(state="disabled")

        handler = ColoredTextHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

    def create_settings_tab(self):
        tab = self.tabview.tab("⚙️ Настройки")
        
        settings_scroll = ctk.CTkScrollableFrame(tab, fg_color="#0f172a")
        settings_scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(
            settings_scroll,
            text="⚙️ Дополнительные параметры",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#60a5fa"
        ).pack(pady=(30, 20))

        frame = ctk.CTkFrame(settings_scroll, fg_color="#1e293b", corner_radius=15)
        frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkSwitch(
            frame,
            text="❤️ Ставить лайки после follow",
            variable=self.likes_enabled,
            font=ctk.CTkFont(size=16),
            fg_color="#3b82f6"
        ).pack(anchor="w", pady=15, padx=20)
        
        ctk.CTkSwitch(
            frame,
            text="🌍 Проверять страну профиля",
            variable=self.country_check,
            font=ctk.CTkFont(size=16),
            fg_color="#3b82f6"
        ).pack(anchor="w", pady=15, padx=20)
        
        ctk.CTkSwitch(
            frame,
            text="💾 Авто-бэкап файла строк",
            variable=self.auto_backup,
            font=ctk.CTkFont(size=16),
            fg_color="#3b82f6"
        ).pack(anchor="w", pady=15, padx=20)

        ctk.CTkButton(
            settings_scroll,
            text="💾 Сохранить настройки",
            command=self.save_config,
            width=250,
            height=50,
            corner_radius=12,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669"
        ).pack(pady=40)

    def create_stats_tab(self):
        tab = self.tabview.tab("📊 Статистика")
        
        ctk.CTkLabel(
            tab,
            text="📊 Статистика за последнюю неделю",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#60a5fa"
        ).pack(pady=(30, 15))

        self.stats_frame = ctk.CTkScrollableFrame(tab, fg_color="#0f172a")
        self.stats_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.update_stats_button = ctk.CTkButton(
            tab,
            text="🔄 Обновить статистику",
            command=self.load_and_show_stats,
            width=220,
            height=45,
            corner_radius=10,
            fg_color="#3b82f6",
            hover_color="#2563eb"
        )
        self.update_stats_button.pack(pady=10)

        self.load_and_show_stats()

    def load_daily_stats(self):
        if os.path.exists(DAILY_STATS_FILE):
            try:
                with open(DAILY_STATS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def load_and_show_stats(self):
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        stats = self.load_daily_stats()
        today = datetime.now().date()
        total_p = total_f = 0

        for i in range(7):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            data = stats.get(day, {"processed": 0, "followed": 0})
            p = data["processed"]
            f = data["followed"]
            total_p += p
            total_f += f

            row = ctk.CTkFrame(self.stats_frame, fg_color="#1e293b", corner_radius=10)
            row.pack(fill="x", pady=5, padx=10)

            ctk.CTkLabel(row, text=day, width=120, anchor="w", font=ctk.CTkFont(weight="bold", size=14)).pack(side="left", padx=15, pady=10)
            ctk.CTkLabel(row, text=f"✅ Обработано: {p}", width=180, font=ctk.CTkFont(size=13)).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=f"👥 Follow: {f}", width=150, font=ctk.CTkFont(size=13), text_color="#10b981").pack(side="left", padx=5)

        summary = ctk.CTkFrame(self.stats_frame, fg_color="#1e293b", corner_radius=15)
        summary.pack(fill="x", pady=20, padx=10)
        ctk.CTkLabel(summary, text=f"🎯 ИТОГО ЗА 7 ДНЕЙ: {total_p} строк • {total_f} follow",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#60a5fa").pack(pady=15)

    def update_progress(self, current, total):
        if total == 0: return
        p = current / total
        self.root.after(0, lambda: self.progress.set(p))
        self.root.after(0, lambda: self.progress_label.configure(text=f"📊 {current} / {total} ({p*100:.1f}%)"))

    def update_big_status(self, text, color="#cbd5e1"):
        self.root.after(0, lambda: self.big_status.configure(text=text, text_color=color))

    def update_status_bar(self):
        p_ok = "✅" if self.proxy else "❌"
        c_ok = "✅" if self.cookies_valid else "❌"
        b_ok = "✅" if self.browser else "❌"
        text = f"🌐 Прокси: {p_ok}  |  🍪 Cookies: {c_ok}  |  🌍 Браузер: {b_ok}"
        color = "#10b981" if self.cookies_valid and self.proxy else "#ef4444"
        self.root.after(0, lambda t=text, col=color: self.status_bar.configure(text=t, text_color=col))

    def backup_input_file(self):
        if not self.input_file_path or not self.auto_backup.get():
            return
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(BACKUP_DIR, f"backup_{ts}.txt")
        shutil.copy(self.input_file_path, dest)
        logger.info(f"💾 Бэкап создан: {dest}")

    def load_config(self):
        logger.info("📂 Загрузка конфигурации")
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Load proxy
                proxy = config.get('proxy', '')
                if hasattr(self, 'proxy_entry'):
                    self.proxy_entry.delete(0, "end")
                    self.proxy_entry.insert(0, proxy)
                
                # Load cookies path
                self.cookies_path = config.get('cookies_path', None)
                
                # Load delays and settings
                if hasattr(self, 'delay_entry') and 'delay' in config:
                    self.delay_entry.delete(0, "end")
                    self.delay_entry.insert(0, str(config['delay']))
                
                if hasattr(self, 'max_followers_entry') and 'max_followers' in config:
                    self.max_followers_entry.delete(0, "end")
                    self.max_followers_entry.insert(0, str(config['max_followers']))
                
                if hasattr(self, 'follows_before_rest_entry') and 'follows_before_rest' in config:
                    self.follows_before_rest_entry.delete(0, "end")
                    self.follows_before_rest_entry.insert(0, str(config['follows_before_rest']))
                
                if hasattr(self, 'rest_entry') and 'rest_minutes' in config:
                    self.rest_entry.delete(0, "end")
                    self.rest_entry.insert(0, str(config['rest_minutes']))
                
                if hasattr(self, 'min_likes_entry') and 'min_likes' in config:
                    self.min_likes_entry.delete(0, "end")
                    self.min_likes_entry.insert(0, str(config['min_likes']))
                
                if hasattr(self, 'max_likes_entry') and 'max_likes' in config:
                    self.max_likes_entry.delete(0, "end")
                    self.max_likes_entry.insert(0, str(config['max_likes']))
                
                # Load boolean settings
                if hasattr(self, 'likes_enabled') and 'likes_enabled' in config:
                    self.likes_enabled.set(config['likes_enabled'])
                
                if hasattr(self, 'country_check') and 'country_check' in config:
                    self.country_check.set(config['country_check'])
                
                if hasattr(self, 'auto_backup') and 'auto_backup' in config:
                    self.auto_backup.set(config['auto_backup'])
                
                logger.info(f"✅ Конфигурация загружена: прокси={proxy}, cookies_path={self.cookies_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка при загрузке config.json: {e}")

    def save_config(self):
        logger.info("💾 Сохранение конфигурации")
        config = {
            'proxy': self.proxy_entry.get().strip() if hasattr(self, 'proxy_entry') else "",
            'cookies_path': self.cookies_path,
            'delay': self.delay_entry.get() if hasattr(self, 'delay_entry') else "3",
            'max_followers': self.max_followers_entry.get() if hasattr(self, 'max_followers_entry') else "5000",
            'follows_before_rest': self.follows_before_rest_entry.get() if hasattr(self, 'follows_before_rest_entry') else "50",
            'rest_minutes': self.rest_entry.get() if hasattr(self, 'rest_entry') else "60",
            'min_likes': self.min_likes_entry.get() if hasattr(self, 'min_likes_entry') else "0",
            'max_likes': self.max_likes_entry.get() if hasattr(self, 'max_likes_entry') else "3",
            'likes_enabled': self.likes_enabled.get() if hasattr(self, 'likes_enabled') else True,
            'country_check': self.country_check.get() if hasattr(self, 'country_check') else True,
            'auto_backup': self.auto_backup.get() if hasattr(self, 'auto_backup') else True,
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            logger.info("✅ Конфигурация сохранена")
            messagebox.showinfo("Успех", "✅ Настройки сохранены!")
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении config.json: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\n{str(e)}")

    def load_file(self):
        logger.info("📂 Выбор файла со строками")
        file_path = filedialog.askopenfilename(title="Выберите файл", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.input_lines = [line.strip() for line in f if line.strip()]
                self.input_file_path = file_path
                logger.info(f"✅ Загружено {len(self.input_lines)} строк из {file_path}")
                messagebox.showinfo("Успех", f"✅ Загружено {len(self.input_lines)} строк\n\nФайл: {file_path}")
                self.update_big_status(f"✅ Загружено {len(self.input_lines)} строк\nГотово к запуску!", "#10b981")
            except Exception as e:
                logger.error(f"❌ Ошибка при загрузке файла: {e}")
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{str(e)}")

    def remove_line_from_input(self, line):
        if not self.input_file_path:
            return
        try:
            with open(self.input_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            with open(self.input_file_path, 'w', encoding='utf-8') as f:
                for l in lines:
                    if l.strip() != line:
                        f.write(l)
            logger.info(f"🗑 Удалена строка: {line[:50]}...")
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении строки: {e}")

    def load_processed(self):
        if os.path.exists(PROCESSED_FILE):
            try:
                with open(PROCESSED_FILE, 'r', encoding='utf-8') as f:
                    return set(line.strip() for line in f)
            except:
                return set()
        return set()

    def save_processed(self, line):
        try:
            with open(PROCESSED_FILE, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
            self.processed.add(line)
            self.session_processed_count += 1
            logger.info(f"✅ Сохранена отработанная строка: {line[:50]}...")
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении processed: {e}")

    def parse_proxy(self, proxy_str):
        if not proxy_str or not proxy_str.strip():
            return None
        if proxy_str.startswith("http://"):
            proxy_str = proxy_str[7:]
        parts = proxy_str.split('@')
        if len(parts) == 2:
            auth, server = parts
            try:
                user, passw = auth.split(':')
                ip, port = server.split(':')
                return {
                    "server": f"http://{ip}:{port}",
                    "username": user,
                    "password": passw
                }
            except:
                return None
        return None

    def check_proxy(self):
        logger.info("🔍 Проверка прокси")
        proxy_str = self.proxy_entry.get().strip() if hasattr(self, 'proxy_entry') else ""
        if not proxy_str:
            messagebox.showwarning("Предупреждение", "⚠️ Прокси не указан.")
            return

        proxy = self.parse_proxy(proxy_str)
        if not proxy:
            messagebox.showerror("Ошибка", "❌ Неверный формат прокси\n\nИспользуйте: http://user:pass@ip:port")
            return

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(proxy=proxy)
                page = context.new_page()
                page.goto("http://httpbin.org/ip", timeout=25000)
                logger.info("✅ Прокси работает!")
                messagebox.showinfo("Успех", "✅ Прокси работает!")
                self.proxy = proxy
                self.update_status_bar()
                self.save_config()
                browser.close()
        except Exception as e:
            logger.error(f"❌ Ошибка проверки прокси: {e}")
            messagebox.showerror("Ошибка", f"❌ Прокси не работает:\n{str(e)[:200]}")
            self.proxy = None
            self.update_status_bar()

    def validate_cookies(self, cookies):
        validated = []
        for cookie in cookies:
            if isinstance(cookie, dict):
                same_site = cookie.get('sameSite')
                if isinstance(same_site, str):
                    lower = same_site.lower()
                    if lower == 'lax':
                        cookie['sameSite'] = 'Lax'
                    elif lower == 'strict':
                        cookie['sameSite'] = 'Strict'
                    else:
                        cookie['sameSite'] = 'None'
                else:
                    cookie['sameSite'] = 'None'
            validated.append(cookie)
        return validated

    def check_cookies(self):
        file_path = filedialog.askopenfilename(title="Выберите файл с cookies", filetypes=[("Text files", "*.txt"), ("JSON files", "*.json")])
        if not file_path:
            return
        self.check_cookies_with_path(file_path)

    def check_cookies_with_path(self, file_path):
        logger.info(f"🍪 Проверка cookies из {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                cookies_data = f.read().strip()
                cookies = json.loads(cookies_data)

            if not isinstance(cookies, list):
                raise ValueError("Cookies должны быть списком")

            cookies = self.validate_cookies(cookies)

            proxy_str = self.proxy_entry.get().strip() if hasattr(self, 'proxy_entry') else ""
            proxy = self.parse_proxy(proxy_str)

            with sync_playwright() as p:
                launch_options = {'proxy': proxy} if proxy else {}
                browser = p.chromium.launch(headless=False, **launch_options)
                context = browser.new_context(proxy=proxy)
                context.add_cookies(cookies)
                page = context.new_page()
                page.goto("https://x.com/home", timeout=30000)
                time.sleep(5)

                if page.query_selector('[data-testid="SideNav_NewTweet_Button"]'):
                    logger.info("✅ Cookies действительны!")
                    messagebox.showinfo("Успех", "✅ Cookies действительны!\nАккаунт залогинен!")
                    self.cookies_path = file_path
                    self.cookies_valid = True
                    self.save_config()
                    self.update_status_bar()
                else:
                    raise Exception("Аккаунт не залогинен")
                browser.close()
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке cookies: {e}")
            messagebox.showerror("Ошибка cookies", f"❌ Не удалось проверить cookies:\n{str(e)[:250]}")
            self.cookies_path = None
            self.cookies_valid = False
            self.update_status_bar()

    def parse_followers(self, text):
        try:
            num_str = text.strip().replace(',', '')
            if num_str.upper().endswith('K'):
                return int(float(num_str[:-1]) * 1000)
            elif num_str.upper().endswith('M'):
                return int(float(num_str[:-1]) * 1000000)
            return int(num_str)
        except:
            return float('inf')

    def get_country(self):
        try:
            pivot_locator = self.page.locator('div[data-testid="pivot"]', has_text="Account based in")
            country_elem = pivot_locator.locator('div > div:nth-child(2) > div:nth-child(2) > span')
            if country_elem.count() > 0:
                country = country_elem.inner_text().strip()
                logger.info(f"🌍 Страна: {country}")
                return country
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка при получении страны: {e}")
            return None

    def check_recent_tweets(self):
        """Проверка даты последних 2 твитов"""
        try:
            logger.info("🔍 Проверка даты последних 2 твитов...")
            self.page.wait_for_selector('article[data-testid="tweet"]', timeout=18000)
            posts = self.page.locator('article[data-testid="tweet"]').all()[:2]

            if len(posts) < 2:
                logger.warning("⚠️ Найдено меньше 2 твитов — профиль неактивен")
                return False

            years = []
            for i, post in enumerate(posts):
                time_elem = post.locator('time').first()
                if time_elem.count() > 0:
                    try:
                        dt_attr = time_elem.get_attribute('datetime', timeout=3000)
                        if dt_attr and len(dt_attr) >= 4:
                            year = int(dt_attr[:4])
                            years.append(year)
                            logger.info(f"📅 Твит #{i+1}: {dt_attr[:10]} (год {year})")
                    except Exception as te:
                        logger.warning(f"⚠️ Не удалось получить дату твита #{i+1}: {te}")

            if not years:
                return False

            if all(y < 2025 for y in years):
                logger.info("⛔ Последние 2 твита до 2025 года — удаляем строку")
                return False
            else:
                logger.info("✅ Есть хотя бы один твит 2025+ — продолжаем")
                return True

        except Exception as e:
            logger.error(f"❌ Ошибка при проверке дат твитов: {e}")
            return False

    def start_process(self):
        if self.is_running:
            messagebox.showwarning("Внимание", "⚠️ Процесс уже запущен!")
            return

        if not self.input_lines:
            messagebox.showerror("Ошибка", "❌ Сначала загрузите файл со строками!")
            return

        if not self.cookies_path:
            messagebox.showwarning("Предупреждение", "⚠️ Файл cookies не выбран!\nРабота без авторизации может быть ограничена.")
        elif not self.cookies_valid:
            messagebox.showwarning("Предупреждение", "⚠️ Cookies не проверены!\nРекомендуется проверить их перед запуском.")

        self.save_config()
        self.session_processed_count = 0
        self.session_followed_count = 0
        self.is_running = True
        self.is_paused = False
        self._set_button_states(False, True)
        self.update_big_status("🚀 Запуск процесса...\nПодготовка браузера", "#3b82f6")
        self.process_thread = threading.Thread(target=self.run_process, daemon=True)
        self.process_thread.start()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_button.configure(text="▶️ Продолжить", fg_color="#10b981", hover_color="#059669")
            self.update_big_status("⏸ Процесс на паузе", "#f59e0b")
            logger.info("⏸ Процесс на паузе")
        else:
            self.pause_button.configure(text="⏸ Пауза", fg_color="#f59e0b", hover_color="#d97706")
            self.update_big_status("▶️ Процесс возобновлен!", "#3b82f6")
            logger.info("▶️ Процесс возобновлен")

    def stop_process(self):
        self.is_running = False
        self.is_paused = False
        self._set_button_states(True, False)
        self.pause_button.configure(state="disabled")
        self.update_big_status("⏹ Процесс остановлен", "#ef4444")
        logger.info("⏹ Процесс остановлен пользователем")

    def _set_button_states(self, start_enabled=True, stop_enabled=False):
        self.root.after(0, lambda: self.start_button.configure(state="normal" if start_enabled else "disabled"))
        self.root.after(0, lambda: self.stop_button.configure(state="normal" if stop_enabled else "disabled"))
        self.root.after(0, lambda: self.pause_button.configure(state="normal" if stop_enabled else "disabled"))
        self.root.after(0, lambda: self.file_button.configure(state="normal" if start_enabled else "disabled"))

    def run_process(self):
        logger.info("🚀 run_process ЗАПУЩЕН — начинаем обработку")
        try:
            min_delay = int(self.delay_entry.get() or 3)
            max_followers = int(self.max_followers_entry.get() or 5000)
            follows_before_rest = int(self.follows_before_rest_entry.get() or 50)
            rest_minutes = int(self.rest_entry.get() or 60)
            proxy_str = self.proxy_entry.get().strip() if hasattr(self, 'proxy_entry') else ""
            self.proxy = self.parse_proxy(proxy_str)
            self.update_status_bar()

            if not self.cookies_path:
                logger.warning("⚠️ Cookies не выбраны — работа без авторизации")
            else:
                with open(self.cookies_path, 'r', encoding='utf-8') as f:
                    cookies_data = f.read()
                    cookies = json.loads(cookies_data)
                cookies = self.validate_cookies(cookies)

            with sync_playwright() as p:
                launch_options = {'proxy': self.proxy} if self.proxy else {}
                self.browser = p.chromium.launch(headless=False, **launch_options)
                self.context = self.browser.new_context(proxy=self.proxy)
                if self.cookies_path:
                    self.context.add_cookies(cookies)
                self.page = self.context.new_page()
                self.page.goto("https://x.com/home", timeout=60000)
                time.sleep(5)
                self.update_status_bar()

                total = len(self.input_lines)
                self.root.after(0, lambda: self.progress.set(0))

                follow_count = 0
                idx = 0
                while idx < len(self.input_lines) and self.is_running:
                    while self.is_paused:
                        time.sleep(1)
                    
                    line = self.input_lines[idx]

                    if line in self.processed:
                        logger.info(f"⏭ Пропуск отработанной строки: {line[:50]}...")
                        self.root.after(0, lambda v=idx+1: self.progress.set(v / total))
                        self.remove_line_from_input(line)
                        del self.input_lines[idx]
                        continue

                    parts = line.split()
                    if len(parts) < 2:
                        logger.warning(f"⚠️ Неверный формат строки: {line}")
                        self.remove_line_from_input(line)
                        del self.input_lines[idx]
                        continue
                    x_link = parts[1]

                    self.root.after(0, lambda link=x_link: self.update_big_status(f"🔄 Обработка профиля:\n{link}", "#3b82f6"))
                    logger.info(f"🔄 Обработка профиля: {x_link}")

                    try:
                        self.page.goto(x_link, timeout=60000)
                        self.page.wait_for_load_state("domcontentloaded", timeout=30000)
                    except TimeoutError:
                        logger.error(f"❌ Таймаут загрузки профиля {x_link} — пропускаем")
                        self.save_processed(line)
                        self.remove_line_from_input(line)
                        del self.input_lines[idx]
                        continue

                    time.sleep(8)

                    # Проверка даты твитов
                    if not self.check_recent_tweets():
                        logger.info(f"⛔ Пропуск неактивного профиля (твиты до 2025): {x_link}")
                        self.save_processed(line)
                        self.remove_line_from_input(line)
                        del self.input_lines[idx]
                        continue

                    followers = float('inf')
                    try:
                        followers_link = self.page.query_selector('a[href*="followers"]')
                        if followers_link:
                            full_text = followers_link.inner_text().strip()
                            num_part = full_text.split()[0]
                            followers = self.parse_followers(num_part)
                            logger.info(f"👥 Фолловеров: {followers} (найдено: {num_part})")
                    except Exception as e:
                        logger.error(f"❌ Ошибка при получении фолловеров: {e}")

                    if followers > max_followers:
                        logger.info(f"⏭ Пропуск: слишком много фолловеров ({followers} > {max_followers})")
                        self.save_processed(line)
                        self.remove_line_from_input(line)
                        del self.input_lines[idx]
                        continue

                    skip_profile = False
                    if self.country_check.get():
                        try:
                            join_date_elem = self.page.query_selector('[data-testid="UserJoinDate"]')
                            if join_date_elem:
                                join_date_elem.click()
                                time.sleep(5)
                                country = self.get_country()

                                if country is None or country.strip() == "":
                                    logger.info(f"🌍 Страна не найдена — удаляем строку")
                                    skip_profile = True
                                elif country in INVALID_COUNTRIES:
                                    logger.info(f"⏭ Пропуск: недопустимая страна {country}")
                                    skip_profile = True
                                else:
                                    logger.info(f"✅ Страна {country} — OK")
                            else:
                                logger.info(f"⚠️ Элемент даты не найден — страна не определена")
                                skip_profile = True

                            self.page.go_back()
                            time.sleep(5)
                        except Exception as e:
                            logger.error(f"❌ Ошибка при проверке страны: {e}")
                            skip_profile = True

                    if skip_profile:
                        self.save_processed(line)
                        self.remove_line_from_input(line)
                        del self.input_lines[idx]
                        continue

                    try:
                        follow_button = self.page.query_selector('[data-testid$="-follow"]')
                        if follow_button:
                            follow_button.click()
                            time.sleep(2)
                            logger.info(f"✅ Follow выполнен для {x_link}")
                            follow_count += 1
                            self.session_followed_count += 1

                            time.sleep(4)
                            num_likes = random.randint(int(self.min_likes_entry.get() or 0), int(self.max_likes_entry.get() or 3))
                            logger.info(f"❤️ Будем ставить {num_likes} случайных лайка(ов) на профиле {x_link}")

                            liked_count = 0
                            try:
                                self.page.wait_for_selector('article[data-testid="tweet"]', timeout=25000)
                                posts = self.page.locator('article[data-testid="tweet"]').all()[:6]

                                for i, post in enumerate(posts):
                                    if liked_count >= num_likes:
                                        break
                                    like_btn = post.locator('[data-testid="like"]')
                                    if like_btn.count() > 0 and like_btn.is_visible(timeout=3000):
                                        like_btn.click()
                                        time.sleep(random.uniform(1.8, 3.5))
                                        liked_count += 1
                                        logger.info(f"✅ Поставлен лайк #{liked_count}/{num_likes} на профиле {x_link}")
                            except Exception as like_err:
                                logger.error(f"❌ Ошибка при постановке лайков: {like_err}")

                            if follow_count >= follows_before_rest and rest_minutes > 0:
                                logger.info(f"😴 Отдых {rest_minutes} минут после {follows_before_rest} follow")
                                time.sleep(rest_minutes * 60)
                                follow_count = 0
                    except Exception as e:
                        logger.error(f"❌ Ошибка при follow: {e}")

                    self.save_processed(line)
                    self.remove_line_from_input(line)
                    self.root.after(0, lambda v=idx+1: self.progress.set(v / total))
                    idx += 1

                    if idx < len(self.input_lines) and self.is_running:
                        random_delay = random.randint(min_delay, min_delay + 2)
                        logger.info(f"⏳ Случайная задержка: {random_delay} минут (мин {min_delay})")
                        time.sleep(random_delay * 60)

                if self.browser:
                    try:
                        self.browser.close()
                    except:
                        pass
                self.context = None
                self.page = None
                self.update_status_bar()
                if self.is_running:
                    messagebox.showinfo("Завершено", "✅ Процесс завершен!")
                    self.update_big_status("✅ Процесс завершён успешно!", "#10b981")

            today = datetime.now().strftime("%Y-%m-%d")
            self.save_daily_stats(today, self.session_processed_count, self.session_followed_count)
            self.root.after(0, self.load_and_show_stats)

        except Exception as e:
            logger.error(f"❌ Критическая ошибка в run_process: {e}")
            self.root.after(0, lambda: messagebox.showerror("Критическая ошибка", str(e)))
            self.update_big_status(f"❌ Ошибка:\n{str(e)[:100]}", "#ef4444")
            if self.browser:
                try:
                    self.browser.close()
                except:
                    pass
            self.context = None
            self.page = None
            self.update_status_bar()
        finally:
            self.is_running = False
            self._set_button_states(True, False)
            self.pause_button.configure(state="disabled")

    def save_daily_stats(self, date, processed, followed):
        stats = self.load_daily_stats()
        stats[date] = {"processed": processed, "followed": followed}
        try:
            with open(DAILY_STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=4)
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении статистики: {e}")

if __name__ == "__main__":
    logger.info("🚀 Запуск приложения AutoFollow X")
    app = AutoFollowApp()
