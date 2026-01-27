import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [step, setStep] = useState('email'); // email, code, success
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { forgotPassword, resetPassword } = useAuth();

  const handleRequestCode = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await forgotPassword(email);
      setStep('code');
    } catch (err) {
      setError(err.message || 'Failed to send reset code');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await resetPassword(email, code, newPassword);
      setStep('success');
    } catch (err) {
      setError(err.message || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  if (step === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
        <div className="max-w-md w-full text-center space-y-6">
          <div className="text-6xl">✅</div>
          <h2 className="text-2xl font-bold text-gray-900">Password reset successful</h2>
          <p className="text-gray-600">You can now sign in with your new password.</p>
          <Link to="/login" className="btn-primary inline-block">
            Sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Reset your password
          </h2>
        </div>

        {step === 'email' && (
          <form className="mt-8 space-y-6" onSubmit={handleRequestCode}>
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input mt-1"
                placeholder="you@example.com"
              />
            </div>

            <button type="submit" disabled={loading} className="w-full btn-primary py-3">
              {loading ? 'Sending...' : 'Send reset code'}
            </button>

            <div className="text-center">
              <Link to="/login" className="text-sm text-primary-600 hover:text-primary-500">
                Back to sign in
              </Link>
            </div>
          </form>
        )}

        {step === 'code' && (
          <form className="mt-8 space-y-6" onSubmit={handleResetPassword}>
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label htmlFor="code" className="block text-sm font-medium text-gray-700">
                  Verification code
                </label>
                <input
                  id="code"
                  type="text"
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="input mt-1"
                  placeholder="123456"
                />
              </div>

              <div>
                <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700">
                  New password
                </label>
                <input
                  id="newPassword"
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="input mt-1"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button type="submit" disabled={loading} className="w-full btn-primary py-3">
              {loading ? 'Resetting...' : 'Reset password'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default ForgotPassword;
