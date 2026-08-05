let
    // === Read Config tables ===
    ConfigPaths = Excel.CurrentWorkbook(){[Name="ConfigPaths"]}[Content],
    ConfigTx    = Excel.CurrentWorkbook(){[Name="ConfigTx"]}[Content],

    // === Read active plant from plant_evaluation ===
    PlantEvaluationRaw =
        Excel.CurrentWorkbook(){[Name="plant_evaluation"]}[Content],

    CleanPlantEvalHeaders =
        Table.TransformColumnNames(
            PlantEvaluationRaw,
            each Text.Trim(_)
        ),

    PlantColName =
        List.First(
            List.Select(
                Table.ColumnNames(CleanPlantEvalHeaders),
                each Text.Lower(_) = "plant"
            ),
            null
        ),

    EvaluateColName =
        List.First(
            List.Select(
                Table.ColumnNames(CleanPlantEvalHeaders),
                each Text.Lower(_) = "evaluate"
            ),
            null
        ),

    CheckPlantEvalCols =
        if PlantColName = null then
            error "plant_evaluation table must contain a Plant column."
        else if EvaluateColName = null then
            error "plant_evaluation table must contain an Evaluate column."
        else
            CleanPlantEvalHeaders,

    PlantEvaluation =
        Table.RenameColumns(
            CheckPlantEvalCols,
            {
                {PlantColName, "Plant"},
                {EvaluateColName, "Evaluate"}
            },
            MissingField.Ignore
        ),

    PlantEvaluationTyped =
        Table.TransformColumns(
            PlantEvaluation,
            {
                {"Plant", each Text.Upper(Text.Trim(Text.From(_))), type text},
                {"Evaluate", each if _ = true or Text.Upper(Text.Trim(Text.From(_))) = "TRUE" then true else false, type logical}
            }
        ),

    ActivePlants =
        Table.SelectRows(
            PlantEvaluationTyped,
            each [Evaluate] = true
        ),

    ParamPlant =
        if Table.RowCount(ActivePlants) = 0 then
            error "No active plant found in plant_evaluation where Evaluate = TRUE."
        else if Table.RowCount(ActivePlants) > 1 then
            error "More than one active plant found in plant_evaluation. Only one plant can be evaluated at a time."
        else
            ActivePlants{0}[Plant],

    // === Resolve paths for MB5T ===
    OutputRoot  = Table.SelectRows(ConfigPaths, each [Key] = "OutputRoot"){0}[Value],
    TxFolder    = Table.SelectRows(ConfigTx, each [TransactionCode] = "MB5T"){0}[OutputFolder],

    FullPath =
        if Text.EndsWith(OutputRoot, "\")
        then OutputRoot & TxFolder
        else OutputRoot & "\" & TxFolder,

    // === Load latest SAP export ===
    Source = Folder.Files(FullPath),

    HiddenFiltered =
        Table.SelectRows(
            Source,
            each [Attributes]?[Hidden]? <> true
        ),

    LatestRow =
        Table.SelectRows(
            HiddenFiltered,
            let latest = List.Max(HiddenFiltered[Date created])
            in each [Date created] = latest
        ),

    LatestFile = LatestRow{0}[Content],

    // === Import as pipe-delimited SAP export ===
    Imported =
        Csv.Document(
            LatestFile,
            [
                Delimiter = "|",
                Columns = 18,
                Encoding = 1252,
                QuoteStyle = QuoteStyle.None
            ]
        ),

    TypedRaw =
        Table.TransformColumnTypes(
            Imported,
            List.Transform({1..18}, each {"Column" & Text.From(_), type text})
        ),

    // === Cleanup SAP pipe export structure ===
    RemovedCols =
        Table.RemoveColumns(
            TypedRaw,
            {"Column1", "Column18"}
        ),

    Trimmed =
        Table.TransformColumns(
            RemovedCols,
            List.Transform(
                Table.ColumnNames(RemovedCols),
                each {_, each Text.Trim(Text.From(_)), type text}
            )
        ),

    SkippedTop =
        Table.Skip(Trimmed, 3),

    Promoted =
        Table.PromoteHeaders(
            SkippedTop,
            [PromoteAllScalars = true]
        ),

    Cleaned =
        Table.Skip(Promoted, 1),

    // === Type conversions ===
   Typed =
    Table.TransformColumnTypes(
        Cleaned,
        List.Select(
            {
                {"Net Value", type number},
                {"Amount in LC", type number},
                {"Quantity", Int64.Type},
                {"Quantity_1", Int64.Type}
            },
            each List.Contains(Table.ColumnNames(Cleaned), _{0})
        )
    ),

    // === Normalize keys ===
    NormKeys =
        Table.TransformColumns(
            Typed,
            {
                {"Plnt", each Text.Upper(Text.Trim(Text.From(_))), type text},
                {"Material", each Text.TrimStart(Text.Upper(Text.Trim(Text.From(_))), {"0"}), type text}
            },
            null,
            MissingField.Ignore
        ),

    // === Filter to active evaluation plant ===
    FilteredPlant =
        Table.SelectRows(
            NormKeys,
            each [Plnt] = ParamPlant
        ),

    // === Plant-Material key ===
    AddKey =
        Table.AddColumn(
            FilteredPlant,
            "plant_material_key",
            each [Plnt] & "-" & [Material],
            type text
        ),

    // === Preserve old Group column shape, but no DefinedSet grouping is used ===
    AddGroup =
        Table.AddColumn(
            AddKey,
            "Group",
            each null,
            type text
        ),

    // === Sort for reporting ===
    Sorted =
        Table.Sort(
            AddGroup,
            {
                {"Plnt", Order.Ascending},
                {"Material", Order.Ascending}
            }
        ),

    // === Final column order ===
    Reordered =
        Table.ReorderColumns(
            Sorted,
            {
                "plant_material_key",
                "Group",
                "Material",
                "Material Description",
                "Quantity",
                "Plnt",
                "Name 1",
                "Pur. Doc.",
                "Item",
                "SPlt",
                "S",
                "BUn",
                "Amount in LC",
                "Crcy",
                "Quantity_1",
                "OUn",
                "Net Value",
                "Crcy_2"
            },
            MissingField.Ignore
        ),

    FilteredRows =
        Table.SelectRows(
            Reordered,
            each [Material] <> ""
        )
in
    FilteredRows