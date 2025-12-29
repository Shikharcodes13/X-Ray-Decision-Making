import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { XRayAPI } from '../api'
import { JSONFieldRenderer } from '../components/JSONFieldRenderer'
import './ExecutionDetail.css'

function ExecutionDetail() {
  const { executionId } = useParams()
  const navigate = useNavigate()
  const [execution, setExecution] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (executionId) {
      loadExecution()
    }
  }, [executionId])

  const loadExecution = async () => {
    if (!executionId) return
    
    try {
      setLoading(true)
      setError(null)
      const data = await XRayAPI.getExecution(executionId)
      console.log('Execution data received:', data)
      console.log('Steps count:', data?.steps?.length || 0)
      
      // Ensure steps is always an array
      if (data && !data.steps) {
        data.steps = []
      }
      
      setExecution(data)
    } catch (err) {
      console.error('Error loading execution:', err)
      setError(err.message || 'Failed to load execution')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="execution-detail">
        <div className="loading">Loading execution data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="execution-detail">
        <div className="error">
          <p>Error: {error}</p>
          <button onClick={() => navigate('/')}>Back to Executions</button>
        </div>
      </div>
    )
  }

  if (!execution) {
    return (
      <div className="execution-detail">
        <div className="error">
          <p>Execution not found</p>
          <button onClick={() => navigate('/')}>Back to Executions</button>
        </div>
      </div>
    )
  }

  return (
    <div className="execution-detail">
      <div className="execution-header">
        <button className="back-button" onClick={() => navigate('/')}>
          ← Back to executions
        </button>
        <h1>Execution Detail</h1>
        <div className="execution-info">
          <div className="execution-name">{execution.name || 'Unnamed Execution'}</div>
          <div className="execution-id">ID: {execution.id || execution.execution_id || 'N/A'}</div>
          <div className="execution-time">
            Started: {execution.started_at ? new Date(execution.started_at).toLocaleString() : 'N/A'}
            {execution.ended_at && ` • Ended: ${new Date(execution.ended_at).toLocaleString()}`}
          </div>
        </div>
      </div>

      <div className="steps-container">
        {execution.steps && Array.isArray(execution.steps) && execution.steps.length > 0 ? (
          execution.steps.map((step, index) => (
            <StepCard key={step.id || step.name || index} step={step} index={index} />
          ))
        ) : (
          <div className="empty-state">
            <p>No steps found in this execution</p>
            {execution.metadata && (
              <div style={{ marginTop: '1rem', padding: '1rem', background: '#f9fafb', borderRadius: '4px' }}>
                <strong>Execution Metadata:</strong>
                <pre style={{ marginTop: '0.5rem', fontSize: '12px', overflow: 'auto' }}>
                  {JSON.stringify(execution.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function StepCard({ step, index }) {
  // Support both canonical and legacy formats
  const stepName = step.name || step.step || 'unknown'
  const stepType = step.type || 'general'
  const stepId = step.id || `step_${index + 1}`

  return (
    <div className="step-card">
      <div className="step-header">
        <div>
          <span className="step-name">{stepName}</span>
          <span className="step-type">{stepType}</span>
        </div>
        <span className="step-number">Step {index + 1}</span>
      </div>
      <div className="step-content">
        {step.reasoning && (
          <div className="section">
            <div className="section-title">Reasoning</div>
            <div className="reasoning">{step.reasoning}</div>
          </div>
        )}

        {step.rules && Array.isArray(step.rules) && step.rules.length > 0 && (
          <div className="section">
            <div className="section-title">Rules Applied</div>
            <div className="rules-list">
              {step.rules.map((rule, idx) => (
                <div key={idx} className="rule-item">
                  <strong>{rule.name}</strong>
                  <span className="rule-type">({rule.type})</span>
                  {rule.value && <span className="rule-value">: {String(rule.value)}</span>}
                  {rule.source && <span className="rule-source">from {rule.source}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {step.input && Object.keys(step.input).length > 0 && (
          <div className="section">
            <JSONFieldRenderer data={step.input} title="Input" readOnly={true} />
          </div>
        )}

        {step.evaluations && Array.isArray(step.evaluations) && step.evaluations.length > 0 && (
          <div className="section">
            <div className="section-title">Evaluations</div>
            <div className="evaluations-list">
              {step.evaluations.map((evaluation, idx) => {
                // Support canonical format
                const entityId = evaluation.entity_id || evaluation.item_id || `entity_${idx}`
                const attributes = evaluation.attributes || evaluation.metrics || {}
                const checks = evaluation.checks || []
                const finalDecision = evaluation.final_decision || (evaluation.passed ? 'accepted' : 'rejected')
                
                // Determine status from final_decision or checks
                const isAccepted = finalDecision === 'accepted' || finalDecision === 'selected' || evaluation.passed === true
                const className = isAccepted ? 'qualified' : 'disqualified'
                const icon = isAccepted ? '✓' : '✗'
                const itemName = attributes.name || attributes.title || entityId

                return (
                  <div key={idx} className={`evaluation-item ${className}`}>
                    <div className="evaluation-header">
                      <span className="evaluation-icon">{icon}</span>
                      <strong>{itemName}</strong>
                      <span className="entity-id">({entityId})</span>
                      <span className={`decision-badge ${finalDecision}`}>{finalDecision}</span>
                    </div>
                    
                    {checks.length > 0 && (
                      <div className="checks-list">
                        {checks.map((check, checkIdx) => (
                          <div key={checkIdx} className={`check-item ${check.passed ? 'passed' : 'failed'}`}>
                            <span className="check-rule">{check.rule}</span>
                            <span className="check-status">{check.passed ? '✓' : '✗'}</span>
                            {check.expected && <span className="check-expected">Expected: {check.expected}</span>}
                            {check.actual !== undefined && <span className="check-actual">Actual: {String(check.actual)}</span>}
                            {check.reason && <span className="check-reason">{check.reason}</span>}
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {Object.keys(attributes).length > 0 && (
                      <div className="metrics">
                        {Object.entries(attributes).map(([k, v]) => (
                          <span key={k}>
                            {k}: {String(v)}
                          </span>
                        ))}
                      </div>
                    )}
                    
                    {/* Legacy format support */}
                    {!checks.length && evaluation.filter_results && (
                      <div className="filter-results">
                        {Object.entries(evaluation.filter_results).map(([filterName, result]) => {
                          const passed = result.passed !== false
                          const statusClass = passed ? 'passed' : 'failed'
                          return (
                            <span key={filterName} className={`filter-result ${statusClass}`}>
                              {filterName}: {passed ? '✓' : '✗'}
                            </span>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Legacy ranked_candidates support - now handled in evaluations */}
        {step.ranked_candidates && Array.isArray(step.ranked_candidates) && !step.evaluations && (
          <div className="section">
            <div className="section-title">Ranked Candidates</div>
            <div className="ranking-list">
              {step.ranked_candidates.map((candidate, idx) => {
                const itemName = candidate.item_name || candidate.item_id || 'Item'
                const rank = candidate.rank ?? idx + 1
                const totalScore = candidate.total_score ?? 0
                const scoreBreakdown = candidate.score_breakdown
                  ? Object.entries(candidate.score_breakdown)
                      .map(([k, v]) => `${k}: ${Number(v).toFixed(2)}`)
                      .join(', ')
                  : ''

                return (
                  <div
                    key={candidate.item_id || candidate.item_name || idx}
                    className={`ranked-item ${step.selection && step.selection.item_id === candidate.item_id ? 'selected' : ''}`}
                  >
                    <div className="rank-badge">Rank {rank}</div>
                    <div className="rank-content">
                      <strong>{itemName}</strong>
                      <div className="rank-score">Score: {totalScore.toFixed(2)}</div>
                      {scoreBreakdown && <div className="score-breakdown">{scoreBreakdown}</div>}
                      {candidate.metrics && (
                        <div className="metrics">
                          {Object.entries(candidate.metrics).map(([k, v]) => (
                            <span key={k}>
                              {k}: {String(v)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
            {step.selection && (
              <div className="selection-result">
                <div className="section-title">Selection</div>
                <div className="selected-item">
                  <strong>{step.selection.item_name || step.selection.item_id || 'Selected Item'}</strong>
                  {step.selection.reason && (
                    <div className="selection-reason">{step.selection.reason}</div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {step.output && Object.keys(step.output).length > 0 && (
          <div className="section">
            <JSONFieldRenderer data={step.output} title="Output" readOnly={true} />
          </div>
        )}

        {!step.reasoning && !step.input && !step.output && !step.evaluations && !step.ranked_candidates && (
          <div style={{ color: '#999' }}>No additional data</div>
        )}
      </div>
    </div>
  )
}

export default ExecutionDetail

