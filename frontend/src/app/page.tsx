import React from 'react';

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-6xl">
        Decentralized P2P Autonomous <br />
        <span className="text-indigo-500">AI Code Review Mesh</span>
      </h1>
      <p className="mt-6 text-lg leading-8 text-slate-400 max-w-2xl">
        Enterprise multi-agent mesh verifying pull requests with deterministic security gates,
        isolated execution sandboxes, and immutable compliance auditing.
      </p>
      <div className="mt-10 flex items-center justify-center gap-x-6">
        <a
          href="/dashboard"
          className="rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 transition"
        >
          Open Dashboard
        </a>
        <a
          href="/login"
          className="text-sm font-semibold leading-6 text-slate-300 hover:text-white"
        >
          Sign In &rarr;
        </a>
      </div>
    </div>
  );
}
