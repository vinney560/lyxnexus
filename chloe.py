from flask import Blueprint, render_template

_chloe_ai = Blueprint('chloe', __name__, url_prefix='/ai')

@_chloe_ai.route('/chloe')
def chloe():
    return render_template('chloe.html')

print('Reached to Chloe AI') 