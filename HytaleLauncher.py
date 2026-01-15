import flet as ft
import os
import subprocess
import asyncio
import json
import logging
from pathlib import Path
import random

# Цветовая палитра Hytale
COLORS = {
    "accent": "#2bc1aa",        
    "panel_bg": "#EE0a0b0f",    
    "hover": "#1f8c7a",
    "border": "#22ffffff",
    "text_secondary": "#b3b3b3"
}

class HytaleLauncher:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Hytale Launcher"
        
        # Настройки окна
        self.page.window.width = 913
        self.page.window.height = 600
        self.page.window.resizable = False
        self.page.window.maximizable = False
        
        # Фиксируем границы
        self.page.window.min_width = 913
        self.page.window.max_width = 913
        self.page.window.min_height = 600
        self.page.window.max_height = 600
        
        # Центрирование окна
        self.page.run_task(self.page.window.center)
        
        self.page.padding = 0
        self.page.spacing = 0
        self.page.theme_mode = ft.ThemeMode.DARK
        
        # Директории
        self.base_dir = Path(__file__).parent.absolute()
        self.launcher_data_dir = self.base_dir / "launcher"
        self.log_dir = self.launcher_data_dir / "error-logs"
        
        # Создание необходимых папок
        for path in [self.launcher_data_dir, self.log_dir]:
            path.mkdir(parents=True, exist_ok=True)
            
        self.config_path = self.launcher_data_dir / "Launcher-settings.json"
        
        # Настройка логирования
        logging.basicConfig(
            filename=self.log_dir / "launcher_errors.log",
            level=logging.ERROR,
            format="%(asctime)s - %(levelname)s - %(message)s",
            encoding="utf-8"
        )
        
        self.settings = self.load_settings()

        # Ресурсы
        self.img_dir = self.base_dir / "backgrounds"
        if not self.img_dir.exists():
            self.img_dir.mkdir(parents=True, exist_ok=True)
            
        self.bg_images = [f.name for f in self.img_dir.glob("*") if f.suffix.lower() in [".jpg", ".png", ".jpeg"]]
        self.current_img_index = 0

        self.init_ui_elements()
        self.build_main_screen()

        # Фон
        self.bg_image = ft.Image(
            src=self.get_img_url(),
            fit="cover", 
            expand=True,
            opacity=1,
            animate_opacity=1000, 
        )

        self.layout = ft.Stack(
            [
                self.bg_image,
                ft.Container(
                    content=self.main_container, 
                    alignment=ft.alignment.Alignment(0,0),
                    expand=True
                ),
            ],
            expand=True,
        )

        self.page.add(self.layout)
        self.page.run_task(self.animate_backgrounds)

    def load_settings(self):
        default_settings = {
            "nickname": os.getlogin(),
            "version": "Latest Release",
            "java_path": str(self.base_dir / "package" / "jre" / "latest" / "bin" / "java.exe"),
            "ram_gb": 4,
            "uuid": "32283228-3228-3228-3228-322832283228"
        }
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return {**default_settings, **json.load(f)}
            except Exception as e:
                logging.error(f"Ошибка загрузки настроек: {e}")
        return default_settings

    def save_settings(self, e=None):
        try:
            self.settings["nickname"] = self.nickname_input.value
            self.settings["java_path"] = self.java_path_input.value
            self.settings["ram_gb"] = int(self.ram_slider.value)
            self.settings["uuid"] = self.uuid_input.value
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as ex:
            logging.error(f"Ошибка сохранения настроек: {ex}")

    def open_folder(self, path: Path):
        try:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(path))
        except Exception as e:
            logging.error(f"Не удалось открыть папку {path}: {e}")


    def init_ui_elements(self):
        # Поля ввода
        self.nickname_input = ft.TextField(
            label="Никнейм", value=self.settings["nickname"],
            width=300, border_color=COLORS["accent"], focused_border_color="white"
        )
        
        self.java_path_input = ft.TextField(
            label="Путь к java.exe", value=self.settings["java_path"],
            width=300, text_size=12, border_color="#444444"
        )
        
        self.uuid_input = ft.TextField(
            label="UUID игрока", value=self.settings["uuid"],
            width=300, text_size=12, border_color="#444444"
        )

        self.ram_slider = ft.Slider(
            min=2, max=16, divisions=14, label="{value}GB RAM",
            value=self.settings["ram_gb"], active_color=COLORS["accent"]
        )

        # Прогресс-бар (изначально скрыт)
        self.launch_progress = ft.ProgressBar(
            width=300, color=COLORS["accent"], bgcolor="#333333", 
            visible=False, border_radius=5
        )

        # Кнопка запуска с проверкой существования файла
        game_path = self.base_dir / "package" / "game" / "latest"
        client_exe = game_path / "Client" / "HytaleClient.exe"
        file_exists = client_exe.exists()

        self.play_button = ft.FilledButton(
            content=ft.Text("ИГРАТЬ", size=20, weight="bold"),
            width=300, height=55,
            disabled=not file_exists,
            style=ft.ButtonStyle(
                bgcolor={ft.ControlState.DEFAULT: COLORS["accent"], ft.ControlState.DISABLED: "#444444"},
                shape=ft.RoundedRectangleBorder(radius=12),
                color=ft.Colors.WHITE
            ),
            on_click=self.launch_game
        )

        self.status_text = ft.Text(
            "Ready to play" if file_exists else "Client not found!", 
            color=COLORS["text_secondary"] if file_exists else ft.Colors.RED_400, 
            size=12
        )

        self.main_container = ft.Container(
            bgcolor=COLORS["panel_bg"],
            blur=ft.Blur(1, 1),
            border=ft.Border.all(1, COLORS["border"]),
            border_radius=30,
            padding=40,
            width=450,
            height=350,
            alignment=ft.alignment.Alignment(0,0),
            animate=ft.Animation(300, ft.AnimationCurve.DECELERATE)
        )

    def build_main_screen(self, e=None):
        self.main_container.content = ft.Column(
            [
                ft.Row([
                    ft.Text("HYTALE", size=52, weight="bold", color=COLORS["accent"]),
                    ft.IconButton(ft.Icons.SETTINGS_ROUNDED, icon_color="white", on_click=self.build_settings_screen)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Column([
                    self.nickname_input,
                ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                
                ft.Column([
                    self.play_button,
                    self.launch_progress, # Добавили в UI
                    self.status_text
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        self.page.update()

    def build_settings_screen(self, e):
        self.main_container.content = ft.Column(
            [
                ft.Text("НАСТРОЙКИ", size=24, weight="bold", color=COLORS["accent"]),
                
                ft.Column([
                    # ft.Text("Выделение памяти (RAM)", size=14, color=COLORS["text_secondary"]),
                    # self.ram_slider,
                    self.java_path_input,
                    self.uuid_input,

                ft.Row([
                        ft.TextButton(
                            "ПАПКА ИГРЫ", 
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=lambda _: self.open_folder(self.base_dir / "package" / "game"),
                            style=ft.ButtonStyle(color=COLORS["text_secondary"])
                        ),
                        ft.TextButton(
                            "ЛОГИ ИГРЫ", 
                            icon=ft.Icons.HISTORY_EDU_OUTLINED,
                            on_click=lambda _: self.open_folder(self.base_dir / "UserData" / "Logs"),
                            style=ft.ButtonStyle(color=COLORS["text_secondary"])
                        ),
                        ft.TextButton(
                            "ЛОГИ ЛАУНЧЕРА", 
                            icon=ft.Icons.BUG_REPORT_OUTLINED,
                            on_click=lambda _: self.open_folder(self.log_dir),
                            style=ft.ButtonStyle(color=COLORS["text_secondary"])
                        ),

                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=5, wrap=True),
                ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                
                ft.Column([
                    ft.ElevatedButton(
                        "СОХРАНИТЬ И ВЫЙТИ", 
                        icon=ft.Icons.SAVE,
                        width=300,
                        color="white",
                        bgcolor=COLORS["hover"],
                        on_click=self.save_and_back
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        self.page.update()

    async def save_and_back(self, e):
        self.save_settings()
        self.build_main_screen()

    def get_img_url(self):
        if not self.bg_images: return ""
        return f"backgrounds/{self.bg_images[self.current_img_index]}"


    async def animate_backgrounds(self):
        while True:
            await asyncio.sleep(8)
            if len(self.bg_images) > 1:
                # 2. Убираем прозрачность (начало анимации)
                self.bg_image.opacity = 0
                self.page.update()
                await asyncio.sleep(1)

                # 3. Выбираем новый индекс, который не равен текущему
                new_index = self.current_img_index
                while new_index == self.current_img_index:
                    new_index = random.randint(0, len(self.bg_images) - 1)
                
                self.current_img_index = new_index
                
                # 4. Меняем картинку и возвращаем видимость
                self.bg_image.src = self.get_img_url()
                self.bg_image.opacity = 1
                self.page.update()

    async def launch_game(self, e):
        # Визуальный отклик
        self.play_button.disabled = True
        self.launch_progress.visible = True
        self.status_text.value = "Запуск игры..."
        self.status_text.color = COLORS["accent"]
        self.page.update()

        self.save_settings()
        
        game_path = self.base_dir / "package" / "game" / "latest"
        client_exe = game_path / "Client" / "HytaleClient.exe"
        user_data = self.base_dir / "UserData"
        
        if not user_data.exists():
            user_data.mkdir(parents=True, exist_ok=True)
        
        args = [
            str(client_exe),
            "--app-dir", str(game_path),
            "--user-dir", str(user_data),
            "--java-exec", self.settings["java_path"],
            "--auth-mode", "offline",
            "--uuid", self.settings["uuid"],
            "--name", self.settings["nickname"]
        ]
        
        # Небольшая задержка для визуализации прогресс-бара
        await asyncio.sleep(1.5)
        
        try:
            subprocess.Popen(args, cwd=str(self.base_dir))
            await self.page.window.destroy() 
        except Exception as ex:
            logging.error(f"Критическая ошибка при запуске игры: {ex}")
            self.status_text.value = "Ошибка запуска!"
            self.status_text.color = ft.Colors.RED_ACCENT
            self.launch_progress.visible = False
            self.play_button.disabled = False
            self.page.update()

def main(page: ft.Page):
    HytaleLauncher(page)

if __name__ == "__main__":
    ft.run(main, assets_dir=".")