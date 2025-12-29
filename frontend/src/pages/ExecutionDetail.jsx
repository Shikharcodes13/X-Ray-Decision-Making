import { useEffect, useState, useMemo } from 'react'
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
      console.log('Steps is array?', Array.isArray(data?.steps))
      console.log('Steps data:', data?.steps)
      
      // Ensure steps is always an array
      if (data && !data.steps) {
        data.steps = []
      }
      
      // Debug: Log step structure
      if (data?.steps && data.steps.length > 0) {
        console.log('First step:', data.steps[0])
        console.log('Step keys:', Object.keys(data.steps[0] || {}))
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
        <div className="execution-info">
          <div className="execution-name-header">
            <h1>{execution.name || execution.metadata?.name || execution.metadata?.workflow || 'Unnamed Execution'}</h1>
            <div className="execution-stats-header">
              <div className="stat-badge">
                <span className="stat-label">Steps</span>
                <span className="stat-value">{execution.steps?.length || 0}</span>
              </div>
              <div className="stat-badge">
                <span className="stat-label">ID</span>
                <span className="stat-value">{execution.id || execution.execution_id || 'N/A'}</span>
              </div>
            </div>
          </div>
          <div className="execution-time">
            Started: {execution.started_at ? new Date(execution.started_at).toLocaleString() : 'N/A'}
            {execution.ended_at && ` • Ended: ${new Date(execution.ended_at).toLocaleString()}`}
          </div>
        </div>
      </div>

      {/* Timeline View */}
      {execution.steps && Array.isArray(execution.steps) && execution.steps.length > 0 && (
        <div className="execution-timeline">
          <h2>Execution Timeline</h2>
          <div className="timeline-container">
            {execution.steps.map((step, index) => {
              const stepName = step.name || step.step || step.label || `Step ${index + 1}`
              const stepType = step.type || 'general'
              const output = step.output || {}
              const inputCount = step.input?.input_count || step.input?.candidates_count || output.total || output.total_evaluated || 0
              const passedCount = output.passed || output.total_ranked || 0
              const failedCount = output.failed || (inputCount - passedCount)
              const isComplete = step.ended_at || step.output
              
              return (
                <div key={step.id || index} className="timeline-item">
                  <div className="timeline-marker">
                    {isComplete ? (
                      <div className="timeline-checkmark">✓</div>
                    ) : (
                      <div className="timeline-pending">○</div>
                    )}
                    {index < execution.steps.length - 1 && <div className="timeline-line" />}
                  </div>
                  <div className="timeline-content">
                    <div className="timeline-header">
                      <span className="timeline-step-name">{stepName}</span>
                      <span className="timeline-step-type">{stepType}</span>
                      {isComplete && <span className="timeline-status">Completed</span>}
                    </div>
                    <div className="timeline-stats">
                      {stepType === 'filter' && (
                        <>
                          <span className="stat-item input">Input: {inputCount}</span>
                          <span className="stat-item passed">Passed: {passedCount}</span>
                          <span className="stat-item failed">Failed: {failedCount}</span>
                        </>
                      )}
                      {stepType === 'ranking' && (
                        <span className="stat-item">Ranked: {passedCount} items</span>
                      )}
                      {stepType === 'transformation' && (
                        <span className="stat-item">Processed: {inputCount} items</span>
                      )}
                    </div>
                    {step.reasoning && (
                      <div className="timeline-reasoning">{step.reasoning.split('\n').slice(0, 3).join(' ')}</div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Final Recommendation Section */}
      {execution.steps && execution.steps.length > 0 && (() => {
        const rankingStep = execution.steps.find(s => s.type === 'ranking')
        if (rankingStep && rankingStep.output && rankingStep.output.selected_item) {
          const selected = rankingStep.output.selected_item
          const rankedCandidates = rankingStep.evaluations || []
          const topRanked = rankedCandidates.filter(e => e.final_decision === 'selected' || 
            (rankedCandidates.indexOf(e) === 0 && e.final_decision !== 'rejected'))
          
          return (
            <div className="recommendation-section">
              <h2>Final Recommendation</h2>
              <div className="recommendation-card">
                <div className="recommendation-header">
                  <span className="recommendation-badge">Recommended</span>
                  <h3>{selected.name || selected.item_name || selected.id || 'Selected Item'}</h3>
                </div>
                <div className="recommendation-details">
                  {selected.id && <div className="detail-item"><strong>ID:</strong> {selected.id}</div>}
                  {Object.entries(selected).filter(([k]) => !['id', 'name', 'item_name'].includes(k)).map(([key, value]) => (
                    <div key={key} className="detail-item">
                      <strong>{key}:</strong> {String(value)}
                    </div>
                  ))}
                </div>
                {rankingStep.reasoning && (
                  <div className="recommendation-reasoning">
                    <strong>Reasoning:</strong>
                    <div className="reasoning-text">{rankingStep.reasoning}</div>
                  </div>
                )}
              </div>
            </div>
          )
        }
        return null
      })()}

      <div className="steps-container">
        {(() => {
          const hasSteps = execution.steps && Array.isArray(execution.steps) && execution.steps.length > 0
          console.log('Rendering check - hasSteps:', hasSteps, 'steps:', execution.steps)
          
          if (hasSteps) {
            return (
              <>
                <h2>Step Details</h2>
                {execution.steps.map((step, index) => {
                  console.log(`Rendering step ${index}:`, step)
                  return <StepCard key={step.id || step.name || index} step={step} index={index} />
                })}
              </>
            )
          } else {
            return (
              <div className="empty-state">
                <p>No steps found in this execution</p>
                <p style={{ fontSize: '12px', color: '#999', marginTop: '0.5rem' }}>
                  Debug: steps={JSON.stringify(execution.steps)}, 
                  isArray={String(Array.isArray(execution.steps))}, 
                  length={execution.steps?.length || 0}
                </p>
                {execution.metadata && (
                  <div style={{ marginTop: '1rem', padding: '1rem', background: '#f9fafb', borderRadius: '4px' }}>
                    <strong>Execution Metadata:</strong>
                    <pre style={{ marginTop: '0.5rem', fontSize: '12px', overflow: 'auto' }}>
                      {JSON.stringify(execution.metadata, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )
          }
        })()}
      </div>
    </div>
  )
}

function StepCard({ step, index }) {
  // Support both canonical and legacy formats
  const stepName = step.name || step.step || step.label || `Step ${index + 1}`
  const stepType = step.type || 'general'
  const stepId = step.id || `step_${index + 1}`
  
  console.log(`StepCard ${index} - step:`, step, 'name:', stepName, 'type:', stepType)

  return (
    <div className="step-card">
      <div className="step-header">
        <div>
          <span className="step-name">{stepName}</span>
          <span className="step-type">{stepType}</span>
        </div>
        {/* Only show step number if name is generic */}
        {stepName === `Step ${index + 1}` && (
          <span className="step-number">Step {index + 1}</span>
        )}
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
            <EvaluationsList evaluations={step.evaluations} />
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
          <div className="section">
            <div className="section-title">Step Data</div>
            <div style={{ padding: '1rem', background: '#f9fafb', borderRadius: '4px', fontSize: '12px' }}>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {JSON.stringify(step, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Evaluations list with pagination for performance
function EvaluationsList({ evaluations }) {
  const [showAll, setShowAll] = useState(false)
  const [expandedItems, setExpandedItems] = useState(new Set())
  const INITIAL_SHOW = 20

  const displayedEvaluations = showAll ? evaluations : evaluations.slice(0, INITIAL_SHOW)
  const hasMore = evaluations.length > INITIAL_SHOW

  const toggleItem = (idx) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(idx)) {
      newExpanded.delete(idx)
    } else {
      newExpanded.add(idx)
    }
    setExpandedItems(newExpanded)
  }

  // Count passed/failed
  const passedCount = evaluations.filter(e => 
    e.final_decision === 'accepted' || e.final_decision === 'selected' || e.passed === true
  ).length
  const failedCount = evaluations.length - passedCount

  return (
    <div className="evaluations-container">
      <div className="evaluations-summary">
        <span className="summary-item passed">✓ {passedCount} Passed</span>
        <span className="summary-item failed">✗ {failedCount} Failed</span>
        <span className="summary-item total">{evaluations.length} Total</span>
      </div>
      
      <div className="evaluations-list">
        {displayedEvaluations.map((evaluation, idx) => {
          const entityId = evaluation.entity_id || evaluation.item_id || `entity_${idx}`
          const attributes = evaluation.attributes || evaluation.metrics || {}
          const checks = evaluation.checks || []
          const finalDecision = evaluation.final_decision || (evaluation.passed ? 'accepted' : 'rejected')
          
          const isAccepted = finalDecision === 'accepted' || finalDecision === 'selected' || evaluation.passed === true
          const className = isAccepted ? 'accepted' : 'rejected'
          const icon = isAccepted ? '✓' : '✗'
          const itemName = attributes.name || attributes.title || entityId
          const isExpanded = expandedItems.has(idx)

          return (
            <div key={idx} className={`evaluation-item ${className} ${isExpanded ? 'expanded' : ''}`}>
              <div className="evaluation-header" onClick={() => toggleItem(idx)} style={{ cursor: 'pointer' }}>
                <span className="evaluation-icon">{icon}</span>
                <strong>{itemName}</strong>
                <span className="entity-id">({entityId})</span>
                <span className={`decision-badge ${finalDecision}`}>{finalDecision}</span>
                <button className="expand-toggle" type="button" style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer' }}>
                  {isExpanded ? '▼' : '▶'}
                </button>
              </div>
              
              {isExpanded && (
                <div className="evaluation-details">
                  {checks.length > 0 && (
                    <div className="checks-list">
                      {checks.map((check, checkIdx) => {
                        // Extract field name and value from check
                        const ruleName = check.rule || 'Unknown rule'
                        // Try to get field from check object first, then parse from rule name
                        const fieldName = check.field || (() => {
                          const fieldMatch = ruleName.match(/(\w+)\s*(>=|<=|==|>|<|contains|in|in \[)/i)
                          return fieldMatch ? fieldMatch[1] : ruleName
                        })()
                        const actualValue = check.field_value !== undefined ? String(check.field_value) : 
                                          (check.actual !== undefined ? String(check.actual) : 'N/A')
                        const expectedValue = check.expected || 'N/A'
                        
                        return (
                          <div key={checkIdx} className={`check-item ${check.passed ? 'passed' : 'failed'}`}>
                            <span className="check-rule">{ruleName}</span>
                            <span className="check-status">{check.passed ? '✓' : '✗'}</span>
                            <span className="check-field">Field: <strong>{fieldName}</strong></span>
                            <span className="check-expected">Expected: {expectedValue}</span>
                            <span className="check-actual">Actual: <strong>{actualValue}</strong></span>
                            {check.reason && <span className="check-reason">{check.reason}</span>}
                          </div>
                        )
                      })}
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
              )}
            </div>
          )
        })}
      </div>

      {hasMore && !showAll && (
        <button className="show-more-btn" onClick={() => setShowAll(true)} style={{ marginTop: '1rem', padding: '0.5rem 1rem', background: '#2563eb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          Show All {evaluations.length} Evaluations
        </button>
      )}
      
      {showAll && hasMore && (
        <button className="show-less-btn" onClick={() => setShowAll(false)} style={{ marginTop: '1rem', padding: '0.5rem 1rem', background: '#6b7280', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          Show Less (First {INITIAL_SHOW})
        </button>
      )}
    </div>
  )
}

export default ExecutionDetail

