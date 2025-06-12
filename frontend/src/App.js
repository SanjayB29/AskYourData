import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DatasetUpload = ({ onDatasetUploaded }) => {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleFileUpload = async (file) => {
    if (!file) return;
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axios.post(`${API}/upload-dataset`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      onDatasetUploaded(response.data);
    } catch (error) {
      console.error('Error uploading dataset:', error);
      alert('Error uploading dataset. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div
      className={`upload-zone ${dragActive ? 'drag-active' : ''} ${uploading ? 'uploading' : ''}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      {uploading ? (
        <div className="upload-loading">
          <div className="spinner"></div>
          <p>Uploading and processing your dataset...</p>
        </div>
      ) : (
        <div className="upload-content">
          <div className="upload-icon">📊</div>
          <h3>Upload Your Dataset</h3>
          <p>Drag & drop your CSV or JSON file here, or click to select</p>
          <input
            type="file"
            accept=".csv,.json"
            onChange={(e) => handleFileUpload(e.target.files[0])}
            className="file-input"
          />
          <div className="supported-formats">
            <span>Supported formats: CSV, JSON</span>
          </div>
        </div>
      )}
    </div>
  );
};

const DatasetInfo = ({ dataset }) => (
  <div className="dataset-info">
    <div className="dataset-header">
      <h3>📊 {dataset.name}</h3>
      <span className="dataset-meta">{dataset.row_count} rows • {dataset.columns.length} columns</span>
    </div>
    <div className="dataset-columns">
      <strong>Columns:</strong>
      <div className="columns-list">
        {dataset.columns.map((col, idx) => (
          <span key={idx} className="column-tag">{col}</span>
        ))}
      </div>
    </div>
    <div className="dataset-preview">
      <strong>Sample Data:</strong>
      <div className="preview-table">
        <table>
          <thead>
            <tr>
              {dataset.columns.slice(0, 4).map((col, idx) => (
                <th key={idx}>{col}</th>
              ))}
              {dataset.columns.length > 4 && <th>...</th>}
            </tr>
          </thead>
          <tbody>
            {dataset.data_preview.slice(0, 3).map((row, idx) => (
              <tr key={idx}>
                {dataset.columns.slice(0, 4).map((col, colIdx) => (
                  <td key={colIdx}>{String(row[col]).slice(0, 20)}{String(row[col]).length > 20 ? '...' : ''}</td>
                ))}
                {dataset.columns.length > 4 && <td>...</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  </div>
);

const QueryInterface = ({ dataset, onQueryResult }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions] = useState([
    "Show me the average values by category",
    "Which item has the highest value?",
    "Create a bar chart of the top 10 items",
    "Show trends over time",
    "What's the distribution of values?",
    "Compare categories with a pie chart"
  ]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post(`${API}/query`, {
        dataset_id: dataset.id,
        query_text: query
      });
      
      onQueryResult(response.data);
      setQuery('');
    } catch (error) {
      console.error('Error processing query:', error);
      alert('Error processing query. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="query-interface">
      <div className="query-header">
        <h3>🤖 Ask Your Data</h3>
        <p>Ask questions about your data in natural language</p>
      </div>
      
      <form onSubmit={handleSubmit} className="query-form">
        <div className="query-input-container">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question about your data... (e.g., 'Show me the average sales by region')"
            className="query-input"
            rows={3}
            disabled={loading}
          />
          <button type="submit" disabled={loading || !query.trim()} className="query-button">
            {loading ? (
              <div className="button-loading">
                <div className="mini-spinner"></div>
                Analyzing...
              </div>
            ) : (
              'Ask Question'
            )}
          </button>
        </div>
      </form>

      <div className="query-suggestions">
        <p>Try these example queries:</p>
        <div className="suggestions-grid">
          {suggestions.map((suggestion, idx) => (
            <button
              key={idx}
              className="suggestion-chip"
              onClick={() => setQuery(suggestion)}
              disabled={loading}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

const QueryResult = ({ result }) => {
  if (!result) return null;

  if (result.result_type === 'error') {
    return (
      <div className="query-result error">
        <h4>❌ Error</h4>
        <p>{result.error_message}</p>
        <details>
          <summary>Generated Code</summary>
          <pre>{result.generated_code}</pre>
        </details>
      </div>
    );
  }

  const { result_data } = result;

  return (
    <div className="query-result success">
      <div className="result-header">
        <h4>✅ Query Result</h4>
        <span className="result-type">{result.result_type}</span>
      </div>
      
      <div className="result-content">
        {result_data.type === 'table' && (
          <div className="table-result">
            <table>
              <thead>
                <tr>
                  {Object.keys(result_data.data[0] || {}).map((key, idx) => (
                    <th key={idx}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result_data.data.slice(0, 50).map((row, idx) => (
                  <tr key={idx}>
                    {Object.values(row).map((value, valueIdx) => (
                      <td key={valueIdx}>{String(value)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {result_data.data.length > 50 && (
              <p className="table-truncation">Showing first 50 rows of {result_data.data.length} total rows</p>
            )}
          </div>
        )}

        {result_data.type === 'chart' && (
          <div className="chart-result">
            <img src={`data:image/png;base64,${result_data.data}`} alt="Generated Chart" />
          </div>
        )}

        {result_data.type === 'plotly' && (
          <div className="plotly-result">
            <div dangerouslySetInnerHTML={{ __html: result_data.data }} />
          </div>
        )}
      </div>
      
      <details className="code-details">
        <summary>View Generated Code</summary>
        <pre>{result.generated_code}</pre>
      </details>
    </div>
  );
};

function App() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [queryResults, setQueryResults] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDatasets();
  }, []);

  const loadDatasets = async () => {
    try {
      const response = await axios.get(`${API}/datasets`);
      setDatasets(response.data);
      if (response.data.length > 0 && !selectedDataset) {
        setSelectedDataset(response.data[0]);
      }
    } catch (error) {
      console.error('Error loading datasets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDatasetUploaded = (dataset) => {
    setDatasets(prev => [dataset, ...prev]);
    setSelectedDataset(dataset);
    setQueryResults([]);
  };

  const handleQueryResult = (result) => {
    setQueryResults(prev => [result, ...prev]);
  };

  if (loading) {
    return (
      <div className="App">
        <div className="loading-screen">
          <div className="spinner"></div>
          <p>Loading Ask Your Data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="app-header">
        <h1>📊 Ask Your Data</h1>
        <p>Upload datasets and query them with natural language</p>
      </header>

      <main className="app-main">
        {!selectedDataset ? (
          <div className="welcome-section">
            <DatasetUpload onDatasetUploaded={handleDatasetUploaded} />
          </div>
        ) : (
          <div className="dashboard">
            <div className="sidebar">
              <div className="dataset-selector">
                <h3>Your Datasets</h3>
                {datasets.map(dataset => (
                  <div
                    key={dataset.id}
                    className={`dataset-card ${selectedDataset?.id === dataset.id ? 'active' : ''}`}
                    onClick={() => {
                      setSelectedDataset(dataset);
                      setQueryResults([]);
                    }}
                  >
                    <strong>{dataset.name}</strong>
                    <span>{dataset.row_count} rows</span>
                  </div>
                ))}
                <DatasetUpload onDatasetUploaded={handleDatasetUploaded} />
              </div>
            </div>

            <div className="main-content">
              <DatasetInfo dataset={selectedDataset} />
              <QueryInterface dataset={selectedDataset} onQueryResult={handleQueryResult} />
              
              <div className="results-section">
                {queryResults.map((result, idx) => (
                  <QueryResult key={idx} result={result} />
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;