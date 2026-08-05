let
    Source = Excel.CurrentWorkbook(){[Name="tbl_tag_top60"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"plant", type text}, {"material", type text}, {"plant_material_key", type text}, {"top_60_flag", type text}}),
    #"Reordered Columns" = Table.ReorderColumns(#"Changed Type",{"plant_material_key", "plant", "material", "top_60_flag"})
in
    #"Reordered Columns"