import React from 'react'
import type { CsvColumn } from '../types'

interface Props {
  columns: CsvColumn[]
  rows: string[][]
}

export const PreviewTable: React.FC<Props> = ({ columns, rows }) => {
  if (!rows || rows.length === 0) return null

  return (
    <div style={{ marginTop: '20px', overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
        <thead>
          <tr style={{ background: '#f5f5f5', textAlign: 'left' }}>
            {columns.map((col, idx) => (
              <th key={idx} style={{ padding: '8px', borderBottom: '2px solid #ddd' }}>
                {col.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <tr key={rowIdx} style={{ borderBottom: '1px solid #eee' }}>
              {row.map((cell, cellIdx) => (
                <td key={cellIdx} style={{ padding: '8px' }}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
