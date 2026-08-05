let
    Source = stg_mm_mrp_elements_rec_clean,

    // Keep only fields needed for weekly forecast structure
    RemovedOtherColumns =
        Table.SelectColumns(
            Source,
            {"Material No.", "Plant", "Week Ending", "Requirements Type", "Req. Qty."},
            MissingField.Ignore
        ),

    // Remove zero/null requirement rows
    FilteredActiveReq =
        Table.SelectRows(
            RemovedOtherColumns,
            each [#"Req. Qty."] <> null and [#"Req. Qty."] <> 0
        ),

    // Normalize fields
    Normalized =
        Table.TransformColumns(
            FilteredActiveReq,
            {
                {"Plant", each Text.Upper(Text.Trim(Text.From(_))), type text},
                {"Material No.", each Text.TrimStart(Text.Upper(Text.Trim(Text.From(_))), {"0"}), type text},
                {"Requirements Type", each Text.Upper(Text.Trim(Text.From(_))), type text},
                {"Week Ending", each try Date.From(_) otherwise null, type date},
                {"Req. Qty.", each try Number.From(Text.Replace(Text.From(_), ",", "")) otherwise 0, type number}
            },
            null,
            MissingField.Ignore
        ),

    // Load REC req type sign table
    RecReqTypeRaw =
        Excel.CurrentWorkbook(){[Name="rec_req_type"]}[Content],

    RecReqType =
        Table.Buffer(
            Table.TransformColumns(
                RecReqTypeRaw,
                {
                    {"type", each Text.Upper(Text.Trim(Text.From(_))), type text},
                    {"negative", each if _ = true or Text.Upper(Text.Trim(Text.From(_))) = "TRUE" then true else false, type logical}
                }
            )
        ),

    // Merge sign logic
    MergedReqType =
        Table.NestedJoin(
            Normalized,
            {"Requirements Type"},
            RecReqType,
            {"type"},
            "ReqTypeLookup",
            JoinKind.LeftOuter
        ),

    ExpandedReqType =
        Table.ExpandTableColumn(
            MergedReqType,
            "ReqTypeLookup",
            {"negative"},
            {"Is Negative Req Type"}
        ),

    FilledSign =
        Table.ReplaceValue(
            ExpandedReqType,
            null,
            false,
            Replacer.ReplaceValue,
            {"Is Negative Req Type"}
        ),

    // Create adjusted requirement quantity
    AddedAdjReqQty =
        Table.AddColumn(
            FilledSign,
            "Adj Req Qty",
            each
                if [Is Negative Req Type]
                then -Number.Abs([#"Req. Qty."])
                else Number.Abs([#"Req. Qty."]),
            type number
        ),

    // Create plant/material key
    AddedKey =
        Table.AddColumn(
            AddedAdjReqQty,
            "plant_material_key",
            each [Plant] & "-" & [#"Material No."],
            type text
        ),

    // Final downstream-facing columns only
    FinalColumns =
        Table.SelectColumns(
            AddedKey,
            {"plant_material_key", "Week Ending", "Adj Req Qty"},
            MissingField.Ignore
        ),

    // Type hardening
    ChangedType =
        Table.TransformColumnTypes(
            FinalColumns,
            {
                {"plant_material_key", type text},
                {"Week Ending", type date},
                {"Adj Req Qty", type number}
            }
        ),

    Sorted =
        Table.Sort(
            ChangedType,
            {
                {"plant_material_key", Order.Ascending},
                {"Week Ending", Order.Ascending}
            }
        ),


        AbsAdjReqQty =
    Table.TransformColumns(
        Sorted,
        {
            {"Adj Req Qty", each Number.Abs(_), type number}
        }
    )


    in   



    AbsAdjReqQty