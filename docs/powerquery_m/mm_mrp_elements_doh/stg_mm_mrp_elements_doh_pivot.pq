let
    Source = stg_mm_mrp_elements_doh_clean,

    // Remove zero/null adjusted requirement rows before pivot
    FilteredActiveReq =
        Table.SelectRows(
            Source,
            each [#"Adj Req Qty"] <> null and [#"Adj Req Qty"] <> 0
        ),

    // Select relevant columns
    RemovedOtherColumns =
        Table.SelectColumns(
            FilteredActiveReq,
            {"Material No.", "Plant", "Requirements Type", "Adj Req Qty"},
            MissingField.Ignore
        ),

    // Normalize text fields
    NormalizedText =
        Table.TransformColumns(
            RemovedOtherColumns,
            {
                {"Plant", each Text.Upper(Text.Trim(Text.From(_))), type text},
                {"Material No.", each Text.TrimStart(Text.Upper(Text.Trim(Text.From(_))), {"0"}), type text},
                {"Requirements Type", each Text.Upper(Text.Trim(Text.From(_))), type text}
            },
            null,
            MissingField.Ignore
        ),

    // Rename adjusted quantity to Req_Qty for pivot
    RenamedColumns =
        Table.RenameColumns(
            NormalizedText,
            {{"Adj Req Qty", "Req_Qty"}},
            MissingField.Ignore
        ),

    // Ensure Req_Qty is numeric
    EnsureReqQty =
        Table.TransformColumns(
            RenamedColumns,
            {
                {"Req_Qty", each try Number.From(Text.Replace(Text.From(_), ",", "")) otherwise 0, type number}
            },
            null,
            MissingField.Ignore
        ),

    // Ensure Requirements Type is populated
    FilledReqType =
        Table.TransformColumns(
            EnsureReqQty,
            {
                {
                    "Requirements Type",
                    each
                        if _ = null or Text.Trim(Text.From(_)) = ""
                        then "UNSPEC"
                        else Text.Upper(Text.Trim(Text.From(_))),
                    type text
                }
            },
            null,
            MissingField.Ignore
        ),

    // Group before pivot
    Grouped =
        Table.Group(
            FilledReqType,
            {"Material No.", "Plant", "Requirements Type"},
            {{"Req_Qty", each List.Sum([Req_Qty]), type number}}
        ),

    // Pivot requirement types
    PivotedColumn =
        Table.Pivot(
            Grouped,
            List.Sort(List.Distinct(Grouped[Requirements Type])),
            "Requirements Type",
            "Req_Qty",
            List.Sum
        ),

    // Add normalized key
    AddedPlantMaterialKey =
        Table.AddColumn(
            PivotedColumn,
            "plant_material_key",
            each [Plant] & "-" & [#"Material No."],
            type text
        ),

    // Ensure expected pivot columns always exist
    Expected = {"WB", "PP", "U2", "VC", "VJ", "U1"},

    AddedMissingExpectedColumns =
        List.Accumulate(
            Expected,
            AddedPlantMaterialKey,
            (t, c) =>
                if Table.HasColumns(t, c) then
                    t
                else
                    Table.AddColumn(t, c, each 0, type number)
        ),

    // Replace nulls in expected and other pivot columns with 0
    NonKeyColumns =
        List.RemoveItems(
            Table.ColumnNames(AddedMissingExpectedColumns),
            {"plant_material_key", "Material No.", "Plant"}
        ),

    NullsToZero =
        Table.ReplaceValue(
            AddedMissingExpectedColumns,
            null,
            0,
            Replacer.ReplaceValue,
            NonKeyColumns
        ),

    // Deterministic column order
    Desired =
        {"plant_material_key", "Material No.", "Plant"} & Expected,

    Existing =
        Table.ColumnNames(NullsToZero),

    FinalOrder =
        List.Intersect({Desired, Existing}) & List.RemoveItems(Existing, Desired),

    ReorderedColumns =
        Table.ReorderColumns(
            NullsToZero,
            FinalOrder,
            MissingField.Ignore
        ),

    // Type enforcement
    ChangedType =
        Table.TransformColumnTypes(
            ReorderedColumns,
            {{"plant_material_key", type text}, {"Material No.", type text}, {"Plant", type text}}
                & List.Transform(Expected, each {_, type number})
        )
in
    ChangedType