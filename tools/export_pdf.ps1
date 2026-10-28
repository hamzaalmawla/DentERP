# Opens each generated .docx under docs/ with Microsoft Word, builds the table of
# contents, and saves the document plus a PDF next to it. Arabic documents (-AR)
# get a right-to-left table of contents.
$docs = Join-Path (Split-Path $PSScriptRoot -Parent) "docs"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    Get-ChildItem $docs -Recurse -Filter "SPU-Dental-*.docx" | Where-Object { $_.Name -notlike "~$*" } | ForEach-Object {
        $doc = $word.Documents.Open($_.FullName)
        foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
        $doc.Fields.Update() | Out-Null
        if ($_.BaseName -like "*-AR") {
            # wdReadingOrderRtl = 0
            foreach ($toc in $doc.TablesOfContents) { $toc.Range.ParagraphFormat.ReadingOrder = 0 }
        }
        $doc.Repaginate()
        foreach ($toc in $doc.TablesOfContents) { $toc.UpdatePageNumbers() }
        $doc.Save()
        $pdf = [IO.Path]::ChangeExtension($_.FullName, ".pdf")
        $doc.ExportAsFixedFormat($pdf, 17, $false, 0, 0, 0, 0, 0, $true, $true, 1)
        $doc.Close()
        Write-Output "wrote $pdf"
    }
}
finally {
    $word.Quit()
}
