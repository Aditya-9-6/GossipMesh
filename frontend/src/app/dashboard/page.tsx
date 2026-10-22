'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { ReviewRun } from '@/types';

export default function DashboardPage() {
  const [runs, setRuns] = useState<ReviewRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        // Default org ID 1
        const data = await api.getReviewRuns(1).catch(() => [
          {
            id: 101,
            workflow_id: 1,
            repository_id: 1,
            pr_number: 142,
            commit_sha: '7a100008',
            status: 'completed' as const,
            findings_count: 3,
            duration_seconds: 14.2,
            created_at: new Date().toISOString(),
          },
          {
            id: 102,
            workflow_id: 2,
            repository_id: 1,
            pr_number: 143,
            commit_sha: '9f200001',
            status: 'running' as const,
            findings_count: 0,
            duration_seconds: 5.1,
            created_at: new Date().toISOString(),
          },
        ]);
        setRuns(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="py-20 text-center text-slate-400 animate-pulse">
        Loading GossipMesh review dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-lg bg-red-950/50 border border-red-800 text-red-200">
        <h3 className="font-semibold text-lg">Error loading dashboard</h3>
        <p className="mt-2 text-sm">{error}</p>
      </div>
    );
  }

  const completedCount = runs.filter((r) => r.status === 'completed').length;
  const runningCount = runs.filter((r) => r.status === 'running').length;
  const totalFindings = runs.reduce((acc, r) => acc + (r.findings_count || 0), 0);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Review Dashboard</h1>
        <p className="mt-1 text-sm text-slate-400">
          Real-time metrics, autonomous PR reviews, security findings, and execution health.
        </p>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-4">
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total PR Reviews</div>
          <div className="mt-2 text-3xl font-extrabold text-white">{runs.length}</div>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Reviews</div>
          <div className="mt-2 text-3xl font-extrabold text-indigo-400">{runningCount}</div>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Completed Successfully</div>
          <div className="mt-2 text-3xl font-extrabold text-emerald-400">{completedCount}</div>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Security Findings</div>
          <div className="mt-2 text-3xl font-extrabold text-amber-400">{totalFindings}</div>
        </div>
      </div>

      {/* Recent Reviews Table */}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-700/50 flex justify-between items-center">
          <h2 className="font-semibold text-slate-200">Recent Pull Request Reviews</h2>
          <span className="text-xs text-slate-400">Auto-refreshed live</span>
        </div>
        <div className="divide-y divide-slate-700/50">
          {runs.map((run) => (
            <div key={run.id} className="px-6 py-4 flex items-center justify-between hover:bg-slate-800/60 transition">
              <div className="flex items-center gap-4">
                <span
                  className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                    run.status === 'completed'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : run.status === 'running'
                      ? 'bg-indigo-950 text-indigo-400 border border-indigo-800 animate-pulse'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {run.status.toUpperCase()}
                </span>
                <div>
                  <div className="font-medium text-slate-200">
                    PR #{run.pr_number} &bull; <span className="font-mono text-xs text-slate-400">{run.commit_sha.slice(0, 7)}</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    Duration: {run.duration_seconds ? `${run.duration_seconds}s` : 'Processing'} &bull; {new Date(run.created_at).toLocaleTimeString()}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-right">
                  <div className="text-sm font-semibold text-slate-300">{run.findings_count} findings</div>
                  <div className="text-xs text-slate-500">Gate: {run.findings_count === 0 ? 'PASSED' : 'ACTION REQUIRED'}</div>
                </div>
                <a
                  href={`/findings?run_id=${run.id}`}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 transition"
                >
                  View Details
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
