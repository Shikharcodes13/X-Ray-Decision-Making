import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { XRayAPI } from '../api'
import './WorkflowBuilder.css'

function WorkflowBuilder() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const datasetId = searchParams.get('dataset_id')

  const [workflow, setWorkflow] = useState({
    workflow_id: '',
    name: '',
    steps: []
  })
  const [dataset, setDataset] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  useEffect(() => {
    if (datasetId) {
      loadDataset()
    } else {
      setLoading(false)
    }
  }, [datasetId])

  const loadDataset = async () => {
    try {
      setLoading(true)
      const data = await XRayAPI.getDataset(datasetId)
      setDataset(data)
    } catch (err) {
      setError(err.message || 'Failed to load dataset')
    } finally {
      setLoading(false)
    }
  }

  const addStep = () => {
    const newStep = {
      id: `step_${workflow.steps.length + 1}`,
      type: 'filter',
      label: `Step ${workflow.steps.length + 1}`,
      input_fields: [],
      rule: {
        operator: '>=',
        value: ''
      }
    }
    setWorkflow({
      ...workflow,
      steps: [...workflow.steps, newStep]
    })
  }

  const updateStep = (index, updates) => {
    const newSteps = [...workflow.steps]
    newSteps[index] = { ...newSteps[index], ...updates }
    setWorkflow({ ...workflow, steps: newSteps })
  }

  const deleteStep = (index) => {
    const newSteps = workflow.steps.filter((_, i) => index !== i)
    setWorkflow({ ...workflow, steps: newSteps })
  }

  const handleSave = async () => {
    if (!workflow.name.trim()) {
      setError('Please enter a workflow name')
      return
    }

    try {
      setSaving(true)
      setError(null)
      await XRayAPI.saveWorkflow(workflow)
      setSuccess('Workflow saved successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err.message || 'Failed to save workflow')
    } finally {
      setSaving(false)
    }
  }

  const handleExecute = async () => {
    if (!datasetId) {
      setError('No dataset selected')
      return
    }

    if (workflow.steps.length === 0) {
      setError('Please add at least one step to the workflow')
      return
    }

    try {
      setExecuting(true)
      setError(null)
      
      // Generate workflow_id if not set
      if (!workflow.workflow_id) {
        const workflowWithId = {
          ...workflow,
          workflow_id: `wf_${Date.now()}`
        }
        await XRayAPI.saveWorkflow(workflowWithId)
        setWorkflow(workflowWithId)
      }

      const result = await XRayAPI.executeWorkflow(
        workflow.workflow_id || `wf_${Date.now()}`,
        datasetId,
        workflow.name || 'Workflow Execution'
      )
      
      // Navigate to execution detail
      navigate(`/execution/${result.execution_id}`)
    } catch (err) {
      setError(err.message || 'Failed to execute workflow')
    } finally {
      setExecuting(false)
    }
  }

  if (loading) {
    return (
      <div className="workflow-builder">
        <div className="loading">Loading dataset...</div>
      </div>
    )
  }

  if (!dataset && datasetId) {
    return (
      <div className="workflow-builder">
        <div className="error">Failed to load dataset</div>
      </div>
    )
  }

  return (
    <div className="workflow-builder">
      <div className="builder-header">
        <h1>🔧 Workflow Builder</h1>
        <p className="subtitle">Build your workflow with visual steps and rules</p>
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

      <div className="builder-layout">
        {/* Left Panel: Dataset Schema */}
        <div className="schema-panel">
          <h3>📋 Data Schema</h3>
          {dataset ? (
            <>
              <div className="dataset-info">
                <div className="info-item">
                  <strong>Dataset:</strong> {dataset.filename}
                </div>
                <div className="info-item">
                  <strong>Rows:</strong> {dataset.row_count.toLocaleString()}
                </div>
              </div>
              <div className="fields-list">
                <h4>Available Fields</h4>
                {dataset.fields.map((field) => (
                  <div key={field} className="field-item">
                    <span className="field-name">{field}</span>
                    <span className="field-type">{dataset.schema[field]}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="no-dataset">
              <p>No dataset selected</p>
              <button
                className="btn-link"
                onClick={() => navigate('/data-upload')}
              >
                Upload Dataset →
              </button>
            </div>
          )}
        </div>

        {/* Center Panel: Workflow Steps */}
        <div className="workflow-panel">
          <div className="workflow-header">
            <div className="workflow-name-input">
              <label>
                <strong>Workflow Name</strong>
                <input
                  type="text"
                  value={workflow.name}
                  onChange={(e) => setWorkflow({ ...workflow, name: e.target.value })}
                  placeholder="e.g., Product Filtering Workflow"
                />
              </label>
            </div>
            <div className="workflow-actions">
              <button
                className="btn-secondary"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Workflow'}
              </button>
              <button
                className="btn-primary"
                onClick={handleExecute}
                disabled={executing || !datasetId || workflow.steps.length === 0}
              >
                {executing ? 'Executing...' : '▶ Run Workflow'}
              </button>
            </div>
          </div>

          <div className="steps-container">
            {workflow.steps.length === 0 ? (
              <div className="empty-steps">
                <p>No steps yet. Click "Add Step" to get started!</p>
                <button className="btn-primary" onClick={addStep}>
                  + Add Step
                </button>
              </div>
            ) : (
              workflow.steps.map((step, index) => (
                <StepEditor
                  key={step.id}
                  step={step}
                  index={index}
                  dataset={dataset}
                  onUpdate={(updates) => updateStep(index, updates)}
                  onDelete={() => deleteStep(index)}
                />
              ))
            )}
          </div>

          {workflow.steps.length > 0 && (
            <button className="btn-add-step" onClick={addStep}>
              + Add Step
            </button>
          )}
        </div>

        {/* Right Panel: Live Preview */}
        <div className="preview-panel">
          <h3>📊 Live Preview</h3>
          <div className="preview-content">
            <div className="preview-stats">
              <div className="stat">
                <span className="stat-label">Steps</span>
                <span className="stat-value">{workflow.steps.length}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Dataset</span>
                <span className="stat-value">
                  {dataset ? dataset.row_count.toLocaleString() : 'N/A'}
                </span>
              </div>
            </div>

            {workflow.steps.length > 0 && (
              <div className="workflow-summary">
                <h4>Workflow Summary</h4>
                <div className="summary-steps">
                  {workflow.steps.map((step, idx) => (
                    <div key={step.id} className="summary-step">
                      <span className="step-number">{idx + 1}</span>
                      <div className="step-info">
                        <strong>{step.label}</strong>
                        <span className="step-type">{step.type}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StepEditor({ step, index, dataset, onUpdate, onDelete }) {
  const [expanded, setExpanded] = useState(true)

  const handleFieldToggle = (field) => {
    const currentFields = step.input_fields || []
    const newFields = currentFields.includes(field)
      ? currentFields.filter(f => f !== field)
      : [...currentFields, field]
    onUpdate({ input_fields: newFields })
  }

  return (
    <div className="step-editor">
      <div className="step-header" onClick={() => setExpanded(!expanded)}>
        <div className="step-title">
          <span className="step-number">{index + 1}</span>
          <input
            type="text"
            value={step.label}
            onChange={(e) => onUpdate({ label: e.target.value })}
            onClick={(e) => e.stopPropagation()}
            className="step-label-input"
            placeholder="Step label"
          />
          <span className="step-type-badge">{step.type}</span>
        </div>
        <div className="step-actions">
          <button
            className="btn-icon"
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            title="Delete step"
          >
            🗑️
          </button>
          <button className="btn-icon" onClick={() => setExpanded(!expanded)}>
            {expanded ? '▼' : '▶'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="step-content">
          <div className="form-group">
            <label>
              <strong>Step Type</strong>
              <select
                value={step.type}
                onChange={(e) => onUpdate({ type: e.target.value })}
              >
                <option value="filter">Filter</option>
                <option value="ranking">Ranking</option>
                <option value="transformation">Transformation</option>
              </select>
            </label>
          </div>

          {step.type === 'filter' && (
            <>
              <div className="form-group">
                <label>
                  <strong>Select Fields</strong>
                  <small>Choose which fields to apply the filter to</small>
                </label>
                <div className="fields-selector">
                  {dataset?.fields.map((field) => (
                    <label key={field} className="field-checkbox">
                      <input
                        type="checkbox"
                        checked={step.input_fields?.includes(field) || false}
                        onChange={() => handleFieldToggle(field)}
                      />
                      <span>{field}</span>
                      <span className="field-type-hint">
                        ({dataset.schema[field]})
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>
                    <strong>Operator</strong>
                    <select
                      value={step.rule?.operator || '=='}
                      onChange={(e) =>
                        onUpdate({
                          rule: { ...step.rule, operator: e.target.value }
                        })
                      }
                    >
                      <option value="==">Equals (==) - Exact match</option>
                      <option value="!=">Not equals (!=)</option>
                      <option value="contains">Contains - Substring match</option>
                      <option value="not_contains">Not Contains</option>
                      <option value="starts_with">Starts With</option>
                      <option value="ends_with">Ends With</option>
                      <option value="in">In List</option>
                      <option value="not_in">Not In List</option>
                      <option value=">=">Greater than or equal (≥) - Numbers only</option>
                      <option value="<=">Less than or equal (≤) - Numbers only</option>
                      <option value=">">Greater than (&gt;) - Numbers only</option>
                      <option value="<">Less than (&lt;) - Numbers only</option>
                    </select>
                  </label>
                </div>

                <div className="form-group">
                  <label>
                    <strong>Value</strong>
                    <input
                      type="text"
                      value={step.rule?.value || ''}
                      onChange={(e) =>
                        onUpdate({
                          rule: { ...step.rule, value: e.target.value }
                        })
                      }
                      placeholder="e.g., 4, 50, 'text'"
                    />
                  </label>
                </div>
              </div>
            </>
          )}

          {step.type === 'ranking' && (
            <>
              <div className="form-group">
                <label>
                  <strong>Rank By Fields</strong>
                  <small>Select fields to rank by (in order of priority)</small>
                </label>
                <div className="fields-selector">
                  {dataset?.fields.map((field) => (
                    <label key={field} className="field-checkbox">
                      <input
                        type="checkbox"
                        checked={step.input_fields?.includes(field) || false}
                        onChange={() => handleFieldToggle(field)}
                      />
                      <span>{field}</span>
                      <span className="field-type-hint">
                        ({dataset.schema[field]})
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label>
                  <strong>Order</strong>
                  <select
                    value={step.rule?.order || 'desc'}
                    onChange={(e) =>
                      onUpdate({
                        rule: { ...step.rule, order: e.target.value }
                      })
                    }
                  >
                    <option value="desc">Descending (Highest first)</option>
                    <option value="asc">Ascending (Lowest first)</option>
                  </select>
                </label>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default WorkflowBuilder

