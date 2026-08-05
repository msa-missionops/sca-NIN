"""Tests for pipeline configuration loading (Phase 1F)."""

import pytest

from nin_pipeline.config import load_config


def write_config(tmp_path, extra: str = "") -> str:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        f"""
paths:
  prdpl3_folder: "{tmp_path}/prdpl3"
  mrp_rec_folder: "{tmp_path}/mrp_rec"
  mrp_doh_folder: "{tmp_path}/mrp_doh"
  mb5t_folder: "{tmp_path}/mb5t"
  reference_data_folder: "{tmp_path}/reference_data"
  output_folder: "{tmp_path}/output"
  run_folder: "{tmp_path}/runs"
  log_folder: "{tmp_path}/logs"
{extra}
""",
        encoding="utf-8",
    )
    return str(config_path)


def test_load_config_reads_paths_and_defaults(tmp_path):
    config = load_config(write_config(tmp_path))

    assert config.paths.prdpl3_folder == tmp_path / "prdpl3"
    assert config.paths.output_folder == tmp_path / "output"
    assert config.file_selection.strategy == "latest_modified"
    assert config.output.write_csv is True


def test_load_config_reads_overridden_sections(tmp_path):
    extra = """
file_selection:
  strategy: latest_created
  ignore_hidden: false
output:
  write_parquet: false
  write_csv: true
  write_excel: false
"""
    config = load_config(write_config(tmp_path, extra))

    assert config.file_selection.strategy == "latest_created"
    assert config.file_selection.ignore_hidden is False
    assert config.output.write_parquet is False
    assert config.output.write_excel is False


def test_load_config_raises_on_missing_required_path(tmp_path):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text('paths:\n  prdpl3_folder: "x"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="mrp_rec_folder"):
        load_config(config_path)


def test_load_config_accepts_reference_data_workbook_instead_of_folder(tmp_path):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        f"""
paths:
  prdpl3_folder: "{tmp_path}/prdpl3"
  mrp_rec_folder: "{tmp_path}/mrp_rec"
  mrp_doh_folder: "{tmp_path}/mrp_doh"
  mb5t_folder: "{tmp_path}/mb5t"
  reference_data_workbook: "{tmp_path}/reference_data.xlsx"
  output_folder: "{tmp_path}/output"
  run_folder: "{tmp_path}/runs"
  log_folder: "{tmp_path}/logs"
""",
        encoding="utf-8",
    )
    config = load_config(config_path)

    assert config.paths.reference_data_workbook == tmp_path / "reference_data.xlsx"
    assert config.paths.reference_data_folder is None


def test_load_config_raises_when_both_reference_data_options_set(tmp_path):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        f"""
paths:
  prdpl3_folder: "{tmp_path}/prdpl3"
  mrp_rec_folder: "{tmp_path}/mrp_rec"
  mrp_doh_folder: "{tmp_path}/mrp_doh"
  mb5t_folder: "{tmp_path}/mb5t"
  reference_data_folder: "{tmp_path}/reference_data"
  reference_data_workbook: "{tmp_path}/reference_data.xlsx"
  output_folder: "{tmp_path}/output"
  run_folder: "{tmp_path}/runs"
  log_folder: "{tmp_path}/logs"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Exactly one"):
        load_config(config_path)


def test_load_config_raises_when_neither_reference_data_option_set(tmp_path):
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        f"""
paths:
  prdpl3_folder: "{tmp_path}/prdpl3"
  mrp_rec_folder: "{tmp_path}/mrp_rec"
  mrp_doh_folder: "{tmp_path}/mrp_doh"
  mb5t_folder: "{tmp_path}/mb5t"
  output_folder: "{tmp_path}/output"
  run_folder: "{tmp_path}/runs"
  log_folder: "{tmp_path}/logs"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Exactly one"):
        load_config(config_path)
