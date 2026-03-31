import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { flavorsApi, serversApi, ServerCreate } from '../api/client'

type FormData = {
  name: string
  flavor: string
  template: string
  count: number
  storage_name: string
  storage_quota_gb: number
  database_name: string
  ssh_key: string
}

export default function Launch() {
  const [step, setStep] = useState(1)
  const [tasks, setTasks] = useState<{ name: string; taskId: string; status: string }[]>([])
  const { data: flavors = [] } = useQuery({ queryKey: ['flavors'], queryFn: flavorsApi.list })
  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormData>({
    defaultValues: { flavor: 'small', template: 'base', count: 1, storage_quota_gb: 50 }
  })

  const selectedFlavor = flavors.find(f => f.name === watch('flavor'))

  const launch = useMutation({
    mutationFn: async (data: FormData) => {
      const servers: ServerCreate[] = Array.from({ length: data.count }, (_, i) => ({
        name: data.count > 1 ? `${data.name}-${i + 1}` : data.name,
        flavor: data.flavor,
        template: data.template,
        storage_name: data.storage_name || undefined,
        storage_quota_gb: data.storage_quota_gb || undefined,
        database_name: data.database_name || undefined,
        ssh_keys: data.ssh_key ? [data.ssh_key] : undefined,
      }))
      if (servers.length === 1) {
        const task = await serversApi.create(servers[0])
        return [{ name: servers[0].name, taskId: task.id, status: 'pending' }]
      } else {
        const taskList = await serversApi.batchCreate(servers)
        return taskList.map((t, i) => ({ name: servers[i].name, taskId: t.id, status: 'pending' }))
      }
    },
    onSuccess: (result) => {
      setTasks(result)
      setStep(4)
    },
  })

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Launch Servers</h1>

      {/* Step indicators */}
      <div className="flex items-center gap-2 mb-8">
        {[1, 2, 3].map(n => (
          <div key={n} className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
              step >= n ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-400'
            }`}>{n}</div>
            {n < 3 && <div className={`flex-1 h-0.5 w-16 ${step > n ? 'bg-indigo-600' : 'bg-gray-700'}`} />}
          </div>
        ))}
        <span className="ml-4 text-sm text-gray-400">
          {step === 1 && 'Choose flavor & template'}
          {step === 2 && 'Configure'}
          {step === 3 && 'Review & launch'}
          {step === 4 && 'Launching…'}
        </span>
      </div>

      {step < 4 && (
        <form onSubmit={handleSubmit(data => launch.mutate(data))}>
          {step === 1 && (
            <div className="space-y-4">
              <label className="block">
                <span className="text-sm text-gray-400 mb-1 block">Flavor</span>
                <div className="grid grid-cols-2 gap-3">
                  {flavors.map(f => (
                    <label key={f.name} className="cursor-pointer">
                      <input type="radio" value={f.name} {...register('flavor')} className="sr-only" />
                      <div className={`border rounded-lg p-3 text-sm transition-colors ${
                        watch('flavor') === f.name
                          ? 'border-indigo-500 bg-indigo-950'
                          : 'border-gray-600 hover:border-gray-500'
                      }`}>
                        <div className="font-semibold">{f.name}</div>
                        <div className="text-gray-400 text-xs">{f.cores}c · {f.memory_mb}MB · {f.disk_gb}GB</div>
                        <div className="text-gray-500 text-xs mt-1">{f.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </label>
              <label className="block">
                <span className="text-sm text-gray-400 mb-1 block">Template</span>
                <div className="grid grid-cols-2 gap-3">
                  {['base', 'dev'].map(t => (
                    <label key={t} className="cursor-pointer">
                      <input type="radio" value={t} {...register('template')} className="sr-only" />
                      <div className={`border rounded-lg p-3 text-sm transition-colors ${
                        watch('template') === t
                          ? 'border-indigo-500 bg-indigo-950'
                          : 'border-gray-600 hover:border-gray-500'
                      }`}>
                        <div className="font-semibold">{t}</div>
                        <div className="text-gray-500 text-xs">
                          {t === 'base' ? 'Ubuntu 24.04 + Tailscale' : 'Base + full dev toolchain (zsh, nvim, docker, nvm, pyenv, go, rust…)'}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </label>
              <button type="button" onClick={() => setStep(2)}
                className="mt-4 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2 rounded text-sm font-medium w-full">
                Next →
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <Field label="Server name" error={errors.name?.message}>
                <input {...register('name', { required: 'Required' })}
                  className="input w-full" placeholder="my-server" />
              </Field>
              <Field label="Count (batch)">
                <input type="number" {...register('count', { min: 1, max: 50 })}
                  className="input w-24" />
                <span className="text-xs text-gray-500 ml-2">Names will be suffixed -1, -2… for count &gt; 1</span>
              </Field>
              <Field label="NAS storage name (optional)">
                <input {...register('storage_name')} className="input w-full" placeholder="my-project-data" />
              </Field>
              <Field label="NAS quota (GB)">
                <input type="number" {...register('storage_quota_gb')} className="input w-24" />
              </Field>
              <Field label="Postgres database name (optional)">
                <input {...register('database_name')} className="input w-full" placeholder="myapp" />
              </Field>
              <Field label="SSH public key (optional)">
                <textarea {...register('ssh_key')} rows={3}
                  className="input w-full font-mono text-xs" placeholder="ssh-ed25519 AAAA..." />
              </Field>
              <div className="flex gap-3">
                <button type="button" onClick={() => setStep(1)}
                  className="flex-1 border border-gray-600 hover:border-gray-500 text-gray-300 px-5 py-2 rounded text-sm font-medium">
                  ← Back
                </button>
                <button type="button" onClick={() => setStep(3)}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2 rounded text-sm font-medium">
                  Review →
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div className="bg-gray-800 rounded-lg p-4 space-y-2 text-sm">
                <Row label="Name" value={watch('name')} />
                <Row label="Count" value={String(watch('count'))} />
                <Row label="Flavor" value={`${watch('flavor')} (${selectedFlavor?.cores}c · ${selectedFlavor?.memory_mb}MB · ${selectedFlavor?.disk_gb}GB)`} />
                <Row label="Template" value={watch('template')} />
                {watch('storage_name') && <Row label="NAS storage" value={`${watch('storage_name')} (${watch('storage_quota_gb')}GB)`} />}
                {watch('database_name') && <Row label="Database" value={watch('database_name')} />}
              </div>
              <div className="flex gap-3">
                <button type="button" onClick={() => setStep(2)}
                  className="flex-1 border border-gray-600 text-gray-300 px-5 py-2 rounded text-sm">
                  ← Back
                </button>
                <button type="submit" disabled={launch.isPending}
                  className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-5 py-2 rounded text-sm font-medium">
                  {launch.isPending ? 'Launching…' : '🚀 Launch'}
                </button>
              </div>
            </div>
          )}
        </form>
      )}

      {step === 4 && (
        <div className="space-y-3">
          {tasks.map(t => (
            <div key={t.taskId} className="bg-gray-800 rounded-lg p-3 flex items-center gap-3 text-sm">
              <TaskPoller taskId={t.taskId} name={t.name} />
            </div>
          ))}
          <button onClick={() => { setStep(1); setTasks([]) }}
            className="mt-4 text-indigo-400 hover:underline text-sm">
            Launch another →
          </button>
        </div>
      )}
    </div>
  )
}

function TaskPoller({ taskId, name }: { taskId: string; name: string }) {
  const { data } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => import('../api/client').then(m => m.tasksApi.get(taskId)),
    refetchInterval: (q) => (q.state.data?.status === 'ok' || q.state.data?.status === 'error') ? false : 2000,
  })
  const status = data?.status ?? 'pending'
  const icons: Record<string, string> = { pending: '⏳', running: '⚙️', ok: '✅', error: '❌' }
  return (
    <>
      <span>{icons[status]}</span>
      <span className="font-mono">{name}</span>
      <span className="text-gray-400 ml-auto capitalize">{status}</span>
      {data?.error && <span className="text-red-400 text-xs">{data.error}</span>}
    </>
  )
}

function Field({ label, children, error }: { label: string; children: React.ReactNode; error?: string }) {
  return (
    <div>
      <label className="block text-sm text-gray-400 mb-1">{label}</label>
      {children}
      {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-400">{label}</span>
      <span className="text-white">{value}</span>
    </div>
  )
}
