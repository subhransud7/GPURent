import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { 
  CpuChipIcon, 
  UserIcon,
  ArrowRightOnRectangleIcon,
  Cog8ToothIcon
} from '@heroicons/react/24/outline'

export default function Navbar() {
  const { user, activeRole, switchRole, logout, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [roleLoading, setRoleLoading] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const handleRoleSwitch = async (newRole) => {
    setRoleLoading(true)
    const result = await switchRole(newRole)
    setRoleLoading(false)
    
    if (!result.success) {
      // You could add a toast notification here
      console.error('Failed to switch role:', result.error)
    }
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
                {/* Role Toggle */}
                <div className="flex items-center space-x-2">
                  <div className="flex bg-gray-100 rounded-lg p-1">
                    <button
                      onClick={() => handleRoleSwitch('renter')}
                      disabled={roleLoading}
                      className={`px-3 py-1 text-xs font-medium rounded-md transition-all duration-200 ${
                        activeRole === 'renter'
                          ? 'bg-blue-600 text-white shadow-sm'
                          : 'text-gray-600 hover:text-blue-600'
                      }`}
                    >
                      Renter
                    </button>
                    <button
                      onClick={() => handleRoleSwitch('host')}
                      disabled={roleLoading}
                      className={`px-3 py-1 text-xs font-medium rounded-md transition-all duration-200 ${
                        activeRole === 'host'
                          ? 'bg-green-600 text-white shadow-sm'
                          : 'text-gray-600 hover:text-green-600'
                      }`}
                    >
                      Host
                    </button>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <UserIcon className="h-5 w-5 text-gray-400" />
                  <span className="text-sm text-gray-700">
                    {user?.username || user?.email}
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