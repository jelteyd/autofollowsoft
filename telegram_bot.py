# telegram_bot.py
import telebot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import threading
import logging

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, app, token):
        self.app = app
        self.bot = telebot.TeleBot(token)
        self.setup_handlers()
        threading.Thread(target=self.bot.infinity_polling, daemon=True).start()
        logger.info("🤖 Telegram bot запущен")

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def handle_start(message: Message):
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row(
                KeyboardButton("🚀 Запустить процесс"),
                KeyboardButton("⏸ Остановить процесс")
            )
            markup.row(
                KeyboardButton("⏸ Пауза"),
                KeyboardButton("▶️ Продолжить")
            )
            markup.row(
                KeyboardButton("📊 Статистика"),
                KeyboardButton("📥 Импорт строк")
            )
            self.bot.reply_to(
                message,
                "🎯 *Добро пожаловать в AutoFollow X!*\n\n"
                "Используй кнопки ниже для управления 👇\n\n"
                "📌 *Доступные команды:*\n"
                "/status - текущий статус\n"
                "/stats - подробная статистика\n"
                "/help - помощь",
                reply_markup=markup,
                parse_mode="Markdown"
            )

        @self.bot.message_handler(commands=['start_process', 'run'])
        def handle_start_process(message: Message):
            try:
                if self.app.is_running:
                    self.bot.reply_to(message, "⚠️ Процесс уже запущен!")
                    return
                
                # Запуск в основном потоке через after
                self.app.root.after(0, lambda: self._safe_start_process(message))
            except Exception as e:
                logger.error(f"Ошибка при запуске процесса: {e}")
                self.bot.reply_to(message, f"❌ Ошибка: {str(e)}")

        @self.bot.message_handler(commands=['stop_process', 'stop'])
        def handle_stop_process(message: Message):
            try:
                if not self.app.is_running:
                    self.bot.reply_to(message, "⚠️ Процесс не запущен!")
                    return
                
                self.app.root.after(0, lambda: self._safe_stop_process(message))
            except Exception as e:
                logger.error(f"Ошибка при остановке процесса: {e}")
                self.bot.reply_to(message, f"❌ Ошибка: {str(e)}")

        @self.bot.message_handler(commands=['pause'])
        def handle_pause(message: Message):
            try:
                if not self.app.is_running:
                    self.bot.reply_to(message, "⚠️ Процесс не запущен!")
                    return
                if self.app.is_paused:
                    self.bot.reply_to(message, "⚠️ Процесс уже на паузе!")
                    return
                
                self.app.root.after(0, lambda: self._safe_pause_process(message))
            except Exception as e:
                logger.error(f"Ошибка при паузе процесса: {e}")
                self.bot.reply_to(message, f"❌ Ошибка: {str(e)}")

        @self.bot.message_handler(commands=['resume', 'continue'])
        def handle_resume(message: Message):
            try:
                if not self.app.is_paused:
                    self.bot.reply_to(message, "⚠️ Процесс не на паузе!")
                    return
                
                self.app.root.after(0, lambda: self._safe_resume_process(message))
            except Exception as e:
                logger.error(f"Ошибка при возобновлении процесса: {e}")
                self.bot.reply_to(message, f"❌ Ошибка: {str(e)}")

        @self.bot.message_handler(commands=['status'])
        def handle_status(message: Message):
            status_text = self._get_status_text()
            self.bot.reply_to(message, status_text, parse_mode="Markdown")

        @self.bot.message_handler(commands=['stats', 'statistics'])
        def handle_stats(message: Message):
            stats_text = self._get_detailed_stats()
            self.bot.reply_to(message, stats_text, parse_mode="Markdown")

        @self.bot.message_handler(commands=['help'])
        def handle_help(message: Message):
            help_text = (
                "📖 *Доступные команды:*\n\n"
                "/start - Главное меню\n"
                "/run или /start_process - Запустить процесс\n"
                "/stop или /stop_process - Остановить процесс\n"
                "/pause - Пауза\n"
                "/resume или /continue - Продолжить\n"
                "/status - Текущий статус\n"
                "/stats - Подробная статистика\n"
                "/import - Импорт строк\n\n"
                "💡 *Совет:* Используйте кнопки в главном меню для быстрого доступа!"
            )
            self.bot.reply_to(message, help_text, parse_mode="Markdown")

        @self.bot.message_handler(commands=['import', 'import_lines'])
        def handle_import_lines_command(message: Message):
            self.bot.reply_to(
                message,
                "📥 *Импорт строк*\n\n"
                "Отправьте текст со строками (каждая с новой строки) или файл `.txt`",
                parse_mode="Markdown"
            )

        @self.bot.message_handler(commands=['set_follows_before_rest'])
        def handle_set_follows_before_rest(message: Message):
            try:
                parts = message.text.split()
                if len(parts) < 2:
                    raise ValueError("Укажите число")
                number = int(parts[1])
                if number <= 0:
                    raise ValueError("Число должно быть положительным")
                
                self.app.root.after(0, lambda: self._update_follows_before_rest(number, message))
            except ValueError as e:
                self.bot.reply_to(message, f"❌ Ошибка: {str(e)}\n\nИспользование: `/set_follows_before_rest <число>`", parse_mode="Markdown")

        # === ОБРАБОТКА КНОПОК ===
        @self.bot.message_handler(func=lambda m: m.text == "🚀 Запустить процесс")
        def handle_start_button(message: Message):
            handle_start_process(message)

        @self.bot.message_handler(func=lambda m: m.text == "⏸ Остановить процесс")
        def handle_stop_button(message: Message):
            handle_stop_process(message)

        @self.bot.message_handler(func=lambda m: m.text == "⏸ Пауза")
        def handle_pause_button(message: Message):
            handle_pause(message)

        @self.bot.message_handler(func=lambda m: m.text == "▶️ Продолжить")
        def handle_resume_button(message: Message):
            handle_resume(message)

        @self.bot.message_handler(func=lambda m: m.text == "📊 Статистика")
        def handle_stats_button(message: Message):
            handle_stats(message)

        @self.bot.message_handler(func=lambda m: m.text == "📥 Импорт строк")
        def handle_import_button(message: Message):
            handle_import_lines_command(message)

        # === ИМПОРТ ТЕКСТА ===
        @self.bot.message_handler(content_types=['text'])
        def handle_text_import(message: Message):
            if message.text.startswith('/'):
                return
            
            lines = [line.strip() for line in message.text.split('\n') if line.strip()]
            if not lines:
                self.bot.reply_to(message, "⚠️ Не найдено строк для импорта")
                return
            
            self.app.input_lines.extend(lines)
            self.bot.reply_to(message, f"✅ Импортировано `{len(lines)}` строк\n\nВсего строк: `{len(self.app.input_lines)}`", parse_mode="Markdown")

        # === ИМПОРТ ФАЙЛА ===
        @self.bot.message_handler(content_types=['document'])
        def handle_document_import(message: Message):
            try:
                if not message.document.file_name.endswith('.txt'):
                    self.bot.reply_to(message, "⚠️ Поддерживаются только `.txt` файлы")
                    return
                
                file_info = self.bot.get_file(message.document.file_id)
                downloaded_file = self.bot.download_file(file_info.file_path)
                lines = [line.strip() for line in downloaded_file.decode('utf-8').split('\n') if line.strip()]
                
                if not lines:
                    self.bot.reply_to(message, "⚠️ Файл пустой")
                    return
                
                self.app.input_lines.extend(lines)
                self.bot.reply_to(message, f"✅ Импортировано `{len(lines)}` строк из файла `{message.document.file_name}`\n\nВсего строк: `{len(self.app.input_lines)}`", parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Ошибка при импорте файла: {e}")
                self.bot.reply_to(message, f"❌ Ошибка при импорте файла: {str(e)}")

    def _safe_start_process(self, message):
        """Безопасный запуск процесса"""
        try:
            self.app.start_process()
            self.bot.reply_to(message, "✅ Процесс запущен!")
        except Exception as e:
            logger.error(f"Ошибка запуска: {e}")
            self.bot.reply_to(message, f"❌ Ошибка запуска: {str(e)}")

    def _safe_stop_process(self, message):
        """Безопасная остановка"""
        try:
            self.app.stop_process()
            self.bot.reply_to(message, "⏹ Процесс остановлен!")
        except Exception as e:
            logger.error(f"Ошибка остановки: {e}")
            self.bot.reply_to(message, f"❌ Ошибка остановки: {str(e)}")

    def _safe_pause_process(self, message):
        """Безопасная пауза"""
        try:
            self.app.toggle_pause()
            self.bot.reply_to(message, "⏸ Процесс на паузе!")
        except Exception as e:
            logger.error(f"Ошибка паузы: {e}")
            self.bot.reply_to(message, f"❌ Ошибка паузы: {str(e)}")

    def _safe_resume_process(self, message):
        """Безопасное возобновление"""
        try:
            self.app.toggle_pause()
            self.bot.reply_to(message, "▶️ Процесс возобновлен!")
        except Exception as e:
            logger.error(f"Ошибка возобновления: {e}")
            self.bot.reply_to(message, f"❌ Ошибка возобновления: {str(e)}")

    def _update_follows_before_rest(self, number, message):
        """Обновление настройки follows_before_rest"""
        try:
            import tkinter as tk
            self.app.follows_before_rest_entry.delete(0, tk.END)
            self.app.follows_before_rest_entry.insert(0, str(number))
            self.bot.reply_to(message, f"✅ Установлено: `{number}` follow перед отдыхом", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка обновления настройки: {e}")
            self.bot.reply_to(message, f"❌ Ошибка: {str(e)}")

    def _get_status_text(self):
        """Получение текущего статуса"""
        status = "📊 *Статус AutoFollow X*\n\n"
        
        if self.app.is_running:
            status += "🟢 *Статус:* Работает\n"
        elif self.app.is_paused:
            status += "🟡 *Статус:* На паузе\n"
        else:
            status += "🔴 *Статус:* Остановлен\n"
        
        status += (
            f"\n📈 *Сессия:*\n"
            f"• Обработано: `{self.app.session_processed_count}`\n"
            f"• Follow сделано: `{self.app.session_followed_count}`\n"
            f"• Строк в очереди: `{len(self.app.input_lines)}`\n\n"
            f"🌐 *Подключения:*\n"
            f"• Прокси: {'✓' if self.app.proxy else '✗'}\n"
            f"• Cookies: {'✓' if self.app.cookies_valid else '✗'}\n"
            f"• Браузер: {'✓' if self.app.browser else '✗'}"
        )
        
        return status

    def _get_detailed_stats(self):
        """Получение подробной статистики"""
        stats = "📊 *Подробная статистика*\n\n"
        
        # Статистика сессии
        stats += (
            f"🎯 *Сессия:*\n"
            f"• Обработано строк: `{self.app.session_processed_count}`\n"
            f"• Follow сделано: `{self.app.session_followed_count}`\n"
            f"• Строк в очереди: `{len(self.app.input_lines)}`\n\n"
        )
        
        # Настройки
        try:
            delay = self.app.delay_entry.get()
            max_followers = self.app.max_followers_entry.get()
            follows_before_rest = self.app.follows_before_rest_entry.get()
            rest_minutes = self.app.rest_entry.get()
            min_likes = self.app.min_likes_entry.get()
            max_likes = self.app.max_likes_entry.get()
            
            stats += (
                f"⚙️ *Настройки:*\n"
                f"• Задержка: `{delay}` мин\n"
                f"• Макс. фолловеров: `{max_followers}`\n"
                f"• Follow перед отдыхом: `{follows_before_rest}`\n"
                f"• Время отдыха: `{rest_minutes}` мин\n"
                f"• Лайки: `{min_likes}`-`{max_likes}`\n\n"
            )
        except:
            pass
        
        # Подключения
        stats += (
            f"🔌 *Подключения:*\n"
            f"• Прокси: {'✓ Подключен' if self.app.proxy else '✗ Не подключен'}\n"
            f"• Cookies: {'✓ Проверены' if self.app.cookies_valid else '✗ Не проверены'}\n"
            f"• Браузер: {'✓ Активен' if self.app.browser else '✗ Не запущен'}"
        )
        
        return stats
