let
// The main SAP transparent table that stores the configuration for special procurement types is T460A. This table holds the special procurement keys (SOBSL) and defines their specific procurement types (BESKZ) such as subcontracting, phantom assemblies, or stock transfers


    Source = Excel.CurrentWorkbook(){[Name="tbl_tag_sourceplant"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"source_key", type text}, {"desc", type text}, {"source_plant", type text}})
in
    #"Changed Type"