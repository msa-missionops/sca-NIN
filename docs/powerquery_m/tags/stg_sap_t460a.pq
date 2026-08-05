let
    Source = Csv.Document(File.Contents("\\filer3\power_bi$\GSP\Stockout_Excel\Other\T460A_05.29.2026.csv"),[Delimiter=",", Columns=14, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Column1", type text}, {"Column2", type text}, {"Column3", type text}, {"Column4", type text}, {"Column5", type text}, {"Column6", type text}, {"Column7", type text}, {"Column8", type text}, {"Column9", type text}, {"Column10", type text}, {"Column11", type text}, {"Column12", type text}, {"Column13", type text}, {"Column14", type text}}),
    #"Promoted Headers" = Table.PromoteHeaders(#"Changed Type", [PromoteAllScalars=true]),
    #"Changed Type1" = Table.TransformColumnTypes(#"Promoted Headers",{{"Plant", type text}, {"Special procurement", type text}, {"Procurement type", type text}, {"Special procurement_1", type text}, {"Plant_2", type text}, {"Direct production", type text}, {"Phantom item", type text}, {"Withdr.altern.plant", type text}, {"Issuing plant", type text}, {"Direct procurement", type text}, {"Ind. Stock Transfer", type text}, {"Add. Info for BAdI", type text}, {"Multilevel Subcontracting", type text}, {"Long Text", type text}}),
    #"Filtered Rows" = Table.SelectRows(#"Changed Type1", each ([Plant_2] <> ""))
in
    #"Filtered Rows"