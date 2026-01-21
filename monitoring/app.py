import streamlit as st
import oracledb
import pandas as pd
import os
import time

# Page config
st.set_page_config(
    page_title="Oracle Database Monitor",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Oracle Database Setup Monitor")

# Database connection details from environment variables
# We use the internal docker network service names by default
DB1_NAME = os.getenv("DB1_NAME", "Database 1")
DB1_HOST = os.getenv("DB1_HOST", "oracle-db1")
DB1_PORT = os.getenv("DB1_PORT", "1521")
DB1_SID = os.getenv("DB1_SID", "ORCLCDB1")
DB1_PDB = os.getenv("DB1_PDB", "ORCLPDB1")
DB1_USER = os.getenv("DB1_USER", "SYS")
DB1_PWD = os.getenv("DB1_PWD", "Welcome123456")

DB2_NAME = os.getenv("DB2_NAME", "Database 2")
DB2_HOST = os.getenv("DB2_HOST", "oracle-db2")
DB2_PORT = os.getenv("DB2_PORT", "1521") # Internal port is always 1521
DB2_SID = os.getenv("DB2_SID", "ORCLCDB2")
DB2_PDB = os.getenv("DB2_PDB", "ORCLPDB2")
DB2_USER = os.getenv("DB2_USER", "SYS")
DB2_PWD = os.getenv("DB2_PWD", "Welcome123456")

def check_db_status(name, host, port, sid, user, pwd):
    """
    Connects to the database and retrieves basic status information.
    """
    status_dict = {
        "name": name,
        "status": "Offline 🔴",
        "version": "N/A",
        "sessions": 0,
        "open_mode": "N/A",
        "host": host,
        "error": None
    }
    
    dsn = f"{host}:{port}/{sid}"
    
    try:
        # Connect as SYSDBA for full monitoring capabilities
        # In Thin mode, we can't always use SYSDBA purely, but SYS usually requires it.
        # python-oracledb Thin mode supports SYSDBA.
        conn = oracledb.connect(
            user=user,
            password=pwd,
            dsn=dsn,
            mode=oracledb.SYSDBA,
            disable_oob=True # Helps with container setups sometimes
        )
        
        cursor = conn.cursor()
        
        # Get Version and Status
        cursor.execute("SELECT VERSION, STATUS, INSTANCE_NAME, DATABASE_STATUS FROM V$INSTANCE")
        row = cursor.fetchone()
        if row:
            status_dict["version"] = row[0]
            status_dict["open_mode"] = row[3] # ACTIVE, SUSPENDED, mount, etc
            status_dict["status"] = "Online 🟢"
            
        # Get Session Count
        cursor.execute("SELECT count(*) FROM v$session")
        row = cursor.fetchone()
        if row:
            status_dict["sessions"] = row[0]
            
        conn.close()
        
    except oracledb.Error as e:
        error_obj = e.args[0]
        status_dict["error"] = error_obj.message
    except Exception as e:
        status_dict["error"] = str(e)
        
    return status_dict

# Layout with two columns
col1, col2 = st.columns(2)

# Auto-refresh mechanism
if st.button('🔄 Refresh Now'):
    st.rerun()

st.write("---")

# Check DB1
with col1:
    st.header(f"{DB1_NAME} ({DB1_SID})")
    with st.spinner(f"Connecting to {DB1_HOST}..."):
        db1_status = check_db_status("DB1", DB1_HOST, DB1_PORT, DB1_SID, DB1_USER, DB1_PWD)
    
    if "Online" in db1_status["status"]:
        st.success(f"Status: {db1_status['status']}")
        st.metric(label="Sessions", value=db1_status['sessions'])
        st.write(f"**Version:** {db1_status['version']}")
        st.write(f"**Mode:** {db1_status['open_mode']}")
        
        with st.expander("🔑 Connection Info & Credentials"):
            st.code(f"""
Host: localhost (mapped to {DB1_PORT})
Container Host: {DB1_HOST}
SID: {DB1_SID}
PDB: {DB1_PDB}
User: {DB1_USER}
Password: {DB1_PWD}
            """, language="yaml")
    else:
        st.error(f"Status: {db1_status['status']}")
        st.write(f"**Error:** {db1_status['error']}")
        with st.expander("🔑 Connection Info & Credentials"):
            st.code(f"""
Host: localhost (mapped to {DB1_PORT})
Container Host: {DB1_HOST}
SID: {DB1_SID}
PDB: {DB1_PDB}
User: {DB1_USER}
Password: {DB1_PWD}
            """, language="yaml")

# Check DB2
with col2:
    st.header(f"{DB2_NAME} ({DB2_SID})")
    with st.spinner(f"Connecting to {DB2_HOST}..."):
        db2_status = check_db_status("DB2", DB2_HOST, DB2_PORT, DB2_SID, DB2_USER, DB2_PWD)
    
    if "Online" in db2_status["status"]:
        st.success(f"Status: {db2_status['status']}")
        st.metric(label="Sessions", value=db2_status['sessions'])
        st.write(f"**Version:** {db2_status['version']}")
        st.write(f"**Mode:** {db2_status['open_mode']}")
        
        with st.expander("🔑 Connection Info & Credentials"):
            st.code(f"""
Host: localhost (mapped to {DB2_PORT} - from inside container: 1521)
Container Host: {DB2_HOST}
SID: {DB2_SID}
PDB: {DB2_PDB}
User: {DB2_USER}
Password: {DB2_PWD}
            """, language="yaml")
    else:
        st.error(f"Status: {db2_status['status']}")
        st.write(f"**Error:** {db2_status['error']}")
        with st.expander("🔑 Connection Info & Credentials"):
            st.code(f"""
Host: localhost (mapped to {DB2_PORT} - from inside container: 1521)
Container Host: {DB2_HOST}
SID: {DB2_SID}
PDB: {DB2_PDB}
User: {DB2_USER}
Password: {DB2_PWD}
            """, language="yaml")

st.write("---")
st.caption("Auto-refreshing is enabled manually via the Refresh button, or you can add `st.empty` logic for loops in a more complex setup.")

# Simple auto-refresh hint info
st.info("Tip: This dashboard uses python-oracledb in 'Thin' mode to connect directly to the Oracle containers.")
