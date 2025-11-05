from flask import Blueprint, render_template

chloe = Blueprint('chloe', __name__, url_prefix='/ai')

@chloe.route('/chloe')
def chloe():
    return render_template('chloe.html')