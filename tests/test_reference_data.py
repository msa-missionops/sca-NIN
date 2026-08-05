"""Tests for reference/tag data loading (Phase 1F)."""

import pytest

from nin_pipeline.reference_data import active_plant, load_reference_data


def write_reference_data(folder):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "region.csv").write_text("Plant,Region\nUS01,Northeast\n")
    (folder / "top60.csv").write_text(
        "plant_material_key,plant,material,top_60_flag\nUS01-123,US01,123,top60\n"
    )
    (folder / "sourceplant.csv").write_text(
        "source_key,desc,source_plant\n40,Subcontract,US02\n"
    )
    (folder / "rec_req_type.csv").write_text(
        "type,negative\nVJ,true\nPP,false\nU1,1\nWB,0\nVC,yes\nVG,no\n"
    )
    (folder / "plant_evaluation.csv").write_text("Plant\n us01 \n")


def test_load_reference_data_parses_negative_flags_case_insensitively(tmp_path):
    folder = tmp_path / "reference_data"
    write_reference_data(folder)

    ref = load_reference_data(folder)

    rec = ref.rec_req_type.set_index("type")["negative"]
    assert bool(rec["VJ"]) is True
    assert bool(rec["PP"]) is False
    assert bool(rec["U1"]) is True
    assert bool(rec["WB"]) is False
    assert bool(rec["VC"]) is True
    assert bool(rec["VG"]) is False


def test_active_plant_trims_and_upper_cases(tmp_path):
    folder = tmp_path / "reference_data"
    write_reference_data(folder)
    ref = load_reference_data(folder)

    assert active_plant(ref) == "US01"


def test_load_reference_data_raises_when_file_missing(tmp_path):
    folder = tmp_path / "reference_data"
    folder.mkdir()

    with pytest.raises(FileNotFoundError):
        load_reference_data(folder)
