import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { XRayAPI } from '../api'
import './DataUpload.css'

function DataUpload() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [uploadedDataset, setUploadedDataset] = useState(null)
  const [datasets, setDatasets] = useState([])
  const [loading, setLoading] = useState(true)

  // Load existing datasets
  useEffect(() => {
    loadDatasets()
  }, [])

  const loadDatasets = async () => {
    try {
      setLoading(true)
      const data = await XRayAPI.listDatasets()
      setDatasets(data)
    } catch (err) {
      console.error('Failed to load datasets:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleFileSelect = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    // Validate file type
    const validTypes = ['.csv', '.xlsx', '.xls', '.json']
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase()
    
    if (!validTypes.includes(fileExtension)) {
      setError(`Invalid file type. Supported formats: ${validTypes.join(', ')}`)
      return
    }

    // Validate file size (max 100MB)
    if (file.size > 100 * 1024 * 1024) {
      setError('File size exceeds 100MB limit')
      return
    }

    try {
      setUploading(true)
      setError(null)
      
      const result = await XRayAPI.uploadDataset(file)
      setUploadedDataset(result)
      
      // Reload datasets list
      await loadDatasets()
      
      // Clear file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (err) {
      setError(err.message || 'Failed to upload file')
    } finally {
      setUploading(false)
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    
    const files = e.dataTransfer.files
    if (files.length > 0) {
      const file = files[0]
      // Create a synthetic event
      const syntheticEvent = {
        target: { files: [file] }
      }
      handleFileSelect(syntheticEvent)
    }
  }

  const handleCreateWorkflow = (dataset) => {
    navigate(`/workflow-builder?dataset_id=${dataset.dataset_id}`)
  }

  return (
    <div className="data-upload">
      <h1>📊 Data Upload</h1>
      <p className="subtitle">Upload your data files (CSV, Excel, JSON) to get started</p>

      {/* Upload Area */}
      <div className="upload-section">
        <div
          className="upload-area"
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls,.json"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          
          {uploading ? (
            <div className="upload-status">
              <div className="spinner"></div>
              <p>Uploading and processing file...</p>
            </div>
          ) : (
            <div className="upload-content">
              <div className="upload-icon">📁</div>
              <h3>Drop your file here or click to browse</h3>
              <p>Supports CSV, Excel (.xlsx, .xls), and JSON files</p>
              <p className="upload-hint">Max file size: 100MB</p>
            </div>
          )}
        </div>

        {error && (
          <div className="error-message">
            <strong>Error:</strong> {error}
          </div>
        )}

        {uploadedDataset && (
          <div className="success-panel">
            <h3>✅ File Uploaded Successfully!</h3>
            <div className="dataset-info">
              <div className="info-row">
                <strong>Filename:</strong> {uploadedDataset.filename}
              </div>
              <div className="info-row">
                <strong>Rows:</strong> {uploadedDataset.row_count.toLocaleString()}
              </div>
              <div className="info-row">
                <strong>Fields:</strong> {uploadedDataset.fields.length}
              </div>
            </div>
            
            <div className="schema-preview">
              <h4>Detected Schema:</h4>
              <div className="fields-list">
                {uploadedDataset.fields.map((field) => (
                  <div key={field} className="field-badge">
                    <span className="field-name">{field}</span>
                    <span className="field-type">{uploadedDataset.schema[field]}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="preview-table">
              <h4>Data Preview (first 10 rows):</h4>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      {uploadedDataset.fields.map((field) => (
                        <th key={field}>{field}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {uploadedDataset.preview.map((row, idx) => (
                      <tr key={idx}>
                        {uploadedDataset.fields.map((field) => (
                          <td key={field}>{String(row[field] || '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="action-buttons">
              <button
                className="btn-primary"
                onClick={() => handleCreateWorkflow(uploadedDataset)}
              >
                Create Workflow with This Data →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Existing Datasets */}
      <div className="datasets-section">
        <h2>Your Datasets</h2>
        {loading ? (
          <div className="loading">Loading datasets...</div>
        ) : datasets.length === 0 ? (
          <div className="empty-state">
            <p>No datasets uploaded yet. Upload a file to get started!</p>
          </div>
        ) : (
          <div className="datasets-grid">
            {datasets.map((dataset) => (
              <div key={dataset.dataset_id} className="dataset-card">
                <div className="dataset-header">
                  <h3>{dataset.filename}</h3>
                  <span className="dataset-id">ID: {dataset.dataset_id}</span>
                </div>
                <div className="dataset-stats">
                  <div className="stat">
                    <span className="stat-label">Rows</span>
                    <span className="stat-value">{dataset.row_count.toLocaleString()}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Fields</span>
                    <span className="stat-value">{dataset.fields.length}</span>
                  </div>
                </div>
                <div className="dataset-fields">
                  {dataset.fields.slice(0, 5).map((field) => (
                    <span key={field} className="field-tag">{field}</span>
                  ))}
                  {dataset.fields.length > 5 && (
                    <span className="field-tag">+{dataset.fields.length - 5} more</span>
                  )}
                </div>
                <button
                  className="btn-secondary"
                  onClick={() => handleCreateWorkflow(dataset)}
                >
                  Use in Workflow →
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default DataUpload

