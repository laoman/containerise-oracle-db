import streamlit as st
import oracledb
import os
import docker

st.set_page_config(page_title="Oracle DB Monitor", page_icon="📊", layout="wide")

# Initialize Docker Client
try:
    docker_client = docker.from_env()
except Exception as e:
    docker_client = None
    print(f"Docker socket error: {e}")

# --- Configuration ---
DB1_CONTAINER = os.getenv('DB1_CONTAINER_NAME', 'oracle-db1')
DB1_NAME = os.getenv('DB1_NAME', 'Database 1')
DB1_CONFIG = {
    "host": os.getenv('DB1_HOST', 'oracle-db1'),
    "port": os.getenv('DB1_PORT', '1521'),
    "sid": os.getenv('DB1_SID', 'ORCLCDB1'),
    "pdb": os.getenv('DB1_PDB', 'ORCLPDB1'),
    "user": os.getenv('DB1_USER', 'SYS'),
    "pwd": os.getenv('DB1_PWD', 'Welcome123456')
}

DB2_CONTAINER = os.getenv('DB2_CONTAINER_NAME', 'oracle-db2')
DB2_NAME = os.getenv('DB2_NAME', 'Database 2')
DB2_CONFIG = {
    "host": os.getenv('DB2_HOST', 'oracle-db2'),
    "port": os.getenv('DB2_PORT', '1521'),
    "sid": os.getenv('DB2_SID', 'ORCLCDB2'),
    "pdb": os.getenv('DB2_PDB', 'ORCLPDB2'),
    "user": os.getenv('DB2_USER', 'SYS'),
    "pwd": os.getenv('DB2_PWD', 'Welcome123456')
}

# --- Helper Functions ---
def get_container_logs(container_name):
    if not docker_client:
        return "Docker socket not connected. Cannot fetch logs."
    try:
        container = docker_client.containers.get(container_name)
        # Fetch last 50 lines
        return container.logs(tail=50).decode('utf-8')
    except Exception as e:
        return f"Error reading logs for {container_name}: {str(e)}"

def execute_query(config, query):
    dsn = f"{config['host']}:{config['port']}/{config['pdb']}"
    try:
        conn = oracledb.connect(user=config['user'], password=config['pwd'], dsn=dsn, mode=oracledb.SYSDBA)
        cursor = conn.cursor()
        cursor.execute(query)
        
        if cursor.description:
            columns = [col[0] for col in cursor.description]
            data = cursor.fetchall()
            # Convert to list of dicts for nicer display without pandas
            result = [dict(zip(columns, row)) for row in data]
            conn.close()
            return {"success": True, "data": result}
        else:
            conn.commit()
            conn.close()
            return {"success": True, "message": "Statement executed successfully (No Output)."}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def check_connection(config):
    dsn = f"{config['host']}:{config['port']}/{config['pdb']}"
    try:
        conn = oracledb.connect(user=config['user'], password=config['pwd'], dsn=dsn, mode=oracledb.SYSDBA)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION, INSTANCE_NAME, STATUS, DATABASE_STATUS FROM V$INSTANCE")
        version, instance, status, db_status = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM V$SESSION")
        session_count = cursor.fetchone()[0]
        conn.close()
        return {
            "status": "Online", "color": "green",
            "details": {"Version": version, "Instance": instance, "Mode": f"{status} / {db_status}", "Sessions": session_count}
        }
    except Exception as e:
        return {"status": "Initializing / Offline", "color": "orange", "error": str(e)}

def display_db_panel(name, config, container_name, db_key):
    st.header(f"{name}")
    
    tab_status, tab_logs, tab_query, tab_info = st.tabs(["🚦 Status", "📜 Live Logs", "🔍 Query", "ℹ️ Info"])
    
    with tab_status:
        result = check_connection(config)
        if result["status"] == "Online":
            st.success(f"Status: {result['status']} 🟢")
            col1, col2, col3 = st.columns(3)
            col1.metric("Sessions", result['details']['Sessions'])
            col2.metric("Version", result['details']['Version'])
            col3.metric("Mode", result['details']['Mode'])
        else:
            st.warning(f"Status: {result['status']} ⏳")
            st.caption("Database is building or starting up.")
            with st.expander("Show Connection Error"):
                st.code(result.get("error", "Unknown"), language="text")

    with tab_logs:
        if st.button(f"Refresh Logs {name}", key=f"btn_{db_key}"):
            st.rerun()
        logs = get_container_logs(container_name)
        st.code(logs, language="bash")

    with tab_query:
        st.caption(f"Run SQL on **{name}** (as SYSDBA)")
        
        # Use a consistent key for result storage
        result_key = f"res_{db_key}"
        
        query = st.text_area("SQL Query", height=100, key=f"q_{db_key}", placeholder="SELECT * FROM v$session WHERE ROWNUM <= 5")
        
        if st.button("Run Query", key=f"run_{db_key}"):
            if query.strip():
                with st.spinner("Executing..."):
                    res = execute_query(config, query)
                    st.session_state[result_key] = res
            else:
                st.warning("Please enter a SQL query.")
        
        # Display persisted result if valid
        if result_key in st.session_state:
            res = st.session_state[result_key]
            if res["success"]:
                if "data" in res:
                    st.write(f"**Results ({len(res['data'])} rows):**")
                    st.dataframe(res["data"])
                else:
                    st.success(res["message"])
            else:
                st.error(f"Error: {res['error']}")

    with tab_info:
        st.markdown(f"**Connection String:** `{config['host']}:{config['port']}/{config['pdb']}`")
        st.markdown(f"**SID:** `{config['sid']}`")

# --- Main UI ---
st.title("📊 Oracle Database Setup Monitor")

col1, col2 = st.columns(2)

with col1:
    try:
        display_db_panel(DB1_NAME, DB1_CONFIG, DB1_CONTAINER, "DB1")
    except Exception as e:
        st.error(f"Error loading DB1 Panel: {e}")

with col2:
    try:
        display_db_panel(DB2_NAME, DB2_CONFIG, DB2_CONTAINER, "DB2")
    except Exception as e:
        st.error(f"Error loading DB2 Panel: {e}")
