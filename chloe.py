from flask import Blueprint, render_template

_chloe_ai = Blueprint('chloe', __name__, url_prefix='/ai')

print('Reached to chloe')
@_chloe_ai.route('/chloe')
def chloe():
    return render_template('chloe.html')