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
    Let's make script to add +1 year to all users except those with operator and creator year(5)
    '''

    users = User.query.all()
    all_users = len(users)
    passed = 0
    
    # Let's try increment by +1 watching out for any errors
    for user in users:
        if user.year == 5:  # Operator/creator accounts
            passed += 1
            print("Passing Operator account...")
            continue
        try:
            user.year += 1
            db.session.add(user)
        except Exception as e:
            db.session.rollback()
            print(f"Incrementation Failed: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to increment user(s)'
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
        return jsonify({"status": "success", "message": "No user(s) incremented"})
    
    return jsonify(
        {
            "status": "success",
            "message": f"All {all_users - passed} user(s) year incremented successfully. | Passed: {passed}"
        }
    )

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
    
    # Let's try decrement by 1 to non operators and year 1(s) watching out for any errors
    for user in users:
        if user.year == 5 or user.year == 1:  # Operator accounts or minimum year
            passed += 1
            print("Passing Operator and year 1...")
            continue
        try:
            user.year -= 1
            db.session.add(user)
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
            "message": f"All {all_users - passed} user(s) year decremented successfully. | Passed: {passed}"
        }
    )

# Add these routes to your modify_year_bp blueprint

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
        year_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
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