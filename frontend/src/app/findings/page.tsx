'use client';

import React, { useState } from 'react';
import { Finding } from '@/types';

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([
    {
      id: 1,
      run_id: 101,
      file_path: 'gossipmesh/api/routers/users.py',
      line_number: 45,
      rule_id: 'GM-SEC-004',
      severity: 'CRITICAL',
      message: 'Unparameterized database query detected: potential SQL injection vulnerability.',
      status: 'open',
      suggested_fix: 'Use parameterized query with SQLAlchemy select() statement.',
    },
    {
      id: 2,
      run_id: 101,
      file_path: 'gossipmesh/runtime/sandbox.py',
      line_number: 112,
      rule_id: 'GM-SANDBOX-002',
      severity: 'HIGH',
      message: 'Subprocess call missing non-root user flag and strict timeout parameter.',
      status: 'open',
      suggested_fix: 'Pass timeout_seconds=30 and execution_adapter=RootlessContainerAdapter.',
    },
  ]);

  const [activeTab, setActiveTab] = useState<'all' | 'open' | 'resolved'>('all');

  const updateFindingStatus = (id: number, newStatus: Finding['status']) => {
    setFindings((prev) =>
      prev.map((f) => (f.id === id ? { ...f, status: newStatus } : f))
    );
  };

  const filtered = findings.filter((f) => {
    if (activeTab === 'open') return f.status === 'open';
    if (activeTab === 'resolved') return f.status !== 'open';
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Review Findings & Human Feedback</h1>
          <p className="mt-1 text-sm text-slate-400">
            Audit findings produced by multi-agent mesh. Accept, dismiss, or flag false positives.
          </p>
        </div>
        <div className="flex gap-2 bg-slate-800/80 p-1 rounded-lg border border-slate-700/60">
          {(['all', 'open', 'resolved'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
                activeTab === tab ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        {filtered.map((finding) => (
          <div
            key={finding.id}
            className="p-6 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-4 hover:border-slate-600 transition"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span
                  className={`px-2.5 py-1 rounded-md text-xs font-bold tracking-wider ${
                    finding.severity === 'CRITICAL'
                      ? 'bg-rose-950 text-rose-400 border border-rose-800'
                      : finding.severity === 'HIGH'
                      ? 'bg-amber-950 text-amber-400 border border-amber-800'
                      : 'bg-blue-950 text-blue-400 border border-blue-800'
                  }`}
                >
                  {finding.severity}
                </span>
                <span className="font-mono text-xs text-indigo-400">{finding.rule_id}</span>
                <span className="text-xs text-slate-400">&bull;</span>
                <span className="font-mono text-xs text-slate-300">
                  {finding.file_path}:{finding.line_number}
                </span>
              </div>
              <span className="text-xs px-2.5 py-1 rounded-full bg-slate-700/60 text-slate-300 font-medium">
                Status: {finding.status.toUpperCase()}
              </span>
            </div>

            <p className="text-sm text-slate-200 leading-relaxed">{finding.message}</p>

            {finding.suggested_fix && (
              <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 font-mono text-xs text-emerald-400">
                <div className="text-[10px] uppercase font-bold text-slate-500 mb-1">Suggested Fix</div>
                {finding.suggested_fix}
              </div>
            )}

            {/* Human Feedback Actions */}
            <div className="pt-2 border-t border-slate-700/40 flex items-center justify-between">
              <span className="text-xs text-slate-400">Actions recorded in immutable audit log</span>
              <div className="flex gap-2">
                <button
                  onClick={() => updateFindingStatus(finding.id, 'accepted')}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30 border border-emerald-500/30 transition"
                >
                  Accept & Patch
                </button>
                <button
                  onClick={() => updateFindingStatus(finding.id, 'dismissed')}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 transition"
                >
                  Dismiss
                </button>
                <button
                  onClick={() => updateFindingStatus(finding.id, 'false_positive')}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-600/20 text-amber-300 hover:bg-amber-600/30 border border-amber-500/30 transition"
                >
                  Mark False Positive
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
