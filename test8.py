from flask import Flask, render_template, abort, send_from_directory
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = 'hiwqh'
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER # Where to save files --> We moved to DB saving


@app.route('/')
def test():
    return render_template('lyxlab.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if '..' in filename or filename.startswith('/'):
        abort(400, "Invalid filename")
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    else:
        abort(404, "File not found")

@app.route("/nav")
def nav_guide():
    
    return render_template("navigation.html")
if __name__ == '__main__':
    app.run()