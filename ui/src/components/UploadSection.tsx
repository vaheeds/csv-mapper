import React, { useState, type FormEvent } from 'react'
import { api } from '../services/api'

interface Props {
  onUploadComplete: (fileId: string, hasHeader: boolean) => void
  onRefreshMappings: () => void
}

export const UploadSection: React.FC<Props> = ({ onUploadComplete, onRefreshMappings }) => {
  const [headerStatus, setHeaderStatus] = useState<string>('')
  const [status, setStatus] = useState<string>('')
  const [statusClass, setStatusClass] = useState<string>('')

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = event.currentTarget
    const fileInput = form.elements.namedItem('file') as HTMLInputElement
    
    if (!fileInput?.files?.length) return

    try {
      const data = await api.uploadFile(fileInput.files[0])
      
      onUploadComplete(data.file_id, data.has_header)
      setHeaderStatus(data.has_header ? 'File has header row.' : 'No header row is detected. Mapping will be suggested based on the column content.')
      setStatus(`Uploaded as file_id=${data.file_id}`)
      setStatusClass('success')
      
      // Refresh saved mappings list after successful upload
      onRefreshMappings()
    } catch (err: any) {
      console.error(err)
      setHeaderStatus('')
      setStatus(err.message || 'Upload failed.')
      setStatusClass('error')
    }
  }

  return (
    <section>
      <form id="upload-form" onSubmit={handleSubmit}>
        <input className='mb-3' type="file" id="file" name="file" accept=".csv" required />
        <button className='btn btn-primary'type="submit" style={{ marginLeft: '0.75rem' }}>Upload</button>
      </form>
      <p id="header-status" className={headerStatus === 'File has header row.' ? "text-success" : "text-danger"}>
        {headerStatus}
      </p>
      <p id="upload-status" className={statusClass}>
        {status}
      </p>
    </section>
  )
}
