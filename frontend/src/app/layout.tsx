import React from 'react';

export const metadata = {
  title: 'GossipMesh Enterprise AI Code Review',
  description: 'Autonomous P2P AI Code Review and Verification Mesh',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-900 text-slate-100 min-h-screen font-sans">
        <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
              GM
            </div>
            <span className="font-semibold text-lg tracking-tight">GossipMesh</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-900/60 text-indigo-400 border border-indigo-700/50">Enterprise</span>
          </div>
          <nav className="flex items-center gap-6 text-sm text-slate-400">
            <a href="/dashboard" className="hover:text-slate-100 transition">Dashboard</a>
            <a href="/repositories" className="hover:text-slate-100 transition">Repositories</a>
            <a href="/runs" className="hover:text-slate-100 transition">Runs</a>
            <a href="/findings" className="hover:text-slate-100 transition">Findings</a>
            <a href="/settings" className="hover:text-slate-100 transition">Settings</a>
            <a href="/members" className="hover:text-slate-100 transition">Members</a>
            <a href="/billing" className="hover:text-slate-100 transition">Billing</a>
            <a href="/audit" className="hover:text-slate-100 transition">Audit Logs</a>
          </nav>
        </header>
        <main className="p-8 max-w-7xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
