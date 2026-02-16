#!/bin/bash
# Download Apache Spark and JDBC Drivers
# This script downloads Spark binaries and all required JDBC drivers
# to be shared across all containers via volume mounts

set -e

SPARK_VERSION="${SPARK_VERSION:-3.5.4}"
HADOOP_VERSION="${HADOOP_VERSION:-3}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${SCRIPT_DIR}/bin"
SBIN_DIR="${SCRIPT_DIR}/sbin"
JARS_DIR="${SCRIPT_DIR}/jars"
CONF_DIR="${SCRIPT_DIR}/conf"
PYTHON_DIR="${SCRIPT_DIR}/python"

echo "========================================"
echo "NovaSight Spark Setup Script"
echo "========================================"
echo ""

# Create directories
echo "[1/4] Creating directories..."
mkdir -p "${BIN_DIR}" "${SBIN_DIR}" "${JARS_DIR}" "${CONF_DIR}"

# Download Spark
SPARK_TARBALL="spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz"
SPARK_URL="https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/${SPARK_TARBALL}"
SPARK_TAR_PATH="${SCRIPT_DIR}/${SPARK_TARBALL}"

if [ ! -f "${BIN_DIR}/spark-submit" ]; then
    echo "[2/4] Downloading Apache Spark ${SPARK_VERSION}..."
    echo "      URL: ${SPARK_URL}"
    
    # Download
    curl -fSL "${SPARK_URL}" -o "${SPARK_TAR_PATH}"
    
    echo "      Extracting Spark binaries..."
    tar -xzf "${SPARK_TAR_PATH}" -C "${SCRIPT_DIR}"
    
    EXTRACTED_DIR="${SCRIPT_DIR}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}"
    if [ -d "${EXTRACTED_DIR}" ]; then
        # Copy bin files
        cp -r "${EXTRACTED_DIR}/bin/"* "${BIN_DIR}/"
        # Copy sbin files
        cp -r "${EXTRACTED_DIR}/sbin/"* "${SBIN_DIR}/"
        # Copy conf files
        cp -r "${EXTRACTED_DIR}/conf/"* "${CONF_DIR}/"
        # Copy python files
        if [ -d "${EXTRACTED_DIR}/python" ]; then
            cp -r "${EXTRACTED_DIR}/python" "${SCRIPT_DIR}/"
        fi
        # Copy jars (only if jars dir is mostly empty)
        if [ "$(ls -1 "${JARS_DIR}" | wc -l)" -lt 10 ]; then
            cp -r "${EXTRACTED_DIR}/jars/"* "${JARS_DIR}/"
        fi
        
        # Cleanup
        rm -rf "${EXTRACTED_DIR}"
    fi
    
    # Cleanup tarball
    rm -f "${SPARK_TAR_PATH}"
    
    echo "      Spark extracted successfully!"
else
    echo "[2/4] Spark binaries already exist, skipping download."
fi

# Download JDBC Drivers
echo "[3/4] Downloading JDBC drivers..."

download_if_missing() {
    local name="$1"
    local file="$2"
    local url="$3"
    local path="${JARS_DIR}/${file}"
    
    if [ ! -f "${path}" ]; then
        echo "      Downloading ${name} driver..."
        curl -fSL "${url}" -o "${path}"
        echo "      ${name} driver downloaded."
    else
        echo "      ${name} driver already exists."
    fi
}

download_if_missing "PostgreSQL" "postgresql-42.7.4.jar" \
    "https://jdbc.postgresql.org/download/postgresql-42.7.4.jar"

download_if_missing "ClickHouse" "clickhouse-jdbc-0.6.3.jar" \
    "https://github.com/ClickHouse/clickhouse-java/releases/download/v0.6.3/clickhouse-jdbc-0.6.3-shaded.jar"

download_if_missing "Oracle" "ojdbc8.jar" \
    "https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc8/21.9.0.0/ojdbc8-21.9.0.0.jar"

download_if_missing "MySQL" "mysql-connector-j-8.2.0.jar" \
    "https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.2.0/mysql-connector-j-8.2.0.jar"

download_if_missing "SQL Server" "mssql-jdbc-12.4.2.jre11.jar" \
    "https://repo1.maven.org/maven2/com/microsoft/sqlserver/mssql-jdbc/12.4.2.jre11/mssql-jdbc-12.4.2.jre11.jar"

# Verify installation
echo "[4/4] Verifying installation..."

if [ -f "${BIN_DIR}/spark-submit" ]; then
    echo "      spark-submit: OK"
else
    echo "      spark-submit: MISSING"
fi

echo "      JDBC drivers found: $(ls -1 "${JARS_DIR}/"*.jar 2>/dev/null | wc -l)"
for jar in postgresql clickhouse ojdbc8 mysql mssql; do
    found=$(ls "${JARS_DIR}/"*"${jar}"*.jar 2>/dev/null | head -1)
    if [ -n "${found}" ]; then
        echo "        - $(basename "${found}")"
    else
        echo "        - ${jar}: MISSING"
    fi
done

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Spark binaries location: ${BIN_DIR}"
echo "JDBC jars location: ${JARS_DIR}"
echo ""
echo "To use in Docker, mount the following volumes:"
echo "  - ./infrastructure/spark/bin:/opt/spark/bin:ro"
echo "  - ./infrastructure/spark/sbin:/opt/spark/sbin:ro"
echo "  - ./infrastructure/spark/jars:/opt/spark/jars:ro"
echo "  - ./infrastructure/spark/conf:/opt/spark/conf:ro"
echo "  - ./infrastructure/spark/python:/opt/spark/python:ro"
echo ""
