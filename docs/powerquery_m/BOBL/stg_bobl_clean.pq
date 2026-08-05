let
    Source = Excel.CurrentWorkbook(){[Name="Table_BOBL"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"PowerBI Consolidated Backlog by PG Last N Weeks[Plant]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Source of Supply]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Order Number.Order Number Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Order Item.Order Item Level 01]", Int64.Type}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Major Product Group.Major Product Group Level 01.Key]", Int64.Type}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Material.Material Level 01.Key]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Material.Material Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Minor Product Group.Minor Product Group Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Sub-Minor Product Group.Sub-Minor Product Group Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Sold-to Party.Sold-to Party Level 01.Key]", Int64.Type}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Sold-to Party.Sold-to Party Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Original Promise Date.Original Promise Date Level 01]", type datetime}, {"PowerBI Consolidated Backlog by PG Last N Weeks[MRP Controller.MRP Controller Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Planning Strat. Grp.Planning Strat. Grp Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Complete Delivery]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Dlv Block Indicator.Dlv Block Indicator Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Credit Hold Ind..Credit Hold Ind. Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Delivery Block.Delivery Block Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Item Category.Item Category Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Threshold Block.Threshold Block Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Creation Date.Creation Date Level 01]", type datetime}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Customer PO Number.Customer PO Number Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Expected Realization Full Date]", type date}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Sales Organization.Sales Organization Level 01.Key]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Billing block.Billing block Level 01.Key]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Billing block.Billing block Level 01]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Customer Request Date.Customer Request Date Level 01]", type datetime}, {"PowerBI Consolidated Backlog by PG Last N Weeks[MRP Controller.MRP Controller Level 01.Key Actual]", type text}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Expected Realization Date]", type datetime}, {"PowerBI Consolidated Backlog by PG Last N Weeks[MRP Block]", type any}, {"PowerBI Consolidated Backlog by PG Last N Weeks[Delivery Block]", type any}, {"[SumBackorder_Actual]", type number}, {"[SumBackorder_Quantity]", Int64.Type}, {"[SumBacklog_Quantity]", Int64.Type}, {"[SumBacklog_Actual]", type number}})


in   

#"Changed Type"
/*
   
   
   
   
   
   
   
    #"Removed Other Columns" = Table.SelectColumns(#"Changed Type",{"PowerBI Consolidated Backlog by PG Last N Weeks[Plant]", "PowerBI Consolidated Backlog by PG Last N Weeks[Material.Material Level 01.Key]", "[SumBackorder_Actual]", "[SumBackorder_Quantity]", "[SumBacklog_Quantity]", "[SumBacklog_Actual]"}),
    #"Added Custom" = Table.AddColumn(#"Removed Other Columns", "plant_material_key", each [#"PowerBI Consolidated Backlog by PG Last N Weeks[Plant]"]&"-"&[#"PowerBI Consolidated Backlog by PG Last N Weeks[Material.Material Level 01.Key]"]),
    #"Removed Other Columns1" = Table.SelectColumns(#"Added Custom",{"[SumBackorder_Actual]", "[SumBackorder_Quantity]", "[SumBacklog_Quantity]", "[SumBacklog_Actual]", "plant_material_key"}),
    #"Reordered Columns" = Table.ReorderColumns(#"Removed Other Columns1",{"plant_material_key", "[SumBackorder_Actual]", "[SumBackorder_Quantity]", "[SumBacklog_Quantity]", "[SumBacklog_Actual]"}),

      // === Count rows per plant_material_key ===
    DuplicateCounts =
        Table.Group(
            #"Reordered Columns",
            {"plant_material_key"},
            {
                {"key_row_count", each Table.RowCount(_), Int64.Type}
            }
        ),

    // === Join duplicate count back to detail rows ===
    MergeDuplicateCounts =
        Table.NestedJoin(
            #"Reordered Columns",
            {"plant_material_key"},
            DuplicateCounts,
            {"plant_material_key"},
            "DuplicateCheck",
            JoinKind.LeftOuter
        ),

    ExpandDuplicateCounts =
        Table.ExpandTableColumn(
            MergeDuplicateCounts,
            "DuplicateCheck",
            {"key_row_count"},
            {"key_row_count"}
        ),

    // === Add duplicate flag ===
    AddDuplicateFlag =
        Table.AddColumn(
            ExpandDuplicateCounts,
            "duplicate_key_flag",
            each if [key_row_count] > 1 then "Duplicate" else "Unique",
            type text
        )
in
    AddDuplicateFlag

    */