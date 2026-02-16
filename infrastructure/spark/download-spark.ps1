# Download Apache Spark and JDBC Drivers
# This script downloads Spark binaries and all required JDBC drivers
# to be shared across all containers via volume mounts

param(
    [string]$SparkVersion = "3.5.4",
    [string]$HadoopVersion = "3"
)

$ErrorActionPreference = "Stop"

$SparkDir = $PSScriptRoot
$BinDir = Join-Path $SparkDir "bin"
$JarsDir = Join-Path $SparkDir "jars"

# Function to download with progress
function Download-WithProgress {
    param(
        [string]$Url,
        [string]$OutFile,
        [string]$Description
    )
    
    Write-Host "      Downloading: $Description" -ForegroundColor Yellow
    Write-Host "      URL: $Url" -ForegroundColor DarkGray
    
    try {
        $webClient = New-Object System.Net.WebClient
        
        # Get file size first
        $request = [System.Net.WebRequest]::Create($Url)
        $request.Method = "HEAD"
        try {
            $response = $request.GetResponse()
            $totalBytes = $response.ContentLength
            $response.Close()
            $totalMB = [math]::Round($totalBytes / 1MB, 2)
            Write-Host "      Size: $totalMB MB" -ForegroundColor DarkGray
        } catch {
            $totalBytes = 0
        }
        
        # Download with progress event
        $downloadComplete = $false
        $lastPercent = 0
        
        Register-ObjectEvent -InputObject $webClient -EventName DownloadProgressChanged -Action {
            $percent = $EventArgs.ProgressPercentage
            $receivedMB = [math]::Round($EventArgs.BytesReceived / 1MB, 1)
            $totalMB = [math]::Round($EventArgs.TotalBytesToReceive / 1MB, 1)
            
            # Only update every 5%
            if ($percent -ge ($script:lastPercent + 5) -or $percent -eq 100) {
                $script:lastPercent = $percent
                Write-Host "`r      Progress: $percent% ($receivedMB MB / $totalMB MB)     " -NoNewline -ForegroundColor Cyan
            }
        } | Out-Null
        
        Register-ObjectEvent -InputObject $webClient -EventName DownloadFileCompleted -Action {
            $script:downloadComplete = $true
        } | Out-Null
        
        $webClient.DownloadFileAsync([Uri]$Url, $OutFile)
        
        while (-not $downloadComplete) {
            Start-Sleep -Milliseconds 100
        }
        
        Write-Host "`r      Progress: 100% - Complete!                    " -ForegroundColor Green
        
        # Cleanup
        $webClient.Dispose()
        Get-EventSubscriber | Where-Object { $_.SourceObject -eq $webClient } | Unregister-Event -ErrorAction SilentlyContinue
        
    } catch {
        Write-Host ""
        Write-Host "      WebClient failed, falling back to Invoke-WebRequest..." -ForegroundColor Yellow
        
        # Fallback to Invoke-WebRequest with visible progress
        $ProgressPreference = 'Continue'
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NovaSight Spark Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Create directories
Write-Host "[1/4] Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
New-Item -ItemType Directory -Force -Path $JarsDir | Out-Null

# Download Spark
$SparkTarball = "spark-$SparkVersion-bin-hadoop$HadoopVersion.tgz"
$SparkUrl = "https://archive.apache.org/dist/spark/spark-$SparkVersion/$SparkTarball"
$SparkTarPath = Join-Path $SparkDir $SparkTarball

if (-not (Test-Path (Join-Path $BinDir "spark-submit"))) {
    Write-Host "[2/4] Setting up Apache Spark $SparkVersion..." -ForegroundColor Yellow
    
    # Check if tarball already exists (from previous interrupted download)
    if (-not (Test-Path $SparkTarPath)) {
        Download-WithProgress -Url $SparkUrl -OutFile $SparkTarPath -Description "Apache Spark $SparkVersion"
    } else {
        Write-Host "      Tarball already exists, skipping download." -ForegroundColor Green
    }
    
    Write-Host "      Extracting Spark binaries (this may take a few minutes)..." -ForegroundColor Yellow
    
    # Extract using tar (available on Windows 10+)
    tar -xzf $SparkTarPath -C $SparkDir
    
    # Move contents to bin directory
    $ExtractedDir = Join-Path $SparkDir "spark-$SparkVersion-bin-hadoop$HadoopVersion"
    if (Test-Path $ExtractedDir) {
        # Copy bin files
        Copy-Item -Path (Join-Path $ExtractedDir "bin\*") -Destination $BinDir -Force
        # Copy sbin files
        $SbinDir = Join-Path $SparkDir "sbin"
        New-Item -ItemType Directory -Force -Path $SbinDir | Out-Null
        Copy-Item -Path (Join-Path $ExtractedDir "sbin\*") -Destination $SbinDir -Force
        # Copy conf files
        $ConfDir = Join-Path $SparkDir "conf"
        New-Item -ItemType Directory -Force -Path $ConfDir | Out-Null
        Copy-Item -Path (Join-Path $ExtractedDir "conf\*") -Destination $ConfDir -Force
        # Copy python files for PySpark
        $PythonDir = Join-Path $SparkDir "python"
        if (Test-Path (Join-Path $ExtractedDir "python")) {
            Copy-Item -Path (Join-Path $ExtractedDir "python") -Destination $SparkDir -Recurse -Force
        }
        # Copy default jars
        Copy-Item -Path (Join-Path $ExtractedDir "jars\*") -Destination $JarsDir -Force
        
        # Cleanup extracted directory
        Remove-Item -Path $ExtractedDir -Recurse -Force
    }
    
    # Cleanup tarball
    Remove-Item -Path $SparkTarPath -Force
    
    Write-Host "      Spark extracted successfully!" -ForegroundColor Green
} else {
    Write-Host "[2/4] Spark binaries already exist, skipping download." -ForegroundColor Green
}

# Download JDBC Drivers
Write-Host "[3/4] Downloading JDBC drivers..." -ForegroundColor Yellow

$JdbcDrivers = @(
    @{
        Name = "PostgreSQL"
        File = "postgresql-42.7.4.jar"
        Url = "https://jdbc.postgresql.org/download/postgresql-42.7.4.jar"
    },
    @{
        Name = "ClickHouse"
        File = "clickhouse-jdbc-0.6.3.jar"
        Url = "https://github.com/ClickHouse/clickhouse-java/releases/download/v0.6.3/clickhouse-jdbc-0.6.3-shaded.jar"
    },
    @{
        Name = "Oracle"
        File = "ojdbc8.jar"
        Url = "https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc8/21.9.0.0/ojdbc8-21.9.0.0.jar"
    },
    @{
        Name = "MySQL"
        File = "mysql-connector-j-8.2.0.jar"
        Url = "https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.2.0/mysql-connector-j-8.2.0.jar"
    },
    @{
        Name = "SQL Server"
        File = "mssql-jdbc-12.4.2.jre11.jar"
        Url = "https://repo1.maven.org/maven2/com/microsoft/sqlserver/mssql-jdbc/12.4.2.jre11/mssql-jdbc-12.4.2.jre11.jar"
    }
)

foreach ($driver in $JdbcDrivers) {
    $DriverPath = Join-Path $JarsDir $driver.File
    if (-not (Test-Path $DriverPath)) {
        Download-WithProgress -Url $driver.Url -OutFile $DriverPath -Description "$($driver.Name) JDBC Driver"
    } else {
        Write-Host "      $($driver.Name) driver already exists." -ForegroundColor Green
    }
}

# Verify installation
Write-Host "[4/4] Verifying installation..." -ForegroundColor Yellow

$SparkSubmit = Join-Path $BinDir "spark-submit"
if (Test-Path $SparkSubmit) {
    Write-Host "      spark-submit: OK" -ForegroundColor Green
} else {
    Write-Host "      spark-submit: MISSING" -ForegroundColor Red
}

$JarFiles = Get-ChildItem -Path $JarsDir -Filter "*.jar" | Select-Object -ExpandProperty Name
Write-Host "      JDBC drivers found: $($JarFiles.Count)" -ForegroundColor Green
foreach ($jar in @("postgresql", "clickhouse", "ojdbc8", "mysql", "mssql")) {
    $found = $JarFiles | Where-Object { $_ -like "*$jar*" }
    if ($found) {
        Write-Host "        - $found" -ForegroundColor Green
    } else {
        Write-Host "        - ${jar} - MISSING" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Spark binaries location: $BinDir"
Write-Host "JDBC jars location: $JarsDir"
Write-Host ""
Write-Host "To use in Docker, mount the following volumes:" -ForegroundColor Yellow
Write-Host "  - ./infrastructure/spark/bin:/opt/spark/bin:ro"
Write-Host "  - ./infrastructure/spark/sbin:/opt/spark/sbin:ro"
Write-Host "  - ./infrastructure/spark/jars:/opt/spark/jars:ro"
Write-Host "  - ./infrastructure/spark/conf:/opt/spark/conf:ro"
Write-Host "  - ./infrastructure/spark/python:/opt/spark/python:ro"
Write-Host ""
