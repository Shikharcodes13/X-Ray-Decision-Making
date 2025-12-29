import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { XRayAPI } from '../api'
import './RunWorkflow.css'

function RunWorkflow() {
  const navigate = useNavigate()
  const [rulesFormat, setRulesFormat] = useState('json')
  const [rulesText, setRulesText] = useState('')
  const [useJsonInput, setUseJsonInput] = useState(false)
  const [inputDataText, setInputDataText] = useState('{}')
  
  // Structured input fields
  const [count, setCount] = useState('')
  const [refValue, setRefValue] = useState('')
  const [refScore, setRefScore] = useState('')
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // Sync structured fields with JSON
  useEffect(() => {
    if (!useJsonInput) {
      try {
        const data = inputDataText.trim() ? JSON.parse(inputDataText) : {}
        setCount(data.count?.toString() || '')
        setRefValue(data.reference?.value?.toString() || '')
        setRefScore(data.reference?.score?.toString() || '')
      } catch (e) {
        // Ignore parse errors when switching modes
      }
    }
  }, [useJsonInput, inputDataText])

  // Update JSON when structured fields change
  useEffect(() => {
    if (!useJsonInput) {
      const inputData = {}
      if (count) {
        const countNum = Number(count)
        if (!isNaN(countNum)) inputData.count = countNum
      }
      if (refValue || refScore) {
        inputData.reference = {}
        if (refValue) {
          const val = Number(refValue)
          if (!isNaN(val)) inputData.reference.value = val
        }
        if (refScore) {
          const score = Number(refScore)
          if (!isNaN(score)) inputData.reference.score = score
        }
      }
      setInputDataText(JSON.stringify(inputData, null, 2))
    }
  }, [count, refValue, refScore, useJsonInput])

  const handleRun = async () => {
    try {
      setLoading(true)
      setError(null)
      setSuccess(null)

      let rules = null
      if (rulesText.trim()) {
        if (rulesFormat === 'json') {
          rules = JSON.parse(rulesText)
        } else {
          rules = rulesText
        }
      }

      let inputData = {}
      if (inputDataText.trim()) {
        inputData = JSON.parse(inputDataText)
      }

      const result = await XRayAPI.runWorkflow(rules, rulesFormat, inputData)
      
      if (!result || !result.execution_id) {
        throw new Error('Workflow execution did not return an execution ID')
      }
      
      setSuccess(`Workflow executed successfully! Execution ID: ${result.execution_id}`)
      
      // Navigate to execution detail after a short delay
      setTimeout(() => {
        navigate(`/execution/${result.execution_id}`)
      }, 1500)
    } catch (err) {
      setError(err.message || 'Failed to run workflow')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="run-workflow">
      <h1>Run Workflow</h1>
      <p className="subtitle">Execute a workflow with custom rules and input data</p>

      <div className="form-section">
        <label>
          <strong>Rules Format</strong>
          <select value={rulesFormat} onChange={(e) => setRulesFormat(e.target.value)}>
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
          </select>
        </label>
      </div>

      <div className="form-section">
        <label>
          <strong>Rules {rulesFormat === 'json' ? '(JSON)' : '(CSV)'}</strong>
          <small>Leave empty to use default rules from rules.csv</small>
        </label>
        <div className="rules-editor-container">
          <textarea
            value={rulesText}
            onChange={(e) => setRulesText(e.target.value)}
            placeholder={rulesFormat === 'json' 
              ? '[\n  {\n    "step": "apply_filters",\n    "type": "filter",\n    "name": "value_range",\n    "field": "value",\n    "rule_type": "range",\n    "min": 25.0,\n    "max": 100.0\n  }\n]'
              : 'step,type,name,field,rule_type,value,min,max\napply_filters,filter,value_range,value,range,,25.0,100.0'}
            rows={10}
            className="rules-editor"
          />
        </div>
      </div>

      <div className="form-section">
        <div className="form-section-header">
          <label>
            <strong>Input Data</strong>
            <small>Input parameters for the workflow</small>
          </label>
          <div className="input-mode-toggle">
            <button
              type="button"
              className={!useJsonInput ? 'active' : ''}
              onClick={() => setUseJsonInput(false)}
            >
              Form Fields
            </button>
            <button
              type="button"
              className={useJsonInput ? 'active' : ''}
              onClick={() => setUseJsonInput(true)}
            >
              JSON Editor
            </button>
          </div>
        </div>

        {!useJsonInput ? (
          <div className="structured-input-form">
            <div className="form-row">
              <label>
                <span>Count</span>
                <small>Number of items to generate</small>
                <input
                  type="number"
                  value={count}
                  onChange={(e) => setCount(e.target.value)}
                  placeholder="e.g., 10"
                />
              </label>
            </div>

            <div className="form-group">
              <label className="group-label">Reference Data</label>
              <div className="form-row">
                <label>
                  <span>Value</span>
                  <small>Reference value</small>
                  <input
                    type="number"
                    step="any"
                    value={refValue}
                    onChange={(e) => setRefValue(e.target.value)}
                    placeholder="e.g., 50"
                  />
                </label>
                <label>
                  <span>Score</span>
                  <small>Reference score</small>
                  <input
                    type="number"
                    step="any"
                    value={refScore}
                    onChange={(e) => setRefScore(e.target.value)}
                    placeholder="e.g., 3.5"
                  />
                </label>
              </div>
            </div>

            <div className="json-preview">
              <small>JSON Preview:</small>
              <pre>{inputDataText || '{}'}</pre>
            </div>
          </div>
        ) : (
          <textarea
            value={inputDataText}
            onChange={(e) => setInputDataText(e.target.value)}
            placeholder='{\n  "count": 10,\n  "reference": {"value": 50, "score": 3.5}\n}'
            rows={8}
            className="json-editor"
          />
        )}
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {success && (
        <div className="success-message">
          {success}
        </div>
      )}

      <div className="form-actions">
        <button onClick={handleRun} disabled={loading}>
          {loading ? 'Running...' : 'Run Workflow'}
        </button>
      </div>
    </div>
  )
}

export default RunWorkflow

