import { useState, useEffect } from 'react'
nimport { getPlanner, updatePlannerItem, deletePlannerItem, purgePlanner } from '../services/api'

const PlannerView = () => {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({ title: '', description: '' })
  const [actionLoading, setActionLoading] = useState(false)

  const loadPlanner = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getPlanner()
      setItems(data.items || [])
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load planner')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPlanner()
  }, [refreshKey])

  // Expose refresh function to parent
  useEffect(() => {
    window.refreshPlanner = () => setRefreshKey(k => k + 1)
  }, [])

  const formatDate = (dateString) => {
    if (!dateString) return 'No date'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    })
  }

  const groupByDate = (items) => {
    const grouped = {}
    items.forEach(item => {
      const date = item.date || 'No Date'
      if (!grouped[date]) {
        grouped[date] = []
      }
      grouped[date].push(item)
    })
    return grouped
  }

  const startEdit = (item) => {
    setEditingId(item.id)
    setEditForm({
      title: item.title || '',
      description: item.description || '',
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditForm({ title: '', description: '' })
  }

  const handleEditChange = (e) => {
    const { name, value } = e.target
    setEditForm(prev => ({ ...prev, [name]: value }))
  }

  const saveEdit = async (itemId) => {
    try {
      setActionLoading(true)
      await updatePlannerItem(itemId, {
        title: editForm.title,
        description: editForm.description,
      })
      setEditingId(null)
      setEditForm({ title: '', description: '' })
      await loadPlanner()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to update item')
    } finally {
      setActionLoading(false)
    }
  }

  const toggleCompleted = async (item) => {
    try {
      setActionLoading(true)
      await updatePlannerItem(item.id, { is_completed: !item.is_completed })
      await loadPlanner()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to update item status')
    } finally {
      setActionLoading(false)
    }
  }

  const handleDelete = async (itemId) => {
    if (!window.confirm('Delete this planner item? This cannot be undone.')) return
    try {
      setActionLoading(true)
      await deletePlannerItem(itemId)
      await loadPlanner()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to delete item')
    } finally {
      setActionLoading(false)
    }
  }

  const handlePurge = async () => {
    if (!window.confirm('Purge all planner items for this user? This cannot be undone.')) return
    try {
      setActionLoading(true)
      await purgePlanner()
      await loadPlanner()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to purge planner')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return <div className="loading">Loading planner...</div>
  }

  if (error) {
    return <div className="error">Error: {error}</div>
  }

  const groupedItems = groupByDate(items)
  const sortedDates = Object.keys(groupedItems).sort((a, b) => {
    if (a === 'No Date') return 1
    if (b === 'No Date') return -1
    return new Date(a) - new Date(b)
  })

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2>Your Planner</h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={loadPlanner} className="btn" style={{ padding: '0.5rem 1rem' }} disabled={actionLoading}>
            Refresh
          </button>
          <button
            onClick={handlePurge}
            className="btn"
            style={{ padding: '0.5rem 1rem', backgroundColor: '#e53e3e' }}
            disabled={actionLoading || items.length === 0}
          >
            Purge All
          </button>
        </div>
      </div>

      {items.length === 0 ? (
        <p style={{ color: '#666', textAlign: 'center', padding: '2rem' }}>
          No items in your planner yet. Upload a syllabus to get started!
        </p>
      ) : (
        <div>
          {sortedDates.map(date => (
            <div key={date} style={{ marginBottom: '2rem' }}>
              <h3 style={{ 
                color: '#667eea', 
                marginBottom: '0.5rem',
                paddingBottom: '0.5rem',
                borderBottom: '2px solid #667eea'
              }}>
                {date}
              </h3>
              {groupedItems[date].map(item => (
                <div 
                  key={item.id} 
                  style={{
                    background: '#f9f9f9',
                    padding: '1rem',
                    marginBottom: '0.5rem',
                    borderRadius: '6px',
                    borderLeft: `4px solid ${item.item_type === 'assignment' ? '#667eea' : '#48bb78'}`,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                    <div style={{ flex: 1, marginRight: '0.75rem' }}>
                      {editingId === item.id ? (
                        <div>
                          <input
                            type="text"
                            name="title"
                            value={editForm.title}
                            onChange={handleEditChange}
                            style={{ width: '100%', marginBottom: '0.5rem', padding: '0.25rem 0.5rem' }}
                          />
                          <textarea
                            name="description"
                            value={editForm.description}
                            onChange={handleEditChange}
                            rows={3}
                            style={{ width: '100%', marginBottom: '0.5rem', padding: '0.25rem 0.5rem', resize: 'vertical' }}
                          />
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              className="btn"
                              style={{ padding: '0.25rem 0.75rem' }}
                              onClick={() => saveEdit(item.id)}
                              disabled={actionLoading}
                            >
                              Save
                            </button>
                            <button
                              className="btn-secondary"
                              style={{ padding: '0.25rem 0.75rem' }}
                              onClick={cancelEdit}
                              disabled={actionLoading}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <h4 style={{ marginBottom: '0.25rem' }}>{item.title}</h4>
                          {item.description && (
                            <p style={{ color: '#666', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                              {item.description}
                            </p>
                          )}
                        </>
                      )}
                      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem', color: '#888' }}>
                        {item.course?.course_code && (
                          <span><strong>Course:</strong> {item.course.course_code} - {item.course.course_name}</span>
                        )}
                        {item.weight && (
                          <span><strong>Weight:</strong> {item.weight}%</span>
                        )}
                        <span><strong>Type:</strong> {item.item_type}</span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', alignItems: 'flex-end' }}>
                      <button
                        className="btn"
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
                        onClick={() => toggleCompleted(item)}
                        disabled={actionLoading}
                      >
                        {item.is_completed ? 'Mark Incomplete' : 'Mark Done'}
                      </button>
                      <button
                        className="btn-secondary"
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
                        onClick={() => startEdit(item)}
                        disabled={actionLoading || editingId === item.id}
                      >
                        Edit
                      </button>
                      <button
                        className="btn"
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem', backgroundColor: '#e53e3e' }}
                        onClick={() => handleDelete(item.id)}
                        disabled={actionLoading}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default PlannerView