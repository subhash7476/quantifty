from core.database.locks import WriterLock


def test_second_writer_is_refused_while_the_first_holds_the_lock(tmp_path):
    path = str(tmp_path / "store.lock")
    first = WriterLock(path)
    assert first.acquire(timeout=0)
    try:
        assert WriterLock(path).acquire(timeout=0) is False
    finally:
        first.release()


def test_lock_is_free_again_after_release(tmp_path):
    path = str(tmp_path / "store.lock")
    with WriterLock(path):
        pass
    second = WriterLock(path)
    assert second.acquire(timeout=0)
    second.release()
