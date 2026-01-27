import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { usersApi } from '../services/api';

function Settings() {
  const { user, signOut } = useAuth();
  const [profile, setProfile] = useState(null);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await usersApi.getProfile();
        setProfile(response.data);
        setName(response.data.name || '');
      } catch (err) {
        setError('Failed to load profile');
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSaving(true);

    try {
      const response = await usersApi.updateProfile({ name });
      setProfile(response.data);
      setSuccess('Profile updated successfully');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-gray-600">Manage your account settings</p>
      </div>

      {/* Profile Settings */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Profile</h2>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
            {success}
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              value={profile?.email || user?.email || ''}
              disabled
              className="input mt-1 bg-gray-50"
            />
            <p className="mt-1 text-xs text-gray-500">Email cannot be changed</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input mt-1"
              placeholder="Your name"
            />
          </div>

          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </div>

      {/* Account Info */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Account Info</h2>

        <div className="space-y-4">
          <div className="flex justify-between py-2 border-b border-gray-100">
            <span className="text-gray-600">User ID</span>
            <span className="text-gray-900 font-mono text-sm">{profile?.user_id}</span>
          </div>

          <div className="flex justify-between py-2 border-b border-gray-100">
            <span className="text-gray-600">Plan</span>
            <span className="text-gray-900 capitalize">{profile?.license_tier || 'Free'}</span>
          </div>

          <div className="flex justify-between py-2 border-b border-gray-100">
            <span className="text-gray-600">Storage Used</span>
            <span className="text-gray-900">
              {formatBytes(profile?.storage_used_bytes || 0)} /{' '}
              {formatBytes(profile?.storage_limit_bytes || 0)}
            </span>
          </div>

          <div className="flex justify-between py-2">
            <span className="text-gray-600">Member Since</span>
            <span className="text-gray-900">
              {profile?.created_at
                ? new Date(profile.created_at).toLocaleDateString()
                : 'Unknown'}
            </span>
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Security</h2>

        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-700">Password</h3>
            <p className="mt-1 text-sm text-gray-500">
              To change your password, sign out and use the "Forgot Password" option on the login
              page.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700">Sessions</h3>
            <p className="mt-1 text-sm text-gray-500">
              Sign out from all devices by clicking the button below.
            </p>
            <button
              onClick={signOut}
              className="mt-2 text-sm text-red-600 hover:text-red-800"
            >
              Sign out from all devices
            </button>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="card border-red-200">
        <h2 className="text-lg font-semibold text-red-600 mb-4">Danger Zone</h2>

        <div>
          <h3 className="text-sm font-medium text-gray-700">Delete Account</h3>
          <p className="mt-1 text-sm text-gray-500">
            Permanently delete your account and all associated data. This action cannot be undone.
          </p>
          <button
            onClick={() => {
              if (
                confirm(
                  'Are you sure you want to delete your account? This action cannot be undone.'
                )
              ) {
                alert('Account deletion is not implemented in this demo.');
              }
            }}
            className="mt-2 text-sm text-red-600 hover:text-red-800"
          >
            Delete my account
          </button>
        </div>
      </div>
    </div>
  );
}

export default Settings;
