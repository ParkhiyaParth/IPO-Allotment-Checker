from app.services import push_token_repository


def test_register_without_device_id_defaults_to_empty():
    push_token_repository.register("ExponentPushToken[abc]")

    assert push_token_repository.get_all() == ["ExponentPushToken[abc]"]
    assert push_token_repository.get_by_device_id("") == ["ExponentPushToken[abc]"]


def test_register_with_device_id_scopes_the_token():
    push_token_repository.register("ExponentPushToken[abc]", "device-1")

    assert push_token_repository.get_by_device_id("device-1") == ["ExponentPushToken[abc]"]
    assert push_token_repository.get_by_device_id("device-2") == []
    # get_all() must still return every token regardless of device_id --
    # the broadcast notify_* functions rely on this.
    assert push_token_repository.get_all() == ["ExponentPushToken[abc]"]


def test_re_registering_same_token_updates_device_id():
    push_token_repository.register("ExponentPushToken[abc]", "device-1")
    push_token_repository.register("ExponentPushToken[abc]", "device-2")

    assert push_token_repository.get_by_device_id("device-1") == []
    assert push_token_repository.get_by_device_id("device-2") == ["ExponentPushToken[abc]"]
