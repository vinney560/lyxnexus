from flask import Flask, render_template_string
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# Cloudinary configuration
cloudinary.config(
    cloud_name='dmkfmr8ry',           # your cloud name
    api_key='193571428832866',       # your API key
    api_secret='YfS4hvX0kkEt4Q8DR_i_xiY_Owk'     # API secret
)

@app.route('/')
def upload_and_show():
    # Upload image
    response = cloudinary.uploader.upload(
        "uploads/OIP3.jpg",          # path to your image
        resource_type="image"
    )

    # Get URL to display
    image_url = response['secure_url']

    # Simple HTML
    html = f"""
    <h2>Uploaded Image</h2>
    <img src="{image_url}" alt="Uploaded Image" width="400">
    """
    return render_template_string(html)

if __name__ == '__main__':
    app.run(debug=True)
