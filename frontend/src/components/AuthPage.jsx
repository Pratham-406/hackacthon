import React, { useState } from 'react';
import { Route, Mail, Lock, User, Phone, Eye, EyeOff, ArrowRight, ShieldCheck, Car, Navigation, AlertCircle, CheckCircle2, Loader2, Sparkles, HelpCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

function mapFirebaseError(err) {
  if (!err) return '';
  const code = err.code || err.message || '';
  if (code.includes('auth/invalid-credential') || code.includes('auth/wrong-password') || code.includes('auth/user-not-found')) {
    return 'Invalid email or password. Please verify your credentials.';
  }
  if (code.includes('auth/email-already-in-use')) {
    return 'An account with this email address already exists. Try signing in.';
  }
  if (code.includes('auth/weak-password')) {
    return 'Password should be at least 6 characters long.';
  }
  if (code.includes('auth/invalid-email')) {
    return 'Please enter a valid email address.';
  }
  if (code.includes('auth/popup-closed-by-user')) {
    return 'Google sign-in popup was closed before completion.';
  }
  if (code.includes('auth/cancelled-popup-request')) {
    return 'Popup request was replaced by another attempt.';
  }
  if (code.includes('auth/network-request-failed')) {
    return 'Network connection error. Check your internet connection.';
  }
  return err.message || 'Authentication failed. Please check your credentials.';
}

export default function AuthPage({ onDemoBypass }) {
  const { login, signup, loginWithGoogle, resetPassword, isFirebaseConfigured } = useAuth();

  const [mode, setMode] = useState('login'); // 'login' | 'signup' | 'forgot'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [role, setRole] = useState('passenger'); // 'passenger' | 'driver'
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successNotice, setSuccessNotice] = useState('');

  const clearMessages = () => {
    setError('');
    setSuccessNotice('');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    clearMessages();
    if (!email.trim() || !password) {
      setError('Please fill in both email and password.');
      return;
    }
    setLoading(true);
    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(mapFirebaseError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    clearMessages();
    if (!fullName.trim()) {
      setError('Please enter your full name.');
      return;
    }
    if (!email.trim() || !password) {
      setError('Please enter your email and password.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (!acceptTerms) {
      setError('Please agree to the Terms of Service to create an account.');
      return;
    }

    setLoading(true);
    try {
      await signup(email.trim(), password, fullName.trim(), role, phone.trim());
    } catch (err) {
      setError(mapFirebaseError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleAuth = async () => {
    clearMessages();
    setLoading(true);
    try {
      await loginWithGoogle(role);
    } catch (err) {
      setError(mapFirebaseError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    clearMessages();
    if (!email.trim()) {
      setError('Please enter your account email to receive a password reset link.');
      return;
    }
    setLoading(true);
    try {
      await resetPassword(email.trim());
      setSuccessNotice('Password reset email sent! Check your inbox for reset instructions.');
    } catch (err) {
      setError(mapFirebaseError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      {/* Background radial gradient decoration */}
      <div className="auth-backdrop-glow" />

      {/* Unconfigured Firebase Alert Banner */}
      {!isFirebaseConfigured && (
        <div className="auth-unconfigured-banner">
          <div className="auth-banner-content">
            <AlertCircle size={20} className="auth-banner-icon" />
            <div>
              <strong>Firebase Configuration Required</strong>
              <p>
                Firebase credentials are not yet set in <code>frontend/.env</code>.
                To connect real Firebase Authentication and Firestore, supply <code>VITE_FIREBASE_API_KEY</code>, <code>VITE_FIREBASE_PROJECT_ID</code>, etc.
              </p>
            </div>
          </div>
          {onDemoBypass && (
            <button className="auth-bypass-btn" onClick={onDemoBypass}>
              Continue in Demo Mode <ArrowRight size={14} />
            </button>
          )}
        </div>
      )}

      <div className="auth-card">
        {/* Brand header */}
        <div className="auth-brand">
          <div className="brand-logo-pill">
            <span className="brand-icon"><Route size={24} /></span>
            <span className="brand-text">smartpool<span className="brand-period">.</span></span>
          </div>
          <div className="auth-eyebrow">
            <span className="eyebrow-line" />
            PUNE — MUMBAI EXPRESSWAY
          </div>
          <h1 className="auth-title">Welcome to SmartPool</h1>
          <p className="auth-subtitle">Your route. Our ride.</p>
        </div>

        {/* Mode Selector Tabs (Login / Signup) */}
        {mode !== 'forgot' && (
          <div className="auth-mode-tabs">
            <button
              type="button"
              className={`auth-tab ${mode === 'login' ? 'active' : ''}`}
              onClick={() => { setMode('login'); clearMessages(); }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`auth-tab ${mode === 'signup' ? 'active' : ''}`}
              onClick={() => { setMode('signup'); clearMessages(); }}
            >
              Create Account
            </button>
          </div>
        )}

        {/* Alerts */}
        {error && (
          <div className="auth-alert error" role="alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {successNotice && (
          <div className="auth-alert success" role="status">
            <CheckCircle2 size={16} />
            <span>{successNotice}</span>
          </div>
        )}

        {/* Quick Google Login */}
        {mode !== 'forgot' && (
          <>
            <button
              type="button"
              className="auth-google-btn"
              disabled={loading || !isFirebaseConfigured}
              onClick={handleGoogleAuth}
              title={!isFirebaseConfigured ? 'Firebase configuration required' : 'Continue with Google'}
            >
              <svg className="google-icon" width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
              </svg>
              <span>Continue with Google</span>
            </button>

            <div className="auth-divider">
              <span className="divider-line" />
              <span className="divider-text">or with email</span>
              <span className="divider-line" />
            </div>
          </>
        )}

        {/* LOGIN FORM */}
        {mode === 'login' && (
          <form onSubmit={handleLogin} className="auth-form">
            <div className="auth-field">
              <label htmlFor="login-email">
                <Mail size={15} /> Email Address
              </label>
              <input
                id="login-email"
                type="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </div>

            <div className="auth-field">
              <div className="field-label-split">
                <label htmlFor="login-password">
                  <Lock size={15} /> Password
                </label>
                <button
                  type="button"
                  className="auth-link-btn"
                  onClick={() => { setMode('forgot'); clearMessages(); }}
                >
                  Forgot Password?
                </button>
              </div>
              <div className="password-input-wrap">
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="auth-submit-btn"
              disabled={loading || !isFirebaseConfigured}
            >
              {loading ? <Loader2 className="spin" size={18} /> : <ArrowRight size={18} />}
              <span>{loading ? 'Authenticating…' : 'Sign In to SmartPool'}</span>
            </button>
          </form>
        )}

        {/* SIGNUP FORM */}
        {mode === 'signup' && (
          <form onSubmit={handleSignup} className="auth-form">
            <div className="auth-field">
              <label htmlFor="signup-name">
                <User size={15} /> Full Name
              </label>
              <input
                id="signup-name"
                type="text"
                required
                placeholder="e.g. Rahul Sharma"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
              />
            </div>

            <div className="auth-field">
              <label htmlFor="signup-email">
                <Mail size={15} /> Email Address
              </label>
              <input
                id="signup-email"
                type="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </div>

            <div className="auth-field">
              <label htmlFor="signup-phone">
                <Phone size={15} /> Phone Number <span className="auth-optional">(optional)</span>
              </label>
              <input
                id="signup-phone"
                type="tel"
                placeholder="+91 98765 43210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                autoComplete="tel"
              />
            </div>

            {/* Account Role Selector */}
            <div className="auth-field">
              <label>Account Role</label>
              <div className="auth-role-selector">
                <button
                  type="button"
                  className={`role-option ${role === 'passenger' ? 'active' : ''}`}
                  onClick={() => setRole('passenger')}
                >
                  <Car size={16} />
                  <div>
                    <strong>Passenger</strong>
                    <small>Pool shared rides</small>
                  </div>
                </button>
                <button
                  type="button"
                  className={`role-option ${role === 'driver' ? 'active' : ''}`}
                  onClick={() => setRole('driver')}
                >
                  <Navigation size={16} />
                  <div>
                    <strong>Driver</strong>
                    <small>Drive corridor batch</small>
                  </div>
                </button>
              </div>
            </div>

            <div className="auth-field">
              <label htmlFor="signup-password">
                <Lock size={15} /> Password
              </label>
              <div className="password-input-wrap">
                <input
                  id="signup-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  placeholder="At least 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="auth-field">
              <label htmlFor="signup-confirm-password">
                <Lock size={15} /> Confirm Password
              </label>
              <div className="password-input-wrap">
                <input
                  id="signup-confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  required
                  placeholder="Re-type password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                >
                  {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <label className="auth-checkbox-label">
              <input
                type="checkbox"
                checked={acceptTerms}
                onChange={(e) => setAcceptTerms(e.target.checked)}
              />
              <span>
                I agree to the SmartPool Terms of Service & Privacy Policy.
              </span>
            </label>

            <button
              type="submit"
              className="auth-submit-btn"
              disabled={loading || !isFirebaseConfigured}
            >
              {loading ? <Loader2 className="spin" size={18} /> : <ArrowRight size={18} />}
              <span>{loading ? 'Creating Account…' : 'Create SmartPool Account'}</span>
            </button>
          </form>
        )}

        {/* FORGOT PASSWORD FORM */}
        {mode === 'forgot' && (
          <form onSubmit={handleForgotPassword} className="auth-form">
            <div className="forgot-header">
              <h2>Reset Password</h2>
              <p>Enter your account email. We will send a secure password reset link directly to your inbox.</p>
            </div>

            <div className="auth-field">
              <label htmlFor="forgot-email">
                <Mail size={15} /> Account Email
              </label>
              <input
                id="forgot-email"
                type="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </div>

            <button
              type="submit"
              className="auth-submit-btn"
              disabled={loading || !isFirebaseConfigured}
            >
              {loading ? <Loader2 className="spin" size={18} /> : <Mail size={18} />}
              <span>{loading ? 'Sending link…' : 'Send Reset Link'}</span>
            </button>

            <button
              type="button"
              className="auth-back-btn"
              onClick={() => { setMode('login'); clearMessages(); }}
            >
              Back to Sign In
            </button>
          </form>
        )}

        {/* Trust Badges Footer */}
        <div className="auth-card-footer">
          <div className="auth-footer-badge">
            <ShieldCheck size={15} />
            <span>Secure Firebase Auth & Firestore</span>
          </div>
          <div className="auth-footer-badge">
            <Sparkles size={15} />
            <span>VRPTW & Shapley Fair Pricing</span>
          </div>
        </div>
      </div>
    </div>
  );
}
