import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Settings, Database, Server, Clock, Activity, CheckCircle, XCircle } from 'lucide-react';

export default function Dashboard() {
  const navigate = useNavigate();
  const [taskDesc, setTaskDesc] = useState('Build a Python REST API for managing student courses...');
  const [requirements, setRequirements] = useState('Users can create courses.\nUsers can retrieve courses.\nInvalid course IDs return a proper error.\nThe API must include tests.');
  const [useRag, setUseRag] = useState(false);
  const [useMemory, setUseMemory] = useState(false);
  const [provider, setProvider] = useState('groq');
  const [system, setSystem] = useState('MULTI_AGENT');
  const [runs, setRuns] = useState<any[]>([]);

  useEffect(() => {
    fetch('/api/runs')
      .then(r => r.json())
      .then(data => setRuns(data.runs || []))
      .catch(e => console.error(e));
  }, []);

  const handleStart = async () => {
    const reqList = requirements.split('\n').map(r => r.trim()).filter(r => r);
    const res = await fetch('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_description: taskDesc,
        requirements: reqList,
        use_rag: useRag,
        use_memory: useMemory,
        provider: provider,
        system: system
      })
    });
    if (res.ok) {
      const data = await res.json();
      navigate(`/runs/${data.run_id}`);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div className="lg:col-span-2 space-y-6">
        <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Play className="w-5 h-5 text-blue-400" /> Create DevAgents Run
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">System Architecture</label>
              <select 
                className="w-full bg-[#0f111a] border border-slate-700 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-blue-500"
                value={system}
                onChange={e => setSystem(e.target.value)}
              >
                <option value="MULTI_AGENT">Multi-Agent Workflow</option>
                <option value="SINGLE_AGENT_BASELINE">Single-Agent Baseline</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Task Description</label>
              <textarea 
                className="w-full h-32 bg-[#0f111a] border border-slate-700 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-blue-500"
                value={taskDesc}
                onChange={e => setTaskDesc(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Requirements (one per line)</label>
              <textarea 
                className="w-full h-32 bg-[#0f111a] border border-slate-700 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-blue-500"
                value={requirements}
                onChange={e => setRequirements(e.target.value)}
              />
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
              <div className="bg-[#0f111a] border border-slate-800 p-3 rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <Database className="w-4 h-4 text-purple-400" /> RAG
                </div>
                <input type="checkbox" checked={useRag} onChange={e => setUseRag(e.target.checked)} className="w-4 h-4" />
              </div>
              <div className="bg-[#0f111a] border border-slate-800 p-3 rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <Server className="w-4 h-4 text-green-400" /> Project Memory
                </div>
                <input type="checkbox" checked={useMemory} onChange={e => setUseMemory(e.target.checked)} className="w-4 h-4" />
              </div>
              <div className="bg-[#0f111a] border border-slate-800 p-3 rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <Settings className="w-4 h-4 text-slate-400" /> Provider
                </div>
                <select className="bg-transparent text-sm outline-none" value={provider} onChange={e => setProvider(e.target.value)}>
                  <option value="groq">Groq</option>
                  <option value="openrouter">OpenRouter</option>
                  <option value="mock">Mock</option>
                </select>
              </div>
            </div>

            <div className="pt-6">
              <button 
                onClick={handleStart}
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg transition-colors flex items-center gap-2"
              >
                Start Run <Play className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div className="space-y-6">
        <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl h-full">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" /> Run History
          </h2>
          <div className="space-y-3">
            {runs.length === 0 ? (
              <p className="text-slate-500 text-sm italic">No runs yet</p>
            ) : (
              runs.map((r, i) => (
                <div 
                  key={i} 
                  onClick={() => navigate(`/runs/${r.run_id}`)}
                  className="bg-[#0f111a] border border-slate-800 p-3 rounded-lg cursor-pointer hover:border-slate-600 transition-colors"
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-mono text-slate-400">{r.run_id}</span>
                    {r.final_status === 'VERIFIED' ? <CheckCircle className="w-4 h-4 text-emerald-500" /> : <Clock className="w-4 h-4 text-amber-500" />}
                  </div>
                  <div className="text-sm font-medium text-slate-300 truncate">
                    {r.status}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
