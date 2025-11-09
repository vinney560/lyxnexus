import os
import mimetypes
from flask import Blueprint, current_app, render_template
from app import db, File
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

cloud_migration_bp = Blueprint('cloud_migration', __name__, url_prefix='/storage')

# ---------------- Cloudinary configuration ----------------
cloudinary.config(
    cloud_name='dmkfmr8ry',
    api_key='193571428832866',
    api_secret='YfS4hvX0kkEt4Q8DR_i_xiY_Owk'
)

# Temporary folder for uploads
TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

# Max file size (5MB for LyxNexus)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# ---------------- Helper functions ----------------
def get_resource_type(filename):
    mime, _ = mimetypes.guess_type(filename)
    if mime and (mime.startswith("image") or mime.startswith("video")):
        return "auto"
    return "raw"  # PDFs, Word, Excel, etc.

def generate_signed_url(file_id, resource_type="raw"):
    url, _ = cloudinary_url(
        f"file_{file_id}",
        resource_type=resource_type,
        sign_url=True  # avoids 401
    )
    return url

# ---------------- Migration Route ----------------
@cloud_migration_bp.route('/seed-cloud', methods=['GET'])
def migrate_files():
    migrated_count = 0
    files = File.query.all()

    for f in files:
        if f.file_url:
            continue  # already migrated

        if f.file_size > MAX_FILE_SIZE:
            current_app.logger.warning(f"Skipping {f.filename}: exceeds 5MB")
            continue

        temp_path = os.path.join(TEMP_DIR, f.filename)
        try:
            with open(temp_path, "wb") as temp_file:
                temp_file.write(f.file_data)

            resource_type = get_resource_type(f.filename)
            response = cloudinary.uploader.upload(
                temp_path,
                resource_type=resource_type,
                public_id=f"file_{f.id}",
                overwrite=True
            )

            f.file_url = response['secure_url']
            db.session.commit()
            migrated_count += 1
            current_app.logger.info(f"Migrated {f.filename} → {f.file_url}")

        except Exception as e:
            current_app.logger.error(f"Error migrating {f.filename}: {str(e)}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return f"Migration complete! {migrated_count} files updated."

# ---------------- Files Preview Route ----------------
@cloud_migration_bp.route('/files-preview')
def files_preview():
    files = File.query.order_by(File.uploaded_at.desc()).all()
    # Prepare signed URLs to avoid 401
    for f in files:
        if f.file_url:
            f.signed_url = generate_signed_url(f.id, get_resource_type(f.filename))
        else:
            f.signed_url = None
    return render_template('file_preview.html', files=files)

print('Cloud Storage Blueprint Initialized ✅')
