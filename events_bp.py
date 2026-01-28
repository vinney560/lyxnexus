from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from app import db, Event, Enrollment
from functools import wraps
import json

events_bp = Blueprint('events', __name__, url_prefix='/events')

# =========== Decorator ============
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('events.index'))
        return f(*args, **kwargs)
    return decorated_function

# ============ PUBLIC ROUTES ============

@events_bp.route('/')
@login_required
def index():
    """Public event listing page"""
    events = Event.query.filter_by(is_active=True).order_by(Event.start_date.asc()).all()
    return render_template('events.html', events=events)

@events_bp.route('/<int:event_id>')
@login_required
def event_detail(event_id):
    """Event detail page"""
    event = Event.query.get_or_404(event_id)
    if not event.is_active:
        flash('This event is not available', 'danger')
        return redirect(url_for('events.index'))
    return render_template('event_detail.html', event=event)

# ============ EVENT CRUD (Admin) ============

@events_bp.route('/admin/events')
@admin_required
def admin_events():
    """Admin: List all events"""
    events = Event.query.order_by(Event.created_at.desc()).all()
    return render_template('admin_events.html', events=events)

@events_bp.route('/admin/events/new', methods=['GET', 'POST'])
@admin_required
def admin_new_event():
    """Admin: Create new event"""
    if request.method == 'POST':
        try:
            # Parse form data
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            venue = request.form.get('venue', '').strip()
            start_date_str = request.form.get('start_date', '').strip()
            end_date_str = request.form.get('end_date', '').strip()
            fee = float(request.form.get('fee', 0.0))
            tutors = request.form.get('tutors', '').strip()
            poster_url = request.form.get('poster_url', '').strip()
            capacity = int(request.form.get('capacity', 50))
            is_active = request.form.get('is_active') == 'true'
            
            # Validate required fields
            if not all([title, description, venue, start_date_str, end_date_str]):
                flash('Please fill in all required fields', 'danger')
                return render_template('admin_event_form.html')
            
            # Parse dates
            start_date = datetime.fromisoformat(start_date_str.replace('T', ' '))
            end_date = datetime.fromisoformat(end_date_str.replace('T', ' '))
            
            if end_date <= start_date:
                flash('End date must be after start date', 'danger')
                return render_template('admin_event_form.html')
            
            # Create event
            event = Event(
                title=title,
                description=description,
                venue=venue,
                start_date=start_date,
                end_date=end_date,
                fee=fee,
                tutors=tutors,
                poster_url=poster_url,
                capacity=capacity,
                is_active=is_active
            )
            
            db.session.add(event)
            db.session.commit()
            
            flash('Event created successfully!', 'success')
            return redirect(url_for('events.admin_events'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating event: {str(e)}', 'danger')
            return render_template('admin_event_form.html')
    
    return render_template('admin_event_form.html')

@events_bp.route('/enrollment/confirmation/<int:enrollment_id>')
@login_required
def enrollment_confirmation(enrollment_id):
    """Show enrollment confirmation page"""
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    
    # Verify the enrollment belongs to the current user
    if enrollment.username != current_user.username and not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('events.index'))
    
    return render_template('enrollment_confirmation.html', enrollment=enrollment)


@events_bp.route('/api/events/<int:event_id>/enrollment-status')
@login_required
def check_enrollment_status(event_id):
    """API endpoint to check if user is enrolled in an event"""
    event = Event.query.get_or_404(event_id)
    
    enrollment = Enrollment.query.filter_by(
        username=current_user.username,
        event_id=event_id
    ).first()
    
    return jsonify({
        'enrolled': enrollment is not None,
        'enrollment_id': enrollment.id if enrollment else None,
        'status': enrollment.status if enrollment else None
    })

@events_bp.route('/admin/events/<int:event_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_event(event_id):
    """Admin: Edit event"""
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        try:
            # Update event data
            event.title = request.form.get('title', '').strip()
            event.description = request.form.get('description', '').strip()
            event.venue = request.form.get('venue', '').strip()
            event.fee = float(request.form.get('fee', 0.0))
            event.tutors = request.form.get('tutors', '').strip()
            event.poster_url = request.form.get('poster_url', '').strip()
            event.capacity = int(request.form.get('capacity', 50))
            event.is_active = request.form.get('is_active') == 'true'
            
            # Parse dates
            start_date_str = request.form.get('start_date', '').strip()
            end_date_str = request.form.get('end_date', '').strip()
            
            if start_date_str:
                event.start_date = datetime.fromisoformat(start_date_str.replace('T', ' '))
            if end_date_str:
                event.end_date = datetime.fromisoformat(end_date_str.replace('T', ' '))
            
            # Validate
            if not all([event.title, event.description, event.venue]):
                flash('Please fill in all required fields', 'danger')
                return render_template('admin_event_form.html', event=event)
            
            if event.end_date <= event.start_date:
                flash('End date must be after start date', 'danger')
                return render_template('admin_event_form.html', event=event)
            
            db.session.commit()
            flash('Event updated successfully!', 'success')
            return redirect(url_for('events.admin_events'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating event: {str(e)}', 'danger')
            return render_template('admin_event_form.html', event=event)
    
    return render_template('admin_event_form.html', event=event)


@events_bp.route('/admin/events/<int:event_id>/delete', methods=['POST'])
@admin_required
def admin_delete_event(event_id):
    """Admin: Delete event"""
    try:
        event = Event.query.get_or_404(event_id)
        db.session.delete(event)
        db.session.commit()
        flash('Event deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting event: {str(e)}', 'danger')
    
    return redirect(url_for('events.admin_events'))

# ============ ENROLLMENT CRUD (Admin) ============

@events_bp.route('/admin/enrollments')
@admin_required
def admin_enrollments():
    """Admin: List all enrollments"""
    enrollments = Enrollment.query.order_by(Enrollment.enrollment_date.desc()).all()
    return render_template('admin_enrollments.html', enrollments=enrollments)

@events_bp.route('/admin/enrollments/new', methods=['GET', 'POST'])
@admin_required
def admin_new_enrollment():
    """Admin: Create new enrollment"""
    events = Event.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        try:
            # Parse form data
            username = request.form.get('username', '').strip()
            full_name = request.form.get('full_name', '').strip()
            email = "lyxnexus_user@gmail.com"
            phone = request.form.get('phone', '').strip()
            event_id = int(request.form.get('event_id', 0))
            notes = request.form.get('notes', '').strip()
            
            # Validate required fields
            if not all([username, full_name, event_id]):
                flash('Please fill in all required fields', 'danger')
                return render_template('admin_enrollment_form.html', events=events)
            
            # Check event capacity
            event = Event.query.get(event_id)
            if not event:
                flash('Event not found', 'danger')
                return render_template('admin_enrollment_form.html', events=events)
            
            if len(event.enrollments) >= event.capacity:
                flash('Event is full', 'danger')
                return render_template('admin_enrollment_form.html', events=events)
            
            # Check if already enrolled
            existing = Enrollment.query.filter_by(
                username=username,
                event_id=event_id
            ).first()
            
            if existing:
                flash('User is already enrolled in this event', 'danger')
                return render_template('admin_enrollment_form.html', events=events)
            
            # Create enrollment
            enrollment = Enrollment(
                username=username,
                full_name=full_name,
                email=email,
                phone=phone,
                event_id=event_id,
                notes=notes
            )
            
            db.session.add(enrollment)
            db.session.commit()
            
            flash('Enrollment created successfully!', 'success')
            return redirect(url_for('events.admin_enrollments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating enrollment: {str(e)}', 'danger')
            return render_template('admin_enrollment_form.html', events=events)
    
    return render_template('admin_enrollment_form.html', events=events)

@events_bp.route('/enroll/<int:event_id>', methods=['GET', 'POST'])
@login_required
def enroll(event_id=None):
    """User enrollment for events"""
    
    # Get the event if specific ID is provided
    event = None
    if event_id:
        event = Event.query.get_or_404(event_id)
        if not event.is_active:
            flash('This event is no longer available for enrollment', 'danger')
            return redirect(url_for('events.index'))
    
    # Get all active events if no specific event
    events = Event.query.filter_by(is_active=True).all() if not event else None
    
    # Check if user is already enrolled in this event
    if event:
        existing_enrollment = Enrollment.query.filter_by(
            username=current_user.username,
            event_id=event.id
        ).first()
        
        if existing_enrollment:
            flash('You are already enrolled in this event!', 'info')
            return redirect(url_for('events.index'))
    
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form.get('username', '').strip()
            full_name = request.form.get('full_name', '').strip()
            email = "lyxnexus_user@gmail.com"
            phone = request.form.get('phone', '').strip()
            event_id = int(request.form.get('event_id', 0))
            notes = request.form.get('notes', '').strip()
            
            # Validate required fields
            if not all([username, full_name, event_id]):
                flash('Please fill in all required fields', 'danger')
                return render_template('enrollment.html', event=event, events=events)
            
            # Verify username matches current user (prevent enrollment for others)
            if username != current_user.username:
                flash('You can only enroll with your own username', 'danger')
                return render_template('enrollment.html', event=event, events=events)
            
            # Get the event
            if not event:  # If event wasn't passed in URL, get it from form
                event = Event.query.get(event_id)
            
            if not event or not event.is_active:
                flash('Event not found or no longer active', 'danger')
                return render_template('enrollment.html', event=event, events=events)
            
            # Check event capacity
            if len(event.enrollments) >= event.capacity:
                flash('This event is full. Please try another event.', 'danger')
                return render_template('enrollment.html', event=event, events=events)
            
            # Check if already enrolled (double-check)
            existing = Enrollment.query.filter_by(
                username=username,
                event_id=event_id
            ).first()
            
            if existing:
                flash('You are already enrolled in this event', 'info')
                return redirect(url_for('events.index'))
            
            # Create enrollment with default status
            enrollment = Enrollment(
                username=username,
                full_name=full_name,
                email=email,
                phone=phone,
                event_id=event_id,
                notes=notes,
                status='pending',  # Default status for user enrollments
                payment_status='unpaid'  # Default payment status
            )
            
            db.session.add(enrollment)
            db.session.commit()
            
            flash('Successfully enrolled! Your enrollment is pending approval.', 'success')
            return redirect(url_for('events.enrollment_confirmation', enrollment_id=enrollment.id))
            
        except ValueError:
            flash('Invalid event selection', 'danger')
            return render_template('enrollment.html', event=event, events=events)
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating enrollment: {str(e)}', 'danger')
            return render_template('enrollment.html', event=event, events=events)
    
    return render_template('enrollment.html', event=event, events=events)

@events_bp.route('/admin/enrollments/<int:enrollment_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_enrollment(enrollment_id):
    """Admin: Edit enrollment"""
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    events = Event.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        try:
            # Update enrollment data
            enrollment.username = request.form.get('username', '').strip()
            enrollment.full_name = request.form.get('full_name', '').strip()
            enrollment.email = request.form.get('email', '').strip()
            enrollment.phone = request.form.get('phone', '').strip()
            enrollment.event_id = int(request.form.get('event_id', 0))
            enrollment.status = request.form.get('status', 'pending')
            enrollment.payment_status = request.form.get('payment_status', 'unpaid')
            enrollment.notes = request.form.get('notes', '').strip()
            
            # Validate required fields
            if not all([enrollment.username, enrollment.full_name, enrollment.email, enrollment.event_id]):
                flash('Please fill in all required fields', 'danger')
                return render_template('admin_enrollment_form.html', 
                                     enrollment=enrollment, 
                                     events=events)
            
            db.session.commit()
            flash('Enrollment updated successfully!', 'success')
            return redirect(url_for('events.admin_enrollments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating enrollment: {str(e)}', 'danger')
            return render_template('admin_enrollment_form.html', 
                                 enrollment=enrollment, 
                                 events=events)
    
    return render_template('admin_enrollment_form.html', 
                         enrollment=enrollment, 
                         events=events)

@events_bp.route('/admin/enrollments/<int:enrollment_id>/delete', methods=['POST'])
@admin_required
def admin_delete_enrollment(enrollment_id):
    """Admin: Delete enrollment"""
    try:
        enrollment = Enrollment.query.get_or_404(enrollment_id)
        db.session.delete(enrollment)
        db.session.commit()
        flash('Enrollment deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting enrollment: {str(e)}', 'danger')
    
    return redirect(url_for('events.admin_enrollments'))

# ============ API ENDPOINTS ============

@events_bp.route('/api/events')
def api_events():
    """Get all events (API)"""
    events = Event.query.filter_by(is_active=True).order_by(Event.start_date.asc()).all()
    return jsonify({
        'success': True,
        'events': [event.to_dict() for event in events]
    })

@events_bp.route('/api/events/<int:event_id>')
def api_event_detail(event_id):
    """Get single event (API)"""
    event = Event.query.get_or_404(event_id)
    return jsonify({
        'success': True,
        'event': event.to_dict()
    })

@events_bp.route('/api/events/<int:event_id>/enrollments')
def api_event_enrollments(event_id):
    """Get event enrollments (API)"""
    enrollments = Enrollment.query.filter_by(event_id=event_id).all()
    return jsonify({
        'success': True,
        'enrollments': [enrollment.to_dict() for enrollment in enrollments]
    })

@events_bp.route('/api/enrollments')
def api_all_enrollments():
    """Get all enrollments (API)"""
    enrollments = Enrollment.query.order_by(Enrollment.enrollment_date.desc()).all()
    return jsonify({
        'success': True,
        'enrollments': [enrollment.to_dict() for enrollment in enrollments]
    })

@events_bp.route('/api/events', methods=['POST'])
@admin_required
def api_create_event():
    """Create event (API)"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    try:
        # Validate required fields
        required_fields = ['title', 'description', 'venue', 'start_date', 'end_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        # Create event
        event = Event(
            title=data['title'],
            description=data['description'],
            venue=data['venue'],
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            fee=data.get('fee', 0.0),
            tutors=data.get('tutors', ''),
            poster_url=data.get('poster_url', ''),
            capacity=data.get('capacity', 50),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(event)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Event created successfully',
            'event': event.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@events_bp.route('/api/enroll', methods=['POST'])
@admin_required
def api_enroll():
    """Enroll in event (API)"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    try:
        # Validate required fields
        required_fields = ['username', 'full_name', 'email', 'event_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        event_id = data['event_id']
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify({'success': False, 'error': 'Event not found'}), 404
        
        if not event.is_active:
            return jsonify({'success': False, 'error': 'Event is not active'}), 400
        
        # Check capacity
        if len(event.enrollments) >= event.capacity:
            return jsonify({'success': False, 'error': 'Event is full'}), 400
        
        # Check if already enrolled
        existing = Enrollment.query.filter_by(
            username=data['username'],
            event_id=event_id
        ).first()
        
        if existing:
            return jsonify({'success': False, 'error': 'Already enrolled in this event'}), 400
        
        # Create enrollment
        enrollment = Enrollment(
            username=data['username'],
            full_name=data['full_name'],
            email=data['email'],
            phone=data.get('phone', ''),
            event_id=event_id,
            notes=data.get('notes', '')
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Successfully enrolled',
            'enrollment': enrollment.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@events_bp.route('/api/enrollments/<string:username>')
def api_user_enrollments(username):
    """Get user's enrollments (API)"""
    enrollments = Enrollment.query.filter_by(username=username).order_by(Enrollment.enrollment_date.desc()).all()
    return jsonify({
        'success': True,
        'enrollments': [enrollment.to_dict() for enrollment in enrollments]
    })