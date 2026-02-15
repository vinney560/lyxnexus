from flask import Flask, send_from_directory, render_template

app = Flask(__name__)
app.config["SECRET_KEY"] = 'KHDKHRKF'

@app.route("/")
def index():
    return render_template("lyxnexus_ads.html")
@app.route('/tailwind.all.css')
def tailwindcss():
    return send_from_directory('static', 'css/tailwind.all.css', mimetype='application/javascript')

@app.route('/_0eXv3/<filename>')
def css(filename):
    return send_from_directory('static/css', filename)
# ------------------------------------------------------------------
@app.route('/_0eXv4/<filename>')
def js(filename):
    return send_from_directory('static/js', filename, mimetype='application/javascript')

if __name__ == '__main__':
    app.run(debug=True)