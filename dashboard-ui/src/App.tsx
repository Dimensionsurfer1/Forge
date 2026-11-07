
import { useEffect, useState } from "react";

interface Approval {
  approval_id: string;
  project_id: string;
  task_id: string;
  agent_id: string;
  summary: string;
  status: string;
  created_at: string;
}

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [apiStatus, setApiStatus] = useState("Connecting");
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadApprovals() {
      try {
        const response = await fetch(`${API_URL}/approvals`);

        if (!response.ok) {
          throw new Error("Could not fetch approvals.");
        }

        const data: Approval[] = await response.json();
        setApprovals(data);
        setApiStatus("Connected");
        setError("");
      } catch {
        setApiStatus("Disconnected");
        setError("Cannot connect to Forge API.");
      }
    }

    loadApprovals();
    const interval = setInterval(loadApprovals, 5000);

    return () => clearInterval(interval);
  }, []);

  const agents = [
    ["Orchestrator", "Workflow coordination", "Online"],
    ["Planner", "Task decomposition", "Idle"],
    ["Architect", "System architecture", "Idle"],
    ["Backend", "Backend development", "Idle"],
    ["Frontend", "Frontend development", "Idle"],
    ["QA Engineer", "Testing and validation", "Idle"],
  ];

  return (
    <div className="min-h-screen bg-[#09090b] text-slate-200 flex">
      <aside className="w-64 border-r border-white/10 p-6 hidden md:block">
        <h1 className="text-2xl font-bold text-white">
          FORGE<span className="text-violet-500">.</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          AI ENGINEERING PLATFORM
        </p>

        <nav className="mt-12 space-y-2 text-sm">
          {["Overview", "Agents", "Workflows", "Approvals", "Projects", "Settings"].map((item, index) => (
            <div
              key={item}
              className={`px-4 py-3 rounded-lg ${
                index === 0
                  ? "bg-violet-500/15 text-violet-400"
                  : "text-slate-400 hover:bg-white/5"
              }`}
            >
              {item}
            </div>
          ))}
        </nav>

        <div className="absolute bottom-6 text-xs text-slate-600">
          FORGE v0.1.0 · DEVELOPMENT
        </div>
      </aside>

      <main className="flex-1 p-6 md:p-10">
        <header className="flex justify-between items-center mb-10">
          <div>
            <p className="text-sm text-slate-500">Workspace / Overview</p>
            <h2 className="text-3xl font-semibold text-white mt-2">
              Control Centre
            </h2>
          </div>

          <div className="flex items-center gap-2 text-sm border border-white/10 rounded-full px-4 py-2">
            <span className={`w-2 h-2 rounded-full ${
              apiStatus === "Connected" ? "bg-green-400" : "bg-red-400"
            }`} />
            API {apiStatus}
          </div>
        </header>

        <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {[
            ["Total Agents", "9"],
            ["Active Workflows", "0"],
            ["Pending Approvals", String(approvals.length)],
            ["Completed Tasks", "0"],
          ].map(([label, value]) => (
            <div key={label} className="bg-[#111114] border border-white/10 rounded-xl p-5">
              <p className="text-sm text-slate-500">{label}</p>
              <p className="text-3xl font-semibold text-white mt-3">{value}</p>
            </div>
          ))}
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-3 gap-6 mt-8">
          <div className="xl:col-span-2 bg-[#111114] border border-white/10 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-6">
              Agent Team
            </h3>

            <div className="grid sm:grid-cols-2 gap-3">
              {agents.map(([name, role, status]) => (
                <div key={name} className="border border-white/10 rounded-lg p-4">
                  <div className="flex justify-between">
                    <p className="font-medium text-white">{name}</p>
                    <span className="text-xs text-slate-500">{status}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-2">{role}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-[#111114] border border-white/10 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white">
              System Activity
            </h3>
            <p className="text-sm text-slate-500 mt-5">
              No active workflows.
            </p>
          </div>
        </section>

        <section className="bg-[#111114] border border-white/10 rounded-xl p-6 mt-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-white">
              Approval Queue
            </h3>
            <span className="text-sm text-violet-400">
              {approvals.length} pending
            </span>
          </div>

          {error && (
            <p className="text-red-400 text-sm mt-4">{error}</p>
          )}

          {approvals.length === 0 && !error && (
            <p className="text-sm text-slate-500 mt-4">
              No pending approvals.
            </p>
          )}

          <div className="space-y-3 mt-4">
            {approvals.map((approval) => (
              <div
                key={approval.approval_id}
                className="border border-white/10 rounded-lg p-4"
              >
                <div className="flex justify-between gap-4">
                  <p className="font-medium text-white">
                    {approval.summary}
                  </p>
                  <span className="text-xs text-yellow-400">
                    {approval.status}
                  </span>
                </div>

                <p className="text-xs text-slate-500 mt-2">
                  Project: {approval.project_id} · Agent: {approval.agent_id}
                </p>

                <p className="text-xs text-slate-500 mt-1">
                  Task: {approval.task_id}
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
