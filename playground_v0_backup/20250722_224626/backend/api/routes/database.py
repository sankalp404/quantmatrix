from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, text, inspect
from typing import Dict, List, Any
import os
from backend.config import settings

router = APIRouter(prefix="/api/v1/database", tags=["Database Schema"])

@router.get("/schema", response_model=Dict[str, Any])
async def get_database_schema():
    """
    Get complete database schema with tables, columns, relationships, and indexes
    for interactive ERD visualization like FastAPI /docs
    """
    try:
        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)
        
        schema_data = {
            "tables": {},
            "relationships": [],
            "indexes": {},
            "summary": {
                "total_tables": 0,
                "total_columns": 0,
                "total_relationships": 0,
                "total_indexes": 0
            }
        }
        
        # Get all table names
        table_names = inspector.get_table_names()
        schema_data["summary"]["total_tables"] = len(table_names)
        
        # Process each table
        for table_name in table_names:
            # Get columns
            columns = inspector.get_columns(table_name)
            
            # Get primary keys
            pk_constraint = inspector.get_pk_constraint(table_name)
            primary_keys = pk_constraint.get('constrained_columns', [])
            
            # Get foreign keys
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            # Get indexes
            indexes = inspector.get_indexes(table_name)
            schema_data["indexes"][table_name] = indexes
            schema_data["summary"]["total_indexes"] += len(indexes)
            
            # Process columns
            table_columns = []
            for col in columns:
                column_info = {
                    "name": str(col["name"]),
                    "type": str(col["type"]),
                    "nullable": bool(col["nullable"]),
                    "default": str(col["default"]) if col["default"] is not None else None,
                    "primary_key": col["name"] in primary_keys,
                    "foreign_key": None
                }
                
                # Check if this column is a foreign key
                for fk in foreign_keys:
                    if col["name"] in fk["constrained_columns"]:
                        idx = fk["constrained_columns"].index(col["name"])
                        column_info["foreign_key"] = {
                            "table": fk["referred_table"],
                            "column": fk["referred_columns"][idx]
                        }
                        break
                
                table_columns.append(column_info)
                schema_data["summary"]["total_columns"] += 1
            
            # Store table info
            schema_data["tables"][table_name] = {
                "columns": table_columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "indexes": [idx["name"] for idx in indexes],
                "row_count": None  # Will be filled separately for performance
            }
            
            # Add relationships
            for fk in foreign_keys:
                relationship = {
                    "from_table": table_name,
                    "to_table": fk["referred_table"],
                    "from_columns": fk["constrained_columns"],
                    "to_columns": fk["referred_columns"],
                    "constraint_name": fk["name"]
                }
                schema_data["relationships"].append(relationship)
                schema_data["summary"]["total_relationships"] += 1
        
        # Get row counts for each table (optional, can be slow)
        with engine.connect() as conn:
            for table_name in table_names:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    schema_data["tables"][table_name]["row_count"] = count
                except Exception as e:
                    schema_data["tables"][table_name]["row_count"] = 0
                    # Log error but don't fail the whole response
        
        return {
            "status": "success",
            "data": schema_data,
            "message": f"Schema retrieved for {len(table_names)} tables"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve schema: {str(e)}")

@router.get("/relationships", response_model=Dict[str, Any])
async def get_database_relationships():
    """
    Get simplified relationship graph for ERD visualization
    """
    try:
        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)
        
        relationships = []
        table_names = inspector.get_table_names()
        
        for table_name in table_names:
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            for fk in foreign_keys:
                relationships.append({
                    "source": table_name,
                    "target": fk["referred_table"],
                    "type": "one_to_many",  # Most FK relationships are 1:N
                    "columns": {
                        "source": fk["constrained_columns"],
                        "target": fk["referred_columns"]
                    }
                })
        
        # Create nodes for visualization
        nodes = []
        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            primary_keys = pk_constraint.get('constrained_columns', [])
            
            nodes.append({
                "id": table_name,
                "label": table_name,
                "type": "table",
                "column_count": len(columns),
                "primary_keys": primary_keys
            })
        
        return {
            "status": "success",
            "data": {
                "nodes": nodes,
                "edges": relationships,
                "summary": {
                    "tables": len(table_names),
                    "relationships": len(relationships)
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve relationships: {str(e)}")

@router.get("/table/{table_name}", response_model=Dict[str, Any])
async def get_table_details(table_name: str):
    """
    Get detailed information about a specific table
    """
    try:
        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)
        
        if table_name not in inspector.get_table_names():
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        # Get all table details
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        indexes = inspector.get_indexes(table_name)
        unique_constraints = inspector.get_unique_constraints(table_name)
        check_constraints = inspector.get_check_constraints(table_name)
        
        # Get sample data
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = result.scalar()
            
            # Get sample rows (limit 5) with safe serialization
            try:
                sample_result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 5"))
                sample_data = []
                for row in sample_result:
                    row_dict = {}
                    for key, value in row._mapping.items():
                        # Convert non-JSON serializable types to strings
                        if value is None:
                            row_dict[key] = None
                        elif isinstance(value, (str, int, float, bool)):
                            row_dict[key] = value
                        else:
                            # Convert datetime, decimal, etc. to string
                            row_dict[key] = str(value)
                    sample_data.append(row_dict)
            except Exception as sample_error:
                sample_data = [{"error": f"Could not load sample data: {str(sample_error)}"}]
        
        # Convert all SQLAlchemy objects to serializable format
        serializable_columns = []
        for col in columns:
            serializable_columns.append({
                "name": str(col["name"]),
                "type": str(col["type"]),
                "nullable": bool(col["nullable"]),
                "default": str(col["default"]) if col["default"] is not None else None,
                "primary_key": col["name"] in pk_constraint.get('constrained_columns', []),
                "autoincrement": col.get("autoincrement", False)
            })
        
        return {
            "status": "success",
            "data": {
                "table_name": str(table_name),
                "columns": serializable_columns,
                "primary_key": {
                    "name": pk_constraint.get("name"),
                    "constrained_columns": pk_constraint.get("constrained_columns", [])
                },
                "foreign_keys": [
                    {
                        "name": fk.get("name"),
                        "constrained_columns": fk.get("constrained_columns", []),
                        "referred_table": fk.get("referred_table"),
                        "referred_columns": fk.get("referred_columns", [])
                    } for fk in foreign_keys
                ],
                "indexes": [idx.get("name") for idx in indexes],
                "row_count": int(row_count) if row_count is not None else 0,
                "sample_data": sample_data
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve table details: {str(e)}") 

@router.get("/schema-viewer", response_class=HTMLResponse)
async def database_schema_viewer():
    """
    Interactive database schema viewer - like FastAPI /docs but for database structure
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>QuantMatrix Database Schema Viewer</title>
        <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style>
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; 
                background: #1a1a1a; 
                color: #e0e0e0;
            }
            .header { 
                background: #2d2d2d; 
                padding: 20px; 
                border-bottom: 2px solid #0ea5e9;
            }
            .header h1 { 
                margin: 0; 
                color: #0ea5e9; 
                font-size: 24px;
            }
            .container { 
                display: flex; 
                height: calc(100vh - 80px);
            }
            .sidebar { 
                width: 350px; 
                background: #2d2d2d; 
                padding: 20px; 
                overflow-y: auto;
                border-right: 1px solid #404040;
            }
            .main { 
                flex: 1; 
                display: flex;
                flex-direction: column;
            }
            .schema-graph { 
                height: 60%; 
                border-bottom: 1px solid #404040;
            }
            .table-details { 
                height: 40%; 
                background: #1e1e1e; 
                padding: 20px; 
                overflow-y: auto;
            }
            .table-item { 
                background: #333; 
                margin: 8px 0; 
                padding: 15px; 
                border-radius: 8px; 
                cursor: pointer;
                border: 1px solid #444;
                transition: all 0.2s;
            }
            .table-item:hover { 
                background: #404040; 
                border-color: #0ea5e9;
            }
            .table-name { 
                font-weight: bold; 
                color: #0ea5e9; 
                font-size: 16px;
            }
            .table-info { 
                color: #888; 
                font-size: 12px; 
                margin-top: 5px;
            }
            .column { 
                margin: 5px 0; 
                padding: 8px; 
                background: #2a2a2a; 
                border-radius: 4px;
                font-family: 'Monaco', 'Menlo', monospace;
            }
            .column-name { 
                color: #4ade80; 
                font-weight: bold;
            }
            .column-type { 
                color: #f59e0b; 
            }
            .primary-key { 
                color: #ef4444; 
            }
            .foreign-key { 
                color: #8b5cf6; 
            }
            .summary { 
                background: #333; 
                padding: 15px; 
                border-radius: 8px; 
                margin-bottom: 20px;
            }
            .stat { 
                display: inline-block; 
                margin: 5px 15px 5px 0;
            }
            .stat-value { 
                color: #0ea5e9; 
                font-weight: bold; 
                font-size: 18px;
            }
            .loading { 
                text-align: center; 
                padding: 50px; 
                color: #888;
            }
            .error { 
                color: #ef4444; 
                background: #2d1a1a; 
                padding: 15px; 
                border-radius: 8px; 
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🗄️ QuantMatrix Database Schema</h1>
            <p style="margin: 5px 0 0 0; color: #888;">Interactive Entity Relationship Diagram</p>
        </div>
        
        <div class="container">
            <div class="sidebar">
                <div id="summary" class="summary">
                    <div class="loading">Loading schema...</div>
                </div>
                <div id="tables-list"></div>
            </div>
            
            <div class="main">
                <div id="schema-graph" class="schema-graph">
                    <div class="loading">Building relationship graph...</div>
                </div>
                <div id="table-details" class="table-details">
                    <h3>📋 Table Details</h3>
                    <p style="color: #888;">Click on a table to view its structure</p>
                </div>
            </div>
        </div>

        <script>
            let schemaData = null;
            let network = null;

            // Load schema data
            async function loadSchema() {
                try {
                    const response = await fetch('/api/v1/database/schema');
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        schemaData = result.data;
                        displaySummary();
                        displayTablesList();
                        loadRelationshipGraph();
                    } else {
                        throw new Error(result.error || 'Failed to load schema');
                    }
                } catch (error) {
                    document.getElementById('summary').innerHTML = 
                        `<div class="error">Error loading schema: ${error.message}</div>`;
                }
            }

            // Display summary stats
            function displaySummary() {
                const summary = schemaData.summary;
                document.getElementById('summary').innerHTML = `
                    <h3>📊 Database Summary</h3>
                    <div class="stat">
                        <div class="stat-value">${summary.total_tables}</div>
                        <div>Tables</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${summary.total_columns}</div>
                        <div>Columns</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${summary.total_relationships}</div>
                        <div>Relations</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${summary.total_indexes}</div>
                        <div>Indexes</div>
                    </div>
                `;
            }

            // Display tables list
            function displayTablesList() {
                const tablesHtml = Object.entries(schemaData.tables)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([tableName, tableData]) => `
                        <div class="table-item" onclick="showTableDetails('${tableName}')">
                            <div class="table-name">${tableName}</div>
                            <div class="table-info">
                                ${tableData.columns.length} columns | 
                                ${tableData.row_count || 0} rows |
                                ${tableData.foreign_keys.length} FK
                            </div>
                        </div>
                    `).join('');
                
                document.getElementById('tables-list').innerHTML = `
                    <h3>📋 Tables (${Object.keys(schemaData.tables).length})</h3>
                    ${tablesHtml}
                `;
            }

            // Load relationship graph
            async function loadRelationshipGraph() {
                try {
                    const response = await fetch('/api/v1/database/relationships');
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        createNetworkGraph(result.data);
                    }
                } catch (error) {
                    document.getElementById('schema-graph').innerHTML = 
                        `<div class="error">Error loading relationships: ${error.message}</div>`;
                }
            }

            // Create vis.js network graph
            function createNetworkGraph(data) {
                const nodes = new vis.DataSet(data.nodes.map(node => ({
                    id: node.id,
                    label: `${node.label}\\n(${node.column_count} cols)`,
                    shape: 'box',
                    color: {
                        background: '#2d2d2d',
                        border: node.primary_keys.length > 0 ? '#0ea5e9' : '#666',
                        highlight: { background: '#404040', border: '#0ea5e9' }
                    },
                    font: { color: '#e0e0e0', size: 12 }
                })));

                const edges = new vis.DataSet(data.edges.map((edge, i) => ({
                    id: i,
                    from: edge.source,
                    to: edge.target,
                    arrows: 'to',
                    color: { color: '#666', highlight: '#0ea5e9' },
                    width: 2
                })));

                const container = document.getElementById('schema-graph');
                const graphData = { nodes, edges };
                const options = {
                    layout: {
                        improvedLayout: false
                    },
                    physics: {
                        stabilization: { iterations: 100 },
                        barnesHut: { gravitationalConstant: -2000, springConstant: 0.04, springLength: 95 }
                    },
                    interaction: {
                        hover: true,
                        selectConnectedEdges: false
                    }
                };

                network = new vis.Network(container, graphData, options);
                
                // Handle table clicks
                network.on('click', function(params) {
                    if (params.nodes.length > 0) {
                        const tableName = params.nodes[0];
                        showTableDetails(tableName);
                    }
                });
            }

            // Show table details
            async function showTableDetails(tableName) {
                try {
                    const response = await fetch(`/api/v1/database/table/${tableName}`);
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        const table = result.data;
                        const columnsHtml = table.columns.map(col => `
                            <div class="column">
                                <span class="column-name">${col.name}</span>
                                <span class="column-type">${col.type}</span>
                                ${col.primary_key ? '<span class="primary-key">[PK]</span>' : ''}
                                ${col.foreign_key ? `<span class="foreign-key">[FK → ${col.foreign_key.table}.${col.foreign_key.column}]</span>` : ''}
                                ${col.nullable ? '' : '<span style="color: #ef4444;">[NOT NULL]</span>'}
                            </div>
                        `).join('');

                        document.getElementById('table-details').innerHTML = `
                            <h3>📋 ${tableName}</h3>
                            <p><strong>Rows:</strong> ${table.row_count} | 
                               <strong>Columns:</strong> ${table.columns.length} | 
                               <strong>Indexes:</strong> ${table.indexes.length}</p>
                            <h4>Columns:</h4>
                            <div>${columnsHtml}</div>
                        `;
                    }
                } catch (error) {
                    document.getElementById('table-details').innerHTML = 
                        `<div class="error">Error loading table details: ${error.message}</div>`;
                }
            }

            // Load schema on page load
            loadSchema();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content) 