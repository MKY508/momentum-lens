import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Target, 
  Satellite, 
  FileText, 
  BarChart3, 
  Settings,
  TrendingUp
} from 'lucide-react'
import clsx from 'clsx'

interface NavItem {
  path: string
  label: string
  icon: React.ReactNode
}

const navItems: NavItem[] = [
  { path: '/dashboard', label: '决策台', icon: <LayoutDashboard size={20} /> },
  { path: '/core', label: 'Core模块', icon: <Target size={20} /> },
  { path: '/satellite', label: '卫星模块', icon: <Satellite size={20} /> },
  { path: '/convertible', label: '可转债', icon: <FileText size={20} /> },
  { path: '/kpi', label: '日志KPI', icon: <BarChart3 size={20} /> },
  { path: '/settings', label: '设置', icon: <Settings size={20} /> },
]

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation()

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <aside className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
        <div className="p-6">
          <div className="flex items-center space-x-2">
            <TrendingUp className="text-blue-600" size={28} />
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              动量透镜
            </h1>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            ETF核心卫星策略系统
          </p>
        </div>
        
        <nav className="px-4 pb-6">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={clsx(
                'flex items-center space-x-3 px-3 py-2.5 rounded-lg mb-1 transition-colors',
                location.pathname === item.path
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              )}
            >
              {item.icon}
              <span className="font-medium">{item.label}</span>
            </Link>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  )
}

export default Layout