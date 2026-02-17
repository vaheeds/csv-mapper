import React, { useState } from 'react'
import { api } from '../services/api'

interface Props {
  fileId: string
  hasHeader: boolean
  mapping: Record<string, string>
  onApplyMapping: (newMapping: Record<string, string>) => void
  onTriggerAutoSuggest: () => void
}

export const ActionPanel: React.FC<Props> = ({ 
  fileId, 
  hasHeader, 
  mapping, 
  onTriggerAutoSuggest 
}) => {
  const [status, setStatus] = useState<'idle' | 'validating' | 'success' | 'error'>('idle')
  const [errorList, setErrorList] = useState<string[]>([])

  const handleValidate = async () => {
    // Filter out empty mappings
    const mappingFiltered = Object.fromEntries(
      Object.entries(mapping).filter(([_, v]) => v != null && v !== '')
    )

    setStatus('validating')
    setErrorList([])

    try {
      const data = await api.validateMapping(fileId, hasHeader, mappingFiltered)
      
      if (data.is_valid) {
        setStatus('success')
      } else {
        setStatus('error')
        setErrorList(data.errors || [])
      }
    } catch (err) {
      console.error(err)
      setStatus('error')
      setErrorList(['System error: Failed to connect to validation service.'])
    }
  }

  return (
    <div style={{ marginBottom: '20px' }}>
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
        <button className='btn btn-secondary'
          type="button" 
          onClick={onTriggerAutoSuggest}
          style={{ background: '#f0f0f0', color: '#333' }}
        >
          Reset & Auto Suggest
        </button>

        <button className='btn btn-primary'
          type="button" 
          onClick={handleValidate}
          disabled={status === 'validating'}
          style={{ background: '#007bff', color: 'white' }}
        >
          {status === 'validating' ? 'Validating...' : 'Validate Mapping'}
        </button>
      </div>

      {status === 'success' && (
        <div style={{ 
          padding: '10px', 
          background: '#d4edda', 
          color: '#155724', 
          borderRadius: '4px',
          border: '1px solid #c3e6cb'
        }}>
          <strong>✅ Validation Successful!</strong> All required fields are properly mapped.
        </div>
      )}

      {status === 'error' && errorList.length > 0 && (
        <ValidationReport errors={errorList} />
      )}
    </div>
  )
}

// Cap the visual rendering to 100 errors to prevent DOM freezing if there are 10k errors
const ValidationReport: React.FC<{ errors: string[] }> = ({ errors }) => {
  const MAX_DISPLAY = 100
  const totalCount = errors.length
  const displayErrors = errors.slice(0, MAX_DISPLAY)
  const remaining = totalCount - MAX_DISPLAY

  return (
    <div style={{ 
      marginTop: '10px', 
      border: '1px solid #f5c6cb', 
      borderRadius: '4px', 
      background: '#fff' 
    }}>
      {/* Header */}
      <div style={{ 
        padding: '10px', 
        background: '#f8d7da', 
        color: '#721c24',
        borderBottom: '1px solid #f5c6cb',
        fontWeight: 'bold'
      }}>
        Validation Failed: {totalCount} error{totalCount !== 1 ? 's' : ''} found
      </div>

      {/* Scrollable List Container */}
      <div style={{ 
        maxHeight: '200px', // Fixed height prevents UI freezing
        overflowY: 'auto', 
        padding: '10px',
        fontSize: '0.9rem'
      }}>
        <ul style={{ margin: 0, paddingLeft: '20px', color: '#dc3545' }}>
          {displayErrors.map((err, i) => (
            <li key={i} style={{ marginBottom: '4px' }}>{err}</li>
          ))}
        </ul>

        {remaining > 0 && (
          <div style={{ 
            marginTop: '8px', 
            fontStyle: 'italic', 
            color: '#666', 
            textAlign: 'center' 
          }}>
            ... and {remaining} more errors.
          </div>
        )}
      </div>
    </div>
  )
}
