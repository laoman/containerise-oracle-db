# Oracle Database on Docker (ARM64/Apple Silicon)

This project provides an automated setup for running Oracle Database 19c on Apple Silicon (M1/M2/M3) Macs using Docker. It builds the image from official Oracle sources and orchestrates two database instances along with a monitoring dashboard.

## Prerequisites

*   macOS (ARM64/Apple Silicon)
*   Docker Desktop
*   Git
*   Oracle Database 19c (19.19) for LINUX ARM (aarch64) zip file (download from Oracle)

## Quick Start

1.  **Download Oracle 19c**: Download `LINUX.ARM64_1919000_db_home.zip` from [Oracle](https://www.oracle.com/database/technologies/oracle19c-linux-arm64-downloads.html).
2.  **Run Setup**:
    ```bash
    ./setup-oracle-database.sh
    ```
    (The script will guide you to place the zip file if it's missing)

## Services

Once the setup is complete, the following services will be available:

### Databases

| Service Name | Host (Internal) | Port (Local) | SID      | PDB      |
| :--- | :--- | :--- | :--- | :--- |
| **oracle-db1** | `oracle-db1`    | 1521         | ORCLCDB1 | ORCLPDB1 |
| **oracle-db2** | `oracle-db2`    | 1522         | ORCLCDB2 | ORCLPDB2 |

### Monitoring Dashboard

*   **URL:** [http://localhost:8501](http://localhost:8501)
*   **Description:** A Streamlit application that shows the status, version, and active sessions of both databases. It also displays connection credentials for easy reference.

## Configuration

*   **`.env`**: Contains database names, ports, and passwords.
*   **`docker-compose.yml`**: orchestration configuration.

## Managing Containers

*   **Logs:** `docker-compose logs -f`
*   **Stop:** `docker-compose stop`
*   **Start:** `docker-compose start`
*   **Down (Remove):** `docker-compose down`
