from flask import Flask, send_from_directory, render_template

app = Flask(__name__)
app.config["SECRET_KEY"] = 'KHDKHRKF'
@app.route("/")
def index():
    return render_template("lyxnexus_ads.html")
@app.route('/tailwind.all.css')
def tailwindcss():
    return send_from_directory('static', 'css/tailwind.all.css', mimetype='application/javascript')

if __name__ == '__main__':
    app.run(debug=True)