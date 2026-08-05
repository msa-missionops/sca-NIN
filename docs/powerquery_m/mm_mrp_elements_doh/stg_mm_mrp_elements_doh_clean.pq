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

    CheckPlantEvalCols =
        if PlantColName = null then
            error "plant_evaluation table must contain a Plant column."
        else
            CleanPlantEvalHeaders,

    PlantEvaluation =
        Table.RenameColumns(
            CheckPlantEvalCols,
            {{PlantColName, "Plant"}},
            MissingField.Ignore
        ),

    ParamPlant =
        if Table.RowCount(PlantEvaluation) = 0 then
            error "plant_evaluation table must contain one plant row."
        else
            Text.Upper(Text.Trim(Text.From(PlantEvaluation{0}[Plant]))),

    // === Resolve paths for MM_MRP_ELEMENTS_DOH ===
    OutputRoot =
        Table.SelectRows(ConfigPaths, each [Key] = "OutputRoot"){0}[Value],

    TxRow =
        Table.SelectRows(ConfigTx, each [TransactionCode] = "MM_MRP_ELEMENTS_DOH"){0},

    TxFolder = TxRow[OutputFolder],
    FileExt  = TxRow[FileExt],

    FullPath =
        if Text.EndsWith(OutputRoot, "\")
        then OutputRoot & TxFolder
        else OutputRoot & "\" & TxFolder,

    // === Find latest run folder ===
    FolderSource =
        Folder.Contents(FullPath),

    VisibleFolders =
        Table.SelectRows(
            FolderSource,
            each [Attributes]?[Hidden]? <> true
                and [Attributes]?[Directory]? = true
        ),

    AddFolderSortDate =
        Table.AddColumn(
            VisibleFolders,
            "FolderSortDate",
            each if [Date created] <> null then [Date created] else [Date modified],
            type datetime
        ),

    SortedFolders =
        Table.Sort(
            AddFolderSortDate,
            {{"FolderSortDate", Order.Descending}}
        ),

    LatestFolderName =
        if Table.RowCount(SortedFolders) = 0 then
            error "No run folders found under: " & FullPath
        else
            SortedFolders{0}[Name],

    LatestFolderPath =
        if Text.EndsWith(FullPath, "\")
        then FullPath & LatestFolderName
        else FullPath & "\" & LatestFolderName,

    // === Load only active plant DOH export from latest run folder ===
    LatestFolderFiles =
        Folder.Files(LatestFolderPath),

    FileFiltered =
        Table.SelectRows(
            LatestFolderFiles,
            each [Attributes]?[Hidden]? <> true
                and Text.Lower([Extension]) = "." & Text.Lower(Text.Replace(FileExt, ".", ""))
                and Text.StartsWith(Text.Upper([Name]), "MM_MRP_ELEMENTS_DOH_")
                and Text.Contains(Text.Upper([Name]), "_" & ParamPlant & "_")
        ),

    SortedPlantFiles =
        Table.Sort(
            FileFiltered,
            {{"Date created", Order.Descending}}
        ),

    SelectedFile =
        if Table.RowCount(SortedPlantFiles) = 0 then
            error "No MM_MRP_ELEMENTS_DOH export file found for plant " & ParamPlant & " in latest run folder: " & LatestFolderPath
        else
            SortedPlantFiles{0},

    AsOfDate_st =
        Date.From(SelectedFile[Date created]),

    // === Function to import SQ01 MRP_ELEMENTS DOH export ===
    TransformSapFile = (FileContent as binary, SourceFileName as text) as table =>
        let
            Imported =
                Csv.Document(
                    FileContent,
                    [
                        Delimiter = "#(tab)",
                        Encoding = 1252,
                        QuoteStyle = QuoteStyle.None
                    ]
                ),

            ColCount =
                Table.ColumnCount(Imported),

            TypedRaw =
                Table.TransformColumnTypes(
                    Imported,
                    List.Transform(
                        {1..ColCount},
                        each {"Column" & Text.From(_), type text}
                    )
                ),

            Trimmed =
                Table.TransformColumns(
                    TypedRaw,
                    List.Transform(
                        Table.ColumnNames(TypedRaw),
                        each {_, each Text.Trim(Text.From(_)), type text}
                    )
                ),

            NonBlank =
                Table.SelectRows(
                    Trimmed,
                    each not List.IsEmpty(
                        List.RemoveMatchingItems(
                            Record.FieldValues(_),
                            {"", null}
                        )
                    )
                ),

            // Find the SAP header row dynamically
            AddIndex =
                Table.AddIndexColumn(
                    NonBlank,
                    "__RowIndex",
                    0,
                    1,
                    Int64.Type
                ),

            HeaderRows =
                Table.SelectRows(
                    AddIndex,
                    each
                        List.Contains(Record.FieldValues(_), "Plnt")
                        and List.Contains(Record.FieldValues(_), "Material")
                        and List.Contains(Record.FieldValues(_), "El")
                ),

            HeaderRowIndex =
                if Table.RowCount(HeaderRows) = 0 then
                    error "Could not find SAP header row in file: " & SourceFileName
                else
                    HeaderRows{0}[__RowIndex],

            FromHeader =
                Table.Skip(NonBlank, HeaderRowIndex),

            Promoted =
                Table.PromoteHeaders(
                    FromHeader,
                    [PromoteAllScalars = true]
                ),

            RemoveBlankHeaderCols =
                Table.SelectColumns(
                    Promoted,
                    List.Select(
                        Table.ColumnNames(Promoted),
                        each Text.Trim(_) <> ""
                    )
                ),

            Renamed =
                Table.RenameColumns(
                    RemoveBlankHeaderCols,
                    {
                        {"Plnt", "Plant"},
                        {"Material", "Material No."},
                        {"El", "Requirements Type"},
                        {"Customer Request Date", "Requirements Date"},
                        {"Rec./reqd.qty", "Req. Qty."}
                    },
                    MissingField.Ignore
                ),

            WithSourceFile =
                Table.AddColumn(
                    Renamed,
                    "Source File",
                    each SourceFileName,
                    type text
                ),

            WithRunFolder =
                Table.AddColumn(
                    WithSourceFile,
                    "Run Folder",
                    each LatestFolderName,
                    type text
                ),

            WithEvaluationPlant =
                Table.AddColumn(
                    WithRunFolder,
                    "Evaluation Plant",
                    each ParamPlant,
                    type text
                )
        in
            WithEvaluationPlant,

    // === Import selected plant file only ===
    ImportedPlantFile =
        TransformSapFile(
            SelectedFile[Content],
            SelectedFile[Name]
        ),

    // === Type conversions ===
    Typed =
        Table.TransformColumns(
            ImportedPlantFile,
            {
                {"Req. Qty.", each try Number.From(Text.Replace(Text.From(_), ",", "")) otherwise null, type number},
                {"Requirements Date", each try Date.From(Text.From(_)) otherwise null, type date},
                {"Changed on", each try Date.From(Text.From(_)) otherwise null, type date}
            },
            null,
            MissingField.Ignore
        ),

    // === Business rules ===
    Replacer_Null_Req_Date =
        Table.ReplaceValue(
            Typed,
            null,
            AsOfDate_st,
            Replacer.ReplaceValue,
            {"Requirements Date"}
        ),

    Filtered =
        Table.SelectRows(
            Replacer_Null_Req_Date,
            each [Requirements Date] >= AsOfDate_st
        ),

    AddWeekEndingDate =
        Table.AddColumn(
            Filtered,
            "Week Ending",
            each
                if [Requirements Date] = null then
                    null
                else
                    Date.AddDays(
                        [Requirements Date],
                        7 - Date.DayOfWeek([Requirements Date], Day.Friday)
                    ),
            type date
        ),

    // Existing DOH adjustment rule retained
    AddAdjReqQty =
        Table.AddColumn(
            AddWeekEndingDate,
            "Adj Req Qty",
            each
                if Text.Lower(Text.From([Requirements Type])) = "bb" then
                    [#"Req. Qty."] / 2
                else
                    [#"Req. Qty."],
            type number
        ),

    // === Normalize keys ===
    ExpKeys =
        Table.TransformColumns(
            AddAdjReqQty,
            {
                {"Plant", each Text.Upper(Text.Trim(Text.From(_))), type text},
                {"Material No.", each Text.TrimStart(Text.Upper(Text.Trim(Text.From(_))), {"0"}), type text},
                {"Requirements Type", each Text.Upper(Text.Trim(Text.From(_))), type text},
                {"BUn", each Text.Upper(Text.Trim(Text.From(_))), type text}
            },
            null,
            MissingField.Ignore
        ),

    // === Final sort ===
    Sorted =
        Table.Sort(
            ExpKeys,
            {
                {"Plant", Order.Ascending},
                {"Material No.", Order.Ascending},
                {"Week Ending", Order.Ascending},
                {"Requirements Date", Order.Ascending}
            }
        )
in
    Sorted