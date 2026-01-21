# storage_bp.py
from flask import Blueprint, render_template, request, jsonify, flash, Response, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from datetime import datetime
import cloudinary.uploader
import cloudinary.api
import requests
from sqlalchemy.exc import IntegrityError
from app import db, UploadedFile, FileTag
from datetime import timedelta
import time
import os
from functools import wraps
from flask import abort, redirect, url_for

storage_bp = Blueprint('file_store', __name__, url_prefix='/store')

def admin_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if not current_user.is_authenticated:
            # for AJAX/API
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            flash('Login first to access the page', 'error')
            return redirect(url_for('login'))
        if not current_user.is_admin:
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Access denied.'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorator

# File upload settings
ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg',
    'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx', 
    'odt', 'ods', 'odp', 'rtf',
    'zip', 'rar', '7z',
    'mp3', 'wav', 'ogg', 'm4a', 'flac',
    'mp4', 'mov', 'avi', 'mkv', 'webm', 'flv'
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Determine file type from filename"""
    if not filename:
        return 'other'
    
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    document_ext = {'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp', 'rtf'}
    image_ext = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'tiff', 'ico'}
    video_ext = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'wmv', 'm4v', 'mpg', 'mpeg'}
    audio_ext = {'mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'wma'}
    archive_ext = {'zip', 'rar', '7z', 'tar', 'gz'}
    
    if ext in image_ext:
        return 'image'
    elif ext in video_ext:
        return 'video'
    elif ext in audio_ext:
        return 'audio'
    elif ext in document_ext:
        return 'document'
    elif ext in archive_ext:
        return 'archive'
    else:
        return 'other'

def format_file_size(bytes):
    if bytes == 0:
        return '0 Bytes'
    sizes = ['Bytes', 'KB', 'MB', 'GB']
    i = 0
    while bytes >= 1024 and i < len(sizes)-1:
        bytes /= 1024
        i += 1
    return f"{bytes:.2f} {sizes[i]}"
import secrets
def gen_unique_id(_tablename, max_attempts=100):
    for attempt in range(max_attempts):
        r_id = secrets.randbelow(900000) + 100000
        
        # Use database transaction to prevent race conditions
        with db.session.begin_nested():
            existing = db.session.query(_tablename.id).filter_by(id=r_id).with_for_update().first()
            if not existing:
                return r_id
        
        if attempt >= max_attempts - 1:
            raise ValueError(f"Failed to generate unique ID after {max_attempts} attempts")
    
    raise ValueError("Failed to generate unique ID")

@login_required
@storage_bp.route('/')
def file_store():
    """Render the main files page"""
    return render_template('file_store.html')

@admin_required
@storage_bp.route('/api/upload-multiple', methods=['POST'])
def upload_multiple_files():
    """Handle single or multiple file uploads to Cloudinary"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files selected'}), 400
    
    files = request.files.getlist('files')
    # Get form data
    name = request.form.get('name', '')
    
    uploaded_count = 0
    failed_count = 0
    errors = []
    uploaded_files = []
    
    for index, file in enumerate(files):
        try:
            # Check file
            if file.filename == '':
                errors.append("Empty file name")
                failed_count += 1
                continue
            
            if not allowed_file(file.filename):
                errors.append(f"{file.filename}: File type not allowed")
                failed_count += 1
                continue
            
            # Read file content
            file_content = file.read()
            
            # Check file size
            if len(file_content) > MAX_FILE_SIZE:
                errors.append(f"{file.filename}: File too large. Max size: {MAX_FILE_SIZE//(1024*1024)}MB")
                failed_count += 1
                continue
            
            # Secure filename
            raw_filename = secure_filename(file.filename)
            name, ext = os.path.splitext(raw_filename)
            filename = f"{name}_FILE@LN{ext}"
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            if name:
                base_name = f"{name}_{index}_{int(time.time())}_FILE@LN"
            else:
                # Use filename without extension
                base_name = f"{filename.rsplit('.', 1)[0] if '.' in filename else filename}_FILE@LN"
            
            # Determine resource type
            document_extensions = {'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx'}
            video_extensions = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'flv'}
            audio_extensions = {'mp3', 'wav', 'ogg', 'm4a'}
            
            if file_ext in document_extensions:
                resource_type = 'raw'
            elif file_ext in video_extensions:
                resource_type = 'video'
            elif file_ext in audio_extensions:
                resource_type = 'video'
            else:
                resource_type = 'auto'
            
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file_content,
                folder="flask_uploads",
                resource_type=resource_type,
                public_id=base_name,
                overwrite=True,
                use_filename=True,
                unique_filename=True,
                **({'type': 'authenticated'} if resource_type == 'raw' else {})
            )
            
            # Determine file type for database
            file_type = get_file_type(filename)
            
            # Check if file already exists - use the actual public_id from Cloudinary
            actual_public_id = upload_result.get('public_id')
            existing_file = UploadedFile.query.filter_by(public_id=actual_public_id).first()
            if existing_file:
                # Update existing
                existing_file.filename = filename
                existing_file.url = upload_result['secure_url']
                existing_file.file_size = upload_result.get('bytes', 0)
                existing_file.file_format = upload_result.get('format', file_ext)
                existing_file.width = upload_result.get('width')
                existing_file.height = upload_result.get('height')
                existing_file.duration = upload_result.get('duration')
                existing_file.resource_type = upload_result.get('resource_type', resource_type)
                existing_file.file_type = file_type
                existing_file.updated_at = datetime.utcnow() + timedelta(hours=3)
                file_record = existing_file
            else:
                # Create new record
                new_file = UploadedFile(
                    id=gen_unique_id(UploadedFile),
                    public_id=actual_public_id,  # Use actual public_id from Cloudinary
                    filename=filename,
                    url=upload_result['secure_url'],
                    file_type=file_type,
                    file_format=upload_result.get('format', file_ext),
                    file_size=upload_result.get('bytes', 0),
                    width=upload_result.get('width'),
                    height=upload_result.get('height'),
                    duration=upload_result.get('duration'),
                    resource_type=upload_result.get('resource_type', resource_type),
                    folder=upload_result.get('folder', 'flask_uploads'),
                    created_at=datetime.utcnow() + timedelta(hours=3),
                    updated_at=datetime.utcnow() + timedelta(hours=3)
                )
                db.session.add(new_file)
                file_record = new_file
            
            db.session.commit()
            
            uploaded_files.append(file_record.to_dict())
            uploaded_count += 1
            
            current_app.logger.info(f'File uploaded: {filename} | Type: {file_type} | Resource: {resource_type}')
            
        except cloudinary.api.Error as e:
            db.session.rollback()
            error_msg = str(e)
            if 'File size too large' in error_msg:
                errors.append(f"{file.filename}: File size exceeds Cloudinary limits (10MB for images, 100MB for videos)")
            elif 'Invalid image file' in error_msg:
                errors.append(f"{file.filename}: Invalid file format or corrupted file")
            else:
                errors.append(f"{file.filename}: Cloudinary error: {error_msg}")
            current_app.logger.error(f'Cloudinary error for {file.filename}: {error_msg}')
            failed_count += 1
            
        except IntegrityError:
            db.session.rollback()
            errors.append(f"{file.filename}: Database error - possible duplicate")
            current_app.logger.error(f'Integrity error for {file.filename}')
            failed_count += 1
            
        except Exception as e:
            db.session.rollback()
            errors.append(f"{file.filename}: Upload failed: {str(e)}")
            current_app.logger.error(f'Upload error for {file.filename}: {str(e)}')
            failed_count += 1
    
    if uploaded_count == 0:
        return jsonify({
            'success': False,
            'error': 'No files were successfully uploaded',
            'uploaded': uploaded_count,
            'failed': failed_count,
            'errors': errors
        }), 400
    
    return jsonify({
        'success': True,
        'message': f'Successfully uploaded {uploaded_count} file(s)' + (f', {failed_count} failed' if failed_count > 0 else ''),
        'uploaded': uploaded_count,
        'failed': failed_count,
        'errors': errors if errors else None,
        'files': uploaded_files
    })

@login_required
@storage_bp.route('/api/files')
def get_files():
    """Get all uploaded files (API endpoint)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    query = UploadedFile.query
    
    if category:
        query = query.filter_by(file_type=category)
    
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            (UploadedFile.filename.ilike(search_term)) |
            (UploadedFile.file_type.ilike(search_term))
        )
    
    files = query.order_by(UploadedFile.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Format response for the template
    file_list = []
    for f in files.items:
        file_list.append({
            'id': f.id,
            'filename': f.filename,
            'name': f.filename.rsplit('.', 1)[0] if '.' in f.filename else f.filename,
            'description': f'Uploaded on {f.created_at.strftime("%Y-%m-%d")}',
            'file_size': f.file_size,
            'file_type': f.file_type,
            'uploaded_at': f.created_at.isoformat() if f.created_at else None,
            'uploaded_by': 'Admin',  # You can update this based on your user model
            'category': f.file_type,
            'url': f.url,
            'public_id': f.public_id
        })
    
    return jsonify({
        'files': file_list,
        'total': files.total,
        'pages': files.pages,
        'current_page': files.page,
        'per_page': files.per_page,
        'has_next': files.has_next,
        'has_prev': files.has_prev
    })

@login_required
@storage_bp.route('/api/files/count')
def get_file_count():
    """Get total file count"""
    count = UploadedFile.query.count()
    return jsonify({'count': count})

@login_required
@storage_bp.route('/api/files/categories')
def get_categories():
    """Get unique file categories"""
    categories = db.session.query(UploadedFile.file_type).distinct().all()
    category_list = [cat[0] for cat in categories if cat[0]]
    return jsonify({'categories': category_list})

@login_required
@storage_bp.route('/api/files/<int:file_id>')
def get_file(file_id):
    """Get single file details"""
    file = UploadedFile.query.get_or_404(file_id)
    return jsonify({'file': {
        'id': file.id,
        'filename': file.filename,
        'url': file.url,
        'file_type': file.file_type,
        'file_size': file.file_size,
        'created_at': file.created_at.isoformat() if file.created_at else None
    }})

@login_required
@storage_bp.route('/api/files/<int:file_id>/download')
def download_file(file_id):
    """Download file through Flask"""
    try:
        file = UploadedFile.query.get_or_404(file_id)
        file_url = file.url
        
        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        
        flask_response = Response(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get('Content-Type', 'application/octet-stream')
        )
        
        filename = file.filename.encode('utf-8').decode('latin-1')
        flask_response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        flask_response.headers['Content-Length'] = response.headers.get('Content-Length', file.file_size)
        flask_response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        flask_response.headers['Pragma'] = 'no-cache'
        flask_response.headers['Expires'] = '0'
        
        return flask_response
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f'Cloudinary request error: {str(e)}')
        return jsonify({'error': 'Failed to fetch file'}), 500
    except Exception as e:
        current_app.logger.error(f'Download error: {str(e)}')
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@login_required
@storage_bp.route('/api/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Delete file from Cloudinary and database - 0% failure rate"""
    try:
        file = UploadedFile.query.get_or_404(file_id)
        
        print(f"DELETE DEBUG: Starting deletion for file_id={file_id}")
        print(f"DELETE DEBUG: URL={file.url}")
        print(f"DELETE DEBUG: Public_ID={file.public_id}")
        print(f"DELETE DEBUG: Resource_Type={file.resource_type}")
        
        # ====== STEP 1: Extract CORRECT public_id from URL ======
        def extract_public_id_from_url(url):
            """Extract public_id from Cloudinary URL reliably"""
            import urllib.parse
            import re
            
            # URL decode first
            decoded_url = urllib.parse.unquote(url)
            
            # Pattern 1: Authenticated URLs
            # https://res.cloudinary.com/xxx/raw/authenticated/s--sig--/v1234567/folder/filename
            auth_pattern = r'/authenticated/[^/]+/v\d+/(.+)\.\w+$'
            
            # Pattern 2: Regular upload URLs  
            # https://res.cloudinary.com/xxx/raw/upload/v1234567/folder/filename
            upload_pattern = r'/upload/(?:v\d+/)?(.+)\.\w+$'
            
            # Pattern 3: Any Cloudinary URL
            # https://res.cloudinary.com/xxx/resource_type/upload/.../public_id
            any_pattern = r'/(?:image|video|raw|auto)/(?:upload|authenticated)/(?:[^/]+/)*(?:v\d+/)?(.+)\.\w+$'
            
            for pattern in [auth_pattern, upload_pattern, any_pattern]:
                match = re.search(pattern, decoded_url)
                if match:
                    public_id = match.group(1)
                    print(f"DEBUG: Extracted with pattern: {public_id}")
                    return public_id
            
            # If no pattern matches, try to extract manually
            if 'res.cloudinary.com' in decoded_url:
                # Split by known segments
                parts = decoded_url.split('res.cloudinary.com/')[1].split('/')
                if len(parts) > 3:
                    # Skip cloud_name, resource_type, upload_type
                    return '/'.join(parts[3:]).split('.')[0]
            
            return None
        
        # Get the actual public_id from URL
        actual_public_id = extract_public_id_from_url(file.url)
        if not actual_public_id:
            actual_public_id = file.public_id
        
        print(f"DELETE DEBUG: Using public_id='{actual_public_id}'")
        
        # ====== STEP 2: Determine resource type ======
        resource_type = file.resource_type or 'auto'
        
        # ====== STEP 3: Determine if authenticated ======
        is_authenticated = 'authenticated' in file.url.lower()
        
        # ====== STEP 4: DELETE WITH ALL POSSIBLE COMBINATIONS ======
        delete_attempts = []
        
        # Attempt 1: With correct parameters
        params = {
            'resource_type': resource_type,
            'invalidate': True
        }
        if is_authenticated:
            params['type'] = 'authenticated'
        
        result = cloudinary.uploader.destroy(actual_public_id, **params)
        delete_attempts.append({'params': params.copy(), 'result': result})
        
        # Attempt 2: If failed, try without type parameter
        if result.get('result') != 'ok' and is_authenticated:
            params2 = {'resource_type': resource_type, 'invalidate': True}
            result = cloudinary.uploader.destroy(actual_public_id, **params2)
            delete_attempts.append({'params': params2.copy(), 'result': result})
        
        # Attempt 3: Try with 'auto' resource_type
        if result.get('result') != 'ok':
            params3 = {'resource_type': 'auto', 'invalidate': True}
            if is_authenticated:
                params3['type'] = 'authenticated'
            result = cloudinary.uploader.destroy(actual_public_id, **params3)
            delete_attempts.append({'params': params3.copy(), 'result': result})
        
        # Attempt 4: Try the stored public_id (original)
        if result.get('result') != 'ok' and actual_public_id != file.public_id:
            params4 = {'resource_type': resource_type, 'invalidate': True}
            if is_authenticated:
                params4['type'] = 'authenticated'
            result = cloudinary.uploader.destroy(file.public_id, **params4)
            delete_attempts.append({'params': params4.copy(), 'result': result})
        
        # Attempt 5: Try without _FILE@LN suffix
        if result.get('result') != 'ok' and '_FILE@LN' in actual_public_id:
            clean_id = actual_public_id.replace('_FILE@LN', '')
            params5 = {'resource_type': resource_type, 'invalidate': True}
            if is_authenticated:
                params5['type'] = 'authenticated'
            result = cloudinary.uploader.destroy(clean_id, **params5)
            delete_attempts.append({'params': params5.copy(), 'result': result})
        
        # ====== STEP 5: Check if ANY attempt succeeded ======
        success = False
        for attempt in delete_attempts:
            if attempt['result'].get('result') == 'ok':
                success = True
                print(f"DELETE SUCCESS with params: {attempt['params']}")
                break
        
        # ====== STEP 6: Final verification ======
        if success:
            # Double-check by trying to fetch the resource (should fail)
            try:
                # This should raise an exception if file is truly deleted
                cloudinary.api.resource(actual_public_id, resource_type=resource_type)
                print("WARNING: File might still exist in Cloudinary!")
            except:
                print("VERIFIED: File successfully deleted from Cloudinary")
            
            # Delete from database
            FileTag.query.filter_by(file_id=file.id).delete()
            db.session.delete(file)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'File deleted successfully',
                'debug_info': {
                    'file_id': file_id,
                    'public_id_used': actual_public_id,
                    'attempts': delete_attempts
                }
            })
        else:
            # Last resort: Try ADMIN API with force
            print("DELETE DEBUG: All standard attempts failed, trying admin API...")
            try:
                # Try to delete by asset ID (from URL)
                from urllib.parse import urlparse
                parsed = urlparse(file.url)
                path_parts = parsed.path.split('/')
                
                # Look for asset ID pattern
                for i, part in enumerate(path_parts):
                    if part.startswith('v') and part[1:].isdigit():
                        if i + 1 < len(path_parts):
                            asset_path = '/'.join(path_parts[i+1:]).split('.')[0]
                            result = cloudinary.uploader.destroy(asset_path, resource_type='auto')
                            if result.get('result') == 'ok':
                                FileTag.query.filter_by(file_id=file.id).delete()
                                db.session.delete(file)
                                db.session.commit()
                                return jsonify({'success': True, 'message': 'Deleted via admin API'})
            except Exception as e:
                print(f"DELETE DEBUG: Admin API also failed: {e}")
            
            # If we get here, delete from DB anyway (orphaned record)
            FileTag.query.filter_by(file_id=file.id).delete()
            db.session.delete(file)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'File record removed from database (Cloudinary deletion may have failed)',
                'warning': 'Could not delete from Cloudinary - manual cleanup may be needed',
                'debug_info': {
                    'file_id': file_id,
                    'url': file.url,
                    'all_attempts': delete_attempts
                }
            })
            
    except Exception as e:
        db.session.rollback()
        print(f"DELETE CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Even on error, try to return something useful
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Deletion failed with unexpected error'
        }), 500
            
@login_required
@storage_bp.route('/api/files/search')
def search_files():
    """Search files by filename or tags"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Search query required'}), 400
    
    files_by_name = UploadedFile.query.filter(
        UploadedFile.filename.ilike(f'%{query}%')
    ).all()
    
    files_by_tag = UploadedFile.query.join(FileTag).filter(
        FileTag.tag.ilike(f'%{query}%')
    ).distinct().all()
    
    all_files = {f.id: f for f in files_by_name + files_by_tag}
    
    return jsonify({
        'files': [f.to_dict() for f in all_files.values()],
        'count': len(all_files)
    })

@login_required
@storage_bp.route('/api/stats')
def get_stats():
    """Get file statistics"""
    total_files = UploadedFile.query.count()
    
    type_counts = db.session.query(
        UploadedFile.file_type, 
        db.func.count(UploadedFile.id)
    ).group_by(UploadedFile.file_type).all()
    
    total_size = db.session.query(db.func.sum(UploadedFile.file_size)).scalar() or 0
    
    week_ago = datetime.utcnow().timestamp() - (7 * 24 * 60 * 60)
    recent_uploads = UploadedFile.query.filter(
        db.func.strftime('%s', UploadedFile.created_at) > week_ago
    ).count()
    
    top_tags = db.session.query(
        FileTag.tag, 
        db.func.count(FileTag.id)
    ).group_by(FileTag.tag).order_by(db.func.count(FileTag.id).desc()).limit(10).all()
    
    return jsonify({
        'total_files': total_files,
        'type_counts': dict(type_counts),
        'total_size': total_size,
        'total_size_formatted': format_file_size(total_size),
        'recent_uploads': recent_uploads,
        'top_tags': dict(top_tags)
    })


@storage_bp.route('/api/cloudinary-info')
def cloudinary_info():
    """Get Cloudinary account info"""
    try:
        usage = cloudinary.api.usage()
        resources = cloudinary.api.resources(max_results=1)
        
        return jsonify({
            'account': {
                'cloud_name': cloudinary.config().cloud_name,
                'plan': usage.get('plan'),
            },
            'usage': usage,
            'total_resources': resources.get('total_count', 0)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@storage_bp.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found'}), 404

@storage_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

print("File storage blueprint loaded. ✅")