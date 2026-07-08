import { useState } from "react";
import { useAuthStore } from "@/store/auth";
import { Factory } from "lucide-react";

export function LoginPage() {
  const { view, loading, error, login, signup, confirm, forceChangePassword, setView, clearError } =
    useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [code, setCode] = useState("");

  const handleLogin = async (e: React.FormEvent) => { e.preventDefault(); await login(email, password); };
  const handleSignup = async (e: React.FormEvent) => { e.preventDefault(); await signup(email, password); };
  const handleConfirm = async (e: React.FormEvent) => { e.preventDefault(); await confirm(code); };
  const handleNewPassword = async (e: React.FormEvent) => { e.preventDefault(); await forceChangePassword(newPassword); };

  const inputCls = "w-full rounded-xl border border-white/[0.08] bg-slate-800/80 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500/40 focus:outline-none focus:ring-1 focus:ring-cyan-500/20 transition-all duration-200";
  const btnCls = "w-full rounded-xl bg-gradient-to-r from-cyan-500 to-teal-500 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 transition-all duration-300 disabled:opacity-50";
  const labelCls = "mb-1.5 block text-[13px] text-slate-400";
  const linkCls = "text-cyan-400 hover:text-cyan-300 transition-colors";

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950">
      {/* Subtle radial glow */}
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_center,rgba(6,182,212,0.06)_0%,transparent_70%)]" />

      <div className="relative w-full max-w-sm glass-card p-8">
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-500 to-teal-500 shadow-lg shadow-cyan-500/25">
            <Factory size={24} className="text-white" />
          </div>
          <h1 className="text-xl font-semibold text-slate-100 tracking-tight" data-testid="auth-title">
            DisruptionAI
          </h1>
          <p className="mt-1 text-sm text-slate-500">Production Intelligence Platform</p>
        </div>

        {error && (
          <div className="mb-5 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400" role="alert" data-testid="auth-error">
            <span className="flex-1">{error}</span>
            <button onClick={clearError} className="text-red-400/60 hover:text-red-400 transition-colors" aria-label="Dismiss error">&times;</button>
          </div>
        )}

        {view === "login" && (
          <form onSubmit={handleLogin} data-testid="login-form" className="space-y-4">
            <div>
              <label htmlFor="login-email" className={labelCls}>Email</label>
              <input id="login-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} placeholder="you@example.com" data-testid="login-email-input" autoComplete="email" />
            </div>
            <div>
              <label htmlFor="login-password" className={labelCls}>Password</label>
              <input id="login-password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls} placeholder="Password" data-testid="login-password-input" autoComplete="current-password" />
            </div>
            <button type="submit" disabled={loading} className={btnCls} data-testid="login-submit-button">
              {loading ? "Signing in..." : "Sign In"}
            </button>
            <p className="text-center text-sm text-slate-500">
              No account?{" "}<button type="button" onClick={() => setView("signup")} className={linkCls} data-testid="goto-signup-button">Sign up</button>
            </p>
          </form>
        )}

        {view === "signup" && (
          <form onSubmit={handleSignup} data-testid="signup-form" className="space-y-4">
            <div>
              <label htmlFor="signup-email" className={labelCls}>Email</label>
              <input id="signup-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} placeholder="you@example.com" data-testid="signup-email-input" autoComplete="email" />
            </div>
            <div>
              <label htmlFor="signup-password" className={labelCls}>Password</label>
              <input id="signup-password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls} placeholder="Min 8 chars, upper + lower + digit" data-testid="signup-password-input" autoComplete="new-password" />
            </div>
            <button type="submit" disabled={loading} className={btnCls} data-testid="signup-submit-button">
              {loading ? "Creating account..." : "Sign Up"}
            </button>
            <p className="text-center text-sm text-slate-500">
              Already have an account?{" "}<button type="button" onClick={() => setView("login")} className={linkCls} data-testid="goto-login-button">Sign in</button>
            </p>
          </form>
        )}

        {view === "confirm" && (
          <form onSubmit={handleConfirm} data-testid="confirm-form" className="space-y-4">
            <p className="text-sm text-slate-400">Check your email for a verification code.</p>
            <div>
              <label htmlFor="confirm-code" className={labelCls}>Verification Code</label>
              <input id="confirm-code" type="text" required value={code} onChange={(e) => setCode(e.target.value)} className={`${inputCls} text-center tracking-[0.3em] font-mono`} placeholder="123456" data-testid="confirm-code-input" autoComplete="one-time-code" />
            </div>
            <button type="submit" disabled={loading} className={btnCls} data-testid="confirm-submit-button">
              {loading ? "Verifying..." : "Verify"}
            </button>
          </form>
        )}

        {view === "newPassword" && (
          <form onSubmit={handleNewPassword} data-testid="new-password-form" className="space-y-4">
            <p className="text-sm text-slate-400">Your account requires a new password. Please choose one below.</p>
            <div>
              <label htmlFor="new-password" className={labelCls}>New Password</label>
              <input id="new-password" type="password" required minLength={8} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className={inputCls} placeholder="Min 8 chars, upper + lower + digit" data-testid="new-password-input" autoComplete="new-password" />
            </div>
            <button type="submit" disabled={loading} className={btnCls} data-testid="new-password-submit-button">
              {loading ? "Updating..." : "Set New Password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
