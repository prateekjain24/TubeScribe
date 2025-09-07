from ytx.config import AppConfig


def test_config_hash_stable_with_engine_options_order():
    cfg1 = AppConfig(engine="whisper", model="small", engine_options={"a": 1, "b": 2})
    cfg2 = AppConfig(engine="whisper", model="small", engine_options={"b": 2, "a": 1})
    assert cfg1.config_hash() == cfg2.config_hash()

