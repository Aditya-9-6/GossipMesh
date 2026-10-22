'use client';

import React, { useState } from 'react';

const STEPS = [
  { id: 1, title: 'Create Organization' },
  { id: 2, title: 'Install GitHub App' },
  { id: 3, title: 'Select Repositories' },
  { id: 4, title: 'Configure Policies' },
  { id: 5, title: 'First Autonomous Review' },
];

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [orgName, setOrgName] = useState('Acme Corp');
  const [selectedRepo, setSelectedRepo] = useState('AcmeCorp/core-backend');
  const [loading, setLoading] = useState(false);
  const [reviewTriggered, setReviewTriggered] = useState(false);

  const nextStep = () => setCurrentStep((prev) => Math.min(prev + 1, STEPS.length));
  const prevStep = () => setCurrentStep((prev) => Math.max(prev - 1, 1));

  const triggerFirstReview = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setReviewTriggered(true);
    }, 1500);
  };

  return (
    <div className="max-w-3xl mx-auto py-10 space-y-10">
      <div className="text-center">
        <h1 className="text-3xl font-extrabold text-white">Welcome to GossipMesh Enterprise</h1>
        <p className="mt-2 text-sm text-slate-400">
          Set up your organization, connect your repositories, and run your first autonomous review.
        </p>
      </div>

      {/* Stepper Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-6">
        {STEPS.map((step) => (
          <div key={step.id} className="flex items-center gap-2">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                currentStep >= step.id
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                  : 'bg-slate-800 text-slate-500 border border-slate-700'
              }`}
            >
              {step.id}
            </div>
            <span
              className={`text-xs font-medium hidden sm:inline ${
                currentStep >= step.id ? 'text-slate-200' : 'text-slate-500'
              }`}
            >
              {step.title}
            </span>
          </div>
        ))}
      </div>

      {/* Step Content */}
      <div className="p-8 rounded-2xl bg-slate-800/40 border border-slate-700/60 shadow-xl space-y-6">
        {currentStep === 1 && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-white">1. Name Your Organization</h2>
            <p className="text-sm text-slate-400">
              This creates your multi-tenant isolation boundary, billing ledger, and role domain.
            </p>
            <input
              type="text"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
              placeholder="e.g. Acme Corporation"
            />
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-white">2. Connect GitHub Organization</h2>
            <p className="text-sm text-slate-400">
              Install the official GossipMesh GitHub App to receive pull request webhooks and post inline review findings.
            </p>
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div>
                <div className="font-semibold text-white">GossipMesh GitHub App</div>
                <div className="text-xs text-slate-400 mt-0.5">Read/Write Pull Requests, Checks, and Repositories</div>
              </div>
              <a
                href="https://github.com/apps/gossipmesh"
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 transition"
              >
                Install App &rarr;
              </a>
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-white">3. Select Target Repository</h2>
            <p className="text-sm text-slate-400">
              Choose which connected repositories should be actively monitored by the mesh.
            </p>
            <div className="space-y-2">
              {['AcmeCorp/core-backend', 'AcmeCorp/web-frontend', 'AcmeCorp/infra-terraform'].map((repo) => (
                <label
                  key={repo}
                  className={`flex items-center justify-between p-4 rounded-xl border cursor-pointer transition ${
                    selectedRepo === repo
                      ? 'bg-indigo-950/40 border-indigo-500/60 text-white'
                      : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <span className="font-mono text-sm">{repo}</span>
                  <input
                    type="radio"
                    name="repo"
                    checked={selectedRepo === repo}
                    onChange={() => setSelectedRepo(repo)}
                    className="text-indigo-600 bg-slate-900"
                  />
                </label>
              ))}
            </div>
          </div>
        )}

        {currentStep === 4 && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-white">4. Review Policy & Security Gate</h2>
            <p className="text-sm text-slate-400">
              Your organization starts on a 14-day Free Trial with 5 seats, 200 PR reviews, and AST vector search.
            </p>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Gate Severity:</span>
                <span className="font-semibold text-white">Block on CRITICAL & HIGH findings</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Execution Sandbox:</span>
                <span className="font-semibold text-emerald-400">Rootless Container Isolation (Active)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Trial Period:</span>
                <span className="font-semibold text-indigo-400">14 Days (No credit card required)</span>
              </div>
            </div>
          </div>
        )}

        {currentStep === 5 && (
          <div className="space-y-4 text-center py-4">
            <h2 className="text-lg font-bold text-white">5. Trigger Initial Autonomous Review</h2>
            <p className="text-sm text-slate-400 max-w-md mx-auto">
              Kick off a scan on <span className="font-mono text-indigo-400">{selectedRepo}</span> to verify end-to-end integration.
            </p>

            {!reviewTriggered ? (
              <button
                onClick={triggerFirstReview}
                disabled={loading}
                className="mt-4 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition shadow-lg shadow-indigo-500/20 disabled:opacity-50"
              >
                {loading ? 'Initializing Mesh Agents...' : 'Start Autonomous Scan'}
              </button>
            ) : (
              <div className="mt-4 p-5 rounded-xl bg-emerald-950/40 border border-emerald-800 text-emerald-300 space-y-2">
                <div className="font-semibold text-base">Scan Initiated Successfully!</div>
                <p className="text-xs text-emerald-400/80">
                  Workflow #101 dispatched to execution loop. Results will appear on your dashboard.
                </p>
                <div className="pt-2">
                  <a
                    href="/dashboard"
                    className="inline-block px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition"
                  >
                    Go to Dashboard &rarr;
                  </a>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step Navigation Buttons */}
        <div className="flex justify-between pt-4 border-t border-slate-700/50">
          <button
            onClick={prevStep}
            disabled={currentStep === 1}
            className="px-4 py-2 text-xs font-medium rounded-lg text-slate-400 hover:text-white disabled:opacity-30"
          >
            &larr; Back
          </button>
          {currentStep < 5 && (
            <button
              onClick={nextStep}
              className="px-5 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition"
            >
              Continue &rarr;
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
