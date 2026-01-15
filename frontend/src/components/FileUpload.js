import React, { useState } from 'react';
import axios from 'axios';
import './FileUpload.css';

const API_BASE_URL = 'http://localhost:8000/api';

function FileUpload({ onFileUploaded }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      const validTypes = ['.pdf', '.docx', '.txt'];
      const fileExtension = selectedFile.name.slice(selectedFile.name.lastIndexOf('.')).toLowerCase();

      if (!validTypes.includes(fileExtension)) {
        setError('Please upload a PDF, DOCX, or TXT file');
        setFile(null);
        return;
      }

      setFile(selectedFile);
      setError('');
      setMessage('');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setError('');
    setMessage('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setMessage(`✅ ${response.data.message}`);
      onFileUploaded(response.data.file_id, response.data.filename);

      // Clear file input
      setFile(null);
      document.getElementById('file-input').value = '';

    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="file-upload-card">
      <h2>📄 Upload Document</h2>

      <div className="upload-area">
        <input
          id="file-input"
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFileChange}
          disabled={uploading}
        />

        {file && (
          <div className="file-selected">
            <span>📎 {file.name}</span>
            <span className="file-size">({(file.size / 1024).toFixed(2)} KB)</span>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="upload-button"
        >
          {uploading ? '⏳ Uploading...' : '🚀 Upload & Index'}
        </button>
      </div>

      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}

      <div className="supported-formats">
        <small>Supported formats: PDF, DOCX, TXT</small>
      </div>
    </div>
  );
}

export default FileUpload;
