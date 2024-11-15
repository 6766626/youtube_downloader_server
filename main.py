from flask import Flask, request, render_template_string, jsonify
import yt_dlp
import threading
import os
import json
import re
from time import time

app = Flask(__name__)


# Определение стандартной папки загрузок для различных ОС
def get_default_download_folder():
    if os.name == 'nt':  # Windows
        return os.path.join(os.environ['USERPROFILE'], 'Downloads')
    else:  # macOS / Linux
        return os.path.join(os.path.expanduser('~'), 'Downloads')


# Загрузка конфигурации
def load_config():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_directory, 'config.json')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {'download_folder': get_default_download_folder()}


# Сохранение конфигурации
def save_config(config):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_directory, 'config.json')
    with open(config_file, 'w') as f:
        json.dump(config, f)


# Очистка статуса загрузок
def clear_download_status():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    status_file = os.path.join(current_directory, 'downloads.json')
    with open(status_file, 'w') as f:
        json.dump({}, f)


# Обновление статуса загрузок
def update_download_status(video_id, data):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    status_file = os.path.join(current_directory, 'downloads.json')

    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            status = json.load(f)
    else:
        status = {}

    status[video_id] = data

    with open(status_file, 'w') as f:
        json.dump(status, f)


# Удаление статуса загрузки после завершения
def remove_download_status(video_id):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    status_file = os.path.join(current_directory, 'downloads.json')

    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            status = json.load(f)

        # Удаляем статус завершённой загрузки
        if video_id in status:
            del status[video_id]
            print(f"Status for video {video_id} removed from downloads.json.")  # Логируем успешное удаление
        else:
            print(f"No status found for video {video_id} in downloads.json.")  # Логируем отсутствие статуса

        # Сохраняем обновленный статус
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=4)



# Функция для скачивания видео с YouTube с отслеживанием прогресса
def download_video(url, download_folder):
    video_id = re.sub(r'\W+', '', str(time()))  # Уникальный ID для видео

    def progress_hook(d):
        if d['status'] == 'downloading':
            progress = {
                'status': 'downloading',
                'filename': os.path.basename(d['filename']),  # Только имя файла без пути
                'downloaded_bytes': d['downloaded_bytes'],
                'total_bytes': d.get('total_bytes', 0),
                'speed': d.get('speed', 0),
                'eta': d.get('eta', 0),
                'progress': d.get('_percent_str', '0%').strip(),
            }
        elif d['status'] == 'finished':
            progress = {'status': 'finished', 'filename': os.path.basename(d['filename'])}
            update_download_status(video_id, progress)  # Обновление статуса с finished
            print(f"Download finished: {d['filename']}")  # Логирование успешного завершения
        elif d['status'] == 'error':
            progress = {'status': 'error', 'filename': os.path.basename(d['filename']), 'error': d.get('error', '')}
            update_download_status(video_id, progress)
            print(f"Download error: {d.get('error', 'Unknown error')}")  # Логирование ошибки

        update_download_status(video_id, progress)

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mkv',
        'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Запуск скачивания видео
            ydl.download([url])

            # После того как все форматы скачаны и сливаются в один файл:
            print(f"Merging and cleaning up files...")
            remove_download_status(video_id)  # Удаляем статус загрузки после слияния и удаления исходных файлов.
            print(f"Download status for video {video_id} removed from JSON")

    except Exception as e:
        update_download_status(video_id, {'status': 'error', 'error': str(e)})
        print(f"Exception during download: {e}")  # Логирование ошибки загрузки




# Маршрут для получения статуса загрузок
@app.route("/status", methods=["GET"])
def download_status():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    status_file = os.path.join(current_directory, 'downloads.json')
    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            status = json.load(f)
        return jsonify(status)
    return jsonify({})


# Основной маршрут для отображения формы и обработки POST-запроса
@app.route("/", methods=["GET", "POST"])
def index():
    config = load_config()
    if request.method == "POST":
        url = request.form["url"]
        folder = request.form["folder"].strip()
        set_default = 'set_default' in request.form

        if not url.startswith("https://www.youtube.com") and not url.startswith("https://youtu.be"):
            pass  # Убираем сообщение о начале загрузки
        else:
            if set_default:
                config['download_folder'] = folder
                save_config(config)

            # Очищаем предыдущие статусы загрузок
            clear_download_status()

            # Запуск скачивания в фоновом потоке
            threading.Thread(target=download_video, args=(url, folder)).start()

    return render_template_string(html, default_folder=config['download_folder'])


# HTML-шаблон для отображения формы и прогресса загрузок
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
        .checkbox-container {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
        }
        .checkbox-container input[type="checkbox"] {
            margin-right: 10px;
        }
        #status {
            margin-top: 20px;
            text-align: left;
            display: flex;
            flex-direction: column;
        }
        .download-item {
            margin-bottom: 10px;
        }
        .download-item .title {
            font-weight: normal;  /* Сделать текст не жирным */
            margin-bottom: 5px;
            font-size: 12px;  /* Уменьшить размер шрифта */
            word-wrap: break-word;  /* Позволяет переносить длинные слова на следующую строку */
            word-break: break-all;  /* Разбивает слово на несколько строк, если оно слишком длинное */
            white-space: normal;  /* Позволяет переносить текст */
        }
        .progress-bar {
            width: 100%;
            background-color: #f3f3f3;
            border-radius: 5px;
            height: 10px;
            position: relative;
            margin-bottom: 5px;
        }
        .progress-bar .progress {
            background-color: #4CAF50;
            height: 100%;
            border-radius: 5px;
            transition: width 0.2s;
        }
        .percentage {
            font-size: 14px;
            font-weight: bold;
            margin-left: 5px;
        }
        #download-header {
            margin-top: 20px;
            margin-bottom: 10px;
            font-weight: normal;
            text-align: left;
            font-size: 14px; /* Сделать заголовок немного меньше */
        }
        .download-container {
            border: 1px solid #ccc;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
    </style>
    <script>
        function truncateFilename(filename, maxLength) {
            if (filename.length > maxLength) {
                return filename.substring(0, maxLength) + '...';
            }
            return filename;
        }

        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    const downloadHeader = document.getElementById('download-header');
                    statusDiv.innerHTML = '';  // Очищаем старые данные

                    let numItems = 0;

                    for (const key in data) {
                        const download = data[key];
                        numItems++;

                        const downloadItemDiv = document.createElement('div');
                        downloadItemDiv.classList.add('download-item');

                        const title = document.createElement('div');
                        title.classList.add('title');
                        title.textContent = truncateFilename(download.filename, 50);  // Ограничение имени файла до 30 символов

                        const progressBar = document.createElement('div');
                        progressBar.classList.add('progress-bar');

                        const progress = document.createElement('div');
                        progress.classList.add('progress');
                        progress.style.width = download.progress; // Устанавливаем ширину прогресса

                        const percentage = document.createElement('span');
                        percentage.classList.add('percentage');
                        percentage.textContent = download.progress; // Отображаем проценты

                        progressBar.appendChild(progress);
                        downloadItemDiv.appendChild(title);
                        downloadItemDiv.appendChild(progressBar);
                        downloadItemDiv.appendChild(percentage);

                        statusDiv.appendChild(downloadItemDiv);
                    }

                    // Заголовок будет всегда "Downloads"
                    downloadHeader.textContent = 'Downloads';
                });
        }

        setInterval(updateStatus, 3000); // Обновляем статус каждые 3 секунды
    </script>
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

        <div id="download-header">Downloads</div> <!-- Заголовок с изменениями -->
        <div class="download-container">
            <div id="status">
                <!-- Статус загрузок будет обновляться здесь -->
            </div>
        </div>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3900)
