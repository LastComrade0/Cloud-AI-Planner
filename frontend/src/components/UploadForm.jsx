import { useState } from 'react'
import { uploadSyllabus } from '../services/api'

const UploadForm = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
    setError(null)
    setSuccess(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) {
      setError('Please select a file')
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const result = await uploadSyllabus(file)
      setSuccess(`Syllabus processed successfully! Document ID: ${result.document_id}`)
      setFile(null)
      e.target.reset()
      
      // Notify parent component to refresh planner
      if (onUploadSuccess) {
        onUploadSuccess()
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h2>Upload Syllabus</h2>
      <p style={{ marginBottom: '1rem', color: '#666' }}>
        Upload a PDF or image of your course syllabus to automatically extract assignments and important dates.
      </p>
      
      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.tiff"
          onChange={handleFileChange}
          disabled={loading}
        />
        
        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}
        
        <button type="submit" className="btn" disabled={loading || !file}>
          {loading ? 'Processing...' : 'Upload Syllabus'}
        </button>
      </form>
    </div>
  )
}

export default UploadForm