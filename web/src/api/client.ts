import axios from 'axios'

const TOKEN_KEY = 'proxlab_token'

export const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

// ---- Types ----------------------------------------------------------------

export interface Server {
  id: number
  name: string
  status: 'running' | 'stopped' | 'pending' | 'error'
  ip?: string
  flavor: string
  template: string
  cores: number
  memory_mb: number
  disk_gb: number
  node: string
  storage_dataset?: string
  database_name?: string
  task_id?: string
}

export interface Flavor {
  name: string
  cores: number
  memory_mb: number
  disk_gb: number
  description: string
}

export interface StorageDataset {
  name: string
  dataset_path: string
  nfs_path: string
  nfs_server: string
  quota_gb: number
  used_gb: number
  available_gb: number
}

export interface Database {
  name: string
  owner: string
  size_mb: number
  connection_string: string
}

export interface Task {
  id: string
  type: string
  status: 'pending' | 'running' | 'ok' | 'error'
  node: string
  vmid?: number
  log?: string[]
  error?: string
}

export interface ServerCreate {
  name: string
  flavor: string
  template: string
  cores?: number
  memory_mb?: number
  disk_gb?: number
  storage_name?: string
  storage_quota_gb?: number
  database_name?: string
  ssh_keys?: string[]
}

// ---- API calls ------------------------------------------------------------

export const serversApi = {
  list: () => api.get<Server[]>('/servers').then(r => r.data),
  get: (id: number) => api.get<Server>(`/servers/${id}`).then(r => r.data),
  create: (data: ServerCreate) => api.post<Task>('/servers', data).then(r => r.data),
  batchCreate: (servers: ServerCreate[]) => api.post<Task[]>('/servers/batch', { servers }).then(r => r.data),
  action: (id: number, action: 'os-start' | 'os-stop' | 'os-reboot') =>
    api.post<Task>(`/servers/${id}/action`, { action }).then(r => r.data),
  destroy: (id: number) => api.delete(`/servers/${id}`),
}

export const flavorsApi = {
  list: () => api.get<Flavor[]>('/flavors').then(r => r.data),
}

export const storageApi = {
  list: () => api.get<StorageDataset[]>('/storage').then(r => r.data),
  create: (name: string, quota_gb: number) => api.post<StorageDataset>('/storage', { name, quota_gb }).then(r => r.data),
  delete: (name: string) => api.delete(`/storage/${name}`),
}

export const databasesApi = {
  list: () => api.get<Database[]>('/databases').then(r => r.data),
  create: (name: string) => api.post<Database>('/databases', { name }).then(r => r.data),
  get: (name: string) => api.get<Database>(`/databases/${name}`).then(r => r.data),
  drop: (name: string) => api.delete(`/databases/${name}`),
}

export const tasksApi = {
  get: (id: string) => api.get<Task>(`/tasks/${id}`).then(r => r.data),
}
