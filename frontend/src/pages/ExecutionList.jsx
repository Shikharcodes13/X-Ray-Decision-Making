import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { XRayAPI } from '../api'
import './ExecutionList.css'

function ExecutionList() {
  const [executions, setExecutions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadExecutions()
  }, [])

  const loadExecutions = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await XRayAPI.listExecutions()
      setExecutions(data)
    } catch (err) {
      setError(err.message || 'Failed to load executions')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="execution-list">
        <div className="loading">Loading executions...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="execution-list">
        <div className="error">
          <p>Error: {error}</p>
          <button onClick={loadExecutions}>Retry</button>
        </div>
      </div>
    )
  }

  if (executions.length === 0) {
    return (
      <div className="execution-list">
        <div className="empty-state">
          <h2>No executions yet</h2>
          <p>Run a demo application or use the Run Workflow page to see X-Ray data here</p>
        </div>
      </div>
    )
  }

  return (
    <div className="execution-list">
      <div className="executions-container">
        {executions.map((exec, idx) => {
          // Support both canonical and legacy formats
          const execId = exec.id || exec.execution_id
          const execName = exec.name || exec.metadata?.workflow || exec.metadata?.name || 'Unnamed Execution'
          const metadata = exec.metadata || {}
          const totalSteps = exec.steps?.length || metadata.total_steps || 0
          const dateStr = exec.started_at || metadata.started_at || exec.created_at || new Date().toISOString()
          const startedAt = new Date(dateStr).toLocaleString()
          
          return (
            <div
              key={execId || idx}
              className="execution-item"
              onClick={() => execId && navigate(`/execution/${execId}`)}
            >
              <div className="execution-header">
                <div className="execution-name">{execName}</div>
                <div className="execution-id">{execId ? execId.substring(0, 8) + '...' : 'N/A'}</div>
                <div className="execution-time">{startedAt}</div>
              </div>
              <div className="execution-stats">
                <div className="stat">
                  <div className="stat-label">Steps</div>
                  <div>{totalSteps}</div>
                </div>
                <div className="stat">
                  <div className="stat-label">Workflow</div>
                  <div>{execName}</div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ExecutionList

