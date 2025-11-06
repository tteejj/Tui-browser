' IDEAScript: Workflow Builder
' Author: Custom
' Date: 2025-09-24
' Purpose: Chain @functions, database operations, and multi-joins for financial data analysis
' Disclaimer: This script is provided as is without any warranties.
' UserType: CAS

Option Explicit

Dim vbcrlf As String
Dim dblist() As String
Dim allfields() As String
Dim numfields() As String
Dim charfields() As String
Dim operationTypes() As String

Dim currentDB As Object
Dim currentDBName As String
Dim currentDBBaseName As String
Dim selectedDBTextValue As String
Dim selectedDBIndexValue As Double
Dim dbcollection As Object
Dim numofdb As Double

Dim step1OpType As Double
Dim step1Database As Double
Dim step1Field As Double
Dim step1Params As String
Dim step1Target As String
Dim step1Active As Double

Dim step2OpType As Double
Dim step2Database As Double
Dim step2Field As Double
Dim step2Params As String
Dim step2Target As String
Dim step2Active As Double

Dim step3OpType As Double
Dim step3Database As Double
Dim step3Field As Double
Dim step3Params As String
Dim step3Target As String
Dim step3Active As Double

Dim step4OpType As Double
Dim step4Database As Double
Dim step4Field As Double
Dim step4Params As String
Dim step4Target As String
Dim step4Active As Double

Dim step5OpType As Double
Dim step5Database As Double
Dim step5Field As Double
Dim step5Params As String
Dim step5Target As String
Dim step5Active As Double

Dim activeSteps As Double
Dim ExitScript As Boolean
Dim choice As Integer
Dim executionLog As String
Dim lastResultDB As String

Begin Dialog WorkflowBuilder 29,0,750,520," ", .WorkflowBuilderDisplay
    Text 10,5,730,15,"Workflow Builder - Multi-Join, Extract, Transform Financial Data"

    Text 10,30,120,12,"Source Database:"
    DropListBox 135,28,200,100,dblist(),.dlbDb
    PushButton 340,28,15,12,"...",.btnChoosedb

    Text 10,55,30,12,"Step"
    Text 45,55,100,12,"Operation"
    Text 150,55,80,12,"Database/Field"
    Text 235,55,80,12,"Source Field"
    Text 320,55,140,12,"Parameters"
    Text 465,55,90,12,"Result Name"
    Text 560,55,40,12,"Active"

    Text 15,75,20,12,"1"
    DropListBox 45,73,100,100,operationTypes(),.OpType1
    DropListBox 150,73,80,100,dblist(),.Database1
    DropListBox 235,73,80,100,allfields(),.Field1
    TextBox 320,73,140,14,.Params1
    TextBox 465,73,90,14,.Target1
    CheckBox 560,73,20,12,"",.Active1

    Text 15,95,20,12,"2"
    DropListBox 45,93,100,100,operationTypes(),.OpType2
    DropListBox 150,93,80,100,dblist(),.Database2
    DropListBox 235,93,80,100,allfields(),.Field2
    TextBox 320,93,140,14,.Params2
    TextBox 465,93,90,14,.Target2
    CheckBox 560,93,20,12,"",.Active2

    Text 15,115,20,12,"3"
    DropListBox 45,113,100,100,operationTypes(),.OpType3
    DropListBox 150,113,80,100,dblist(),.Database3
    DropListBox 235,113,80,100,allfields(),.Field3
    TextBox 320,113,140,14,.Params3
    TextBox 465,113,90,14,.Target3
    CheckBox 560,113,20,12,"",.Active3

    Text 15,135,20,12,"4"
    DropListBox 45,133,100,100,operationTypes(),.OpType4
    DropListBox 150,133,80,100,dblist(),.Database4
    DropListBox 235,133,80,100,allfields(),.Field4
    TextBox 320,133,140,14,.Params4
    TextBox 465,133,90,14,.Target4
    CheckBox 560,133,20,12,"",.Active4

    Text 15,155,20,12,"5"
    DropListBox 45,153,100,100,operationTypes(),.OpType5
    DropListBox 150,153,80,100,dblist(),.Database5
    DropListBox 235,153,80,100,allfields(),.Field5
    TextBox 320,153,140,14,.Params5
    TextBox 465,153,90,14,.Target5
    CheckBox 560,153,20,12,"",.Active5

    GroupBox 10,180,730,110,"Operation Help"
    Text 20,195,710,15,"FIELD OPS: @TRIM @UPPER @LOWER @LEFT(n) @RIGHT(n) @MID(start,len) @ABS @ROUND(dec) @INT @YEAR @MONTH @DAY"
    Text 20,212,710,15,"DATABASE OPS: JOIN(db,prikey,forkey) EXTRACT(criteria) SORT(field,A/D) SUMMARIZE(field) INDEX(field)"
    Text 20,229,710,15,"CUSTOM OPS: REGEX(pattern,replacement) FILLDOWN APPEND(db)"
    Text 20,246,710,15,"MULTI-JOIN: Use JOIN multiple times, output becomes input for next step"
    Text 20,263,710,15,"Variables: Use {RESULT1} {RESULT2} etc in params to reference prior step outputs"

    GroupBox 10,295,730,90,"Execution Log"
    Text 20,310,710,70," ", .lblLog

    PushButton 450,400,80,20,"Preview",.btnPreview
    PushButton 540,400,80,20,"Save Flow",.btnSave
    PushButton 630,400,80,20,"Load Flow",.btnLoad

    PushButton 450,425,80,20,"Refresh DBs",.RefreshDB
    PushButton 540,425,80,20,"Refresh Fields",.RefreshFields
    PushButton 630,425,80,20,"Clear All",.ClearAll

    OKButton 540,470,80,20,"Execute",.btnOK
    CancelButton 630,470,80,20,"Exit",.btnCancel
End Dialog

Dim dlgWorkflowBuilderInstance As WorkflowBuilder

Sub Main
    Init

    Do
        choice = Dialog(dlgWorkflowBuilderInstance)
        If choice = 0 Then
            ExitScript = True
        End If

        If ExitScript = False Then
            ExecuteWorkflow
        End If
        Client.RefreshFileExplorer
    Loop Until ExitScript

    If executionLog <> "" Then
        MsgBox "Workflow completed." & vbcrlf & vbcrlf & executionLog, MB_ICONINFORMATION, "Workflow Complete"
    End If
End Sub

Sub Init
    vbcrlf = Chr(13) & Chr(10)
    ExitScript = False
    activeSteps = 0
    executionLog = ""
    lastResultDB = ""

    ReDim dblist(1)
    ReDim allfields(1)
    ReDim numfields(0)
    ReDim charfields(0)

    dblist(0) = "Current Database"
    allfields(0) = "No Database Selected"
    numfields(0) = "-"
    charfields(0) = "-"

    LoadOperationTypes
    LoadDbCollection
    LoadCurrentDatabase

    step1Active = 1
    step1Target = "RESULT1"
    step2Target = "RESULT2"
    step3Target = "RESULT3"
    step4Target = "RESULT4"
    step5Target = "RESULT5"
End Sub

Sub LoadOperationTypes
    ReDim operationTypes(19)
    operationTypes(0) = "@TRIM"
    operationTypes(1) = "@UPPER"
    operationTypes(2) = "@LOWER"
    operationTypes(3) = "@LEFT"
    operationTypes(4) = "@RIGHT"
    operationTypes(5) = "@MID"
    operationTypes(6) = "@ABS"
    operationTypes(7) = "@ROUND"
    operationTypes(8) = "@INT"
    operationTypes(9) = "@YEAR"
    operationTypes(10) = "@MONTH"
    operationTypes(11) = "@DAY"
    operationTypes(12) = "JOIN"
    operationTypes(13) = "EXTRACT"
    operationTypes(14) = "SORT"
    operationTypes(15) = "SUMMARIZE"
    operationTypes(16) = "INDEX"
    operationTypes(17) = "REGEX"
    operationTypes(18) = "FILLDOWN"
    operationTypes(19) = "APPEND"
End Sub

Function LoadDbCollection
    Dim task As Object
    Dim i As Double

    On Error Resume Next
    If currentDBName = "" Or currentDBName = "-" Then
        currentDBName = Client.CurrentDatabase.name
        currentDBBaseName = GetBaseName(currentDBName)
        selectedDBTextValue = currentDBName
    End If

    Set task = Client.ProjectManagement
    Set dbcollection = task.Databases
    numofdb = dbcollection.Count

    ReDim dblist(numofdb + 1)
    dblist(0) = "Current Database (" & currentDBBaseName & ")"

    For i = 1 To numofdb
        dblist(i) = dbcollection.GetAt(i - 1)
    Next i

    Set task = Nothing
    On Error GoTo 0
End Function

Function GetBaseName(fullPath As String) As String
    Dim pos As Double
    Dim result As String

    result = fullPath
    pos = iIsIni("\", result)

    Do While pos > 0
        result = iMid(result, pos + 1)
        pos = iIsIni("\", result)
    Loop

    GetBaseName = result
End Function

Sub LoadCurrentDatabase
    On Error Resume Next
    Set currentDB = Client.CurrentDatabase
    If currentDB Is Nothing Then
        currentDBName = ""
        Exit Sub
    End If

    currentDBName = currentDB.Name
    currentDBBaseName = GetBaseName(currentDBName)
    LoadFieldLists currentDB
    On Error GoTo 0
End Sub

Function LoadFieldLists(db As Object)
    If db Is Nothing Then Exit Function

    Dim table As Object
    Dim field As Object
    Dim i As Double
    Dim j As Double
    Dim k As Double
    Dim l As Double
    Dim fieldscount As Integer

    Set table = db.TableDef
    fieldscount = table.Count

    ReDim allfields(fieldscount - 1)
    ReDim numfields(0)
    ReDim charfields(0)

    j = 1
    k = 1
    l = 0

    numfields(0) = "-"
    charfields(0) = "-"

    For i = 1 To fieldscount
        Set field = table.GetFieldAt(i)
        allfields(l) = field.Name
        l = l + 1

        If field.IsNumeric Then
            ReDim Preserve numfields(j)
            numfields(j) = field.Name
            j = j + 1
        End If

        If field.IsCharacter Then
            ReDim Preserve charfields(k)
            charfields(k) = field.Name
            k = k + 1
        End If

        Set field = Nothing
    Next i

    Set table = Nothing
End Function

Function WorkflowBuilderDisplay(controlID$, action%, suppValue%)
    Select Case action
        Case 1
            LoadDbCollection
            dlglistboxarray "dlbDb", dblist
            dlglistboxarray "OpType1", operationTypes
            dlglistboxarray "OpType2", operationTypes
            dlglistboxarray "OpType3", operationTypes
            dlglistboxarray "OpType4", operationTypes
            dlglistboxarray "OpType5", operationTypes

            dlglistboxarray "Database1", dblist
            dlglistboxarray "Database2", dblist
            dlglistboxarray "Database3", dblist
            dlglistboxarray "Database4", dblist
            dlglistboxarray "Database5", dblist

            dlglistboxarray "Field1", allfields
            dlglistboxarray "Field2", allfields
            dlglistboxarray "Field3", allfields
            dlglistboxarray "Field4", allfields
            dlglistboxarray "Field5", allfields

            dlgtext "Target1", step1Target
            dlgtext "Target2", step2Target
            dlgtext "Target3", step3Target
            dlgtext "Target4", step4Target
            dlgtext "Target5", step5Target

            dlgtext "lblLog", executionLog

            UpdateValidationDisplay

        Case 2
            WorkflowBuilderDisplay = 1

            Select Case controlID
                Case "dlbDb"
                    selectedDBIndexValue = dlgvalue("dlbDb")
                    selectedDBTextValue = dlgtext("dlbDb")

                    If selectedDBIndexValue = 0 And currentDBName <> "" Then
                        selectedDBTextValue = currentDBName
                    End If

                    RefreshFieldsFromDB selectedDBTextValue
                    UpdateValidationDisplay

                Case "btnChoosedb"
                    Dim chosenDB As String
                    chosenDB = BrowseForFile
                    If chosenDB <> "" Then
                        selectedDBTextValue = chosenDB
                        RefreshFieldsFromDB selectedDBTextValue
                        UpdateValidationDisplay
                    End If

                Case "OpType1", "OpType2", "OpType3", "OpType4", "OpType5"
                    UpdateValidationDisplay

                Case "Database1"
                    step1Database = suppValue
                    RefreshFieldsForStep 1

                Case "Database2"
                    step2Database = suppValue
                    RefreshFieldsForStep 2

                Case "Database3"
                    step3Database = suppValue
                    RefreshFieldsForStep 3

                Case "Database4"
                    step4Database = suppValue
                    RefreshFieldsForStep 4

                Case "Database5"
                    step5Database = suppValue
                    RefreshFieldsForStep 5

                Case "btnPreview"
                    ShowPreview

                Case "btnSave"
                    SaveWorkflow

                Case "btnLoad"
                    LoadWorkflow

                Case "RefreshDB"
                    LoadDbCollection
                    LoadCurrentDatabase
                    dlglistboxarray "dlbDb", dblist
                    dlglistboxarray "Database1", dblist
                    dlglistboxarray "Database2", dblist
                    dlglistboxarray "Database3", dblist
                    dlglistboxarray "Database4", dblist
                    dlglistboxarray "Database5", dblist
                    dlglistboxarray "Field1", allfields
                    dlglistboxarray "Field2", allfields
                    dlglistboxarray "Field3", allfields
                    dlglistboxarray "Field4", allfields
                    dlglistboxarray "Field5", allfields
                    UpdateValidationDisplay

                Case "RefreshFields"
                    RefreshFieldsFromDB selectedDBTextValue
                    dlglistboxarray "Field1", allfields
                    dlglistboxarray "Field2", allfields
                    dlglistboxarray "Field3", allfields
                    dlglistboxarray "Field4", allfields
                    dlglistboxarray "Field5", allfields
                    UpdateValidationDisplay

                Case "ClearAll"
                    step1Active = 0
                    step2Active = 0
                    step3Active = 0
                    step4Active = 0
                    step5Active = 0
                    dlgvalue "Active1", 0
                    dlgvalue "Active2", 0
                    dlgvalue "Active3", 0
                    dlgvalue "Active4", 0
                    dlgvalue "Active5", 0
                    executionLog = ""
                    dlgtext "lblLog", executionLog
                    UpdateValidationDisplay

                Case "btnOK"
                    GetDialogValues
                    WorkflowBuilderDisplay = 0
                    ExitScript = False

                Case "btnCancel"
                    WorkflowBuilderDisplay = 0
                    ExitScript = True

            End Select
    End Select

    If action = 2 Then UpdateValidationDisplay
End Function

Sub UpdateValidationDisplay
    Dim validationText As String
    Dim stepCount As Double

    stepCount = 0
    validationText = "Workflow Status:" & vbcrlf

    If dlgvalue("Active1") = 1 Then stepCount = stepCount + 1
    If dlgvalue("Active2") = 1 Then stepCount = stepCount + 1
    If dlgvalue("Active3") = 1 Then stepCount = stepCount + 1
    If dlgvalue("Active4") = 1 Then stepCount = stepCount + 1
    If dlgvalue("Active5") = 1 Then stepCount = stepCount + 1

    validationText = validationText & "Active Steps: " & stepCount & vbcrlf

    If selectedDBTextValue <> "" Then
        validationText = validationText & "Source DB: " & GetBaseName(selectedDBTextValue)
    End If

    dlgtext "lblValidation", validationText
End Sub

Sub GetDialogValues
    step1OpType = dlgvalue("OpType1")
    step1Database = dlgvalue("Database1")
    step1Field = dlgvalue("Field1")
    step1Params = dlgtext("Params1")
    step1Target = dlgtext("Target1")
    step1Active = dlgvalue("Active1")

    step2OpType = dlgvalue("OpType2")
    step2Database = dlgvalue("Database2")
    step2Field = dlgvalue("Field2")
    step2Params = dlgtext("Params2")
    step2Target = dlgtext("Target2")
    step2Active = dlgvalue("Active2")

    step3OpType = dlgvalue("OpType3")
    step3Database = dlgvalue("Database3")
    step3Field = dlgvalue("Field3")
    step3Params = dlgtext("Params3")
    step3Target = dlgtext("Target3")
    step3Active = dlgvalue("Active3")

    step4OpType = dlgvalue("OpType4")
    step4Database = dlgvalue("Database4")
    step4Field = dlgvalue("Field4")
    step4Params = dlgtext("Params4")
    step4Target = dlgtext("Target4")
    step4Active = dlgvalue("Active4")

    step5OpType = dlgvalue("OpType5")
    step5Database = dlgvalue("Database5")
    step5Field = dlgvalue("Field5")
    step5Params = dlgtext("Params5")
    step5Target = dlgtext("Target5")
    step5Active = dlgvalue("Active5")
End Sub

Sub RefreshFieldsForStep(stepNum As Double)
    Dim dbIndex As Double
    Dim workingDB As Object
    Dim dbName As String

    Select Case stepNum
        Case 1: dbIndex = step1Database
        Case 2: dbIndex = step2Database
        Case 3: dbIndex = step3Database
        Case 4: dbIndex = step4Database
        Case 5: dbIndex = step5Database
    End Select

    If dbIndex = 0 Then
        Set workingDB = currentDB
        dbName = currentDBName
    Else
        dbName = dblist(dbIndex)
        On Error Resume Next
        Set workingDB = Client.OpenDatabase(dbName)
        On Error GoTo 0
    End If

    If Not workingDB Is Nothing Then
        LoadFieldLists workingDB
        Select Case stepNum
            Case 1: dlglistboxarray "Field1", allfields
            Case 2: dlglistboxarray "Field2", allfields
            Case 3: dlglistboxarray "Field3", allfields
            Case 4: dlglistboxarray "Field4", allfields
            Case 5: dlglistboxarray "Field5", allfields
        End Select
    End If

    If dbIndex <> 0 Then Set workingDB = Nothing
End Sub

Sub RefreshFieldsFromDB(dbName As String)
    Dim workingDB As Object

    If dbName = "" Or dbName = "-" Then Exit Sub

    On Error Resume Next
    Set workingDB = Client.OpenDatabase(dbName)
    If workingDB Is Nothing Then
        Set workingDB = currentDB
    End If
    On Error GoTo 0

    If Not workingDB Is Nothing Then
        LoadFieldLists workingDB
        dlglistboxarray "Field1", allfields
        dlglistboxarray "Field2", allfields
        dlglistboxarray "Field3", allfields
        dlglistboxarray "Field4", allfields
        dlglistboxarray "Field5", allfields
    End If

    Set workingDB = Nothing
End Sub

Sub ShowPreview
    Dim preview As String
    Dim i As Double

    GetDialogValues

    preview = "WORKFLOW PREVIEW:" & vbcrlf & vbcrlf
    preview = preview & "Source: " & GetBaseName(selectedDBTextValue) & vbcrlf & vbcrlf

    For i = 1 To 5
        preview = preview & GetStepPreview(i)
    Next i

    MsgBox preview, MB_ICONINFORMATION, "Workflow Preview"
End Sub

Function GetStepPreview(stepNum As Double) As String
    Dim opIndex As Double
    Dim fieldIndex As Double
    Dim params As String
    Dim targetName As String
    Dim isActive As Double
    Dim dbIndex As Double
    Dim preview As String
    Dim opName As String
    Dim fieldName As String
    Dim dbName As String

    Select Case stepNum
        Case 1
            isActive = step1Active
            opIndex = step1OpType
            dbIndex = step1Database
            fieldIndex = step1Field
            params = step1Params
            targetName = step1Target
        Case 2
            isActive = step2Active
            opIndex = step2OpType
            dbIndex = step2Database
            fieldIndex = step2Field
            params = step2Params
            targetName = step2Target
        Case 3
            isActive = step3Active
            opIndex = step3OpType
            dbIndex = step3Database
            fieldIndex = step3Field
            params = step3Params
            targetName = step3Target
        Case 4
            isActive = step4Active
            opIndex = step4OpType
            dbIndex = step4Database
            fieldIndex = step4Field
            params = step4Params
            targetName = step4Target
        Case 5
            isActive = step5Active
            opIndex = step5OpType
            dbIndex = step5Database
            fieldIndex = step5Field
            params = step5Params
            targetName = step5Target
    End Select

    If isActive = 0 Then
        GetStepPreview = ""
        Exit Function
    End If

    opName = operationTypes(opIndex)
    If fieldIndex <= UBound(allfields) Then
        fieldName = allfields(fieldIndex)
    Else
        fieldName = "[Unknown]"
    End If

    If dbIndex = 0 Then
        dbName = "[Source DB]"
    Else
        dbName = GetBaseName(dblist(dbIndex))
    End If

    preview = "Step " & stepNum & ": " & opName & vbcrlf
    preview = preview & "  Field: " & fieldName & vbcrlf

    If opIndex = 12 Then ' JOIN
        preview = preview & "  Join DB: " & dbName & vbcrlf
    End If

    If params <> "" Then
        preview = preview & "  Params: " & params & vbcrlf
    End If

    preview = preview & "  Output: " & targetName & vbcrlf & vbcrlf

    GetStepPreview = preview
End Function

Sub SaveWorkflow
    Dim filename As String
    Dim fileNum As Integer

    filename = Client.UniqueFileName(Client.WorkingDirectory & "Workflow_" & Format(Now, "YYYYMMDD_HHMMSS") & ".wf")

    On Error Resume Next
    fileNum = FreeFile
    Open filename For Output As fileNum

    GetDialogValues

    Print #fileNum, "WORKFLOW v1.0"
    Print #fileNum, selectedDBTextValue

    ' Step 1
    Print #fileNum, step1Active & "|" & step1OpType & "|" & step1Database & "|" & step1Field & "|" & step1Params & "|" & step1Target
    ' Step 2
    Print #fileNum, step2Active & "|" & step2OpType & "|" & step2Database & "|" & step2Field & "|" & step2Params & "|" & step2Target
    ' Step 3
    Print #fileNum, step3Active & "|" & step3OpType & "|" & step3Database & "|" & step3Field & "|" & step3Params & "|" & step3Target
    ' Step 4
    Print #fileNum, step4Active & "|" & step4OpType & "|" & step4Database & "|" & step4Field & "|" & step4Params & "|" & step4Target
    ' Step 5
    Print #fileNum, step5Active & "|" & step5OpType & "|" & step5Database & "|" & step5Field & "|" & step5Params & "|" & step5Target

    Close fileNum

    If Err.Number = 0 Then
        MsgBox "Workflow saved: " & GetBaseName(filename), MB_ICONINFORMATION
    Else
        MsgBox "Error saving workflow: " & Err.Description, MB_ICONERROR
    End If
    On Error GoTo 0
End Sub

Sub LoadWorkflow
    Dim filename As String
    Dim fileNum As Integer
    Dim version As String
    Dim stepData() As String
    Dim line As String

    filename = Client.OpenFileDialog("", "Workflow Files (*.wf)|*.wf", 0, "", "Select Workflow File", 0)
    If filename = "" Then Exit Sub

    On Error Resume Next
    fileNum = FreeFile
    Open filename For Input As fileNum

    Line Input #fileNum, version
    If version <> "WORKFLOW v1.0" Then
        MsgBox "Invalid workflow file format", MB_ICONERROR
        Close fileNum
        Exit Sub
    End If

    Line Input #fileNum, selectedDBTextValue

    ' Load Step 1
    Line Input #fileNum, line
    stepData = Split(line, "|")
    If UBound(stepData) >= 5 Then
        step1Active = CDbl(stepData(0))
        step1OpType = CDbl(stepData(1))
        step1Database = CDbl(stepData(2))
        step1Field = CDbl(stepData(3))
        step1Params = stepData(4)
        step1Target = stepData(5)
    End If

    ' Load Step 2
    Line Input #fileNum, line
    stepData = Split(line, "|")
    If UBound(stepData) >= 5 Then
        step2Active = CDbl(stepData(0))
        step2OpType = CDbl(stepData(1))
        step2Database = CDbl(stepData(2))
        step2Field = CDbl(stepData(3))
        step2Params = stepData(4)
        step2Target = stepData(5)
    End If

    ' Load Step 3
    Line Input #fileNum, line
    stepData = Split(line, "|")
    If UBound(stepData) >= 5 Then
        step3Active = CDbl(stepData(0))
        step3OpType = CDbl(stepData(1))
        step3Database = CDbl(stepData(2))
        step3Field = CDbl(stepData(3))
        step3Params = stepData(4)
        step3Target = stepData(5)
    End If

    ' Load Step 4
    Line Input #fileNum, line
    stepData = Split(line, "|")
    If UBound(stepData) >= 5 Then
        step4Active = CDbl(stepData(0))
        step4OpType = CDbl(stepData(1))
        step4Database = CDbl(stepData(2))
        step4Field = CDbl(stepData(3))
        step4Params = stepData(4)
        step4Target = stepData(5)
    End If

    ' Load Step 5
    Line Input #fileNum, line
    stepData = Split(line, "|")
    If UBound(stepData) >= 5 Then
        step5Active = CDbl(stepData(0))
        step5OpType = CDbl(stepData(1))
        step5Database = CDbl(stepData(2))
        step5Field = CDbl(stepData(3))
        step5Params = stepData(4)
        step5Target = stepData(5)
    End If

    Close fileNum

    If Err.Number = 0 Then
        ' Update dialog
        dlgvalue "Active1", step1Active
        dlgvalue "Active2", step2Active
        dlgvalue "Active3", step3Active
        dlgvalue "Active4", step4Active
        dlgvalue "Active5", step5Active

        dlgvalue "OpType1", step1OpType
        dlgvalue "OpType2", step2OpType
        dlgvalue "OpType3", step3OpType
        dlgvalue "OpType4", step4OpType
        dlgvalue "OpType5", step5OpType

        dlgtext "Params1", step1Params
        dlgtext "Params2", step2Params
        dlgtext "Params3", step3Params
        dlgtext "Params4", step4Params
        dlgtext "Params5", step5Params

        dlgtext "Target1", step1Target
        dlgtext "Target2", step2Target
        dlgtext "Target3", step3Target
        dlgtext "Target4", step4Target
        dlgtext "Target5", step5Target

        MsgBox "Workflow loaded successfully", MB_ICONINFORMATION
    Else
        MsgBox "Error loading workflow: " & Err.Description, MB_ICONERROR
    End If
    On Error GoTo 0
End Sub

Sub ExecuteWorkflow
    GetDialogValues
    CollectActiveSteps

    If activeSteps = 0 Then
        MsgBox "No active steps selected", MB_ICONWARNING
        ExitScript = True
        Exit Sub
    End If

    executionLog = "Starting workflow..." & vbcrlf
    lastResultDB = selectedDBTextValue

    Dim i As Double
    For i = 1 To 5
        ExecuteStep i
    Next i

    executionLog = executionLog & vbcrlf & "Workflow complete."
    dlgtext "lblLog", executionLog
End Sub

Sub CollectActiveSteps
    activeSteps = 0

    If step1Active = 1 Then activeSteps = activeSteps + 1
    If step2Active = 1 Then activeSteps = activeSteps + 1
    If step3Active = 1 Then activeSteps = activeSteps + 1
    If step4Active = 1 Then activeSteps = activeSteps + 1
    If step5Active = 1 Then activeSteps = activeSteps + 1
End Sub

Sub ExecuteStep(stepNum As Double)
    Dim opIndex As Double
    Dim dbIndex As Double
    Dim fieldIndex As Double
    Dim params As String
    Dim targetName As String
    Dim workingDB As Object
    Dim fieldName As String
    Dim isActive As Double
    Dim dbName As String
    Dim success As Boolean

    Select Case stepNum
        Case 1
            isActive = step1Active
            opIndex = step1OpType
            dbIndex = step1Database
            fieldIndex = step1Field
            params = step1Params
            targetName = step1Target
        Case 2
            isActive = step2Active
            opIndex = step2OpType
            dbIndex = step2Database
            fieldIndex = step2Field
            params = step2Params
            targetName = step2Target
        Case 3
            isActive = step3Active
            opIndex = step3OpType
            dbIndex = step3Database
            fieldIndex = step3Field
            params = step3Params
            targetName = step3Target
        Case 4
            isActive = step4Active
            opIndex = step4OpType
            dbIndex = step4Database
            fieldIndex = step4Field
            params = step4Params
            targetName = step4Target
        Case 5
            isActive = step5Active
            opIndex = step5OpType
            dbIndex = step5Database
            fieldIndex = step5Field
            params = step5Params
            targetName = step5Target
    End Select

    If isActive = 0 Then Exit Sub

    ' Resolve variable substitution
    params = ResolveVariables(params)

    ' Get working database - use last result if available
    If lastResultDB <> "" And dbIndex = 0 Then
        dbName = lastResultDB
    ElseIf dbIndex = 0 Then
        Set workingDB = currentDB
        dbName = currentDBName
    Else
        dbName = dblist(dbIndex)
        On Error Resume Next
        Set workingDB = Client.OpenDatabase(dbName)
        On Error GoTo 0
    End If

    If workingDB Is Nothing And dbName <> "" Then
        On Error Resume Next
        Set workingDB = Client.OpenDatabase(dbName)
        On Error GoTo 0
    End If

    If workingDB Is Nothing Then
        executionLog = executionLog & "Step " & stepNum & ": ERROR - Cannot open database" & vbcrlf
        dlgtext "lblLog", executionLog
        Exit Sub
    End If

    LoadFieldLists workingDB
    If fieldIndex <= UBound(allfields) Then
        fieldName = allfields(fieldIndex)
    Else
        fieldName = ""
    End If

    If iLen(iTrim(targetName)) = 0 Then
        targetName = "RESULT" & stepNum
    End If

    executionLog = executionLog & "Step " & stepNum & ": " & operationTypes(opIndex) & " "

    ' Execute operation
    success = False
    If opIndex <= 11 Then
        ' Field operations
        success = ExecuteFieldOperation(workingDB, opIndex, fieldName, targetName, params)
    ElseIf opIndex = 12 Then
        ' JOIN
        success = ExecuteJoin(workingDB, dbName, fieldName, targetName, params, dbIndex)
    ElseIf opIndex = 13 Then
        ' EXTRACT
        success = ExecuteExtract(workingDB, targetName, params)
    ElseIf opIndex = 14 Then
        ' SORT
        success = ExecuteSort(workingDB, fieldName, targetName, params)
    ElseIf opIndex = 15 Then
        ' SUMMARIZE
        success = ExecuteSummarize(workingDB, fieldName, targetName)
    ElseIf opIndex = 16 Then
        ' INDEX
        success = ExecuteIndex(workingDB, fieldName, targetName)
    ElseIf opIndex = 17 Then
        ' REGEX
        success = ExecuteRegex(workingDB, fieldName, targetName, params)
    ElseIf opIndex = 18 Then
        ' FILLDOWN
        success = ExecuteFillDown(workingDB, fieldName, targetName)
    ElseIf opIndex = 19 Then
        ' APPEND
        success = ExecuteAppend(workingDB, targetName, params, dbIndex)
    End If

    If success Then
        executionLog = executionLog & "✓ OK" & vbcrlf
        ' Update last result for chaining
        If targetName <> "" Then
            lastResultDB = Client.WorkingDirectory & targetName & ".IMD"
        End If
    Else
        executionLog = executionLog & "✗ FAILED" & vbcrlf
    End If

    dlgtext "lblLog", executionLog
    Set workingDB = Nothing
End Sub

Function ResolveVariables(params As String) As String
    Dim result As String
    Dim i As Double

    result = params

    For i = 1 To 5
        result = Replace(result, "{RESULT" & i & "}", Client.WorkingDirectory & "RESULT" & i & ".IMD")
    Next i

    ResolveVariables = result
End Function

Function ExecuteFieldOperation(db As Object, opIndex As Double, fieldName As String, targetName As String, params As String) As Boolean
    On Error GoTo ErrorHandler

    Dim task As Object
    Dim equation As String

    Set task = db.FieldManipulation

    Select Case opIndex
        Case 0: equation = "@Trim(" & fieldName & ")"
        Case 1: equation = "@Upper(" & fieldName & ")"
        Case 2: equation = "@Lower(" & fieldName & ")"
        Case 3: equation = "@Left(" & fieldName & "," & params & ")"
        Case 4: equation = "@Right(" & fieldName & "," & params & ")"
        Case 5: equation = "@Mid(" & fieldName & "," & params & ")"
        Case 6: equation = "@Abs(" & fieldName & ")"
        Case 7: equation = "@Round(" & fieldName & "," & params & ")"
        Case 8: equation = "@Int(" & fieldName & ")"
        Case 9: equation = "@Year(" & fieldName & ")"
        Case 10: equation = "@Month(" & fieldName & ")"
        Case 11: equation = "@Day(" & fieldName & ")"
    End Select

    task.AddFieldAt 1, targetName, equation
    task.PerformTask

    Set task = Nothing
    ExecuteFieldOperation = True
    Exit Function

ErrorHandler:
    ExecuteFieldOperation = False
End Function

Function ExecuteJoin(db As Object, priDBName As String, priKey As String, targetName As String, params As String, dbIndex As Double) As Boolean
    On Error GoTo ErrorHandler

    Dim task As Object
    Dim forDBName As String
    Dim forKey As String
    Dim paramsArr() As String

    ' Parse params: foreignDB,foreignKey or just foreignKey if DB specified in dropdown
    If iIsIni(",", params) > 0 Then
        paramsArr = Split(params, ",")
        forDBName = iTrim(paramsArr(0))
        forKey = iTrim(paramsArr(1))
    Else
        If dbIndex > 0 Then
            forDBName = dblist(dbIndex)
        Else
            forDBName = params
            forKey = priKey
        End If
        forKey = iTrim(params)
    End If

    Set task = db.JoinDatabase
    task.FileToJoin forDBName
    task.IncludeAllPriRecs
    task.PriIndexField priKey
    task.ForIndexField forKey
    task.OutputFileName targetName
    task.PerformTask db, targetName

    Set task = Nothing
    ExecuteJoin = True
    Exit Function

ErrorHandler:
    ExecuteJoin = False
End Function

Function ExecuteExtract(db As Object, targetName As String, criteria As String) As Boolean
    On Error GoTo ErrorHandler

    Dim task As Object

    Set task = db.Extraction
    task.AddExtraction targetName, "", criteria
    task.CreatePercentDb
    task.PerformTask 1, db.Count

    Set task = Nothing
    ExecuteExtract = True
    Exit Function

ErrorHandler:
    ExecuteExtract = False
End Function

Function ExecuteSort(db As Object, fieldName As String, targetName As String, sortOrder As String) As Boolean
    On Error GoTo ErrorHandler

    Dim task As Object
    Dim ascending As Boolean

    ascending = True
    If iUpper(iTrim(sortOrder)) = "D" Or iUpper(iTrim(sortOrder)) = "DESC" Then
        ascending = False
    End If

    Set task = db.Sort
    task.AddSortField fieldName, ascending
    task.OutputFileName targetName
    task.PerformTask

    Set task = Nothing
    ExecuteSort = True
    Exit Function

ErrorHandler:
    ExecuteSort = False
End Function

Function ExecuteSummarize(db As Object, fieldName As String, targetName As String) As Boolean
    On Error GoTo ErrorHandler

    Dim task As Object

    Set task = db.Summarization
    task.AddFieldToSummarize fieldName
    task.OutputFileName targetName
    task.PerformTask

    Set task = Nothing
    ExecuteSummarize = True
    Exit Function

ErrorHandler:
    ExecuteSummarize = False
End Function

Function ExecuteIndex(db As Object, fieldName As String, targetName As String) As Boolean
    On Error GoTo ErrorHandler

    Dim task As Object

    Set task = db.Index
    task.AddFieldToIndex fieldName
    task.OutputFileName targetName
    task.CreateIndex

    Set task = Nothing
    ExecuteIndex = True
    Exit Function

ErrorHandler:
    ExecuteIndex = False
End Function

Function ExecuteRegex(db As Object, fieldName As String, targetName As String, params As String) As Boolean
    On Error GoTo ErrorHandler

    Dim task As Object
    Dim paramsArr() As String
    Dim pattern As String
    Dim replacement As String
    Dim equation As String

    ' Parse params: pattern,replacement
    If iIsIni(",", params) > 0 Then
        paramsArr = Split(params, ",", 2)
        pattern = iTrim(paramsArr(0))
        If UBound(paramsArr) >= 1 Then
            replacement = iTrim(paramsArr(1))
        Else
            replacement = ""
        End If
    Else
        pattern = iTrim(params)
        replacement = ""
    End If

    Set task = db.FieldManipulation

    ' Use @RegexReplace if available, otherwise create custom function call
    equation = "@RegexReplace(" & fieldName & ",""" & pattern & """,""" & replacement & """)"

    task.AddFieldAt 1, targetName, equation
    task.PerformTask

    Set task = Nothing
    ExecuteRegex = True
    Exit Function

ErrorHandler:
    ExecuteRegex = False
End Function

Function ExecuteFillDown(db As Object, fieldName As String, targetName As String) As Boolean
    On Error GoTo ErrorHandler

    Dim task As Object

    Set task = db.FieldManipulation
    task.AddFieldAt 1, targetName, fieldName
    task.FillDown targetName
    task.PerformTask

    Set task = Nothing
    ExecuteFillDown = True
    Exit Function

ErrorHandler:
    ExecuteFillDown = False
End Function

Function ExecuteAppend(db As Object, targetName As String, params As String, dbIndex As Double) As Boolean
    On Error GoTo ErrorHandler

    Dim task As Object
    Dim appendDBName As String

    If params <> "" Then
        appendDBName = params
    ElseIf dbIndex > 0 Then
        appendDBName = dblist(dbIndex)
    Else
        ExecuteAppend = False
        Exit Function
    End If

    Set task = db.AppendDatabase
    task.AddDatabase appendDBName
    task.OutputFileName targetName
    task.PerformTask

    Set task = Nothing
    ExecuteAppend = True
    Exit Function

ErrorHandler:
    ExecuteAppend = False
End Function

Function BrowseForFile() As String
    BrowseForFile = Client.OpenFileDialog("", "IDEA Database (*.imd)|*.imd|All Files (*.*)|*.*", 0, "", "Select Database", 0)
End Function
