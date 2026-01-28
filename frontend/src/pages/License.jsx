import React, { useState, useEffect } from 'react';
import { licensesApi } from '../services/api';

function License() {
  const [license, setLicense] = useState(null);
  const [tiers, setTiers] = useState(null);
  const [licenseKey, setLicenseKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [activating, setActivating] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [licenseRes, tiersRes] = await Promise.all([
          licensesApi.getCurrent(),
          licensesApi.getTiers(),
        ]);
        setLicense(licenseRes.data);
        setTiers(tiersRes.data.tiers);
      } catch (err) {
        console.error('Failed to fetch license data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleActivate = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setActivating(true);

    try {
      const response = await licensesApi.activate(licenseKey);
      setLicense(response.data);
      setSuccess('License activated successfully!');
      setLicenseKey('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to activate license');
    } finally {
      setActivating(false);
    }
  };

  const formatNumber = (num) => {
    if (num === -1) return 'Unlimited';
    return num.toLocaleString();
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
        <h1 className="text-2xl font-bold text-gray-900">License</h1>
        <p className="mt-1 text-gray-600">Manage your subscription and features</p>
      </div>

      {/* Current License */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Current Plan</h2>
        <div className="flex items-center space-x-4">
          <div
            className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl ${
              license?.tier === 'free'
                ? 'bg-gray-100'
                : license?.tier === 'pro'
                ? 'bg-primary-100'
                : 'bg-yellow-100'
            }`}
          >
            {license?.tier === 'free' ? '🆓' : license?.tier === 'pro' ? '⭐' : '👑'}
          </div>
          <div>
            <div className="text-xl font-bold text-gray-900 capitalize">
              {license?.tier || 'Free'} Plan
            </div>
            <div className="text-sm text-gray-500">
              Status: {license?.status || 'Active'}
            </div>
          </div>
        </div>

        {license?.tier !== 'free' && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="text-sm text-gray-600">
              Activations: {license?.activations || 0} / {license?.max_activations || 3}
            </div>
          </div>
        )}
      </div>

      {/* Activate License */}
      {license?.tier === 'free' && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Activate License</h2>
          <p className="text-sm text-gray-600 mb-4">
            Enter your license key to unlock premium features
          </p>

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

          <form onSubmit={handleActivate} className="flex space-x-4">
            <input
              type="text"
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value)}
              placeholder="XXXXX-XXXXX-XXXXX-XXXXX"
              className="input flex-1"
              required
            />
            <button type="submit" disabled={activating} className="btn-primary">
              {activating ? 'Activating...' : 'Activate'}
            </button>
          </form>

          <p className="mt-4 text-xs text-gray-500">
            Don't have a license? Purchase one from our store.
          </p>
        </div>
      )}

      {/* Plan Comparison */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-6">Plan Comparison</h2>

        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 text-sm font-medium text-gray-500">Feature</th>
                {tiers &&
                  Object.keys(tiers).map((tier) => (
                    <th
                      key={tier}
                      className={`text-center py-3 text-sm font-medium ${
                        tier === license?.tier ? 'text-primary-600' : 'text-gray-500'
                      }`}
                    >
                      {tier.charAt(0).toUpperCase() + tier.slice(1)}
                      {tier === license?.tier && ' ✓'}
                    </th>
                  ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-100">
                <td className="py-3 text-sm text-gray-700">Storage</td>
                {tiers &&
                  Object.values(tiers).map((config, i) => (
                    <td key={i} className="py-3 text-sm text-center text-gray-900">
                      {config.storage_limit_gb} GB
                    </td>
                  ))}
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3 text-sm text-gray-700">Uploads/Day</td>
                {tiers &&
                  Object.values(tiers).map((config, i) => (
                    <td key={i} className="py-3 text-sm text-center text-gray-900">
                      {formatNumber(config.uploads_per_day)}
                    </td>
                  ))}
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3 text-sm text-gray-700">Max File Size</td>
                {tiers &&
                  Object.values(tiers).map((config, i) => (
                    <td key={i} className="py-3 text-sm text-center text-gray-900">
                      {config.max_file_size_mb} MB
                    </td>
                  ))}
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3 text-sm text-gray-700">GPU Processing</td>
                {tiers &&
                  Object.values(tiers).map((config, i) => (
                    <td key={i} className="py-3 text-sm text-center">
                      {config.gpu_processing ? '✅' : '❌'}
                    </td>
                  ))}
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3 text-sm text-gray-700">API Rate Limit</td>
                {tiers &&
                  Object.values(tiers).map((config, i) => (
                    <td key={i} className="py-3 text-sm text-center text-gray-900">
                      {config.api_rate_limit}/min
                    </td>
                  ))}
              </tr>
              <tr>
                <td className="py-3 text-sm text-gray-700">Cloud Connectors</td>
                {tiers &&
                  Object.values(tiers).map((config, i) => (
                    <td key={i} className="py-3 text-sm text-center text-gray-900">
                      {config.cloud_connectors.length}
                    </td>
                  ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default License;
