from flask import render_template, jsonify, request

from . import backtest_bp
from flask_app.middleware import login_required
from app_facade.backtest_facade import BacktestFacade
from core.logging import setup_logger

logger = setup_logger("backtest_bp")


def _get_facade() -> BacktestFacade:
    return BacktestFacade()


@backtest_bp.route('/')
@login_required
def index():
    return render_template('backtest/index.html')


@backtest_bp.route('/api/strategies')
@login_required
def list_strategies():
    try:
        facade = _get_facade()
        strategies = facade.list_strategies()
        return jsonify({"success": True, "strategies": strategies})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@backtest_bp.route('/api/symbols')
@login_required
def list_symbols():
    try:
        facade = _get_facade()
        symbols = facade.get_futures_symbols()
        return jsonify({"success": True, "count": len(symbols), "symbols": symbols[:5]})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@backtest_bp.route('/api/run', methods=['POST'])
@login_required
def run_backtest():
    try:
        data = request.get_json()
        facade = _get_facade()
        job = facade.run_backtest(
            strategy_id=data["strategy_id"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            params=data.get("params"),
        )
        return jsonify({"success": True, "job": job})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@backtest_bp.route('/api/status/<job_id>')
@login_required
def job_status(job_id):
    try:
        facade = _get_facade()
        result = facade.get_job_status(job_id)
        if result is None:
            return jsonify({"success": True, "job": None})
        return jsonify({"success": True, "job": result})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
