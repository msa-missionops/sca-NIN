"""End-to-end integration test for the pipeline orchestration (Phase 1F)."""

import pandas as pd

from nin_pipeline.config import PipelineConfig, load_config
from nin_pipeline.pipeline import run_pipeline

PRDPL3_HEADER = [
    "Plnt",
    "Material",
    "Material Description",
    "BUn",
    "Product hierarchy",
    "Basic material",
    "Basic material 2",
    "MRP Typ",
    "MRP Controller",
    "PuRGrp",
    "DelFlag",
    "MtlSt_XPlt",
    "MtlSt_Plt",
    "X-Chn Mtl St",
    "SG",
    "ProcType",
    "Spec Proc",
    "ABC",
    "MTyp",
    "IPT",
    "PDT",
    "GRT",
    "TRLT",
    "Planning time fence",
    "LotSize",
    "Min. Lot Sze",
    "Rounding val.",
    "Max. Lot Size",
    "Fix. lot size",
    "BUn_1",
    "Safety Stock",
    "Reorder Point",
    "Threshold Qty",
    "AvaiChk",
    "Consumption mode",
    "Bwd cons. per.",
    "Fwd cons.period",
    "BkFlush",
    "PSloc",
    "Language",
    "Tot Valuated Stk",
    "Total Value",
    "Standard price",
    "Price Un",
    "SLife",
    "Propos.SA",
    "ESLoc",
    "R. Profile",
    "ProdS",
]


def _pipe_row(header, overrides):
    values = {name: "" for name in header}
    values.update(overrides)
    return "|" + "|".join(values[name] for name in header) + "|"


def write_prdpl3_export(path, data_rows):
    lines = [f"BANNER LINE {i}" for i in range(6)]
    lines.append(_pipe_row(PRDPL3_HEADER, dict(zip(PRDPL3_HEADER, PRDPL3_HEADER))))
    lines.append(_pipe_row(PRDPL3_HEADER, {}))
    lines.extend(_pipe_row(PRDPL3_HEADER, row) for row in data_rows)
    path.write_text("\n".join(lines), encoding="cp1252")


MB5T_HEADER = [
    "Material",
    "Material Description",
    "Quantity",
    "Plnt",
    "Name 1",
    "Pur. Doc.",
    "Item",
    "SPlt",
    "S",
    "BUn",
    "Amount in LC",
    "Crcy",
    "Quantity_1",
    "OUn",
    "Net Value",
    "Crcy_2",
]


def write_mb5t_export(path, data_rows):
    lines = [f"BANNER LINE {i}" for i in range(3)]
    lines.append(_pipe_row(MB5T_HEADER, dict(zip(MB5T_HEADER, MB5T_HEADER))))
    lines.append(_pipe_row(MB5T_HEADER, {}))
    lines.extend(_pipe_row(MB5T_HEADER, row) for row in data_rows)
    path.write_text("\n".join(lines), encoding="cp1252")


DOH_HEADER = [
    "Plnt",
    "Material",
    "El",
    "Customer Request Date",
    "Rec./reqd.qty",
    "BUn",
]


def write_doh_export(path, data_rows):
    lines = ["Banner text 0", "Banner text 1", ""]
    lines.append("\t".join(DOH_HEADER))
    for row in data_rows:
        lines.append("\t".join(row.get(col, "") for col in DOH_HEADER))
    path.write_text("\n".join(lines), encoding="cp1252")


REC_HEADER = [
    "Plnt",
    "Material",
    "El",
    "Customer Request Date",
    "Rec./reqd.qty",
    "BUn",
]


def write_rec_export(path, data_rows):
    lines = ["Banner text 0", "Banner text 1", ""]
    lines.append("\t".join(REC_HEADER))
    for row in data_rows:
        lines.append("\t".join(row.get(col, "") for col in REC_HEADER))
    path.write_text("\n".join(lines), encoding="cp1252")


def write_reference_data(folder):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "region.csv").write_text("Plant,Region\nUS01,Northeast\n")
    (folder / "top60.csv").write_text("plant_material_key,plant,material,top_60_flag\n")
    (folder / "sourceplant.csv").write_text("source_key,desc,source_plant\n")
    (folder / "rec_req_type.csv").write_text("type,negative\n")
    (folder / "plant_evaluation.csv").write_text("Plant\nUS01\n")
    (folder / "bobl.csv").write_text(
        "PowerBI Consolidated Backlog by PG Last N Weeks[Plant],"
        "PowerBI Consolidated Backlog by PG Last N Weeks"
        "[Material.Material Level 01.Key],"
        "[SumBackorder_Actual],[SumBackorder_Quantity],"
        "[SumBacklog_Quantity],[SumBacklog_Actual]\n"
        "US01,123,1,2,3,4\n"
    )


def make_config(tmp_path) -> PipelineConfig:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        f"""
paths:
  prdpl3_folder: "{tmp_path / 'prdpl3'}"
  mrp_rec_folder: "{tmp_path / 'mrp_rec'}"
  mrp_doh_folder: "{tmp_path / 'mrp_doh'}"
  mb5t_folder: "{tmp_path / 'mb5t'}"
  reference_data_folder: "{tmp_path / 'reference_data'}"
  output_folder: "{tmp_path / 'output'}"
  run_folder: "{tmp_path / 'runs'}"
  log_folder: "{tmp_path / 'logs'}"
""",
        encoding="utf-8",
    )
    return load_config(config_path)


def test_run_pipeline_assembles_base_table_end_to_end(tmp_path):
    prdpl3_folder = tmp_path / "prdpl3"
    prdpl3_folder.mkdir()
    write_prdpl3_export(
        prdpl3_folder / "PRDPL3_export.txt",
        [
            {
                "Plnt": "US01",
                "Material": "000123",
                "Product hierarchy": "00020ABC",
                "DelFlag": "",
                "Tot Valuated Stk": "200",
                "Total Value": "5000",
                "Safety Stock": "10",
            }
        ],
    )

    mb5t_folder = tmp_path / "mb5t"
    mb5t_folder.mkdir()
    write_mb5t_export(
        mb5t_folder / "MB5T_export.txt",
        [{"Plnt": "US01", "Material": "000123", "Quantity": "7"}],
    )

    doh_run_folder = tmp_path / "mrp_doh" / "20260201_run"
    doh_run_folder.mkdir(parents=True)
    write_doh_export(
        doh_run_folder / "MM_MRP_ELEMENTS_DOH_20260201_US01_x.txt",
        [
            {
                "Plnt": "US01",
                "Material": "000123",
                "El": "VJ",
                "Customer Request Date": "2026-12-06",
                "Rec./reqd.qty": "30",
                "BUn": "EA",
            }
        ],
    )

    rec_run_folder = tmp_path / "mrp_rec" / "20260201_run"
    rec_run_folder.mkdir(parents=True)
    write_rec_export(
        rec_run_folder / "MM_MRP_ELEMENTS_REC_20260201_US01_x.txt",
        [
            {
                "Plnt": "US01",
                "Material": "000123",
                "El": "VJ",
                "Customer Request Date": "2026-12-04",  # Friday -> week 1
                "Rec./reqd.qty": "10",
                "BUn": "EA",
            },
            {
                "Plnt": "US01",
                "Material": "000123",
                "El": "VJ",
                "Customer Request Date": "2026-12-11",  # next Friday -> week 2
                "Rec./reqd.qty": "5",
                "BUn": "EA",
            },
        ],
    )

    write_reference_data(tmp_path / "reference_data")

    config = make_config(tmp_path)
    result = run_pipeline(config, run_id="20260201_000000")

    assert len(result.base_table) == 1
    row = result.base_table.iloc[0]
    assert row["plant_material_key"] == "US01-123"
    assert row["Quantity in Transit"] == 7
    assert row["VJ"] == 30
    # Available Stock = max(0, 200 - (30+0+0+0)) = 170
    assert row["Available Stock"] == 170
    assert row["Backorder Actual"] == 1
    assert row["Backlog Qnty"] == 3

    # Weekly REC forecast transpose: week 1 = earliest Week Ending (10),
    # week 2 = next (5), remaining weeks default to 0, Total Forecast (Qty)
    # = sum of week 1..27 only.
    assert row["week 1"] == 10
    assert row["week 2"] == 5
    assert row["week 3"] == 0
    assert row["Total Forecast (Qty)"] == 15

    assert result.manifest_path.exists()
    manifest = pd.read_json(result.manifest_path, typ="series")
    assert manifest["run_id"] == "20260201_000000"
    assert manifest["row_counts"]["nin_base_table"] == 1
    assert manifest["row_counts"]["mrp_rec_raw"] == 2

    output_folder = tmp_path / "output"
    assert (output_folder / "nin_base_table.csv").exists()
    assert (output_folder / "nin_base_table.parquet").exists()
    assert (output_folder / "nin_base_table.xlsx").exists()
