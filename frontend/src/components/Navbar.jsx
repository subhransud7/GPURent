import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { 
  CpuChipIcon, 
  UserIcon,
  ArrowRightOnRectangleIcon,
  Cog8ToothIcon
} from '@heroicons/react/24/outline'

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <nav className="bg-white shadow-lg border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-2">
              <CpuChipIcon className="h-8 w-8 text-blue-600" />
              <span className="font-bold text-xl text-gray-900">
                P2P GPU Cloud
              </span>
            </Link>
          </div>

          {/* Navigation Links */}
          <div className="hidden md:block">
            <div className="flex items-center space-x-8">
              <Link 
                to="/marketplace" 
                className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium transition duration-150"
              >
                GPU Marketplace
              </Link>
              
              {isAuthenticated && (
                <Link 
                  to="/dashboard" 
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium transition duration-150"
                >
                  Dashboard
                </Link>
              )}
            </div>
          </div>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            {isAuthenticated ? (
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  <UserIcon className="h-5 w-5 text-gray-400" />
                  <span className="text-sm text-gray-700">
                    {user?.username || user?.email}
                  </span>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    user?.role === 'host' ? 'bg-green-100 text-green-800' :
                    user?.role === 'admin' ? 'bg-purple-100 text-purple-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {user?.role}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-1 text-gray-500 hover:text-red-600 px-3 py-2 text-sm font-medium transition duration-150"
                >
                  <ArrowRightOnRectangleIcon className="h-4 w-4" />
                  <span>Logout</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-4">
                <Link 
                  to="/login"
                  className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium transition duration-150"
                >
                  Login
                </Link>
                <Link 
                  to="/register"
                  className="bg-blue-600 text-white hover:bg-blue-700 px-4 py-2 rounded-lg text-sm font-medium transition duration-150"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}