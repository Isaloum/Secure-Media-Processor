import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usersApi, filesApi } from '../services/api';

function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [recentFiles, setRecentFiles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [usageRes, filesRes] = await Promise.all([
          usersApi.getUsage(),
          filesApi.list(1, 5),
        ]);
        setStats(usageRes.data);
        setRecentFiles(filesRes.data.files);
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

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
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back{user?.name ? `, ${user.name}` : ''}!
        </h1>
        <p className="mt-1 text-gray-600">
          Here's an overview of your account
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card">
          <div className="text-sm font-medium text-gray-500">Storage Used</div>
          <div className="mt-2 text-2xl font-bold text-gray-900">
            {formatBytes(stats?.storage_used_bytes || 0)}
          </div>
          <div className="mt-1 text-xs text-gray-500">
            of {formatBytes(stats?.limits?.storage_limit_bytes || 0)}
          </div>
        </div>

        <div className="card">
          <div className="text-sm font-medium text-gray-500">Uploads Today</div>
          <div className="mt-2 text-2xl font-bold text-gray-900">
            {stats?.uploads_count || 0}
          </div>
          <div className="mt-1 text-xs text-gray-500">
            of {stats?.limits?.uploads_per_day || 10} allowed
          </div>
        </div>

        <div className="card">
          <div className="text-sm font-medium text-gray-500">Downloads Today</div>
          <div className="mt-2 text-2xl font-bold text-gray-900">
            {stats?.downloads_count || 0}
          </div>
        </div>

        <div className="card">
          <div className="text-sm font-medium text-gray-500">API Calls</div>
          <div className="mt-2 text-2xl font-bold text-gray-900">
            {stats?.api_calls_count || 0}
          </div>
          <div className="mt-1 text-xs text-gray-500">
            {stats?.limits?.api_rate_limit || 60}/min limit
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-4">
          <Link to="/files" className="btn-primary">
            Upload Files
          </Link>
          <Link to="/license" className="btn-secondary">
            Manage License
          </Link>
          <Link to="/settings" className="btn-secondary">
            Settings
          </Link>
        </div>
      </div>

      {/* Recent Files */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Recent Files</h2>
          <Link to="/files" className="text-sm text-primary-600 hover:text-primary-500">
            View all
          </Link>
        </div>

        {recentFiles.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">📁</div>
            <p>No files uploaded yet</p>
            <Link to="/files" className="text-primary-600 hover:text-primary-500 text-sm">
              Upload your first file
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 text-sm font-medium text-gray-500">Name</th>
                  <th className="text-left py-3 text-sm font-medium text-gray-500">Size</th>
                  <th className="text-left py-3 text-sm font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 text-sm font-medium text-gray-500">Date</th>
                </tr>
              </thead>
              <tbody>
                {recentFiles.map((file) => (
                  <tr key={file.file_id} className="border-b border-gray-100">
                    <td className="py-3 text-sm text-gray-900">{file.filename}</td>
                    <td className="py-3 text-sm text-gray-600">{formatBytes(file.size_bytes)}</td>
                    <td className="py-3">
                      <span
                        className={`inline-flex px-2 py-1 text-xs rounded-full ${
                          file.status === 'ready'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {file.status}
                      </span>
                    </td>
                    <td className="py-3 text-sm text-gray-600">
                      {new Date(file.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
