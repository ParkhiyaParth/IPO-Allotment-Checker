from app.services import device_pan_repository


def test_replace_for_device_inserts_new_entries():
    device_pan_repository.replace_for_device("device-1", [("pan-a", "Alice", "cipher-a")])

    all_pans = device_pan_repository.get_all()
    assert len(all_pans) == 1
    assert all_pans[0].device_id == "device-1"
    assert all_pans[0].label == "Alice"
    assert all_pans[0].pan_encrypted == "cipher-a"


def test_replace_for_device_removes_entries_no_longer_present():
    device_pan_repository.replace_for_device(
        "device-1", [("pan-a", "Alice", "cipher-a"), ("pan-b", "Bob", "cipher-b")]
    )

    # Second sync omits pan-b -- it must be deleted, not left stale.
    device_pan_repository.replace_for_device("device-1", [("pan-a", "Alice", "cipher-a-updated")])

    all_pans = device_pan_repository.get_all()
    assert len(all_pans) == 1
    assert all_pans[0].pan_encrypted == "cipher-a-updated"


def test_replace_for_device_does_not_affect_other_devices():
    device_pan_repository.replace_for_device("device-1", [("pan-a", "Alice", "cipher-a")])
    device_pan_repository.replace_for_device("device-2", [("pan-b", "Bob", "cipher-b")])

    device_pan_repository.replace_for_device("device-1", [])

    remaining = device_pan_repository.get_all()
    assert len(remaining) == 1
    assert remaining[0].device_id == "device-2"


def test_delete_for_device_removes_all_its_entries():
    device_pan_repository.replace_for_device("device-1", [("pan-a", "Alice", "cipher-a")])

    device_pan_repository.delete_for_device("device-1")

    assert device_pan_repository.get_all() == []


def test_update_last_result_sets_status_and_timestamp():
    device_pan_repository.replace_for_device("device-1", [("pan-a", "Alice", "cipher-a")])
    pan_id = device_pan_repository.get_all()[0].id

    device_pan_repository.update_last_result(pan_id, "ALLOTTED", "2026-08-18T10:00:00Z")

    updated = device_pan_repository.get_all()[0]
    assert updated.last_status == "ALLOTTED"
    assert updated.last_checked_at == "2026-08-18T10:00:00Z"
