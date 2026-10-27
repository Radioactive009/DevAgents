import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Settings, Database, Server, Clock, Activity, CheckCircle, XCircle } from 'lucide-react';

export default function Dashboard() {
  const navigate = useNavigate();
  const [taskDesc, setTaskDesc] = useState('Build a Python calculator module with add, subtract, multiply, divide, division-by-zero handling, and pytest tests.');
  const [requirements, setRequirements] = useState('Implement add, subtract, multiply, and divide\nHandle division by zero with ValueError\nProvide full pytest test coverage');
  const [useRag, setUseRag] = useState(false);
  const [useMemory, setUseMemory] = useState(false);
  const [provider, setProvider] = useState('openrouter');
  const [system, setSystem] = useState('MULTI_AGENT');
  const [runs, setRuns] = useState<any[]>([]);

  useEffect(() => {
    fetch('/api/runs')
      .then(r => r.json())
      .then(data => setRuns(data.runs || []))
      .catch(e => console.error(e));
  }, []);

  const [humanApproval, setHumanApproval] = useState(false);
  const [modelName, setModelName] = useState('');

  const loadPreset = (type: string) => {
    if (type === 'python') {
      setTaskDesc('Build a Python calculator module with add, subtract, multiply, divide, division-by-zero handling, and pytest tests.');
      setRequirements('Implement add, subtract, multiply, and divide\nHandle division by zero with ValueError\nProvide full pytest test coverage');
    } else if (type === 'react') {
      setTaskDesc('Build a responsive web task management application where users can add tasks, edit task titles, mark tasks as completed, delete tasks, and filter between all, active, and completed tasks.');
      setRequirements('Generate index.html at root with clean modern styling and full interactive JavaScript\nAllow adding tasks, editing titles, toggling completion, and deleting tasks\nProvide task filtering for all, active, and completed\nInclude automated tests verifying task management functionality');
    } else if (type === 'string_utils') {
      setTaskDesc('Build a Python string utility module with reverse_string, is_palindrome, count_vowels, and comprehensive pytest tests.');
      setRequirements('Implement reverse_string(s: str) -> str\nImplement is_palindrome(s: str) -> bool (case-insensitive)\nImplement count_vowels(s: str) -> int\nInclude full pytest test coverage');
    }
  };

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
        model: modelName.trim() || undefined,
        system: system,
        human_approval: humanApproval
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
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800/80 mb-6 gap-3">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Play className="w-5 h-5 text-blue-400" /> Create DevAgents Run
            </h2>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400 font-medium">Quick Presets:</span>
              <button onClick={() => loadPreset('python')} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 transition-colors">Python Calc</button>
              <button onClick={() => loadPreset('react')} className="px-2.5 py-1 bg-blue-900/40 hover:bg-blue-800/50 text-blue-300 rounded border border-blue-500/30 transition-colors">Web Dashboard</button>
              <button onClick={() => loadPreset('string_utils')} className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 transition-colors">String Utils</button>
            </div>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">System Architecture</label>
              <select 
                className="w-full bg-[#0f111a] border border-slate-700 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-blue-500"
                value={system}
                onChange={e => setSystem(e.target.value)}
              >
                <option value="MULTI_AGENT">Multi-Agent Workflow (Supervisor, Arch, Code, Test, Debug, Verify)</option>
                <option value="SINGLE_AGENT_BASELINE">Single-Agent Baseline (Single LLM Iterative Feedback)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Task Description</label>
              <textarea 
                className="w-full h-28 bg-[#0f111a] border border-slate-700 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-blue-500 font-mono text-sm"
                value={taskDesc}
                onChange={e => setTaskDesc(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Requirements (one per line)</label>
              <textarea 
                className="w-full h-28 bg-[#0f111a] border border-slate-700 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-blue-500 font-mono text-sm"
                value={requirements}
                onChange={e => setRequirements(e.target.value)}
              />
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
              <div className="bg-[#0f111a] border border-slate-800 p-3 rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <Database className="w-4 h-4 text-purple-400" /> RAG Context
                </div>
                <input type="checkbox" checked={useRag} onChange={e => setUseRag(e.target.checked)} className="w-4 h-4 accent-purple-500 cursor-pointer" />
              </div>
              <div className="bg-[#0f111a] border border-slate-800 p-3 rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <Server className="w-4 h-4 text-green-400" /> Project Memory
                </div>
                <input type="checkbox" checked={useMemory} onChange={e => setUseMemory(e.target.checked)} className="w-4 h-4 accent-emerald-500 cursor-pointer" />
              </div>
              <div className="bg-[#0f111a] border border-slate-800 p-3 rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <CheckCircle className="w-4 h-4 text-amber-400" /> Human Approval
                </div>
                <input type="checkbox" checked={humanApproval} onChange={e => setHumanApproval(e.target.checked)} className="w-4 h-4 accent-amber-500 cursor-pointer" />
              </div>
              <div className="bg-[#0f111a] border border-slate-800 p-3 rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-slate-300">
                  <Settings className="w-4 h-4 text-slate-400" /> Provider
                </div>
                <select className="bg-transparent text-sm outline-none text-slate-200" value={provider} onChange={e => setProvider(e.target.value)}>
                  <option value="openrouter" className="bg-[#0f111a]">OpenRouter (Recommended)</option>
                  <option value="groq" className="bg-[#0f111a]">Groq</option>
                  <option value="gemini" className="bg-[#0f111a]">Gemini</option>
                  <option value="mock" className="bg-[#0f111a]">Mock (Deterministic)</option>
                </select>
              </div>
            </div>

            <div className="bg-[#0f111a]/60 border border-slate-800/80 p-3 rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="text-xs text-slate-400">
                <span className="font-semibold text-slate-300">Default Model: </span>
                {provider === 'openrouter' && <span className="font-mono text-emerald-400">nvidia/nemotron-3.5-lightning:free</span>}
                {provider === 'groq' && <span className="font-mono text-blue-400">qwen/qwen3.8-27b</span>}
                {provider === 'gemini' && <span className="font-mono text-purple-400">gemini-3.8-flash</span>}
                {provider === 'mock' && <span className="font-mono text-amber-400">deterministic-mock</span>}
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-slate-400 whitespace-nowrap">Model Override (optional):</label>
                <input 
                  type="text" 
                  placeholder="e.g. meta-llama/llama-3.3-70b-instruct" 
                  value={modelName} 
                  onChange={e => setModelName(e.target.value)}
                  className="bg-[#161925] border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 font-mono w-64 focus:outline-none focus:border-blue-500" 
                />
              </div>
            </div>

            <div className="pt-4 flex items-center justify-between">
              <button 
                onClick={handleStart}
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-6 rounded-lg transition-all duration-200 flex items-center gap-2 shadow-lg shadow-blue-600/30 active:scale-95"
              >
                Launch DevAgents Workflow <Play className="w-4 h-4 fill-white" />
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
