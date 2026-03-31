import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { serversApi, storageApi, databasesApi } from '../api/client'

export default function Dashboard() {
  const { data: servers = [] } = useQuery({ queryKey: ['servers'], queryFn: serversApi.list })
  const { data: storage = [] } = useQuery({ queryKey: ['storage'], queryFn: storageApi.list })
  const { data: databases = [] } = useQuery({ queryKey: ['databases'], queryFn: databasesApi.list })

  const running = servers.filter(s => s.status === 'running').length
  const stopped = servers.filter(s => s.status === 'stopped').length
  const totalUsedGb = storage.reduce((a, d) => a + d.used_gb, 0)
  const totalQuotaGb = storage.reduce((a, d) => a + d.quota_gb, 0)

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Running" value={running} color="text-green-400" />
        <StatCard label="Stopped" value={stopped} color="text-gray-400" />
        <StatCard label="NAS Datasets" value={storage.length} color="text-blue-400" />
        <StatCard label="Databases" value={databases.length} color="text-purple-400" />
      </div>
      {storage.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-4 mb-4">
          <h2 className="text-sm font-semibold text-gray-400 mb-2">NAS Storage</h2>
          <div className="flex items-center gap-3">
            <div className="flex-1 bg-gray-700 rounded-full h-3">
              <div
                className="bg-blue-500 h-3 rounded-full"
                style={{ width: `${Math.min(100, (totalUsedGb / (totalQuotaGb || 1)) * 100)}%` }}
              />
            </div>
            <span className="text-sm text-gray-300">{totalUsedGb.toFixed(1)} / {totalQuotaGb} GB</span>
          </div>
        </div>
      )}
      <div className="bg-gray-800 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-400 mb-3">Servers</h2>
        {servers.length === 0 ? (
          <p className="text-gray-500 text-sm">No servers yet. <Link to="/launch" className="text-indigo-400 hover:underline">Launch one →</Link></p>
        ) : (
          <div className="space-y-2">
            {servers.map(s => (
              <div key={s.id} className="flex items-center gap-3 text-sm">
                <StatusDot status={s.status} />
                <span className="font-mono">{s.name}</span>
                <span className="text-gray-400">{s.ip || '—'}</span>
                <span className="text-gray-500 ml-auto">{s.flavor} · {s.cores}c/{s.memory_mb}MB</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className={`text-3xl font-bold ${color}`}>{value}</div>
      <div className="text-sm text-gray-400 mt-1">{label}</div>
    </div>
  )
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    running: 'bg-green-400',
    stopped: 'bg-gray-500',
    pending: 'bg-yellow-400',
    error: 'bg-red-400',
  }
  return <span className={`w-2 h-2 rounded-full inline-block ${colors[status] || 'bg-gray-500'}`} />
}
