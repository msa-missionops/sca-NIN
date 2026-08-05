let
    Source = stg_prdpl3_clean,

    // === Ensure plant_material_key exists and is normalized ===
    EnsurePlantMaterialKey =
        if List.Contains(Table.ColumnNames(Source), "plant_material_key") then
            Table.TransformColumns(
                Source,
                {
                    {
                        "plant_material_key",
                        each Text.Upper(Text.Trim(Text.From(_))),
                        type text
                    }
                }
            )
        else
            Table.AddColumn(
                Source,
                "plant_material_key",
                each
                    Text.Upper(Text.Trim(Text.From([Plant]))) &
                    "-" &
                    Text.Upper(Text.Trim(Text.From([Material]))),
                type text
            ),

    // === Load and normalize Region tag table ===
    RegionTagRaw =
        Excel.CurrentWorkbook(){[Name="tbl_Tag_Region"]}[Content],

    RegionTag =
        Table.TransformColumns(
            RegionTagRaw,
            {
                {"Plant", each Text.Upper(Text.Trim(Text.From(_))), type text},
                {"Region", each Text.Trim(Text.From(_)), type text}
            }
        ),

    // === Join Region tag by Plant ===
    JoinRegion =
        Table.NestedJoin(
            EnsurePlantMaterialKey,
            {"Plant"},
            RegionTag,
            {"Plant"},
            "RegionTag",
            JoinKind.LeftOuter
        ),

    ExpandRegion =
        Table.ExpandTableColumn(
            JoinRegion,
            "RegionTag",
            {"Region"},
            {"Region"}
        ),

    // === Load and normalize Top 60 tag table ===
    Top60TagRaw =
        Excel.CurrentWorkbook(){[Name="tbl_Tag_Top60"]}[Content],

    Top60Tag =
        Table.TransformColumns(
            Top60TagRaw,
            {
                {"plant_material_key", each Text.Upper(Text.Trim(Text.From(_))), type text},
                {"top_60_flag", each Text.Trim(Text.From(_)), type text}
            }
        ),

    // === Join Top 60 tag by plant-material key ===
    JoinTop60 =
        Table.NestedJoin(
            ExpandRegion,
            {"plant_material_key"},
            Top60Tag,
            {"plant_material_key"},
            "Top60Tag",
            JoinKind.LeftOuter
        ),

    // === Add top_60_flag with explicit default ===
    AddTop60Flag =
        Table.AddColumn(
            JoinTop60,
            "top_60_flag",
            each
                if Table.IsEmpty([Top60Tag])
                then "standard"
                else [Top60Tag]{0}[top_60_flag],
            type text
        ),

    // === Remove nested Top 60 join table ===
    RemoveTop60NestedTable =
        Table.RemoveColumns(
            AddTop60Flag,
            {"Top60Tag"}
        ),
    #"Reordered Columns" = Table.ReorderColumns(RemoveTop60NestedTable,{"plant_material_key", "Plant", "Material", "Material Description", "Region", "top_60_flag", "BUn", "Product hierarchy", "Basic material", "Basic material 2", "MRP Typ", "MRP Controller", "PuRGrp", "DelFlag", "MtlSt_XPlt", "MtlSt_Plt", "X-Chn Mtl St", "SG", "ProcType", "Spec Proc", "ABC", "MTyp", "IPT", "PDT", "GRT", "TRLT", "Planning time fence", "LotSize", "Min. Lot Sze", "Rounding val.", "Max. Lot Size", "Fix. lot size", "BUn_1", "Safety Stock", "Reorder Point", "Threshold Qty", "AvaiChk", "Consumption mode", "Bwd cons. per.", "Fwd cons.period", "BkFlush", "PSloc", "Language", "Tot Valuated Stk", "Total Value", "Standard price", "Price Un", "SLife", "Propos.SA", "ESLoc", "R. Profile", "ProdS"}),
  
  // === Normalize source plant lookup table ===
SourcePlantTag =
    Table.TransformColumns(
        tbl_tag_sourceplant,
        {
            {"source_key", each Text.Upper(Text.Trim(Text.From(_))), type text},
            {"source_plant", each Text.Trim(Text.From(_)), type text}
        }
    ),

// === Normalize Spec Proc before source plant lookup ===
NormalizeSpecProc =
    Table.TransformColumns(
        #"Reordered Columns",
        {
            {"Spec Proc", each Text.Upper(Text.Trim(Text.From(_))), type text}
        }
    ),

// === Join source plant by Spec Proc ===
JoinSourcePlant =
    Table.NestedJoin(
        NormalizeSpecProc,
        {"Spec Proc"},
        SourcePlantTag,
        {"source_key"},
        "SourcePlantTag",
        JoinKind.LeftOuter
    ),

// === Add source_plant with explicit default ===
AddSourcePlant =
    Table.AddColumn(
        JoinSourcePlant,
        "source_plant",
        each
            if Table.IsEmpty([SourcePlantTag])
            then "None defined"
            else [SourcePlantTag]{0}[source_plant],
        type text
    ),

// === Remove nested source plant join table ===
RemoveSourcePlantNestedTable =
    Table.RemoveColumns(
        AddSourcePlant,
        {"SourcePlantTag"}
    ),

#"Reordered Columns1" =
    Table.ReorderColumns(
        RemoveSourcePlantNestedTable,
        {
            "plant_material_key", "Plant", "Material", "Material Description",
            "Region", "top_60_flag", "source_plant",
            "BUn", "Product hierarchy", "Basic material", "Basic material 2",
            "MRP Typ", "MRP Controller", "PuRGrp", "DelFlag", "MtlSt_XPlt",
            "MtlSt_Plt", "X-Chn Mtl St", "SG", "ProcType", "Spec Proc",
            "ABC", "MTyp", "IPT", "PDT", "GRT", "TRLT",
            "Planning time fence", "LotSize", "Min. Lot Sze", "Rounding val.",
            "Max. Lot Size", "Fix. lot size", "BUn_1", "Safety Stock",
            "Reorder Point", "Threshold Qty", "AvaiChk", "Consumption mode",
            "Bwd cons. per.", "Fwd cons.period", "BkFlush", "PSloc",
            "Language", "Tot Valuated Stk", "Total Value", "Standard price",
            "Price Un", "SLife", "Propos.SA", "ESLoc", "R. Profile", "ProdS"
        },
        MissingField.Ignore
    )
  
  
  
  
  
  
  
  
  /*
  
    #"Merged Queries" = Table.NestedJoin(#"Reordered Columns", {"Spec Proc"}, tbl_tag_sourceplant, {"source_key"}, "tbl_tag_sourceplant", JoinKind.LeftOuter),
    #"Expanded tbl_tag_sourceplant" = Table.ExpandTableColumn(#"Merged Queries", "tbl_tag_sourceplant", {"source_plant"}, {"source_plant"}),
    #"Replaced Value" = Table.ReplaceValue(#"Expanded tbl_tag_sourceplant",null,"None defined",Replacer.ReplaceValue,{"source_plant"}),
    #"Reordered Columns1" = Table.ReorderColumns(#"Replaced Value",{"plant_material_key", "Plant", "Material", "Material Description", "Region", "top_60_flag", "source_plant", "BUn", "Product hierarchy", "Basic material", "Basic material 2", "MRP Typ", "MRP Controller", "PuRGrp", "DelFlag", "MtlSt_XPlt", "MtlSt_Plt", "X-Chn Mtl St", "SG", "ProcType", "Spec Proc", "ABC", "MTyp", "IPT", "PDT", "GRT", "TRLT", "Planning time fence", "LotSize", "Min. Lot Sze", "Rounding val.", "Max. Lot Size", "Fix. lot size", "BUn_1", "Safety Stock", "Reorder Point", "Threshold Qty", "AvaiChk", "Consumption mode", "Bwd cons. per.", "Fwd cons.period", "BkFlush", "PSloc", "Language", "Tot Valuated Stk", "Total Value", "Standard price", "Price Un", "SLife", "Propos.SA", "ESLoc", "R. Profile", "ProdS"})

    */
in
    #"Reordered Columns1"