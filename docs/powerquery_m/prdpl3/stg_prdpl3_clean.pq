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

    // === Resolve paths for PRDPL3 ===
    OutputRoot  = Table.SelectRows(ConfigPaths, each [Key] = "OutputRoot"){0}[Value],
    TxFolder    = Table.SelectRows(ConfigTx, each [TransactionCode] = "PRDPL3"){0}[OutputFolder],

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

    // === Import as CSV (pipe-delimited, 51 columns) ===
    Imported =
        Csv.Document(
            LatestFile,
            [Delimiter="|", Columns=51, Encoding=1252, QuoteStyle=QuoteStyle.None]
        ),

    TypedRaw =
        Table.TransformColumnTypes(
            Imported,
            List.Transform({1..51}, each {"Column" & Text.From(_), type text})
        ),

    // === Cleanup ===
    RemovedCols = Table.RemoveColumns(TypedRaw, {"Column1", "Column51"}),

    SkippedTop = Table.Skip(RemovedCols, 6),

    Trimmed =
        Table.TransformColumns(
            SkippedTop,
            List.Transform(Table.ColumnNames(SkippedTop), each {_, Text.Trim, type text})
        ),

    Promoted = Table.PromoteHeaders(Trimmed, [PromoteAllScalars=true]),

    // === Type conversions (business fields) ===
    Typed =
        Table.TransformColumnTypes(
            Promoted,
            {
                {"Safety Stock", type number},
                {"Threshold Qty", type number},
                {"Reorder Point", type number},
                {"AvaiChk", type text},
                {"Tot Valuated Stk", type number},
                {"Total Value", type number},
                {"Standard price", type number},
                {"Price Un", type number}
            }
        ),

    // Remove extra header row if present
    Cleaned = Table.Skip(Typed, 1),

    Renamed1 =
        Table.RenameColumns(
            Cleaned,
            {{"Plnt", "Plant"}},
            MissingField.Ignore
        ),

    // === Normalize keys ===
    ExpKeys =
        Table.TransformColumns(
            Renamed1,
            {
                {"Plant", each Text.Upper(Text.Trim(Text.From(_))), type text},
                {"Material", each Text.TrimStart(Text.Upper(Text.Trim(Text.From(_))), {"0"}), type text}
            },
            null,
            MissingField.Ignore
        ),

    // === Filter to active evaluation plant ===
    FilteredPlant =
        Table.SelectRows(
            ExpKeys,
            each [Plant] = ParamPlant
        ),

    // === Existing product hierarchy filter ===
    FilteredProductHierarchy =
        Table.SelectRows(
            FilteredPlant,
            each Text.StartsWith(Text.From([Product hierarchy]), "00020")
        ),

    AddPlantMaterialKey =
        Table.AddColumn(
            FilteredProductHierarchy,
            "plant_material_key",
            each [Plant] & "-" & [Material],
            type text
        ),

    #"Reordered Columns" =
        Table.ReorderColumns(
            AddPlantMaterialKey,
            {
                "plant_material_key",
                "Plant",
                "Material",
                "Material Description",
                "BUn",
                "Product hierarchy",
                "Basic material",
                "Basic material 2",
                "MRP Typ",
                "MRP Controller",
                "PuRGrp",
                "DelFlag",
                "MtlSt_XPlt",
                "MtlSt_Plt",
                "X-Chn Mtl St",
                "SG",
                "ProcType",
                "Spec Proc",
                "ABC",
                "MTyp",
                "IPT",
                "PDT",
                "GRT",
                "TRLT",
                "Planning time fence",
                "LotSize",
                "Min. Lot Sze",
                "Rounding val.",
                "Max. Lot Size",
                "Fix. lot size",
                "BUn_1",
                "Safety Stock",
                "Reorder Point",
                "Threshold Qty",
                "AvaiChk",
                "Consumption mode",
                "Bwd cons. per.",
                "Fwd cons.period",
                "BkFlush",
                "PSloc",
                "Language",
                "Tot Valuated Stk",
                "Total Value",
                "Standard price",
                "Price Un",
                "SLife",
                "Propos.SA",
                "ESLoc",
                "R. Profile",
                "ProdS"
            },
            MissingField.Ignore
        )
in
    #"Reordered Columns"