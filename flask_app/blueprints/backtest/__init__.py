from flask import Blueprint

backtest_bp = Blueprint('backtest', __name__, url_prefix='/backtest')

from . import routes
