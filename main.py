from flask import Flask, request, render_template_string
import yt_dlp
import threading
import os
import json
import re

app = Flask(__name__)

# Определение стандартной папки загрузок для различных ОС
def get_default_download_folder():
    if os.name == 'nt':  # Windows
        return os.path.join(os.environ['USERPROFILE'], 'Downloads')
    else:  # macOS / Linux
        return os.path.join(os.path.expanduser('~'), 'Downloads')

# Загрузка конфигурации
def load_config():
    # Получаем текущую директорию проекта
    current_directory = os.path.dirname(os.path.abspath(__file__))
    # Путь к файлу log1.txt
    config_file = os.path.join(current_directory, 'config.json')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {'download_folder': get_default_download_folder()}

# Сохранение конфигурации
def save_config(config):
    # Получаем текущую директорию проекта
    current_directory = os.path.dirname(os.path.abspath(__file__))
    # Путь к файлу log1.txt
    config_file = os.path.join(current_directory, 'config.json')
    with open(f'{config_file}', 'w') as f:
        json.dump(config, f)

# HTML-шаблон для отображения формы и сообщений
html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Downloader</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background-color: #f4f4f9;
        }
        .container {
            text-align: center;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
            width: 400px;
        }
        input[type="text"] {
            padding: 10px;
            width: 90%;
            margin-bottom: 20px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        input[type="submit"] {
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        input[type="submit"]:hover {
            background-color: #45a049;
        }
        p {
            margin-top: 20px;
        }
        .checkbox-container {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
        }
        .checkbox-container input[type="checkbox"] {
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>YouTube Downloader</h2>
        <form method="POST">
            <label for="url">YouTube URL:</label>
            <input type="text" id="url" name="url" required placeholder="Enter YouTube URL">

            <label for="folder">Download Folder:</label>
            <input type="text" id="folder" name="folder" value="{{ default_folder }}" required placeholder="Enter folder path or leave default">

            <div class="checkbox-container">
                <input type="checkbox" name="set_default">
                <label for="set_default">Set folder as default</label>
            </div>

            <input type="submit" value="Download">
        </form>
        {% if message %}
            <p>{{ message }}</p>
        {% endif %}
    </div>
</body>
</html>
"""

# Функция для скачивания видео с YouTube с использованием yt-dlp
def download_video(url, download_folder):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Максимальное качество
        'merge_output_format': 'mkv',  # Объединить видео и аудио в mkv
        'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),  # Путь сохранения
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"Download completed for {url}")
    except Exception as e:
        print(f"Error downloading video: {e}")

# Основной маршрут для отображения формы и обработки POST-запроса
@app.route("/", methods=["GET", "POST"])
def index():
    config = load_config()  # Загрузка текущей конфигурации
    message = ""
    if request.method == "POST":
        url = request.form["url"]
        folder = request.form["folder"].strip()  # Убираем лишние пробелы в пути
        set_default = 'set_default' in request.form  # Проверка, установлена ли галочка

        # Проверка корректности URL
        if not url.startswith("https://www.youtube.com") and not url.startswith("https://youtu.be"):
            message = "Invalid URL. Please provide a valid YouTube link."
        else:
            # Установка новой папки как стандартной, если выбрано
            if set_default:
                config['download_folder'] = folder
                save_config(config)

            # Запуск скачивания в фоновом потоке
            threading.Thread(target=download_video, args=(url, folder)).start()
            message = "Download started successfully!"

    return render_template_string(html, message=message, default_folder=config['download_folder'])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3900)
