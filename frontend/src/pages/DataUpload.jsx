import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { XRayAPI } from '../api'
import './DataUpload.css'

function DataUpload() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [uploadedDataset, setUploadedDataset] = useState(null)

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

    </div>
  )
}

export default DataUpload

