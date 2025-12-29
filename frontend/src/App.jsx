import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import ExecutionList from './pages/ExecutionList'
import ExecutionDetail from './pages/ExecutionDetail'
import RunWorkflow from './pages/RunWorkflow'
import DataUpload from './pages/DataUpload'
import WorkflowBuilder from './pages/WorkflowBuilder'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <div className="container">
            <Link to="/" className="logo">
              <h1>🔍 X-Ray Dashboard</h1>
            </Link>
            <nav>
              <Link to="/">Executions</Link>
              <Link to="/data-upload">Upload Data</Link>
              <Link to="/workflow-builder">Workflow Builder</Link>
              <Link to="/run-workflow">Run Workflow</Link>
            </nav>
          </div>
        </header>
        
        <main className="app-main">
          <div className="container">
            <Routes>
              <Route path="/" element={<ExecutionList />} />
              <Route path="/execution/:executionId" element={<ExecutionDetail />} />
              <Route path="/data-upload" element={<DataUpload />} />
              <Route path="/workflow-builder" element={<WorkflowBuilder />} />
              <Route path="/run-workflow" element={<RunWorkflow />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App

