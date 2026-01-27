import React, { useState, useEffect, useRef } from 'react';
import { filesApi } from '../services/api';
import config from '../utils/config';

function Files() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      const response = await filesApi.list();
      setFiles(response.data.files);
    } catch (err) {
      setError('Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    // Validate file type
    if (!config.allowedFileTypes.includes(selectedFile.type)) {
      setError('File type not allowed');
      return;
    }

    // Validate file size
    if (selectedFile.size > config.maxFileSize) {
      setError('File too large (max 100MB)');
      return;
    }

    setError('');
    setUploading(true);
    setUploadProgress(0);

    try {
      // Get presigned upload URL
      const urlResponse = await filesApi.getUploadUrl({
        filename: selectedFile.name,
        content_type: selectedFile.type,
        size_bytes: selectedFile.size,
        encrypted: true,
      });

      const { url, file_id } = urlResponse.data;

      // Upload to S3
      await filesApi.uploadToS3(url, selectedFile, (progress) => {
        setUploadProgress(progress);
      });

      // Mark upload complete
      await filesApi.completeUpload(file_id);

      // Refresh file list
      await fetchFiles();
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDownload = async (file) => {
    try {
      const response = await filesApi.getDownloadUrl(file.file_id);
      window.open(response.data.url, '_blank');
    } catch (err) {
      setError('Failed to get download link');
    }
  };

  const handleDelete = async (file) => {
    if (!confirm(`Delete "${file.filename}"?`)) return;

    try {
      await filesApi.delete(file.file_id);
      setFiles(files.filter((f) => f.file_id !== file.file_id));
    } catch (err) {
      setError('Failed to delete file');
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (contentType) => {
    if (contentType.startsWith('image/')) return '🖼️';
    if (contentType.startsWith('video/')) return '🎬';
    if (contentType.startsWith('audio/')) return '🎵';
    return '📄';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Files</h1>
        <label className="btn-primary cursor-pointer">
          {uploading ? `Uploading ${uploadProgress}%` : 'Upload File'}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileSelect}
            disabled={uploading}
            accept={config.allowedFileTypes.join(',')}
          />
        </label>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
          <button onClick={() => setError('')} className="ml-2 text-red-500">
            ×
          </button>
        </div>
      )}

      {uploading && (
        <div className="card">
          <div className="flex items-center space-x-4">
            <div className="flex-1">
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-600 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
            <span className="text-sm text-gray-600">{uploadProgress}%</span>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-200 border-t-primary-600" />
        </div>
      ) : files.length === 0 ? (
        <div className="card text-center py-12">
          <div className="text-6xl mb-4">📁</div>
          <h3 className="text-lg font-medium text-gray-900">No files yet</h3>
          <p className="mt-1 text-gray-500">Upload your first file to get started</p>
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  File
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Size
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Uploaded
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {files.map((file) => (
                <tr key={file.file_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <span className="text-2xl mr-3">{getFileIcon(file.content_type)}</span>
                      <div>
                        <div className="text-sm font-medium text-gray-900">{file.filename}</div>
                        <div className="text-xs text-gray-500">{file.content_type}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {formatBytes(file.size_bytes)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2 py-1 text-xs rounded-full ${
                        file.status === 'ready'
                          ? 'bg-green-100 text-green-800'
                          : file.status === 'processing'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {file.encrypted && '🔒 '}
                      {file.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {new Date(file.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    {file.status === 'ready' && (
                      <button
                        onClick={() => handleDownload(file)}
                        className="text-primary-600 hover:text-primary-800 mr-4"
                      >
                        Download
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(file)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Files;
