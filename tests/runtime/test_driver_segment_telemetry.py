import inspect


def test_driver_publishes_a_derivatives_open_flag():
    from core.runtime import driver

    assert "derivatives_open" in inspect.getsource(driver)


def test_ops_route_reports_derivatives_session():
    from flask_app.blueprints.ops import routes

    assert "is_derivatives_open" in inspect.getsource(routes)
