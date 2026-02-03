import React, { useState } from 'react';
import { submitAnalysis } from '../api';

const styles = {
  container: {
    backgroundColor: '#fff',
    borderRadius: '8px',
    padding: '24px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  title: {
    margin: '0 0 20px 0',
    color: '#333',
  },
  formGroup: {
    marginBottom: '20px',
  },
  label: {
    display: 'block',
    marginBottom: '8px',
    fontWeight: '600',
    color: '#555',
  },
  fileInput: {
    display: 'block',
    width: '100%',
    padding: '10px',
    border: '2px dashed #ccc',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  textarea: {
    width: '100%',
    minHeight: '200px',
    padding: '12px',
    border: '1px solid #ccc',
    borderRadius: '4px',
    fontFamily: 'inherit',
    fontSize: '14px',
    resize: 'vertical',
    boxSizing: 'border-box',
  },
  button: {
    backgroundColor: '#007bff',
    color: '#fff',
    border: 'none',
    padding: '12px 24px',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
    width: '100%',
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
    cursor: 'not-allowed',
  },
  preview: {
    maxWidth: '100%',
    maxHeight: '200px',
    marginTop: '10px',
    borderRadius: '4px',
  },
  error: {
    color: '#dc3545',
    marginTop: '10px',
  },
  hint: {
    fontSize: '12px',
    color: '#666',
    marginTop: '4px',
  },
};

export default function UploadForm({ onAnalysisStarted }) {
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [userStories, setUserStories] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onload = (e) => setImagePreview(e.target.result);
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!imageFile) {
      setError('Please select an ERD image');
      return;
    }

    if (!userStories.trim()) {
      setError('Please enter user stories');
      return;
    }

    setLoading(true);

    try {
      const analysis = await submitAnalysis(imageFile, userStories);
      onAnalysisStarted(analysis);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Upload ERD for Analysis</h2>

      <form onSubmit={handleSubmit}>
        <div style={styles.formGroup}>
          <label style={styles.label}>ERD Image</label>
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.gif,.webp"
            onChange={handleImageChange}
            style={styles.fileInput}
          />
          <p style={styles.hint}>Supported formats: PNG, JPG, GIF, WebP</p>
          {imagePreview && (
            <img src={imagePreview} alt="ERD Preview" style={styles.preview} />
          )}
        </div>

        <div style={styles.formGroup}>
          <label style={styles.label}>User Stories</label>
          <textarea
            value={userStories}
            onChange={(e) => setUserStories(e.target.value)}
            placeholder="Enter your user stories here, one per line...

Example:
As a user, I want to create an account so I can save my preferences.
As a user, I want to add items to my cart so I can purchase them later.
As an admin, I want to view all orders so I can manage fulfillment."
            style={styles.textarea}
          />
        </div>

        {error && <p style={styles.error}>{error}</p>}

        <button
          type="submit"
          disabled={loading}
          style={{
            ...styles.button,
            ...(loading ? styles.buttonDisabled : {}),
          }}
        >
          {loading ? 'Submitting...' : 'Analyze ERD'}
        </button>
      </form>
    </div>
  );
}
