import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { serversApi, Server } from '../api/client'
import { Play, Square, Trash2, Terminal } from 'lucide-react'

const STATUS_BADGE: Record<string, string> = {
  running: 'bg-green-900 text-green-300',
  stopped: 'bg-gray-700 text-gray-400',
  pending: 'bg-yellow-900 text-yellow-300',
  error: 'bg-red-900 text-red-300',
}

export default function Servers() {
  const qc = useQueryClient()
  const { data: servers = [], isLoading } = useQuery({ queryKey: ['servers'], queryFn: serversApi.list })

  const action = useMutation({
    mutationFn: ({ id, act }: { id: number; act: 'os-start' | 'os-stop' | 'os-reboot' }) =>
      serversApi.action(id, act),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['servers'] }),
  })

  const destroy = useMutation({
    mutationFn: (id: number) => serversApi.destroy(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['servers'] }),
  })

  if (isLoading) return <p className="text-gray-400">Loading…</p>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Servers</h1>
        <Link to="/launch" className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded text-sm font-medium">
          + Launch
        </Link>
      </div>

      {servers.length === 0 ? (
        <p className="text-gray-500">No servers. <Link to="/launch" className="text-indigo-400 hover:underline">Launch one →</Link></p>
      ) : (
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-700 text-gray-300">
              <tr>
                <th className="text-left px-4 py-3">ID</th>
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">IP</th>
                <th className="text-left px-4 py-3">Flavor</th>
                <th className="text-left px-4 py-3">Resources</th>
                <th className="text-right px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {servers.map((s: Server) => (
                <tr key={s.id} className="hover:bg-gray-750">
                  <td className="px-4 py-3 text-gray-400 font-mono">{s.id}</td>
                  <td className="px-4 py-3 font-medium">{s.name}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_BADGE[s.status] || STATUS_BADGE.stopped}`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-300">{s.ip || '—'}</td>
                  <td className="px-4 py-3 text-gray-300">{s.flavor}</td>
                  <td className="px-4 py-3 text-gray-400">{s.cores}c · {s.memory_mb}MB</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {s.status === 'stopped' && (
                        <button
                          onClick={() => action.mutate({ id: s.id, act: 'os-start' })}
                          className="p-1.5 rounded hover:bg-green-900 text-green-400"
                          title="Start"
                        >
                          <Play size={14} />
                        </button>
                      )}
                      {s.status === 'running' && (
                        <>
                          <button
                            onClick={() => action.mutate({ id: s.id, act: 'os-stop' })}
                            className="p-1.5 rounded hover:bg-yellow-900 text-yellow-400"
                            title="Stop"
                          >
                            <Square size={14} />
                          </button>
                          {s.ip && (
                            <a
                              href={`ssh://ubuntu@${s.ip}`}
                              className="p-1.5 rounded hover:bg-gray-700 text-gray-400"
                              title="SSH"
                            >
                              <Terminal size={14} />
                            </a>
                          )}
                        </>
                      )}
                      <button
                        onClick={() => {
                          if (confirm(`Destroy ${s.name} (VMID ${s.id})?`)) destroy.mutate(s.id)
                        }}
                        className="p-1.5 rounded hover:bg-red-900 text-red-400"
                        title="Destroy"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
