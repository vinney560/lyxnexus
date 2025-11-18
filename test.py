from flask import Blueprint, redirect, url_for, render_template
from flask_login import current_user, login_required

test_routes = Blueprint('test_routes', __name__, url_prefix='/test')

print('Reached TEST')
@test_routes.route('/template')
def test_template():
    return render_template('test.html')

@test_routes.route('/notification')
def test_notification():
    return render_template('notification.html')

@test_routes.route('/ai/chloe')
@login_required
def ai_lyxin():
    """Render the LyxNexus AI information page"""
    api_keys = [
        'AIzaSyA3o8aKHTnVzuW9-qg10KjNy7Lcgn19N2I',
        'AIzaSyCq8-xrPTC40k8E_i3vXZ_-PR6RiPsuOno'
    ]
    return render_template('talkAI.html', api_keys=api_keys)
