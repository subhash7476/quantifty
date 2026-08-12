from scripts.nifty_shield_paper import session


class _FakeDriver:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


def test_stop_handler_calls_driver_stop():
    drv = _FakeDriver()
    handler = session._make_stop_handler(drv)
    handler(15, None)          # signum, frame
    assert drv.stopped is True


def test_stop_handler_swallows_driver_stop_error():
    class _Boom:
        def stop(self):
            raise RuntimeError("already stopping")

    handler = session._make_stop_handler(_Boom())
    handler(15, None)          # must not raise
