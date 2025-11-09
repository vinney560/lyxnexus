import os
import mimetypes
from flask import Blueprint, current_app
from app import db, File
import cloudinary
import cloudinary.uploader

cloud_migration_bp = Blueprint('cloud_migration', __name__, url_prefix='/storage')

# ---------------- Cloudinary configuration ----------------
cloudinary.config(
    cloud_name='dmkfmr8ry',
    api_key='193571428832866',
    api_secret='YfS4hvX0kkEt4Q8DR_i_xiY_Owk'
)

# Temporary folder to save files before upload
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# ---------------- Helper to determine resource type ----------------
def get_resource_type(filename):
    mime, _ = mimetypes.guess_type(filename)
    if mime and (mime.startswith("image") or mime.startswith("video")):
        return "auto"
    return "raw"  # PDFs, Word, Excel, etc.

# ---------------- Migration function ----------------
@cloud_migration_bp.route('/seed-cloud', methods=['GET'])
def migrate_files():
    migrated_count = 0
    files = File.query.all()

    for f in files:
        if f.file_url:
            continue  # skip already migrated files

        # Save temp file
        temp_path = os.path.join(TEMP_DIR, f.filename)
        with open(temp_path, "wb") as temp_file:
            temp_file.write(f.file_data)

        # Upload to Cloudinary using File.id as public_id
        resource_type = get_resource_type(f.filename)
        response = cloudinary.uploader.upload(
            temp_path,
            resource_type=resource_type,
            public_id=f"file_{f.id}",   # ensures URL corresponds to DB id
            overwrite=True               # allows re-upload if needed
        )
        f.file_url = response['secure_url']
        db.session.commit()

        # Remove temp file
        os.remove(temp_path)
        migrated_count += 1
        current_app.logger.info(f"Migrated {f.filename} → {f.file_url}")

    return f"Migration complete! {migrated_count} files updated."

from flask import render_template

@app.route('/files_preview')
def files_preview():
    files = File.query.order_by(File.uploaded_at.desc()).limit(5).all()
    return render_template('file_preview.html', files=files)
