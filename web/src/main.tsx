import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import Dashboard from './pages/Dashboard'
import Servers from './pages/Servers'
import Launch from './pages/Launch'
import Storage from './pages/Storage'
import Databases from './pages/Databases'
import Tasks from './pages/Tasks'

import './index.css'

const qc = new QueryClient({
  defaultOptions: { queries: { refetchInterval: 10_000 } }
})

function Nav() {
  const link = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded text-sm font-medium transition-colors ${
      isActive ? 'bg-indigo-700 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'
    }`
  return (
    <nav className="bg-gray-900 border-b border-gray-700 px-6 py-3 flex items-center gap-6">
      <span className="text-white font-bold text-lg mr-4">proxlab</span>
      <NavLink to="/" end className={link}>Dashboard</NavLink>
      <NavLink to="/servers" className={link}>Servers</NavLink>
      <NavLink to="/launch" className={link}>Launch</NavLink>
      <NavLink to="/storage" className={link}>Storage</NavLink>
      <NavLink to="/databases" className={link}>Databases</NavLink>
      <NavLink to="/tasks" className={link}>Tasks</NavLink>
    </nav>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-950 text-gray-100">
          <Nav />
          <main className="p-6">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/servers" element={<Servers />} />
              <Route path="/launch" element={<Launch />} />
              <Route path="/storage" element={<Storage />} />
              <Route path="/databases" element={<Databases />} />
              <Route path="/tasks" element={<Tasks />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
)
