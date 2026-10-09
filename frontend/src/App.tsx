import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { BotDetail } from './pages/BotDetail'
import { BotCreate } from './pages/BotCreate'
import { Journal } from './pages/Journal'
import { Compare } from './pages/Compare'
import { Settings } from './pages/Settings'
import { DecisionHistory } from './pages/DecisionHistory'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="layout">
        <aside className="sidebar">
          <div className="brand">Trading Bot</div>
          <nav>
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/bots/new">New bot</NavLink>
            <NavLink to="/decisions">Decisions</NavLink>
            <NavLink to="/journal">Journal</NavLink>
            <NavLink to="/compare">Compare</NavLink>
            <NavLink to="/settings">Settings</NavLink>
          </nav>
        </aside>
        <main className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/bots/new" element={<BotCreate />} />
            <Route path="/bots/:id" element={<BotDetail />} />
            <Route path="/journal" element={<Journal />} />
            <Route path="/journal/:runId" element={<Journal />} />
            <Route path="/decisions" element={<DecisionHistory />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
