import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './Dashboard';
import RunView from './RunView';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-[#0f111a] text-slate-200 font-sans">
        <header className="border-b border-slate-800 bg-[#161925] p-4">
          <div className="container mx-auto">
            <h1 className="text-2xl font-bold tracking-tight text-white">DEVAGENTS</h1>
            <p className="text-sm text-slate-400">Multi-Agent Software Engineering System</p>
          </div>
        </header>
        <main className="container mx-auto p-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/runs/:runId" element={<RunView />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
