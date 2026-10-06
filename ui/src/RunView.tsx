import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle, Clock, XCircle, Activity, Code, Server, Database } from 'lucide-react';

export default function RunView() {
  const { runId } = useParams();
  const [events, setEvents] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [runInfo, setRunInfo] = useState<any>(null);

  const [files, setFiles] = useState<any>({});
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  useEffect(() => {
    // Poll for events and metrics
    const interval = setInterval(() => {
      fetch(`/api/runs/${runId}/events`)
        .then(r => r.json())
        .then(data => setEvents(data.events || []));
        
      fetch(`/api/runs/${runId}`)
        .then(r => r.json())
        .then(data => setRunInfo(data));

      fetch(`/api/runs/${runId}/metrics`)
        .then(r => { if (r.ok) return r.json(); return null; })
        .then(data => { if (data) setMetrics(data); });

      fetch(`/api/runs/${runId}/project`)
        .then(r => { if (r.ok) return r.json(); return null; })
        .then(data => { if (data && data.files) setFiles(data.files); });
    }, 1000);
    return () => clearInterval(interval);
  }, [runId]);

  const pipeline = ["supervisor", "architecture", "coding", "testing", "debugging", "verification"];
  
  const getAgentStatus = (agentName: string) => {
    const starts = events.filter(e => e.event_type === 'agent' && e.agent_name?.toLowerCase() === agentName && e.action === 'started');
    const ends = events.filter(e => e.event_type === 'agent' && e.agent_name?.toLowerCase() === agentName && e.action === 'completed');
    if (ends.length > 0) return { status: 'COMPLETED', duration: ends[0].duration_s };
    if (starts.length > 0) return { status: 'RUNNING', duration: null };
    return { status: 'WAITING', duration: null };
  };

  const getTestResults = () => events.filter(e => e.event_type === 'test').pop();
  const getDebugIterations = () => events.filter(e => e.event_type === 'debug');
  const getVerification = () => events.filter(e => e.event_type === 'verification').pop();
  const getTools = () => events.filter(e => e.event_type === 'tool');

  return (
    <div className="space-y-6">
      <Link to="/" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Dashboard
      </Link>
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 space-y-6">
          
          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Activity className="w-5 h-5 text-emerald-400" /> Pipeline Status
            </h2>
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
              {pipeline.map((agent) => {
                const { status } = getAgentStatus(agent);
                return (
                  <div key={agent} className="flex flex-col items-center gap-2 w-full">
                    <div className={`w-full text-center py-3 px-4 rounded-lg border font-medium text-sm transition-colors ${
                      status === 'COMPLETED' ? 'bg-emerald-900/20 border-emerald-500/50 text-emerald-400' :
                      status === 'RUNNING' ? 'bg-blue-900/20 border-blue-500/50 text-blue-400 animate-pulse' :
                      'bg-[#0f111a] border-slate-800 text-slate-500'
                    }`}>
                      {agent.charAt(0).toUpperCase() + agent.slice(1)}
                    </div>
                    {status === 'COMPLETED' && <CheckCircle className="w-4 h-4 text-emerald-500" />}
                    {status === 'RUNNING' && <Clock className="w-4 h-4 text-blue-400" />}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
              <h2 className="text-lg font-bold mb-4">Test Results</h2>
              {(() => {
                const t = getTestResults();
                if (!t) return <p className="text-sm text-slate-500">Waiting for tests...</p>;
                return (
                  <div className="space-y-3">
                    <div className={`text-xl font-bold ${t.success ? 'text-emerald-400' : 'text-red-400'}`}>{t.success ? 'PASSED' : 'FAILED'}</div>
                    <div className="grid grid-cols-2 gap-4 text-sm text-slate-300">
                      <div>Pass Rate: <span className="text-white font-medium">{Math.round(t.test_pass_rate * 100)}%</span></div>
                      <div>Duration: <span className="text-white font-medium">{t.duration_ms ? (t.duration_ms / 1000).toFixed(2) : 'N/A'}s</span></div>
                    </div>
                  </div>
                );
              })()}
            </div>

            <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
              <h2 className="text-lg font-bold mb-4">Debugging Iterations</h2>
              <div className="space-y-3 max-h-48 overflow-y-auto">
                {getDebugIterations().length === 0 && <p className="text-sm text-slate-500">No debugging required yet.</p>}
                {getDebugIterations().map((d, i) => (
                  <div key={i} className="bg-[#0f111a] border border-slate-800 rounded p-3 text-sm">
                    <div className="font-medium text-slate-300 mb-1">Iteration {d.iteration}</div>
                    <div className={`text-xs mt-1 ${d.success ? 'text-emerald-400' : 'text-red-400'}`}>
                      {d.success ? 'Fixed' : 'Failed'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-lg font-bold mb-4">Final Verification</h2>
            {(() => {
              const v = getVerification();
              if (!v) return <p className="text-sm text-slate-500">Waiting for verification...</p>;
              return (
                <div className="space-y-4">
                  <div className={`text-2xl font-bold ${v.status === 'VERIFIED' ? 'text-emerald-400' : v.status === 'PARTIALLY_VERIFIED' ? 'text-amber-400' : 'text-red-400'}`}>
                    {v.status}
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2">
                    <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${v.requirement_coverage * 100}%` }}></div>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm text-slate-300 pt-2">
                    <div>Coverage: <span className="text-white font-medium">{Math.round(v.requirement_coverage * 100)}%</span></div>
                  </div>
                </div>
              );
            })()}
          </div>

          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2"><Code className="w-5 h-5" /> Code Explorer</h2>
            {Object.keys(files).length === 0 ? (
              <p className="text-sm text-slate-500">Waiting for project generation...</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 border border-slate-700 rounded-lg overflow-hidden h-96">
                <div className="col-span-1 bg-[#0f111a] border-r border-slate-700 p-2 overflow-y-auto">
                  {Object.keys(files).map(filename => (
                    <div 
                      key={filename} 
                      onClick={() => setSelectedFile(filename)}
                      className={`cursor-pointer p-2 text-sm rounded ${selectedFile === filename ? 'bg-blue-900/30 text-blue-400' : 'text-slate-300 hover:bg-slate-800'}`}
                    >
                      {filename}
                    </div>
                  ))}
                </div>
                <div className="col-span-3 bg-[#0a0c10] p-4 overflow-y-auto text-sm font-mono text-slate-300 whitespace-pre">
                  {selectedFile ? files[selectedFile] : 'Select a file'}
                </div>
              </div>
            )}
          </div>

          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2"><Activity className="w-5 h-5" /> Tool Activity</h2>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {getTools().length === 0 && <p className="text-sm text-slate-500">No tool activity.</p>}
              {getTools().map((t, i) => (
                <div key={i} className="bg-[#0f111a] border border-slate-800 p-3 rounded flex justify-between items-center">
                  <div className="text-sm text-slate-300">{t.tool_name}</div>
                  <div className={`text-xs ${t.success ? 'text-emerald-400' : 'text-red-400'}`}>{t.success ? 'Success' : 'Failed'}</div>
                </div>
              ))}
            </div>
          </div>

        </div>
        
        <div className="space-y-6">
          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-sm font-bold text-slate-400 uppercase mb-4">Run Metrics</h2>
            {metrics ? (
              <div className="space-y-4 text-sm">
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Duration</span>
                  <span className="text-white">{metrics.run_duration ? `${metrics.run_duration.toFixed(1)}s` : 'N/A'}</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">LLM Calls</span>
                  <span className="text-white">{metrics.total_llm_calls}</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Tokens</span>
                  <span className="text-white">{metrics.total_tokens || 'N/A'}</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Tool Calls</span>
                  <span className="text-white">{metrics.total_tool_calls}</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">RAG Queries</span>
                  <span className="text-white">{metrics.total_rag_queries}</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">Loading metrics...</p>
            )}
          </div>
          
          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-sm font-bold text-slate-400 uppercase mb-4">Configuration</h2>
            {runInfo ? (
              <div className="space-y-2 text-sm text-slate-300">
                <div>Model: <span className="text-white">{runInfo.model}</span></div>
                <div>RAG: <span className="text-white">{runInfo.configuration?.use_rag ? 'ENABLED' : 'DISABLED'}</span></div>
                <div>Memory: <span className="text-white">{runInfo.configuration?.use_memory ? 'ENABLED' : 'DISABLED'}</span></div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">Loading...</p>
            )}
          </div>

          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl max-h-96 overflow-y-auto">
            <h2 className="text-sm font-bold text-slate-400 uppercase mb-4">Event Timeline</h2>
            <div className="space-y-4">
              {events.slice().reverse().map((e, i) => (
                <div key={i} className="text-xs border-l-2 border-slate-700 pl-3 py-1">
                  <div className="text-slate-500 mb-1">{new Date(e.timestamp).toLocaleTimeString()}</div>
                  <div className="text-slate-300 font-medium">
                    {e.event_type.toUpperCase()}
                  </div>
                  {e.agent_name && <div className="text-slate-400 mt-1">{e.agent_name} {e.action}</div>}
                  {e.tool_name && <div className="text-slate-400 mt-1">Used {e.tool_name}</div>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
