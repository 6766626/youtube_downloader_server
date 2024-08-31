from flask import Flask, request, render_template_string
import os

app = Flask(__name__)

html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Downloader</title>
</head>
<body>
    <h2>YouTube Downloader</h2>
    <form method="POST">
        <label for="url">YouTube URL:</label>
        <input type="text" id="url" name="url" required>
        <input type="submit" value="Download">
    </form>
    {% if message %}
        <p>{{ message }}</p>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        url = request.form["url"]
        # Используем полный путь к yt-dlp
        command = f"/opt/homebrew/bin/yt-dlp -f bestvideo+bestaudio --merge-output-format mkv -o '/Volumes/1tb/downloads/%(title)s.%(ext)s' {url}"
        print("Executing command:", command)  # Отладочный вывод
        result = os.system(command)
        if result == 0:
            message = "Download started successfully!"
        else:
            message = "Failed to start the download. Please check the URL or try again."
    return render_template_string(html, message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)