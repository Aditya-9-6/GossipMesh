'use client';

import React, { useState } from 'react';

export default function RepositorySettingsPage() {
  const [defaultBranch, setDefaultBranch] = useState('main');
  const [severityThreshold, setSeverityThreshold] = useState('HIGH');
  const [activeProvider, setActiveProvider] = useState('gemini');
  const [ignoredPaths, setIgnoredPaths] = useState('tests/**\ndocs/**\nvendor/**');
  const [autoPatchEnabled, setAutoPatchEnabled] = useState(true);
  const [strictSandbox, setStrictSandbox] = useState(true);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="max-w-4xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Repository Settings & Policies</h1>
        <p className="mt-1 text-sm text-slate-400">
          Configure autonomous code review rules, severity thresholds, sandbox enforcement, and LLM providers.
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Branch & Review Rules */}
        <div className="p-6 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-5">
          <h2 className="text-base font-semibold text-slate-200">Branch & Gate Configuration</h2>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Target Default Branch</label>
              <input
                type="text"
                value={defaultBranch}
                onChange={(e) => setDefaultBranch(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Block Gate Severity Threshold</label>
              <select
                value={severityThreshold}
                onChange={(e) => setSeverityThreshold(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="CRITICAL">CRITICAL only</option>
                <option value="HIGH">HIGH and CRITICAL</option>
                <option value="MEDIUM">MEDIUM, HIGH, and CRITICAL</option>
                <option value="LOW">All severities (Strict)</option>
              </select>
            </div>
          </div>
        </div>

        {/* AI Provider Settings */}
        <div className="p-6 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-5">
          <h2 className="text-base font-semibold text-slate-200">AI Model & Multi-Key Provider</h2>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Primary Model Provider</label>
            <select
              value={activeProvider}
              onChange={(e) => setActiveProvider(e.target.value)}
              className="w-full px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="gemini">Google Gemini (Gemini 1.5 Pro / Flash pool)</option>
              <option value="openai">OpenAI (GPT-4o pool)</option>
              <option value="anthropic">Anthropic (Claude 3.5 Sonnet pool)</option>
            </select>
          </div>
        </div>

        {/* Ignored Paths */}
        <div className="p-6 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-5">
          <h2 className="text-base font-semibold text-slate-200">Ignored Paths (Glob Expressions)</h2>
          <textarea
            rows={4}
            value={ignoredPaths}
            onChange={(e) => setIgnoredPaths(e.target.value)}
            className="w-full font-mono text-xs px-3.5 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Security & Sandbox Flags */}
        <div className="p-6 rounded-xl bg-slate-800/40 border border-slate-700/60 space-y-4">
          <h2 className="text-base font-semibold text-slate-200">Autonomous Execution Controls</h2>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={autoPatchEnabled}
              onChange={(e) => setAutoPatchEnabled(e.target.checked)}
              className="w-4 h-4 rounded text-indigo-600 bg-slate-900 border-slate-700"
            />
            <div>
              <span className="text-sm font-medium text-slate-200">Enable Autonomous Patch Generation</span>
              <p className="text-xs text-slate-400">Generates validated diffs and PR suggestions when tests fail.</p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={strictSandbox}
              onChange={(e) => setStrictSandbox(e.target.checked)}
              className="w-4 h-4 rounded text-indigo-600 bg-slate-900 border-slate-700"
            />
            <div>
              <span className="text-sm font-medium text-slate-200">Enforce Rootless Isolated Sandbox</span>
              <p className="text-xs text-slate-400">Strict command whitelist, no network egress, and artifact quarantine.</p>
            </div>
          </label>
        </div>

        <div className="flex items-center justify-between">
          {saved && <span className="text-sm text-emerald-400 font-medium">Policy saved successfully!</span>}
          <div className="ml-auto">
            <button
              type="submit"
              className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition shadow-lg shadow-indigo-500/20"
            >
              Save Configuration
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
