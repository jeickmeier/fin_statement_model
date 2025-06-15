import json

import pytest
from pydantic import ValidationError

from fin_statement_model.config.models import (
    APIConfig,
    Config,
    DisplayConfig,
    ForecastingConfig,
    IOConfig,
    LoggingConfig,
    MetricsConfig,
    PreprocessingConfig,
    StatementsConfig,
    ValidationConfig,
)


def test_logging_config_defaults_and_extra_forbidden():
    lc = LoggingConfig()
    assert lc.level == "WARNING"
    # Extra fields are forbidden
    with pytest.raises(ValidationError):
        LoggingConfig(level="INFO", unknown_field=True)


def test_io_config_defaults_and_extra_forbidden():
    ioc = IOConfig()
    assert ioc.default_excel_sheet == "Sheet1"
    with pytest.raises(ValidationError):
        IOConfig(default_excel_sheet="Sheet1", foo="bar")


def test_forecasting_config_validation():
    fc = ForecastingConfig(default_periods=5)
    assert fc.default_periods == 5
    with pytest.raises(ValidationError):
        ForecastingConfig(default_periods=0)


def test_preprocessing_config_defaults_and_extra_forbidden():
    pc = PreprocessingConfig()
    assert pc.fill_missing_with_zero is False
    with pytest.raises(ValidationError):
        PreprocessingConfig(auto_clean_data=True, extra_field=123)


def test_display_config_scale_factor_validation():
    dc = DisplayConfig(scale_factor=1.0)
    assert dc.scale_factor == 1.0
    with pytest.raises(ValidationError):
        DisplayConfig(scale_factor=0)


def test_api_config_positive_validation():
    ac = APIConfig(api_timeout=10, api_retry_count=2, cache_ttl_hours=5)
    assert ac.api_timeout == 10
    with pytest.raises(ValidationError):
        APIConfig(api_timeout=0)
    with pytest.raises(ValidationError):
        APIConfig(api_retry_count=-1)
    with pytest.raises(ValidationError):
        APIConfig(cache_ttl_hours=0)


def test_metrics_config_defaults_and_extra_forbidden():
    mc = MetricsConfig()
    assert mc.validate_metric_inputs is True
    with pytest.raises(ValidationError):
        MetricsConfig(validate_metric_inputs=False, unknown=1)


def test_validation_config_tolerance_validation():
    vc = ValidationConfig(balance_tolerance=0.5)
    assert vc.balance_tolerance == 0.5
    with pytest.raises(ValidationError):
        ValidationConfig(balance_tolerance=-0.1)


def test_statements_config_defaults_and_extra_forbidden():
    sc = StatementsConfig()
    assert sc.enable_node_validation is False
    with pytest.raises(ValidationError):
        StatementsConfig(foo="bar")


def test_config_to_dict_and_yaml_and_from_dict_and_from_yaml(tmp_path):
    cfg = Config()
    d = cfg.to_dict()
    # config_file_path should be excluded if None
    assert "config_file_path" not in d
    assert "logging" in d and "io" in d

    # to_yaml returns YAML string
    yaml_str = cfg.to_yaml()
    assert isinstance(yaml_str, str) and "logging:" in yaml_str

    # round-trip from_dict
    data = {"project_name": "test_proj"}
    cfg2 = Config.from_dict(data)
    assert cfg2.project_name == "test_proj"

    # round-trip from_yaml
    cfg3 = Config.from_yaml(yaml_str)
    assert cfg3.to_dict() == cfg.to_dict()

    # from_file with yaml
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(yaml_str)
    cfg4 = Config.from_file(yaml_file)
    assert cfg4.to_dict() == cfg.to_dict()

    # from_file with json
    json_file = tmp_path / "config.json"
    json_file.write_text(json.dumps(cfg.to_dict()))
    cfg5 = Config.from_file(json_file)
    assert cfg5.to_dict() == cfg.to_dict()
