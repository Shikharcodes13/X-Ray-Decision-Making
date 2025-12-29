/**
 * API client for X-Ray dashboard
 */

const API_BASE = '/api'

export class XRayAPI {
  /**
   * List all executions
   */
  static async listExecutions(limit = 100) {
    const response = await fetch(`${API_BASE}/executions?limit=${limit}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch executions: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Get a specific execution by ID
   */
  static async getExecution(executionId) {
    const response = await fetch(`${API_BASE}/executions/${executionId}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch execution: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Get rules configuration
   */
  static async getRules() {
    const response = await fetch(`${API_BASE}/rules`)
    if (!response.ok) {
      return null // Rules are optional
    }
    return response.json()
  }

  /**
   * Set rules configuration
   */
  static async setRules(rules, format = 'json') {
    const response = await fetch(`${API_BASE}/rules`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        rules: rules,
        format: format
      })
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || error.error || 'Failed to set rules')
    }
    return response.json()
  }

  /**
   * Run workflow with rules and input data
   */
  static async runWorkflow(rules, rulesFormat, inputData) {
    const response = await fetch(`${API_BASE}/workflow/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        rules: rules,
        rules_format: rulesFormat,
        input_data: inputData
      })
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || error.error || 'Failed to run workflow')
    }
    return response.json()
  }

  /**
   * Upload a dataset file (CSV, Excel, JSON)
   */
  static async uploadDataset(file) {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch(`${API_BASE}/datasets/upload`, {
      method: 'POST',
      body: formData
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || error.error || 'Failed to upload dataset')
    }
    return response.json()
  }

  /**
   * List all datasets
   */
  static async listDatasets() {
    const response = await fetch(`${API_BASE}/datasets`)
    if (!response.ok) {
      throw new Error(`Failed to fetch datasets: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Get a specific dataset
   */
  static async getDataset(datasetId) {
    const response = await fetch(`${API_BASE}/datasets/${datasetId}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch dataset: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Create or update a workflow
   */
  static async saveWorkflow(workflow) {
    const response = await fetch(`${API_BASE}/workflows`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(workflow)
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || error.error || 'Failed to save workflow')
    }
    return response.json()
  }

  /**
   * List all workflows
   */
  static async listWorkflows() {
    const response = await fetch(`${API_BASE}/workflows`)
    if (!response.ok) {
      throw new Error(`Failed to fetch workflows: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Get a specific workflow
   */
  static async getWorkflow(workflowId) {
    const response = await fetch(`${API_BASE}/workflows/${workflowId}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch workflow: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * Execute a workflow on a dataset
   */
  static async executeWorkflow(workflowId, datasetId, executionName) {
    const response = await fetch(`${API_BASE}/workflows/${workflowId}/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        dataset_id: datasetId,
        execution_name: executionName
      })
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || error.error || 'Failed to execute workflow')
    }
    return response.json()
  }
}

