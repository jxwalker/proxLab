import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { databasesApi } from '../api/client'
import { Trash2, Copy, Check } from 'lucide-react'

export default function Databases() {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [copied, setCopied] = useState<string | null>(null)
  const { data: databases = [] } = useQuery({ queryKey: ['databases'], queryFn: databasesApi.list })

  const create = useMutation({
    mutationFn: () => databasesApi.create(name),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['databases'] }); setName('') },
  })

  const drop = useMutation({
    mutationFn: (n: string) => databasesApi.drop(n),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['databases'] }),
  })

  function copyDsn(dsn: string) {
    navigator.clipboard.writeText(dsn)
    setCopied(dsn)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Databases</h1>
      <div className="flex gap-3 mb-6">
        <input value={name} onChange={e => setName(e.target.value)}
          className="input" placeholder="database-name" />
        <button onClick={() => create.mutate()} disabled={!name || create.isPending}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-4 py-2 rounded text-sm font-medium">
          Create DB
        </button>
      </div>
      {databases.length === 0 ? (
        <p className="text-gray-500">No databases yet.</p>
      ) : (
        <div className="space-y-3">
          {databases.map(d => (
            <div key={d.name} className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium">{d.name}</span>
                  <span className="text-gray-400 text-xs ml-2">owner: {d.owner}</span>
                  <span className="text-gray-500 text-xs ml-2">{d.size_mb.toFixed(1)} MB</span>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => copyDsn(d.connection_string)}
                    className="p-1.5 hover:bg-gray-700 text-gray-400 rounded" title="Copy DSN">
                    {copied === d.connection_string ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                  </button>
                  <button onClick={() => { if (confirm(`Drop database '${d.name}'?`)) drop.mutate(d.name) }}
                    className="p-1.5 hover:bg-red-900 text-red-400 rounded">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
              <div className="mt-2 font-mono text-xs text-gray-500 bg-gray-900 rounded px-2 py-1 truncate">
                {d.connection_string}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
