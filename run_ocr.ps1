
Add-Type -AssemblyName System.Drawing
[Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null

 = 'C:/Users/USER/AppData/Local/Temp/ai-chat-custom-attachment-temp-file-953dfd3b-b7c9-4fb3-868d-d23e9dcf237b-2118726006327033869.png'
 = [System.IO.File]::OpenRead()
 = New-Object System.IO.MemoryStream
.CopyTo()
.Close()
 = .ToArray()

 = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
 = New-Object Windows.Storage.Streams.DataWriter()
.WriteBytes()
 = .StoreAsync()
 = .GetType()
 = .GetMethod('GetResults')
while (.Status -eq 0) { [System.Threading.Thread]::Sleep(20) }

.Seek(0)
 = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync()
while (.Status -eq 0) { [System.Threading.Thread]::Sleep(20) }
 = .GetResults()

 = .GetSoftwareBitmapAsync()
while (.Status -eq 0) { [System.Threading.Thread]::Sleep(20) }
 = .GetResults()

 = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
 = .RecognizeAsync()
while (.Status -eq 0) { [System.Threading.Thread]::Sleep(20) }
 = .GetResults()
Write-Output '=== OCR RESULT ==='
Write-Output .Text
