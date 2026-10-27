import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, CheckCircle, Clock, XCircle, Activity, Code, Server, 
  Database, Globe, ExternalLink, RefreshCw, AlertTriangle, ShieldCheck,
  GitBranch, UploadCloud, RotateCw, CheckCircle2
} from 'lucide-react';

export default function RunView() {
  const { runId } = useParams();
  const [events, setEvents] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [runInfo, setRunInfo] = useState<any>(null);
  const [runState, setRunState] = useState<any>(null);
  const [previewStatus, setPreviewStatus] = useState<any>(null);
  const [deployment, setDeployment] = useState<any>(null);
  const [isDeploying, setIsDeploying] = useState<boolean>(false);
  const [deployMock, setDeployMock] = useState<boolean>(false);
  const [deployPrivate, setDeployPrivate] = useState<boolean>(true);

  const [files, setFiles] = useState<any>({});
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'code' | 'preview'>('code');
  const [approvalFeedback, setApprovalFeedback] = useState<string>('');
  const [isSubmittingApproval, setIsSubmittingApproval] = useState<boolean>(false);
  const [iframeKey, setIframeKey] = useState<number>(0);

  useEffect(() => {
    // Poll for events, metrics, state, project files, and preview status
    const interval = setInterval(() => {
      fetch(`/api/runs/${runId}/events`)
        .then(r => r.json())
        .then(data => setEvents(data.events || []))
        .catch(() => {});
        
      fetch(`/api/runs/${runId}`)
        .then(r => r.json())
        .then(data => setRunInfo(data))
        .catch(() => {});

      fetch(`/api/runs/${runId}/state`)
        .then(r => { if (r.ok) return r.json(); return null; })
        .then(data => { if (data) setRunState(data); })
        .catch(() => {});

      fetch(`/api/runs/${runId}/metrics`)
        .then(r => { if (r.ok) return r.json(); return null; })
        .then(data => { if (data) setMetrics(data); })
        .catch(() => {});

      fetch(`/api/runs/${runId}/project`)
        .then(r => { if (r.ok) return r.json(); return null; })
        .then(data => { 
          if (data && data.files) {
            setFiles(data.files);
            // Auto-select first file if none selected
            setSelectedFile(prev => prev || Object.keys(data.files)[0] || null);
          }
        })
        .catch(() => {});

      fetch(`/api/runs/${runId}/preview-status`)
        .then(r => { if (r.ok) return r.json(); return null; })
        .then(data => { 
          if (data) {
            setPreviewStatus(data);
            // If preview becomes ready and activeTab is code, optionally surface preview
            if (data.has_preview && !selectedFile) {
              setActiveTab('preview');
            }
          }
        })
        .catch(() => {});

      fetch(`/api/runs/${runId}/deployment`)
        .then(r => { if (r.ok) return r.json(); return null; })
        .then(data => { if (data) setDeployment(data); })
        .catch(() => {});
    }, 1000);
    return () => clearInterval(interval);
  }, [runId]);

  const handleDeploy = async () => {
    setIsDeploying(true);
    try {
      await fetch(`/api/runs/${runId}/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_private: deployPrivate, use_mock: deployMock })
      });
      const r = await fetch(`/api/runs/${runId}/deployment`);
      if (r.ok) {
        const data = await r.json();
        setDeployment(data);
      }
    } catch (e) {
      console.error("Deploy trigger failed:", e);
    } finally {
      setIsDeploying(false);
    }
  };

  const handleApprovalDecision = async (decision: 'APPROVE' | 'REJECT') => {
    setIsSubmittingApproval(true);
    try {
      await fetch(`/api/runs/${runId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, feedback: approvalFeedback })
      });
      // Fetch state immediately
      const r = await fetch(`/api/runs/${runId}/state`);
      if (r.ok) {
        const s = await r.json();
        setRunState(s);
      }
    } catch (e) {
      console.error("Approval error:", e);
    } finally {
      setIsSubmittingApproval(false);
    }
  };

  const pipeline = ["supervisor", "architecture", "coding", "testing", "debugging", "verification"];
  
  const getAgentStatus = (agentName: string) => {
    const pipelineOrder = ["supervisor", "architecture", "coding", "testing", "debugging", "verification"];
    const myIdx = pipelineOrder.indexOf(agentName);

    const hasLaterEvent = events.some(e => {
      let otherIdx = -1;
      if (e.event_type === 'test') otherIdx = 3;
      else if (e.event_type === 'debug') otherIdx = 4;
      else if (e.event_type === 'verification' || e.phase === 'verification') otherIdx = 5;
      else if (e.event_type === 'agent') {
        const name = (e.agent_name || e.phase || '').toLowerCase();
        if (name.includes('supervisor')) otherIdx = 0;
        else if (name.includes('architecture')) otherIdx = 1;
        else if (name.includes('coding')) otherIdx = 2;
        else if (name.includes('test')) otherIdx = 3;
        else if (name.includes('debug')) otherIdx = 4;
        else if (name.includes('verif')) otherIdx = 5;
      }
      return otherIdx > myIdx;
    });

    const matching = events.filter(e => {
      if (agentName === 'testing') return e.event_type === 'test';
      if (agentName === 'debugging') return e.event_type === 'debug';
      if (agentName === 'verification') return e.event_type === 'verification' || e.phase === 'verification';
      return (e.event_type === 'agent' && (
        (e.agent_name && e.agent_name.toLowerCase().includes(agentName)) || 
        (e.phase && e.phase.toLowerCase().includes(agentName))
      ));
    });

    if (matching.length === 0) {
      if (hasLaterEvent) return { status: 'COMPLETED', duration: null };
      return { status: 'WAITING', duration: null };
    }

    const latest = matching[matching.length - 1];
    if (latest.success === true || latest.status === 'VERIFIED') {
      return { status: 'COMPLETED', duration: latest.duration_ms ? latest.duration_ms / 1000 : null };
    }

    if (agentName === 'testing') {
      return { status: 'COMPLETED', duration: latest.duration_ms ? latest.duration_ms / 1000 : null };
    }

    if (agentName === 'debugging') {
      return { status: latest.success ? 'COMPLETED' : 'FAILED', duration: null };
    }

    if (hasLaterEvent) {
      return { status: 'COMPLETED', duration: null };
    }

    if (latest.success === false) {
      return { status: 'FAILED', duration: null };
    }

    return { status: 'RUNNING', duration: null };
  };

  const getTestResults = () => events.filter(e => e.event_type === 'test').pop();
  const getDebugIterations = () => events.filter(e => e.event_type === 'debug');
  const getVerification = () => events.filter(e => e.event_type === 'verification').pop();
  const getTools = () => events.filter(e => e.event_type === 'tool');

  const isPendingApproval = runState?.approval_status === 'PENDING_APPROVAL';

  const errorEvent = events.slice().reverse().find(e => e.event_type === 'error' || e.error_message || (e.event_type === 'agent' && e.success === false));
  const eventError = errorEvent ? (errorEvent.message || errorEvent.error_message || errorEvent.error_info || errorEvent.action) : null;

  const isRunning = runInfo?.status === 'RUNNING';

  const errorMessage = !isRunning ? (
    runInfo?.error || 
    runState?.metadata?.coding_error || 
    runState?.metadata?.supervisor_error || 
    runState?.metadata?.architecture_error || 
    runState?.metadata?.testing_error || 
    eventError ||
    (runInfo?.status === 'FAILED' || runInfo?.final_status === 'ERROR' ? (runInfo?.final_status || 'Pipeline execution encountered a failure.') : null)
  ) : null;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <Link to="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm">
        <ArrowLeft className="w-4 h-4" /> Back to Dashboard
      </Link>

      {/* Human Approval Checkpoint Banner (Phase 5) */}
      {isPendingApproval && (
        <div className="bg-amber-950/40 border border-amber-500/60 rounded-xl p-6 shadow-2xl animate-pulse-subtle">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-amber-400 font-bold text-lg">
                <AlertTriangle className="w-5 h-5" /> Human Approval Checkpoint (Phase 5)
              </div>
              <p className="text-slate-300 text-sm">
                ArchitectureAgent has generated the proposed software architecture. Code generation is paused waiting for your review.
              </p>
              {runState?.architecture && (
                <div className="mt-3 bg-[#0a0c10] border border-amber-500/30 rounded-lg p-3 text-xs font-mono text-slate-300 space-y-1">
                  <div className="text-amber-300 font-bold">Planned Components:</div>
                  {runState.architecture.components?.map((c: any, i: number) => (
                    <div key={i} className="pl-2">
                      • <span className="text-white font-medium">{c.name}</span>: {c.responsibility}
                    </div>
                  ))}
                </div>
              )}
              <div className="pt-2">
                <input 
                  type="text" 
                  placeholder="Optional review notes or guidance for CodingAgent..."
                  value={approvalFeedback}
                  onChange={e => setApprovalFeedback(e.target.value)}
                  className="w-full bg-[#0a0c10] border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:border-amber-400"
                />
              </div>
            </div>
            <div className="flex flex-col gap-2 shrink-0">
              <button 
                onClick={() => handleApprovalDecision('APPROVE')}
                disabled={isSubmittingApproval}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-4 py-2 rounded-lg text-sm transition-colors flex items-center gap-1.5 shadow-lg shadow-emerald-700/30"
              >
                <ShieldCheck className="w-4 h-4" /> Approve Architecture
              </button>
              <button 
                onClick={() => handleApprovalDecision('REJECT')}
                disabled={isSubmittingApproval}
                className="bg-red-800/80 hover:bg-red-700 text-red-100 font-medium px-4 py-2 rounded-lg text-sm transition-colors flex items-center gap-1.5"
              >
                <XCircle className="w-4 h-4" /> Reject & Abort
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Pipeline Error Banner */}
      {errorMessage && (
        <div className="bg-red-950/40 border border-red-500/60 rounded-xl p-5 shadow-2xl backdrop-blur-sm">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
            <div className="space-y-2 w-full">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-red-200 text-base">Pipeline Execution Halted</h3>
                <span className="text-xs bg-red-900/60 text-red-300 border border-red-700/60 px-2.5 py-0.5 rounded-full font-mono">
                  {runInfo?.final_status || 'EXECUTION_FAILED'}
                </span>
              </div>
              <p className="text-sm text-red-300 font-mono bg-black/50 p-3 rounded-lg border border-red-900/50 break-words whitespace-pre-wrap max-h-48 overflow-y-auto">
                {String(errorMessage)}
              </p>
              <div className="text-xs text-red-300/80 flex flex-wrap gap-2 items-center pt-1">
                <span className="font-medium text-red-200">Troubleshooting:</span>
                <span>If this is a TPM limit or 401 error, try switching to <strong>OpenRouter</strong> or <strong>Mock</strong> on the Dashboard.</span>
              </div>
            </div>
          </div>
        </div>
      )}
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 space-y-6">
          
          {/* Multi-Agent Pipeline Status */}
          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Activity className="w-5 h-5 text-emerald-400" /> Multi-Agent Pipeline Status
            </h2>
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
              {pipeline.map((agent) => {
                const { status } = getAgentStatus(agent);
                return (
                  <div key={agent} className="flex flex-col items-center gap-2 w-full">
                    <div className={`w-full text-center py-3 px-4 rounded-lg border font-medium text-sm transition-all duration-300 ${
                      status === 'COMPLETED' ? 'bg-emerald-900/20 border-emerald-500/50 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)]' :
                      status === 'RUNNING' ? 'bg-blue-900/30 border-blue-400 text-blue-300 shadow-[0_0_20px_rgba(59,130,246,0.8)] scale-105' :
                      status === 'FAILED' ? 'bg-red-950/40 border-red-500/60 text-red-400 shadow-[0_0_15px_rgba(239,68,68,0.3)]' :
                      'bg-[#0f111a] border-slate-800 text-slate-500'
                    }`}>
                      {agent.charAt(0).toUpperCase() + agent.slice(1)}
                    </div>
                    {status === 'COMPLETED' && <CheckCircle className="w-4 h-4 text-emerald-500" />}
                    {status === 'RUNNING' && <Clock className="w-4 h-4 text-blue-400 animate-spin" />}
                    {status === 'FAILED' && <XCircle className="w-4 h-4 text-red-500" />}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Test Results */}
            <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
              <h2 className="text-lg font-bold mb-4">Test Execution & Diagnostics</h2>
              {(() => {
                const t = getTestResults();
                if (!t) return <p className="text-sm text-slate-500">Waiting for sandbox test execution...</p>;
                return (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className={`text-xl font-bold ${t.success ? 'text-emerald-400' : 'text-red-400'}`}>
                        {t.success ? 'PASSED' : 'FAILED'}
                      </div>
                      {t.failure_category && (
                        <span className="px-2.5 py-1 text-xs rounded-full bg-slate-800 border border-slate-700 text-amber-300 font-mono">
                          {t.failure_category}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm text-slate-300 pt-1">
                      <div>Pass Rate: <span className="text-white font-medium">{Math.round((t.test_pass_rate || 0) * 100)}%</span></div>
                      <div>Duration: <span className="text-white font-medium">{t.duration_ms ? (t.duration_ms / 1000).toFixed(2) : 'N/A'}s</span></div>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Debugging Iterations */}
            <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
              <h2 className="text-lg font-bold mb-4">Autonomous Debugging Cycles</h2>
              <div className="space-y-3 max-h-48 overflow-y-auto">
                {getDebugIterations().length === 0 && <p className="text-sm text-slate-500">No debugging required yet.</p>}
                {getDebugIterations().map((d, i) => (
                  <div key={i} className="bg-[#0f111a] border border-slate-800 rounded p-3 text-sm flex justify-between items-center">
                    <div>
                      <div className="font-medium text-slate-300">Cycle {d.iteration}</div>
                      <div className="text-xs text-slate-500">Automated AST code patch</div>
                    </div>
                    <div className={`text-xs px-2 py-0.5 rounded font-medium ${d.success ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-red-950 text-red-400 border border-red-800'}`}>
                      {d.success ? 'Patch Applied' : 'Patch Failed'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Final Verification */}
          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-lg font-bold mb-4">Final Verification & Acceptance</h2>
            {(() => {
              const v = getVerification();
              if (!v) {
                if (runInfo?.status === 'FAILED' || runInfo?.status === 'ERROR') {
                  return (
                    <div className="space-y-2">
                      <div className="text-2xl font-bold text-red-400">FAILED</div>
                      <p className="text-sm text-slate-400">Run terminated with errors during execution.</p>
                    </div>
                  );
                }
                return <p className="text-sm text-slate-500">Waiting for evidence-based verification...</p>;
              }
              return (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className={`text-2xl font-bold ${v.status === 'VERIFIED' ? 'text-emerald-400' : v.status === 'PARTIALLY_VERIFIED' ? 'text-amber-400' : 'text-red-400'}`}>
                      {v.status}
                    </div>
                    <div className="text-xs px-2.5 py-1 bg-slate-800 rounded text-slate-300">
                      Evidence-backed
                    </div>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                    <div className="bg-emerald-500 h-2.5 rounded-full transition-all duration-500" style={{ width: `${(v.requirement_coverage || 0) * 100}%` }}></div>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm text-slate-300 pt-1">
                    <div>Requirement Coverage: <span className="text-white font-medium">{Math.round((v.requirement_coverage || 0) * 100)}%</span></div>
                  </div>
                </div>
              );
            })()}
          </div>

          {/* Autonomous Cloud Deployment & DevOps Card (Phases 1-8) */}
          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    Cloud Deployment & DevOps
                    {deployment?.record?.stage && (
                      <span className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-medium ${
                        deployment.record.stage === 'HEALTH_CHECK_PASSED' || deployment.record.stage === 'DEPLOYMENT_READY'
                          ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-700/60'
                          : deployment.record.stage.includes('FAILED')
                          ? 'bg-red-950/80 text-red-400 border border-red-700/60'
                          : 'bg-blue-950/80 text-blue-300 border border-blue-700/60 animate-pulse'
                      }`}>
                        {deployment.record.stage}
                      </span>
                    )}
                  </h2>
                  <p className="text-xs text-slate-400">Autonomous GitHub publication, CI/CD quality gate & Vercel live deployment</p>
                </div>
              </div>

              {/* Deployment Action Button */}
              <div className="flex items-center gap-3">
                <label className="text-xs text-slate-400 flex items-center gap-1.5 cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={deployMock} 
                    onChange={e => setDeployMock(e.target.checked)} 
                    className="rounded border-slate-700 bg-slate-900 text-emerald-500"
                  />
                  <span>Mock Mode</span>
                </label>
                
                {deployment?.record?.stage?.includes('FAILED') ? (
                  <button
                    onClick={handleDeploy}
                    disabled={isDeploying}
                    className="bg-amber-600 hover:bg-amber-500 text-white font-medium px-4 py-2 rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-lg shadow-amber-700/20"
                  >
                    <RotateCw className={`w-3.5 h-3.5 ${isDeploying ? 'animate-spin' : ''}`} />
                    Retry Deployment
                  </button>
                ) : (
                  <button
                    onClick={handleDeploy}
                    disabled={isDeploying || isRunning || Object.keys(files).length === 0}
                    className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium px-4 py-2 rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-lg shadow-emerald-700/20"
                  >
                    <UploadCloud className={`w-3.5 h-3.5 ${isDeploying ? 'animate-spin' : ''}`} />
                    {deployment?.record ? 'Redeploy Application' : 'Deploy to GitHub & Vercel'}
                  </button>
                )}
              </div>
            </div>

            {/* Deployment Error Banner if Failed */}
            {deployment?.record?.error && (
              <div className="bg-red-950/30 border border-red-500/40 rounded-lg p-3 text-xs text-red-300 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <span className="font-semibold text-red-200">Deployment Stalled:</span>
                  <div className="font-mono">{deployment.record.error}</div>
                </div>
              </div>
            )}

            {/* Active Deployment Details Grid */}
            {deployment?.record ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* 1. GitHub Repository */}
                <div className="bg-[#0f111a] border border-slate-800 rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center gap-1.5 font-medium text-slate-300">
                      <GitBranch className="w-4 h-4 text-slate-400" /> GitHub Repository
                    </span>
                    {deployment.record.github?.is_private && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 font-mono">PRIVATE</span>
                    )}
                  </div>
                  {deployment.record.github?.repo_url ? (
                    <div>
                      <a 
                        href={deployment.record.github.repo_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-sm font-semibold text-blue-400 hover:text-blue-300 flex items-center gap-1 break-all"
                      >
                        {deployment.record.github.repo_name}
                        <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                      </a>
                      <div className="text-[11px] text-slate-500 mt-1 font-mono">
                        Branch: <span className="text-slate-300">{deployment.record.github.default_branch || 'main'}</span> • Commit: <span className="text-slate-400">{deployment.record.github.commit_sha?.slice(0, 7) || 'HEAD'}</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 font-mono">Pending repository creation...</p>
                  )}
                </div>

                {/* 2. CI/CD Quality Gate */}
                <div className="bg-[#0f111a] border border-slate-800 rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center gap-1.5 font-medium text-slate-300">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" /> CI/CD Quality Gate
                    </span>
                    <span className="text-[10px] text-emerald-400 font-mono">CONFIGURED</span>
                  </div>
                  <div>
                    <div className="text-xs font-mono text-slate-200">.github/workflows/ci.yml</div>
                    <div className="text-[11px] text-slate-500 mt-1">
                      Automated tests, dependency installation & build checks enabled.
                    </div>
                  </div>
                </div>

                {/* 3. Vercel Production Deployment & Health */}
                <div className="bg-[#0f111a] border border-slate-800 rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center gap-1.5 font-medium text-slate-300">
                      <Globe className="w-4 h-4 text-emerald-400" /> Vercel Live URL
                    </span>
                    {deployment.record.health_check?.is_healthy ? (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950/80 text-emerald-400 border border-emerald-800 font-mono">
                        HEALTHY ({Math.round(deployment.record.health_check.latency_ms || 0)}ms)
                      </span>
                    ) : deployment.record.vercel?.state ? (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-blue-950/80 text-blue-300 border border-blue-800 font-mono">
                        {deployment.record.vercel.state}
                      </span>
                    ) : null}
                  </div>
                  {deployment.record.vercel?.production_url || deployment.record.vercel?.deployment_url ? (
                    <div>
                      <a 
                        href={deployment.record.vercel.production_url || deployment.record.vercel.deployment_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-sm font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1 break-all"
                      >
                        {deployment.record.vercel.production_url || deployment.record.vercel.deployment_url}
                        <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                      </a>
                      <div className="text-[11px] text-slate-500 mt-1 font-mono">
                        Preset: <span className="text-slate-300">{deployment.record.vercel.framework_preset || 'detected'}</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 font-mono">Waiting for Vercel deployment...</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-[#0f111a]/50 border border-slate-800/80 rounded-lg p-5 text-center space-y-2">
                <div className="text-sm font-medium text-slate-300">Ready for Autonomous Cloud Deployment</div>
                <p className="text-xs text-slate-500 max-w-lg mx-auto">
                  Click <strong className="text-slate-300">Deploy to GitHub & Vercel</strong> above to automatically create a private GitHub repository, push code with automated CI workflows, and deploy live to Vercel.
                </p>
              </div>
            )}
          </div>

          {/* Interactive Code Explorer & Live Web Preview Tabs (Phase 3 & Phase 12) */}
          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-4">
                <button 
                  onClick={() => setActiveTab('code')}
                  className={`flex items-center gap-2 pb-1 text-sm font-bold border-b-2 transition-colors ${
                    activeTab === 'code' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Code className="w-4 h-4" /> Code Explorer ({Object.keys(files).length} files)
                </button>
                <button 
                  onClick={() => setActiveTab('preview')}
                  className={`flex items-center gap-2 pb-1 text-sm font-bold border-b-2 transition-colors ${
                    activeTab === 'preview' ? 'border-emerald-500 text-emerald-400' : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Globe className="w-4 h-4" /> Live Web Preview
                  {previewStatus?.has_preview && (
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  )}
                </button>
              </div>

              {activeTab === 'preview' && previewStatus?.has_preview && (
                <div className="flex items-center gap-2">
                  <button 
                    onClick={() => setIframeKey(k => k + 1)}
                    className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                    title="Reload Preview"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                  <a 
                    href={previewStatus.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors flex items-center gap-1 text-xs"
                    title="Open in new window"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              )}
            </div>

            {/* TAB 1: Code Explorer */}
            {activeTab === 'code' && (
              Object.keys(files).length === 0 ? (
                <p className="text-sm text-slate-500 py-12 text-center">Waiting for project generation...</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 border border-slate-700/80 rounded-lg overflow-hidden h-96">
                  <div className="col-span-1 bg-[#0f111a] border-r border-slate-700/80 p-2 overflow-y-auto">
                    {Object.keys(files).map(filename => (
                      <div 
                        key={filename} 
                        onClick={() => setSelectedFile(filename)}
                        className={`cursor-pointer p-2 text-xs font-mono rounded transition-colors ${
                          selectedFile === filename ? 'bg-blue-900/40 text-blue-300 font-bold border-l-2 border-blue-400' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                        }`}
                      >
                        {filename}
                      </div>
                    ))}
                  </div>
                  <div className="col-span-3 bg-[#0a0c10] p-4 overflow-y-auto text-xs font-mono text-slate-200 whitespace-pre">
                    {selectedFile ? files[selectedFile] : 'Select a file to inspect source code.'}
                  </div>
                </div>
              )
            )}

            {/* TAB 2: Live Web Preview (Phase 3) */}
            {activeTab === 'preview' && (
              <div className="space-y-3">
                {previewStatus?.has_preview ? (
                  <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950">
                    <div className="bg-[#0f111a] border-b border-slate-800 px-4 py-2 flex items-center justify-between text-xs text-slate-400 font-mono">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                        <span>{previewStatus.entrypoint}</span>
                      </div>
                      <span className="text-slate-500">Sandboxed Preview Server</span>
                    </div>
                    <iframe 
                      key={iframeKey}
                      src={previewStatus.url} 
                      title="DevAgents Live Application Preview"
                      className="w-full h-[450px] border-none bg-white"
                      sandbox="allow-scripts allow-forms allow-same-origin allow-modals"
                    />
                  </div>
                ) : (
                  <div className="py-16 text-center space-y-3 bg-[#0a0c10] border border-slate-800/80 rounded-lg">
                    <Globe className="w-10 h-10 text-slate-600 mx-auto" />
                    <div className="text-slate-300 font-medium text-sm">No Web Preview Entrypoint Found</div>
                    <p className="text-xs text-slate-500 max-w-md mx-auto">
                      This run appears to be a Python backend or module without an HTML entrypoint (such as index.html). Use the Code Explorer tab to inspect generated source files and test suites.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Tool Activity */}
          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2"><Activity className="w-5 h-5" /> Tool & Sandbox Activity</h2>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {getTools().length === 0 && <p className="text-sm text-slate-500">No tool activity logged.</p>}
              {getTools().map((t, i) => (
                <div key={i} className="bg-[#0f111a] border border-slate-800 p-3 rounded flex justify-between items-center">
                  <div className="text-sm text-slate-300">{t.tool_name}</div>
                  <div className={`text-xs ${t.success ? 'text-emerald-400' : 'text-red-400'}`}>{t.success ? 'Success' : 'Failed'}</div>
                </div>
              ))}
            </div>
          </div>

        </div>
        
        {/* Right Sidebar: Run Metrics, Telemetry & Timeline */}
        <div className="space-y-6">
          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Run Metrics</h2>
            {metrics ? (
              <div className="space-y-3 text-sm">
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Duration</span>
                  <span className="text-white font-mono">{metrics.run_duration ? `${metrics.run_duration.toFixed(1)}s` : 'N/A'}</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">LLM Invocations</span>
                  <span className="text-white font-mono">{metrics.total_llm_calls || events.filter(e => e.event_type === 'agent' || e.event_type === 'debug' || e.event_type === 'verification').length}</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Estimated Tokens</span>
                  <span className="text-white font-mono">{metrics.total_tokens || events.reduce((sum, e) => sum + (e.total_tokens || 0), 0) || 'N/A'}</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Debug Cycles</span>
                  <span className="text-white font-mono">{metrics.debugging_iterations || getDebugIterations().length}</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">RAG Context Queries</span>
                  <span className="text-white font-mono">{metrics.total_rag_queries || events.filter(e => e.event_type === 'rag').length}</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">Loading telemetry metrics...</p>
            )}
          </div>
          
          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Configuration</h2>
            {runInfo ? (
              <div className="space-y-2 text-sm text-slate-300 font-mono text-xs">
                <div>Provider: <span className="text-white font-semibold">{runInfo.provider || 'unknown'}</span></div>
                <div>Model: <span className="text-white">{runInfo.model || 'default'}</span></div>
                <div>RAG: <span className="text-white">{runInfo.configuration?.use_rag ? 'ENABLED' : 'DISABLED'}</span></div>
                <div>Memory: <span className="text-white">{runInfo.configuration?.use_memory ? 'ENABLED' : 'DISABLED'}</span></div>
                <div>Approval: <span className="text-white">{runState?.metadata?.human_approval ? 'ENABLED' : 'AUTONOMOUS'}</span></div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">Loading configuration...</p>
            )}
          </div>

          <div className="bg-[#161925] border border-slate-800 rounded-xl p-6 shadow-xl max-h-96 overflow-y-auto">
            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Telemetry Timeline</h2>
            <div className="space-y-3">
              {events.slice().reverse().map((e, i) => (
                <div key={i} className="text-xs border-l-2 border-slate-700 pl-3 py-1">
                  <div className="text-slate-500 mb-0.5">{new Date(e.timestamp || e.timestamp_end || e.timestamp_start || Date.now()).toLocaleTimeString()}</div>
                  <div className="text-slate-200 font-medium">
                    {e.event_type.toUpperCase()}
                  </div>
                  {e.agent_name && <div className="text-slate-400 mt-0.5">{e.agent_name} {e.action}</div>}
                  {e.tool_name && <div className="text-slate-400 mt-0.5">Used tool {e.tool_name}</div>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
