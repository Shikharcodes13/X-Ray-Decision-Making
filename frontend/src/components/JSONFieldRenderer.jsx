import { useState } from 'react'
import './JSONFieldRenderer.css'

/**
 * Component to render JSON objects as structured form fields
 * Supports nested objects, arrays, and various data types
 */
export function JSONFieldRenderer({ data, title, readOnly = true, onDataChange }) {
  const [expanded, setExpanded] = useState(true)
  const [collapsedPaths, setCollapsedPaths] = useState(new Set())

  // Handle null, undefined, or non-object primitives
  if (data === null || data === undefined) {
    return (
      <div className="json-field-renderer">
        {title && <div className="json-section-title">{title}</div>}
        <div className="json-value-simple">null</div>
      </div>
    )
  }

  if (typeof data !== 'object' || data instanceof Date) {
    return (
      <div className="json-field-renderer">
        {title && <div className="json-section-title">{title}</div>}
        <div className="json-value-simple">{String(data)}</div>
      </div>
    )
  }

  const togglePath = (path) => {
    const newCollapsed = new Set(collapsedPaths)
    if (newCollapsed.has(path)) {
      newCollapsed.delete(path)
    } else {
      newCollapsed.add(path)
    }
    setCollapsedPaths(newCollapsed)
  }

  const renderValue = (value, path = '', depth = 0) => {
    if (value === null || value === undefined) {
      return <span className="json-null">null</span>
    }

    if (typeof value === 'boolean') {
      return <span className={`json-boolean ${value ? 'true' : 'false'}`}>{String(value)}</span>
    }

    if (typeof value === 'number') {
      return <span className="json-number">{value}</span>
    }

    if (typeof value === 'string') {
      // Check if it's a date string
      if (/^\d{4}-\d{2}-\d{2}/.test(value) && !isNaN(Date.parse(value))) {
        return <span className="json-date">{new Date(value).toLocaleString()}</span>
      }
      // Check if it's a URL
      if (value.startsWith('http://') || value.startsWith('https://')) {
        return <a href={value} target="_blank" rel="noopener noreferrer" className="json-link">{value}</a>
      }
      return <span className="json-string">"{value}"</span>
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="json-empty">[] (empty array)</span>
      }
      
      const isCollapsed = collapsedPaths.has(path)
      return (
        <div className="json-array">
          <button 
            className="json-toggle" 
            onClick={() => togglePath(path)}
            type="button"
          >
            {isCollapsed ? '▶' : '▼'} Array ({value.length} items)
          </button>
          {!isCollapsed && (
            <div className="json-array-items">
              {value.map((item, idx) => (
                <div key={idx} className="json-array-item">
                  <span className="json-array-index">[{idx}]</span>
                  <div className="json-array-value">
                    {renderValue(item, `${path}[${idx}]`, depth + 1)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    if (typeof value === 'object') {
      const keys = Object.keys(value)
      if (keys.length === 0) {
        return <span className="json-empty">{} (empty object)</span>
      }

      const isCollapsed = collapsedPaths.has(path)
      return (
        <div className="json-object">
          <button 
            className="json-toggle" 
            onClick={() => togglePath(path)}
            type="button"
          >
            {isCollapsed ? '▶' : '▼'} Object ({keys.length} {keys.length === 1 ? 'field' : 'fields'})
          </button>
          {!isCollapsed && (
            <div className="json-object-fields">
              {keys.map((key) => {
                const fieldPath = path ? `${path}.${key}` : key
                const fieldValue = value[key]
                const isNested = typeof fieldValue === 'object' && fieldValue !== null && !Array.isArray(fieldValue)
                const isArray = Array.isArray(fieldValue)
                
                return (
                  <div key={key} className="json-field" style={{ marginLeft: `${depth * 16}px` }}>
                    <div className="json-field-header">
                      <span className="json-field-key">{key}:</span>
                      {isNested && (
                        <button 
                          className="json-toggle-inline" 
                          onClick={() => togglePath(fieldPath)}
                          type="button"
                        >
                          {collapsedPaths.has(fieldPath) ? '▶' : '▼'}
                        </button>
                      )}
                    </div>
                    <div className="json-field-value">
                      {isNested && collapsedPaths.has(fieldPath) ? (
                        <span className="json-collapsed-preview">
                          {Object.keys(fieldValue).length} {Object.keys(fieldValue).length === 1 ? 'field' : 'fields'}
                        </span>
                      ) : (
                        renderValue(fieldValue, fieldPath, depth + 1)
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )
    }

    return <span>{String(value)}</span>
  }

  return (
    <div className="json-field-renderer">
      {title && (
        <div className="json-section-header">
          <div className="json-section-title">{title}</div>
          <button 
            className="json-expand-toggle" 
            onClick={() => setExpanded(!expanded)}
            type="button"
          >
            {expanded ? '▼' : '▶'}
          </button>
        </div>
      )}
      {expanded && (
        <div className="json-content">
          {renderValue(data)}
        </div>
      )}
    </div>
  )
}

export default JSONFieldRenderer

