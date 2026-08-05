"""Tests for the common SAP-export file discovery/reading utilities
(Phase 1C — src/nin_pipeline/ingestion/file_reader.py)."""

import os
import time

import pytest

from nin_pipeline.ingestion import (
    detect_sap_header_row,
    find_latest_file,
    find_latest_run_folder,
    find_plant_file,
    read_delimited_text,
)


def _touch(path, content="", mtime_offset=0):
    path.write_text(content, encoding="cp1252")
    if mtime_offset:
        stamp = time.time() + mtime_offset
        os.utime(path, (stamp, stamp))
    return path


def test_find_latest_file_picks_most_recent(tmp_path):
    older = _touch(tmp_path / "PRDPL3_20260101.txt", "a", mtime_offset=-100)
    newer = _touch(tmp_path / "PRDPL3_20260201.txt", "b", mtime_offset=0)
    assert find_latest_file(tmp_path) == newer
    assert older != newer


def test_find_latest_file_ignores_hidden(tmp_path):
    _touch(tmp_path / ".hidden.txt", "a", mtime_offset=100)
    visible = _touch(tmp_path / "visible.txt", "b", mtime_offset=0)
    assert find_latest_file(tmp_path) == visible


def test_find_latest_file_raises_when_empty(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_latest_file(tmp_path)


def test_find_latest_run_folder_picks_most_recent(tmp_path):
    old_run = tmp_path / "20260101_run"
    new_run = tmp_path / "20260201_run"
    old_run.mkdir()
    new_run.mkdir()
    os.utime(old_run, (time.time() - 1000, time.time() - 1000))
    assert find_latest_run_folder(tmp_path) == new_run


def test_find_latest_run_folder_ignores_hidden(tmp_path):
    (tmp_path / ".git").mkdir()
    visible_run = tmp_path / "20260201_run"
    visible_run.mkdir()
    assert find_latest_run_folder(tmp_path) == visible_run


def test_find_latest_run_folder_raises_when_empty(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_latest_run_folder(tmp_path)


def test_find_plant_file_matches_prefix_extension_and_plant(tmp_path):
    match = _touch(tmp_path / "MM_MRP_ELEMENTS_REC_20260201_US01_extract.txt", "x")
    _touch(tmp_path / "MM_MRP_ELEMENTS_REC_20260201_US02_extract.txt", "x")
    _touch(tmp_path / "OTHER_FILE_US01.txt", "x")
    _touch(tmp_path / "MM_MRP_ELEMENTS_REC_20260201_US01_extract.csv", "x")

    result = find_plant_file(
        tmp_path, plant="US01", prefix="MM_MRP_ELEMENTS_REC_", extension="txt"
    )
    assert result == match


def test_find_plant_file_raises_when_no_match(tmp_path):
    _touch(tmp_path / "MM_MRP_ELEMENTS_REC_20260201_US02_extract.txt", "x")
    with pytest.raises(FileNotFoundError):
        find_plant_file(
            tmp_path, plant="US01", prefix="MM_MRP_ELEMENTS_REC_", extension="txt"
        )


def test_read_delimited_text_pipe(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("a | b | c \n1|2|3\n", encoding="cp1252")
    rows = read_delimited_text(path, delimiter="|")
    assert rows == [["a", "b", "c"], ["1", "2", "3"]]


def test_read_delimited_text_tab_placeholder(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("Plnt\tMaterial\tEl\nUS01\t123\tBB\n", encoding="cp1252")
    rows = read_delimited_text(path, delimiter="#(tab)")
    assert rows == [["Plnt", "Material", "El"], ["US01", "123", "BB"]]


def test_detect_sap_header_row_finds_header_beneath_banner_rows():
    rows = [
        ["SAP Export Banner"],
        ["Run date: 2026-02-01"],
        [""],
        ["Plnt", "Material", "El", "Customer Request Date"],
        ["US01", "123", "BB", "2026-02-05"],
    ]
    assert detect_sap_header_row(rows, {"Plnt", "Material", "El"}) == 3


def test_detect_sap_header_row_raises_when_not_found():
    rows = [["not", "a", "header"], ["still", "not"]]
    with pytest.raises(ValueError):
        detect_sap_header_row(rows, {"Plnt", "Material", "El"})
