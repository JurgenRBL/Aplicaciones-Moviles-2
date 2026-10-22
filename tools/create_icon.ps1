Add-Type -AssemblyName System.Drawing
$assetRoot = Join-Path (Get-Location) 'src\assets'
$canvas = New-Object System.Drawing.Bitmap 1024,1024
$paint = [System.Drawing.Graphics]::FromImage($canvas)
$paint.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
function Brush($hex) { return New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml($hex)) }
$teal = Brush '#146B66'
$cream = Brush '#FFF1D4'
$tan = Brush '#DEAB75'
$brown = Brush '#865739'
$ink = Brush '#3E322D'
$white = Brush '#FFFFFF'
$coral = Brush '#EC8F7D'
$paint.Clear([System.Drawing.ColorTranslator]::FromHtml('#146B66'))
$paint.FillEllipse((Brush '#217D75'),105,105,814,814)
$ear = New-Object System.Drawing.Drawing2D.GraphicsPath
$ear.AddBezier(310,280,130,140,112,440,205,650)
$ear.AddBezier(205,650,280,720,345,410,310,280)
$paint.FillPath($brown,$ear)
$other = $ear.Clone()
$mirror = New-Object System.Drawing.Drawing2D.Matrix -ArgumentList @(-1,0,0,1,1024,0)
$other.Transform($mirror)
$paint.FillPath($brown,$other)
$paint.FillEllipse($cream,262,220,500,570)
$paint.FillEllipse($tan,330,348,140,168)
$paint.FillEllipse($ink,385,418,43,53)
$paint.FillEllipse($ink,598,418,43,53)
$paint.FillEllipse($white,394,425,12,14)
$paint.FillEllipse($white,607,425,12,14)
$paint.FillEllipse($white,365,500,294,190)
$paint.FillEllipse($coral,478,612,68,112)
$paint.FillEllipse($ink,463,517,98,65)
$pen = New-Object System.Drawing.Pen ([System.Drawing.ColorTranslator]::FromHtml('#3E322D')),12
$pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
$pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
$paint.DrawBezier($pen,512,572,512,626,471,640,442,610)
$paint.DrawBezier($pen,512,572,512,626,553,640,582,610)
$paint.FillEllipse($tan,327,556,14,14)
$paint.FillEllipse($tan,354,576,10,10)
$paint.FillEllipse($tan,683,556,14,14)
$paint.FillEllipse($tan,660,576,10,10)
$canvas.Save((Join-Path $assetRoot 'icon.png'),[System.Drawing.Imaging.ImageFormat]::Png)
$canvas.Save((Join-Path $assetRoot 'perrito.png'),[System.Drawing.Imaging.ImageFormat]::Png)
$paint.Dispose()
$canvas.Dispose()
