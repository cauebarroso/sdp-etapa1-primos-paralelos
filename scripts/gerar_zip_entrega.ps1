# =============================================================================
# Gera o ZIP da entrega, sem lixo e sem dados pessoais.
#
# Zipar a pasta inteira no Explorer inclui coisas que o git ignora de
# proposito -- entre elas .claude/, que guarda o nome de usuario do Windows.
# Este script copia so o que deve ser entregue.
#
#   .\scripts\gerar_zip_entrega.ps1
#
# Saida: Etapa1-Primos-Paralelos.zip, um nivel acima da pasta do projeto.
# =============================================================================

$ErrorActionPreference = 'Stop'

$raiz = Split-Path -Parent $PSScriptRoot
$nome = 'Etapa1-Primos-Paralelos'
$destino = Join-Path (Split-Path -Parent $raiz) "$nome.zip"
$temp = Join-Path $env:TEMP "entrega-$(Get-Random)\$nome"

# O que NAO entra na entrega
$excluir = @('.git', '.claude', '.vscode', '.idea', '__pycache__', '.venv', 'venv')

Write-Host "Montando a entrega..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $temp -Force | Out-Null

Get-ChildItem -Path $raiz -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($raiz.Length + 1)
    $partes = $rel -split '[\\/]'

    # pula qualquer arquivo sob uma pasta excluida
    if ($partes | Where-Object { $excluir -contains $_ }) { return }
    # pula chaves e segredos, por seguranca
    if ($_.Extension -in '.pem', '.key', '.pyc') { return }

    $alvo = Join-Path $temp $rel
    $pasta = Split-Path -Parent $alvo
    if (-not (Test-Path $pasta)) { New-Item -ItemType Directory -Path $pasta -Force | Out-Null }
    Copy-Item $_.FullName -Destination $alvo
}

if (Test-Path $destino) { Remove-Item $destino -Force }
Compress-Archive -Path $temp -DestinationPath $destino -CompressionLevel Optimal

$arquivos = (Get-ChildItem -Path $temp -Recurse -File).Count
$tamanho = [math]::Round((Get-Item $destino).Length / 1KB, 1)
Remove-Item (Split-Path -Parent $temp) -Recurse -Force

Write-Host ""
Write-Host "ZIP gerado: $destino" -ForegroundColor Green
Write-Host "  $arquivos arquivos, $tamanho KB"
Write-Host ""
Write-Host "Conferencia -- nao deve aparecer .claude, .git nem __pycache__:" -ForegroundColor Cyan
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($destino)
# Barras delimitam pastas, para nao confundir ".gitignore" (legitimo) com ".git/"
$suspeitos = $zip.Entries | Where-Object {
    $_.FullName -match '[\\/]\.claude[\\/]|[\\/]\.git[\\/]|[\\/]__pycache__[\\/]|\.pem$|\.key$|\.pyc$'
}
if ($suspeitos) {
    Write-Host "  !! ENCONTRADO:" -ForegroundColor Red
    $suspeitos | ForEach-Object { Write-Host "     $($_.FullName)" -ForegroundColor Red }
} else {
    Write-Host "  OK: nada indevido no pacote." -ForegroundColor Green
}
Write-Host ""
Write-Host "Conteudo:" -ForegroundColor Cyan
$zip.Entries | Sort-Object FullName | ForEach-Object { Write-Host "  $($_.FullName)" }
$zip.Dispose()
