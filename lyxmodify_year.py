#!/user/env/bin python3 
"""
! ===== LYXSCRIPT =====
This Script gets all the users as registered in the database __tablename__='user' and increment year of study by +1.
This enables manual and soon automatic change in year.
"""

from flask import Blueprint, jsonify, render_template, abort, request
from flask_login import current_user, login_required
from functools import wraps
from app import db, User

# ============ FIRST BLUEPRINT ============

modify_year_bp = Blueprint('increment_year_bp', __name__, url_prefix='/admin/year')

def admin_required(f):
    @wraps(f)
    def decorator_admin(*args, **kwargs):
        if not current_user.is_admin:
            if request.path.startswith('/admin/year/api') or request.is_json:
                return jsonify(
                    {
                        "status": "error",
                        "message": "Authorization required"
                    }
                ), 403
            abort(403)
        return f(*args, **kwargs)
    return decorator_admin  # REMOVED THE () - THIS WAS THE MAIN ISSUE
    
# Serve the Template at /admin/year/    
@modify_year_bp.route('/')
@login_required
@admin_required
def modify_year():
    return render_template("admin_modify_year.html")

# ============== RUN THE ACTUAL API SCRIPT ==============

@modify_year_bp.route('/api/increment-year')
@login_required
@admin_required
def increment_year():
    '''
    Increment year logic:
    - Years 1-3: Add +1
    - Year 4: Change to 7 (mutable)
    - Year 5: Immutable (no change)
    - Year 7: Terciary acc
    '''
    
    users = User.query.all()
    all_users = len(users)
    incremented = 0
    skipped = 0
    
    for user in users:
        print(f"Processing {user.username}: Year {user.year}")
        
        # Year 5: Immutable (no change)
        if user.year == 5:
            skipped += 1
            print(f"  Skipping year 5 (immutable): {user.username}")
            continue
            
        # Year 7: Immutable (no change)
        if user.year == 7:
            skipped += 1
            print(f"  Skipping year 7 (already immutable): {user.username}")
            continue
            
        # Year 4: Change to 7
        if user.year == 4:
            old_year = user.year
            user.year = 7
            db.session.add(user)
            incremented += 1
            print(f"  Changed {user.username} from year {old_year} to 7 (now immutable)")
            continue
            
        # Years 1-3: Add +1
        if user.year in [1, 2, 3]:
            old_year = user.year
            user.year += 1
            db.session.add(user)
            incremented += 1
            print(f"  Incremented {user.username} from year {old_year} to {user.year}")
            continue
            
        # Year 0 or any other unexpected year - skip or handle as needed
        skipped += 1
        print(f"  Skipping unexpected year {user.year}: {user.username}")
    
    try:
        db.session.commit()
        print(f"Successfully committed changes. Incremented: {incremented}, Skipped: {skipped}")
        
    except Exception as e:
        db.session.rollback()
        print(f"Commit Failed: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to save changes to database',
            'error': str(e)
        }), 500
    
    if incremented == 0:
        return jsonify({
            "status": "success", 
            "message": f"No users were incremented. {skipped} users were skipped."
        })
    
    return jsonify({
        "status": "success",
        "message": f"Year increment completed successfully{'. Incremented: {incremented}, Skipped: {skipped}'}",
    })

@modify_year_bp.route('/api/decrement-year')
@login_required
@admin_required
def decrement_year():
    ''' 
    Let's make script to add -1 year to all users except those with operator and creator year(5)
    '''

    users = User.query.all()
    all_users = len(users)
    passed = 0
    decremented = 0
    
    # Let's try decrement by 1 to non operators and year 1(s) watching out for any errors
    for user in users:
        if user.year == 5 or user.year == 1:  # Operator accounts or minimum year
            passed += 1
            print("Passing Operator and year 1...")
            continue

        # Year 7: Change to 4
        if user.year == 7:
            old_year = user.year
            user.year = 4
            db.session.add(user)
            decremented += 1
            print(f"  Changed {user.username} from year {old_year} to 7 (now immutable)")
            continue

        try:
            old_year = user.year
            user.year -= 1
            db.session.add(user)
            decremented += 1
            print(f"  Decremented {user.username} from year {old_year} to {user.year}")
            continue
        except Exception as e:
            db.session.rollback()
            print(f"Decrementation Failed: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to decrement user(s)'
            }), 500
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Commit Failed: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to save changes'
        }), 500
        
    if passed >= all_users: 
        return jsonify({"status": "success", "message": "No user(s) decremented"})
            
    return jsonify(
        {
            "status": "success",
            "message": f"All {decremented} user(s) year decremented successfully. | Passed: {passed}"
        }
    )
# ========================================
@modify_year_bp.route('/api/statistics')
@login_required
@admin_required
def get_statistics():
    """Get system statistics for the dashboard"""
    try:
        # Get all users
        users = User.query.all()
        total_users = len(users)
        
        # Count active users (assuming status=True means active)
        active_users = User.query.filter_by(status=True).count()
        
        # Count operators (year=5)
        operator_count = User.query.filter_by(year=5).count()
        
        # Calculate average year
        total_years = sum(user.year for user in users)
        avg_year = total_years / total_users if total_users > 0 else 0
        
        # Get year distribution
        year_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0}
        for user in users:
            if user.year in year_distribution:
                year_distribution[user.year] += 1
        
        return jsonify({
            'status': 'success',
            'totalUsers': total_users,
            'activeUsers': active_users,
            'operatorCount': operator_count,
            'avgYear': round(avg_year, 2),
            'yearDistribution': year_distribution
        })
        
    except Exception as e:
        print(f"Error getting statistics: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to load statistics'
        }), 500

@modify_year_bp.route('/api/preview/increment')
@login_required
@admin_required
def preview_increment():
    """Preview which users will be affected by increment"""
    try:
        users = User.query.all()
        total_users = len(users)
        operator_count = User.query.filter_by(year=5).count()
        affected_count = total_users - operator_count
        
        # Get detailed breakdown
        breakdown = {}
        for user in users:
            if user.year < 5:
                if user.year not in breakdown:
                    breakdown[user.year] = {'count': 0, 'users': []}
                breakdown[user.year]['count'] += 1
                breakdown[user.year]['users'].append({
                    'id': user.id,
                    'username': user.username
                })
        
        return jsonify({
            'status': 'success',
            'totalUsers': total_users,
            'operatorCount': operator_count,
            'affectedCount': affected_count,
            'breakdown': breakdown,
            'summary': f'{affected_count} users will advance by +1 year, {operator_count} operators will be skipped'
        })
        
    except Exception as e:
        print(f"Error in preview increment: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate preview'
        }), 500

@modify_year_bp.route('/api/preview/decrement')
@login_required
@admin_required
def preview_decrement():
    """Preview which users will be affected by decrement"""
    try:
        users = User.query.all()
        total_users = len(users)
        year1_count = User.query.filter_by(year=1).count()
        operator_count = User.query.filter_by(year=5).count()
        affected_count = total_users - year1_count - operator_count
        
        # Get detailed breakdown
        breakdown = {}
        for user in users:
            if 1 < user.year < 5:
                if user.year not in breakdown:
                    breakdown[user.year] = {'count': 0, 'users': []}
                breakdown[user.year]['count'] += 1
                breakdown[user.year]['users'].append({
                    'id': user.id,
                    'username': user.username
                })
        
        return jsonify({
            'status': 'success',
            'totalUsers': total_users,
            'year1Count': year1_count,
            'operatorCount': operator_count,
            'affectedCount': affected_count,
            'breakdown': breakdown,
            'summary': f'{affected_count} users will decrease by -1 year, {year1_count} Year 1 users and {operator_count} operators will be skipped'
        })
        
    except Exception as e:
        print(f"Error in preview decrement: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate preview'
        }), 500