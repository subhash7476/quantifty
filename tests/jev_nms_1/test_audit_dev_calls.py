from scripts.jev_nms_1.audit_dev_calls import audit, id_time

REPORTED_CACHE = "fd27d793be510a1998d80b4d9a556e67fd0256d134a1e7d84cec3fd6f6a839c9"
REPORTED_LEDGER_DEV_COMPLETED = "cad2f30fbc11142284d0f0760ac829702637d74c2e9ebcdb2a4efc4783d17a16"
REPORTED_LEDGER_BEFORE_DEV = "3c7d73f7ceb9aaec2dbe49a19629f33d77a77149f860c40efad0162975b411a0"


def test_development_call_records_are_complete_and_distinct():
    a = audit()
    assert a["by_stage"] == {"S0": 10, "L2": 90, "L3": 100, "development": 1600}
    assert a["dev_by_template"] == {"h15": 1000, "h5": 300, "h30": 300}
    assert a["dev_keys_distinct"] == 1600 and a["dev_keys_equal_started_in_order"]
    assert a["dev_keys_overlap_other_stages"] == 0
    assert a["request_ids_distinct"] == 1600 and a["request_ids_overlap_other_stages"] == 0
    assert a["retries_total"] == 0 and a["per_record_problems"] == []


def test_hashes_match_the_ledger_and_the_development_report():
    a = audit()
    assert a["cache_sha256"] == REPORTED_CACHE == a["calls_completed_event"]["cache_sha256"]
    assert a["analysis_cache_sha256"] == REPORTED_CACHE
    assert a["calls_completed_event"]["records"] == a["calls_completed_event"]["valid"] == 1600
    assert a["ledger_sha256_through_development_completed"] == REPORTED_LEDGER_DEV_COMPLETED
    assert a["ledger_sha256_through_a3_ruling"] == REPORTED_LEDGER_BEFORE_DEV
    assert a["analysis_valid_observations"] == {"15": 1000, "5": 300, "30": 300}


def test_server_issued_fields_agree_with_local_timing():
    a = audit()
    assert a["request_ids_monotonic_in_send_order"]
    assert a["id_time_outside_local_window_max_s"] < 1.0
    assert a["server_date_outside_local_window_max_s"] <= 1.0


def test_id_time_decodes_first_48_bits_as_unix_ms():
    assert id_time("req_01a0b4c05638733eaeb70792c9dbf03b").isoformat().startswith("2026-09-18T13:41:3")
