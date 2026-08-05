let
    Source = stg_mb5t_enriched,
    #"Renamed Columns" = Table.RenameColumns(Source,{{"qnt_sum", "Quantity in Transit"}})
in
    #"Renamed Columns"