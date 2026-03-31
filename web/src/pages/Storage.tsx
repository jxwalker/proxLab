import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { storageApi } from '../api/client'
import { Trash2 } from 'lucide-react'

export default function Storage() {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [quota, setQuota] = useState(50)
  const { data: datasets = [] } = useQuery({ queryKey: ['storage'], queryFn: storageApi.list })

  const create = useMutation({
    mutationFn: () => storageApi.create(name, quota),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['storage'] }); setName('') },
  })

  const del = useMutation({
    mutationFn: (n: string) => storageApi.delete(n),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['storage'] }),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">NAS Storage</h1>
      <div className="flex gap-3 mb-6">
        <input value={name} onChange={e => setName(e.target.value)}
          className="input" placeholder="dataset-name" />
        <input type="number" value={quota} onChange={e => setQuota(+e.target.value)}
          className="input w-24" />
        <span className="self-center text-gray-400 text-sm">GB</span>
        <button onClick={() => create.mutate()} disabled={!name || create.isPending}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-4 py-2 rounded text-sm font-medium">
          Allocate
        </button>
      </div>
      {datasets.length === 0 ? (
        <p className="text-gray-500">No proxlab storage datasets yet.</p>
      ) : (
        <div className="space-y-3">
          {datasets.map(d => (
            <div key={d.name} className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="font-medium">{d.name}</span>
                  <span className="text-gray-400 text-xs ml-2 font-mono">{d.nfs_server}:{d.nfs_path}</span>
                </div>
                <button onClick={() => { if (confirm(`Delete ${d.name}?`)) del.mutate(d.name) }}
                  className="p-1.5 hover:bg-red-900 text-red-400 rounded">
                  <Trash2 size={14} />
                </button>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <div className="flex-1 bg-gray-700 rounded-full h-1.5">
                  <div className="bg-blue-500 h-1.5 rounded-full"
                    style={{ width: `${Math.min(100, (d.used_gb / (d.quota_gb || 1)) * 100)}%` }} />
                </div>
                <span>{d.used_gb.toFixed(1)} / {d.quota_gb} GB</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
