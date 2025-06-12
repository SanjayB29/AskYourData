from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import pandas as pd
import numpy as np
import json
import io
import base64
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from emergentintegrations.llm.chat import LlmChat, UserMessage
import sys
from contextlib import redirect_stdout, redirect_stderr

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# LLM Chat setup
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Define Models
class Dataset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    file_type: str  # 'csv' or 'json'
    columns: List[str]
    row_count: int
    data_preview: List[Dict[str, Any]]  # First 5 rows
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

class Query(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id: str
    query_text: str
    generated_code: str
    result_type: str  # 'table', 'chart', 'error'
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class QueryRequest(BaseModel):
    dataset_id: str
    query_text: str

class CodeGenerationService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def generate_code(self, query: str, dataset_info: Dict[str, Any]) -> str:
        """Generate Python code from natural language query"""
        
        # Create a new chat instance for each query
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"data_query_{uuid.uuid4()}",
            system_message="""You are an expert data analyst who converts natural language queries into Python code using pandas, matplotlib, seaborn, and plotly.

IMPORTANT RULES:
1. Always assume the DataFrame is named 'df'
2. Only use pandas, numpy, matplotlib, seaborn, plotly
3. For visualizations, save plots as base64 encoded images
4. Return ONLY the Python code, no explanations
5. Use matplotlib.pyplot.savefig() with bbox_inches='tight', dpi=150 for static plots
6. For interactive plots, use plotly and return HTML
7. Handle missing values and data types appropriately
8. Always include proper error handling

For matplotlib plots, use this format:
```python
import matplotlib.pyplot as plt
import base64
import io

# Your plotting code here
plt.figure(figsize=(10, 6))
# ... plotting code ...

# Save as base64
buffer = io.BytesIO()
plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
buffer.seek(0)
plot_base64 = base64.b64encode(buffer.read()).decode()
plt.close()
result = {'type': 'chart', 'data': plot_base64}
```

For plotly plots, use this format:
```python
import plotly.express as px
import plotly.io as pio

# Your plotting code here
fig = px.bar(df, x='column', y='value')
plot_html = pio.to_html(fig, include_plotlyjs='cdn')
result = {'type': 'plotly', 'data': plot_html}
```

For tables, use this format:
```python
# Your data processing code here
result_df = df.groupby('column').sum()
result = {'type': 'table', 'data': result_df.to_dict('records')}
```"""
        ).with_model("gemini", "gemini-2.0-flash-lite")
        
        # Create context about the dataset
        dataset_context = f"""
Dataset Information:
- Name: {dataset_info['name']}
- Columns: {', '.join(dataset_info['columns'])}
- Total Rows: {dataset_info['row_count']}
- Sample Data: {json.dumps(dataset_info['data_preview'][:3], indent=2)}

Query: {query}

Generate Python code to answer this query. The DataFrame is available as 'df'.
"""
        
        user_message = UserMessage(text=dataset_context)
        response = await chat.send_message(user_message)
        
        # Extract code from response
        code = self._extract_code(response)
        return code
    
    def _extract_code(self, response: str) -> str:
        """Extract Python code from LLM response"""
        # Look for code blocks
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # If no code blocks, return the response as is
        return response.strip()

class CodeExecutor:
    def __init__(self):
        self.allowed_imports = {
            'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly', 
            'base64', 'io', 'json', 'datetime', 'math'
        }
    
    async def execute_code(self, code: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Safely execute generated code"""
        try:
            # Create a safe execution environment
            safe_globals = {
                '__builtins__': {},
                'df': df,
                'pd': pd,
                'np': np,
                'plt': plt,
                'sns': sns,
                'px': px,
                'go': go,
                'pio': pio,
                'base64': base64,
                'io': io,
                'json': json,
                'result': None
            }
            
            # Capture stdout and stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, safe_globals)
            
            # Get the result
            result = safe_globals.get('result')
            
            if result is None:
                # If no result variable, try to get the last expression
                return {
                    'type': 'error',
                    'message': 'No result returned from code execution'
                }
            
            return result
            
        except Exception as e:
            return {
                'type': 'error',
                'message': str(e)
            }

# Initialize services
code_generator = CodeGenerationService(GEMINI_API_KEY) if GEMINI_API_KEY else None
code_executor = CodeExecutor()

@api_router.post("/upload-dataset")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload and process a CSV or JSON dataset"""
    try:
        # Read file content
        content = await file.read()
        
        # Determine file type and process
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
            file_type = 'csv'
        elif file.filename.endswith('.json'):
            data = json.loads(content.decode('utf-8'))
            df = pd.DataFrame(data) if isinstance(data, list) else pd.json_normalize(data)
            file_type = 'json'
        else:
            raise HTTPException(status_code=400, detail="Only CSV and JSON files are supported")
        
        # Create dataset info
        dataset = Dataset(
            name=file.filename,
            file_type=file_type,
            columns=df.columns.tolist(),
            row_count=len(df),
            data_preview=df.head().to_dict('records')
        )
        
        # Store dataset info in MongoDB
        await db.datasets.insert_one(dataset.dict())
        
        # Store actual data in a separate collection for efficiency
        data_records = df.to_dict('records')
        await db.dataset_data.insert_one({
            'dataset_id': dataset.id,
            'data': data_records
        })
        
        return dataset
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.get("/datasets", response_model=List[Dataset])
async def get_datasets():
    """Get all uploaded datasets"""
    datasets = await db.datasets.find().to_list(1000)
    return [Dataset(**dataset) for dataset in datasets]

@api_router.post("/query")
async def process_query(request: QueryRequest):
    """Process a natural language query against a dataset"""
    try:
        if not code_generator:
            raise HTTPException(status_code=500, detail="LLM service not configured")
        
        # Get dataset info
        dataset_doc = await db.datasets.find_one({"id": request.dataset_id})
        if not dataset_doc:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        dataset = Dataset(**dataset_doc)
        
        # Get dataset data
        data_doc = await db.dataset_data.find_one({"dataset_id": request.dataset_id})
        if not data_doc:
            raise HTTPException(status_code=404, detail="Dataset data not found")
        
        df = pd.DataFrame(data_doc['data'])
        
        # Generate code from natural language query
        generated_code = await code_generator.generate_code(
            request.query_text, 
            dataset.dict()
        )
        
        # Execute the generated code
        execution_result = await code_executor.execute_code(generated_code, df)
        
        # Create query record
        query = Query(
            dataset_id=request.dataset_id,
            query_text=request.query_text,
            generated_code=generated_code,
            result_type=execution_result.get('type', 'error'),
            result_data=execution_result if execution_result.get('type') != 'error' else None,
            error_message=execution_result.get('message') if execution_result.get('type') == 'error' else None
        )
        
        # Store query in MongoDB
        await db.queries.insert_one(query.dict())
        
        return query
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@api_router.get("/queries/{dataset_id}")
async def get_queries(dataset_id: str):
    """Get all queries for a specific dataset"""
    queries = await db.queries.find({"dataset_id": dataset_id}).to_list(1000)
    return [Query(**query) for query in queries]

@api_router.get("/")
async def root():
    return {"message": "Ask Your Data API is running!"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()