/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export default function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center p-6 font-sans">
      <div className="max-w-2xl w-full bg-slate-800/90 border border-slate-700/80 rounded-2xl p-8 shadow-2xl backdrop-blur-sm">
        <div className="flex items-center space-x-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-blue-500/20 border border-blue-400/30 flex items-center justify-center text-blue-400 font-bold text-xl">
            🤖
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Telegram Auto-Forwarder Bot</h1>
            <p className="text-xs text-slate-400 font-medium">Production-Ready Python 3.12 • aiogram 3.x • Pyrogram 2.x</p>
          </div>
        </div>

        <div className="space-y-4 text-sm text-slate-300">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-700/50">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-blue-400 mb-2">⚡ Project Status</h2>
            <p className="text-slate-300 leading-relaxed">
              Full Python Telegram Bot codebase generated successfully with zero web dependencies. Designed for 24/7 execution on Railway.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="p-3.5 rounded-xl bg-slate-900/40 border border-slate-800">
              <span className="text-xs text-slate-400 font-medium block">Tech Stack</span>
              <span className="text-sm font-semibold text-slate-200">aiogram 3, Pyrogram 2, TgCrypto</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-900/40 border border-slate-800">
              <span className="text-xs text-slate-400 font-medium block">Storage</span>
              <span className="text-sm font-semibold text-slate-200">Async SQLite (aiosqlite)</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-900/40 border border-slate-800">
              <span className="text-xs text-slate-400 font-medium block">Deployment Target</span>
              <span className="text-sm font-semibold text-slate-200">Railway (Dockerfile included)</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-900/40 border border-slate-800">
              <span className="text-xs text-slate-400 font-medium block">Auto Reconnect</span>
              <span className="text-sm font-semibold text-slate-200">Enabled on restart</span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-700/50 mt-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">🚀 Main Entry Point</h2>
            <code className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-2.5 py-1 rounded border border-emerald-800/40 inline-block">
              python main.py
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}

