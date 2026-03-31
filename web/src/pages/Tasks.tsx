import { useQuery } from '@tanstack/react-query'
import { tasksApi } from '../api/client'

// Tasks page shows recent tasks from the in-memory store
// We can only show tasks we know about (no persistent store yet)
export default function Tasks() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Tasks</h1>
      <p className="text-gray-500 text-sm">
        Tasks are tracked per-session. Use <code className="bg-gray-800 px-1 rounded">GET /api/tasks/&#123;id&#125;</code> to
        poll any task by ID, or check <a href="https://192.168.8.197:8006" target="_blank" rel="noreferrer"
          className="text-indigo-400 hover:underline">Proxmox UI</a> for full task history.
      </p>
    </div>
  )
}
