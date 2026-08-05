let
    Source = build_overview_p2_clean,

    // === Helper: convert null/text/number values to safe number ===
    ToNumberOrZero =
        (v as any) as number =>
            let
                n = try Number.From(v) otherwise 0
            in
                if n = null then 0 else n,

    // === Remove deleted materials ===
    removeDeletedMaterials =
        Table.SelectRows(
            Source,
            each [DelFlag] = ""
        ),

    // === Merge DOH demand data ===
    #"Merged Queries" =
        Table.NestedJoin(
            removeDeletedMaterials,
            {"plant_material_key"},
            out_mm_mrp_elements_doh_review,
            {"plant_material_key"},
            "out_zmmmi13a_doh_review",
            JoinKind.LeftOuter
        ),

    // === Bring in key columns from ZMMMI13A_DOH ===
    #"Expanded out_zmmmi13a_doh_review" =
        Table.ExpandTableColumn(
            #"Merged Queries",
            "out_zmmmi13a_doh_review",
            {"WB", "PP", "U2", "VC", "VJ", "VG", "U1"},
            {"WB", "PP", "U2", "VC", "VJ", "VG", "U1"}
        ),

    // === Convert DOH demand columns to safe absolute numbers ===
    AbsDemandColumns =
        Table.TransformColumns(
            #"Expanded out_zmmmi13a_doh_review",
            {
                {"WB", each Number.Abs(ToNumberOrZero(_)), type number},
                {"VJ", each Number.Abs(ToNumberOrZero(_)), type number},
                {"VC", each Number.Abs(ToNumberOrZero(_)), type number},
                {"VG", each Number.Abs(ToNumberOrZero(_)), type number},
                {"PP", each Number.Abs(ToNumberOrZero(_)), type number},
                {"U1", each Number.Abs(ToNumberOrZero(_)), type number},
                {"U2", each Number.Abs(ToNumberOrZero(_)), type number}
            },
            null,
            MissingField.Ignore
        ),

    // === Reorder core columns ===
    #"Reordered Columns" =
        Table.ReorderColumns(
            AbsDemandColumns,
            {
                "plant_material_key",
                "Region",
                "Plant",
                "Major PG",
                "Product hierarchy",
                "Material",
                "Material Description",
                "Source Plant",
                "Safety Stock",
                "BUn",
                "top_60_flag",
                "ABC",
                "Spec Proc",
                "ProcType",
                "TRLT",
                "Tot Valuated Stk",
                "Total Value",
                "Basic material",
                "MRP Typ",
                "MRP Controller",
                "DelFlag",
                "SG",
                "MTyp",
                "IPT",
                "PDT",
                "GRT",
                "Planning time fence",
                "LotSize",
                "Reorder Point",
                "Threshold Qty",
                "AvaiChk",
                "Standard price",
                "Price Un",
                "WB",
                "VJ",
                "VC",
                "VG",
                "PP",
                "U1",
                "U2"
            },
            MissingField.UseNull
        ),

    // === Merge MB5T in-transit quantity ===
    #"Merged Queries1" =
        Table.NestedJoin(
            #"Reordered Columns",
            {"plant_material_key"},
            out_mb5t_review,
            {"plant_material_key"},
            "out_mb5t_review",
            JoinKind.LeftOuter
        ),

    AddMB5TInTransit =
        Table.ExpandTableColumn(
            #"Merged Queries1",
            "out_mb5t_review",
            {"Quantity in Transit"},
            {"Quantity in Transit"}
        ),

    // === Build column Available Stock ===
    AddAvailableStock =
        Table.AddColumn(
            AddMB5TInTransit,
            "Available Stock",
            each
                let
                    TotalStock = ToNumberOrZero([#"Tot Valuated Stk"]),
                    VJ = ToNumberOrZero([VJ]),
                    VC = ToNumberOrZero([VC]),
                    VG = ToNumberOrZero([VG]),
                    U1 = ToNumberOrZero([U1]),
                    x = TotalStock - (VJ + VC + VG + U1)
                in
                    if x <= 0 then 0 else x,
            type number
        ),

    // === Rename final stock/value columns ===
    #"Renamed Columns" =
        Table.RenameColumns(
            AddAvailableStock,
            {
                {"Tot Valuated Stk", "Total Stock Quantity"},
                {"Total Value", "Total Value Stock on Hand"}
            },
            MissingField.Ignore
        ),

  // === Build column Stocked Status based on Total Stock Quantity ===
    AddStockedStatus =
        Table.AddColumn(
            #"Renamed Columns",
            "Stocked Status",
            each
                let
                    TotalStockQuantity = ToNumberOrZero([Total Stock Quantity])
                in
                    if TotalStockQuantity > 0 then "Yes" else "No",
            type text
        ),

    // === Build column Average Monthly Forecast Demand ===
    AddAverageForecastDemand =
        Table.AddColumn(
            AddStockedStatus,
            "Average Monthly Forecast Demand",
            each
                let
                    VJ = ToNumberOrZero([VJ]),
                    PP = ToNumberOrZero([PP]),
                    U1 = ToNumberOrZero([U1]),
                    ForecastDemand = (VJ + PP + U1) / 3
                in
                    ForecastDemand,
            type number
        ),

    // === Build column DOH ===
    AddDOH =
        Table.AddColumn(
            AddAverageForecastDemand,
            "DOH",
            each
                let
                    AvailableStock = ToNumberOrZero([Available Stock]),
                    AvgMonthlyForecastDemand = ToNumberOrZero([Average Monthly Forecast Demand]),
                    DOHValue =
                        if AvgMonthlyForecastDemand = 0 then
                            0
                        else
                            (AvailableStock / AvgMonthlyForecastDemand) * 30
                in
                    DOHValue,
            type number
        ),

    // === Merge BOBL backlog/backorder data ===
    #"Merged Queries2" =
        Table.NestedJoin(
            AddDOH,
            {"plant_material_key"},
            out_bobl_review,
            {"plant_material_key"},
            "out_bobl_review",
            JoinKind.LeftOuter
        ),

    #"Expanded out_bobl_review" =
        Table.ExpandTableColumn(
            #"Merged Queries2",
            "out_bobl_review",
            {"Backorder Actual", "Backorder Qnty", "Backlog Actual", "Backlog Qnty"},
            {"Backorder Actual", "Backorder Qnty", "Backlog Actual", "Backlog Qnty"}
        ),
    #"Reordered Columns1" = Table.ReorderColumns(#"Expanded out_bobl_review",{"plant_material_key", "Region", "Plant", "Major PG", "Product hierarchy", "Material", "Material Description", "Source Plant", "Safety Stock", "BUn", "top_60_flag", "ABC", "Spec Proc", "ProcType", "TRLT", "Total Stock Quantity", "Stocked Status", "Total Value Stock on Hand", "Basic material", "MRP Typ", "MRP Controller", "DelFlag", "SG", "MTyp", "IPT", "PDT", "GRT", "Planning time fence", "LotSize", "Reorder Point", "Threshold Qty", "AvaiChk", "Standard price", "Price Un", "WB", "VJ", "VC", "VG", "PP", "U1", "U2", "Quantity in Transit", "Available Stock", "Average Monthly Forecast Demand", "DOH", "Backorder Actual", "Backorder Qnty", "Backlog Actual", "Backlog Qnty"})

in
    #"Reordered Columns1"