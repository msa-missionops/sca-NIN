let
   
    // Load from MB5T base query
 Source = stg_mb5t_clean,

    // Keep only keys and quantities
    KeepCols = Table.SelectColumns(Source, {"plant_material_key", "Quantity"}),

    // Aggregate to summed quantity
    Grouped = Table.Group(
        KeepCols,
        {"plant_material_key"},
        {{"qnt_sum", each List.Sum([Quantity]), type nullable number}}
    ),

    // Replace nulls with 0
    ReplacedNulls = Table.ReplaceValue(Grouped, null, 0, Replacer.ReplaceValue, {"qnt_sum"})
in
    ReplacedNulls