"""Tool 2: endoflife_lookup - Query endoflife.date API for version and EOL information."""
import logging
import time
import re
from typing import Dict, Any, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

# Product name mapping: ACAT name -> endoflife.date API product ID
PRODUCT_MAP = {
    # Databases
    "PostgreSQL": "postgresql",
    "MySQL": "mysql",
    "MariaDB": "mariadb",
    "SQL Server": "mssql",
    "Microsoft SQL Server": "mssql",
    "Oracle Database": "oracle-database",
    "Oracle": "oracle-database",
    "MongoDB": "mongodb",
    "Redis": "redis",
    "Elasticsearch": "elasticsearch",
    "CockroachDB": "cockroachdb",
    "Couchbase Server": "couchbase-server",
    "Apache Cassandra": "cassandra",
    "Cassandra": "cassandra",
    "Microsoft Access": "microsoft-access",
    "Access": "microsoft-access",
    "DB2": "ibm-db2",
    "IBM DB2": "ibm-db2",
    "Informix": "ibm-informix",
    "Sybase": "sap-ase",
    "SAP ASE": "sap-ase",
    "Neo4j": "neo4j",
    "InfluxDB": "influxdb",
    "TimescaleDB": "timescaledb",
    "Amazon RDS": "amazon-rds",
    "Amazon Aurora": "amazon-aurora",
    "Google Cloud SQL": "google-cloud-sql",
    "Azure SQL": "azure-sql-database",
    
    # Message Queues & Streaming
    "Apache Kafka": "apache-kafka",
    "Kafka": "apache-kafka",
    "RabbitMQ": "rabbitmq",
    "ActiveMQ": "activemq",
    "Apache ActiveMQ": "activemq",
    "Amazon MQ": "amazon-mq",
    
    # Search & Analytics
    "Splunk": "splunk",
    "Apache Solr": "solr",
    "Solr": "solr",
    "Logstash": "logstash",
    "Kibana": "kibana",
    
    # Key-Value Stores
    "Memcached": "memcached",
    "Etcd": "etcd",
    "Consul": "consul",
    "Apache ZooKeeper": "zookeeper",
    "ZooKeeper": "zookeeper",
    
    # Document Stores
    "Couchbase": "couchbase-server",
    "CouchDB": "couchdb",
    "Apache CouchDB": "couchdb",
    
    # Graph Databases
    "ArangoDB": "arangodb",
    "OrientDB": "orientdb",
    
    # Time Series
    "Prometheus": "prometheus",
    "Grafana": "grafana",
    
    # Wide Column Stores
    "HBase": "hbase",
    "Apache HBase": "hbase",
    "ScyllaDB": "scylladb",
    
    # NewSQL
    "VoltDB": "voltdb",
    "NuoDB": "nuodb",
}


def normalize_product_name(product: str) -> Optional[str]:
    """Normalize product name to endoflife.date API format."""
    if product in PRODUCT_MAP:
        return PRODUCT_MAP[product]
    
    for key, value in PRODUCT_MAP.items():
        if key.lower() == product.lower():
            return value
    
    cleaned = re.sub(r'\s+(Database|Server|DB)$', '', product, flags=re.IGNORECASE)
    if cleaned != product and cleaned in PRODUCT_MAP:
        return PRODUCT_MAP[cleaned]
    
    return product.lower().replace(' ', '-')


def normalize_version(version: str) -> str:
    """Normalize version string."""
    version = re.sub(r'[.\-]x$', '', version)
    version = re.sub(r'-log$', '', version, flags=re.IGNORECASE)
    version = re.sub(r'\s+(SP\d+|R\d+|Enterprise|Standard|Express|Developer).*$', '', version, flags=re.IGNORECASE)
    
    parts = version.split('.')
    if len(parts) > 1:
        return '.'.join(parts[:2])
    
    return version.strip()


def find_closest_version(target_version: str, available_versions: list) -> Tuple[Optional[str], str]:
    """Find the closest matching version from available versions."""
    if not available_versions:
        return None, "NOT_FOUND"
    
    if target_version in available_versions:
        return target_version, "EXACT"
    
    target_parts = target_version.split('.')
    target_major = target_parts[0]
    
    for version in available_versions:
        if version == target_major or version.startswith(f"{target_major}."):
            return version, "MAJOR"
    
    try:
        target_float = float(target_parts[0]) + (float(target_parts[1]) / 100 if len(target_parts) > 1 else 0)
        
        version_floats = []
        for v in available_versions:
            v_parts = str(v).split('.')
            v_float = float(v_parts[0]) + (float(v_parts[1]) / 100 if len(v_parts) > 1 else 0)
            version_floats.append((v, v_float))
        
        closest = min(version_floats, key=lambda x: abs(x[1] - target_float))
        return closest[0], "CLOSEST"
        
    except (ValueError, IndexError):
        return available_versions[0] if available_versions else None, "LATEST"


def call_endoflife_api(api_product: str, timeout: int = 30, max_retries: int = 3) -> Dict[str, Any]:
    """Call endoflife.date API to get product version information."""
    url = f"https://endoflife.date/api/{api_product}.json"
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Calling endoflife.date API: {url} (attempt {attempt + 1}/{max_retries})")
            
            response = requests.get(url, timeout=timeout)
            
            if response.status_code == 200:
                return {"status": "success", "data": response.json()}
            elif response.status_code == 404:
                return {
                    "status": "not_found",
                    "error_type": "PRODUCT_NOT_FOUND",
                    "error_message": f"Product '{api_product}' not found in endoflife.date database"
                }
            elif response.status_code == 429:
                wait_time = 5 * (attempt + 1)
                logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            else:
                return {
                    "status": "error",
                    "error_type": "HTTP_ERROR",
                    "error_message": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code
                }
                
        except requests.Timeout:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Request timeout. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            return {
                "status": "error",
                "error_type": "TIMEOUT",
                "error_message": f"Connection timeout after {timeout} seconds",
                "retry_count": max_retries
            }
            
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Request error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            return {
                "status": "error",
                "error_type": "REQUEST_ERROR",
                "error_message": str(e),
                "retry_count": max_retries
            }
    
    return {
        "status": "error",
        "error_type": "MAX_RETRIES",
        "error_message": f"Failed after {max_retries} attempts"
    }


def endoflife_lookup(product: str, version: str, timeout: int = 30, max_retries: int = 3) -> Dict[str, Any]:
    """Look up version and EOL information for a datastore product."""
    try:
        if not product:
            return {
                "status": "error",
                "error_type": "INVALID_INPUT",
                "error_message": "Product name is required"
            }
        
        if not version:
            return {
                "status": "error",
                "error_type": "INVALID_INPUT",
                "error_message": "Version is required"
            }
        
        api_product = normalize_product_name(product)
        if not api_product:
            return {
                "status": "not_found",
                "product": product,
                "version": version,
                "error_type": "PRODUCT_NOT_FOUND",
                "error_message": f"Product '{product}' not found in mapping",
                "available_products": []
            }
        
        normalized_version = normalize_version(version)
        
        logger.info(f"Looking up: {product} ({api_product}) version {normalized_version}")
        
        api_response = call_endoflife_api(api_product, timeout, max_retries)
        
        if api_response["status"] == "not_found":
            return {
                "status": "not_found",
                "product": product,
                "version": version,
                "api_product_name": api_product,
                "error_type": "PRODUCT_NOT_FOUND",
                "error_message": api_response["error_message"],
                "available_products": []
            }
        
        if api_response["status"] == "error":
            return {
                "status": "error",
                "product": product,
                "version": version,
                "api_product_name": api_product,
                "error_type": api_response["error_type"],
                "error_message": api_response["error_message"],
                "retry_count": api_response.get("retry_count", 0)
            }
        
        versions_data = api_response["data"]
        
        if not versions_data:
            return {
                "status": "not_found",
                "product": product,
                "version": version,
                "api_product_name": api_product,
                "error_type": "NO_VERSION_DATA",
                "error_message": "No version data available for this product"
            }
        
        available_versions = [str(v.get("cycle", v.get("version", ""))) for v in versions_data if v.get("cycle")]
        
        if not available_versions:
            return {
                "status": "not_found",
                "product": product,
                "version": version,
                "api_product_name": api_product,
                "error_type": "NO_VERSIONS_FOUND",
                "error_message": "No version cycles found in API response"
            }
        
        matched_version, match_type = find_closest_version(normalized_version, available_versions)
        
        if not matched_version:
            return {
                "status": "not_found",
                "product": product,
                "version": version,
                "api_product_name": api_product,
                "error_type": "VERSION_NOT_FOUND",
                "error_message": f"Version '{normalized_version}' not found. Available versions: {', '.join(available_versions)}",
                "available_versions": available_versions
            }
        
        version_info = next((v for v in versions_data if str(v.get("cycle")) == matched_version), {})
        
        if not version_info:
            return {
                "status": "not_found",
                "product": product,
                "version": version,
                "api_product_name": api_product,
                "error_type": "VERSION_DATA_NOT_FOUND",
                "error_message": f"No data found for matched version {matched_version}"
            }
        
        eol_date = version_info.get("eol", "Unknown")
        support_status = "active" if version_info.get("support", True) else "ended"
        latest_version = available_versions[0] if available_versions else "Unknown"
        lts_version = next((v.get("cycle") for v in versions_data if v.get("lts")), "N/A")
        release_date = version_info.get("releaseDate", "Unknown")
        
        return {
            "status": "success",
            "product": product,
            "version": version,
            "api_product_name": api_product,
            "matched_version": matched_version,
            "match_type": match_type,
            "eol_date": eol_date,
            "support_status": support_status,
            "latest_version": latest_version,
            "lts_version": lts_version,
            "release_date": release_date
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in endoflife_lookup: {e}", exc_info=True)
        return {
            "status": "error",
            "product": product,
            "version": version,
            "error_type": "UNEXPECTED_ERROR",
            "error_message": str(e)
        }
