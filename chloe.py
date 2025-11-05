from flask import Blueprint, render_template

chloe = Blueprint('chloe', __name__, url_prefix='/clhloe')

print('Reached to chloe')
@chloe.route('/ai')
def chloe():
    return render_template('chloe.html')