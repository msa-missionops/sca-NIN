let
    Source = Excel.CurrentWorkbook(){[Name="tbl_tag_region"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Plant", type text}, {"Region", type text}})
in
    #"Changed Type"