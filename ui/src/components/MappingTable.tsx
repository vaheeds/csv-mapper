import React from 'react'
import type { Schema, CsvColumn } from '../types'

interface Props {
  schema: Schema
  csvColumns: CsvColumn[]
  mapping: Record<string, string>
  onChangeMapping: (schemaField: string, csvColumn: string) => void
}

export const MappingTable: React.FC<Props> = ({ 
  schema, 
  csvColumns, 
  mapping, 
  onChangeMapping 
}) => {
  return (
    <div id="mapping-table-container" style={{ marginTop: '10px' }}>
      <table>
        <thead>
          <tr>
            <th>Schema Field</th>
            <th>CSV Column</th>
          </tr>
        </thead>
        <tbody>
          {schema.fields.map((field) => (
            <tr key={field.name}>
              <td>{field.name}<span style={{ color: 'red', fontSize: '20px' }}>{field.required ? '*' : ''}</span></td>
              <td>
                <select
                  value={mapping[field.name] ?? ''}
                  onChange={(e) => onChangeMapping(field.name, e.target.value)}
                >
                  <option value="">-- Not mapped --</option>
                  {csvColumns.map((col) => (
                    <option key={col.name} value={col.name}>
                      {col.name}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
