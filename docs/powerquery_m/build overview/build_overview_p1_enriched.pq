let
    Source = build_overview_p1_clean,
  //  #"Inserted Text Between Delimiters" = Table.AddColumn(Source, "Text Between Delimiters", each Text.BetweenDelimiters([Product hierarchy], "0", "0", 2, 1), type text),

// build product group from prod hier.
    pg_col = Table.AddColumn(Source, "Major PG", each Text.Middle([Product hierarchy], 3, 2), type text),
    #"Renamed Columns" = Table.RenameColumns(pg_col,{{"source_plant", "Source Plant"}}),
    #"Reordered Columns" = Table.ReorderColumns(#"Renamed Columns",{"plant_material_key", "Region", "Plant", "Major PG", "Product hierarchy", "Material", "Material Description", "Source Plant", "Safety Stock", "BUn", "top_60_flag", "ABC", "Spec Proc", "ProcType", "TRLT", "Tot Valuated Stk", "Total Value", "Basic material", "Basic material 2", "MRP Typ", "MRP Controller", "PuRGrp", "DelFlag", "MtlSt_XPlt", "MtlSt_Plt", "X-Chn Mtl St", "SG", "MTyp", "IPT", "PDT", "GRT", "Planning time fence", "LotSize", "Min. Lot Sze", "Rounding val.", "Max. Lot Size", "Fix. lot size", "BUn_1", "Reorder Point", "Threshold Qty", "AvaiChk", "Consumption mode", "Bwd cons. per.", "Fwd cons.period", "BkFlush", "PSloc", "Language", "Standard price", "Price Un", "SLife", "Propos.SA", "ESLoc", "R. Profile", "ProdS"}),
    #"Removed Other Columns" = Table.SelectColumns(#"Reordered Columns",{"plant_material_key", "Region", "Plant", "Major PG", "Product hierarchy", "Material", "Material Description", "Source Plant", "Safety Stock", "BUn", "top_60_flag", "ABC", "Spec Proc", "ProcType", "TRLT", "Tot Valuated Stk", "Total Value", "Basic material", "MRP Typ", "MRP Controller", "DelFlag", "SG", "MTyp", "IPT", "PDT", "GRT", "Planning time fence", "LotSize", "Reorder Point", "Threshold Qty", "AvaiChk", "Standard price", "Price Un"})
in
   #"Removed Other Columns"