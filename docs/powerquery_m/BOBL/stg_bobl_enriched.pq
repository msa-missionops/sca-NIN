let
    Source = stg_bobl_clean,
   
    #"Removed Other Columns" =
        Table.SelectColumns(
            Source,
            {
                "PowerBI Consolidated Backlog by PG Last N Weeks[Plant]",
                "PowerBI Consolidated Backlog by PG Last N Weeks[Material.Material Level 01.Key]",
                "[SumBackorder_Actual]",
                "[SumBackorder_Quantity]",
                "[SumBacklog_Quantity]",
                "[SumBacklog_Actual]"
            }
        ),

    #"Added Custom" =
        Table.AddColumn(
            #"Removed Other Columns",
            "plant_material_key",
            each
                Text.Trim(Text.From([#"PowerBI Consolidated Backlog by PG Last N Weeks[Plant]"]))
                & "-"
                & Text.Trim(Text.From([#"PowerBI Consolidated Backlog by PG Last N Weeks[Material.Material Level 01.Key]"])),
            type text
        ),

    #"Removed Other Columns1" =
        Table.SelectColumns(
            #"Added Custom",
            {
                "plant_material_key",
                "[SumBackorder_Actual]",
                "[SumBackorder_Quantity]",
                "[SumBacklog_Quantity]",
                "[SumBacklog_Actual]"
            }
        ),

    // === Helper for safe numeric conversion ===
    ToNumberOrZero =
        (v as any) as number =>
            let
                n = try Number.From(v) otherwise 0
            in
                if n = null then 0 else n,

    // === Group by plant_material_key and sum numeric columns ===
    #"Grouped Rows" =
        Table.Group(
            #"Removed Other Columns1",
            {"plant_material_key"},
            {
                {
                    "[SumBackorder_Actual]",
                    each List.Sum(List.Transform(Table.Column(_, "[SumBackorder_Actual]"), each ToNumberOrZero(_))),
                    type number
                },
                {
                    "[SumBackorder_Quantity]",
                    each List.Sum(List.Transform(Table.Column(_, "[SumBackorder_Quantity]"), each ToNumberOrZero(_))),
                    type number
                },
                {
                    "[SumBacklog_Quantity]",
                    each List.Sum(List.Transform(Table.Column(_, "[SumBacklog_Quantity]"), each ToNumberOrZero(_))),
                    type number
                },
                {
                    "[SumBacklog_Actual]",
                    each List.Sum(List.Transform(Table.Column(_, "[SumBacklog_Actual]"), each ToNumberOrZero(_))),
                    type number
                }
            }
        ),

    #"Reordered Columns" =
        Table.ReorderColumns(
            #"Grouped Rows",
            {
                "plant_material_key",
                "[SumBackorder_Actual]",
                "[SumBackorder_Quantity]",
                "[SumBacklog_Quantity]",
                "[SumBacklog_Actual]"
            }
        ),
    #"Renamed Columns" = Table.RenameColumns(#"Reordered Columns",{{"[SumBackorder_Actual]", "Backorder Actual"}, {"[SumBackorder_Quantity]", "Backorder Qnty"}, {"[SumBacklog_Quantity]", "Backlog Qnty"}, {"[SumBacklog_Actual]", "Backlog Actual"}}),
    #"Reordered Columns1" = Table.ReorderColumns(#"Renamed Columns",{"plant_material_key", "Backorder Actual", "Backorder Qnty", "Backlog Actual", "Backlog Qnty"})
in
    #"Reordered Columns1"