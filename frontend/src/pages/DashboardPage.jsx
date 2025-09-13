import React, { useState, useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import axios from 'axios'
import { 
  CpuChipIcon, 
  PlayIcon, 
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlusIcon
} from '@heroicons/react/24/outline'

export default function DashboardPage() {
  const { user, activeRole, isAuthenticated } = useAuth()
  const [activeTab, setActiveTab] = useState('overview')
  const [jobs, setJobs] = useState([])
  const [hosts, setHosts] = useState([])
  const [loading, setLoading] = useState(true)

  // Redirect if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (activeRole === 'renter') {
          // Fetch jobs for renters
          const jobsRes = await axios.get('/api/jobs').catch(() => ({ data: [] }))
          setJobs(jobsRes.data || [])
          setHosts([]) // Clear hosts data
        } else if (activeRole === 'host') {
          // Fetch user's own hosts for host view
          const hostsRes = await axios.get('/api/hosts/my').catch(() => ({ data: [] }))
          setHosts(hostsRes.data || [])
          setJobs([]) // Clear jobs data
        }
      } catch (error) {
        console.error('Error fetching dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }

    if (activeRole) {
      fetchData()
    }
  }, [activeRole])

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running': return <PlayIcon className="h-5 w-5 text-blue-500" />
      case 'pending': return <ClockIcon className="h-5 w-5 text-yellow-500" />
      case 'completed': return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'failed': return <XCircleIcon className="h-5 w-5 text-red-500" />
      default: return <ClockIcon className="h-5 w-5 text-gray-500" />
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'bg-blue-100 text-blue-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'completed': return 'bg-green-100 text-green-800'
      case 'failed': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Welcome back, {user?.username}!
          </h1>
          <p className="mt-2 text-gray-600">
            {activeRole === 'host' ? 'Manage your GPU hosts and earnings' : 'Manage your GPU jobs and compute usage'}
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-8">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Overview
            </button>
            {activeRole === 'renter' && (
              <button
                onClick={() => setActiveTab('jobs')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'jobs'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                My Jobs
              </button>
            )}
            {activeRole === 'host' && (
              <button
                onClick={() => setActiveTab('hosts')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'hosts'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                My Hosts
              </button>
            )}
          </nav>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {activeRole === 'renter' ? (
              <>
                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="flex items-center">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <PlayIcon className="h-6 w-6 text-blue-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Running Jobs</p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {jobs.filter(job => job.status === 'running').length}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="flex items-center">
                    <div className="p-2 bg-green-100 rounded-lg">
                      <CheckCircleIcon className="h-6 w-6 text-green-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Completed Jobs</p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {jobs.filter(job => job.status === 'completed').length}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="flex items-center">
                    <div className="p-2 bg-yellow-100 rounded-lg">
                      <ClockIcon className="h-6 w-6 text-yellow-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Pending Jobs</p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {jobs.filter(job => job.status === 'pending').length}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="flex items-center">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <CpuChipIcon className="h-6 w-6 text-purple-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Total Jobs</p>
                      <p className="text-2xl font-semibold text-gray-900">{jobs.length}</p>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="flex items-center">
                    <div className="p-2 bg-green-100 rounded-lg">
                      <CpuChipIcon className="h-6 w-6 text-green-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">My Hosts</p>
                      <p className="text-2xl font-semibold text-gray-900">{hosts.length}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="flex items-center">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <PlayIcon className="h-6 w-6 text-blue-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Online Hosts</p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {hosts.filter(host => host.is_online).length}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="flex items-center">
                    <div className="p-2 bg-yellow-100 rounded-lg">
                      <CheckCircleIcon className="h-6 w-6 text-yellow-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Jobs Completed</p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {hosts.reduce((sum, host) => sum + (host.total_jobs_completed || 0), 0)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="flex items-center">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <CpuChipIcon className="h-6 w-6 text-purple-600" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Total Earnings</p>
                      <p className="text-2xl font-semibold text-gray-900">
                        ${hosts.reduce((sum, host) => sum + (host.total_earnings || 0), 0).toFixed(2)}
                      </p>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Jobs Tab */}
        {activeTab === 'jobs' && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-gray-900">My Jobs</h2>
              <button className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 flex items-center">
                <PlusIcon className="h-4 w-4 mr-2" />
                New Job
              </button>
            </div>

            <div className="bg-white shadow rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Recent Jobs</h3>
              </div>
              <div className="divide-y divide-gray-200">
                {jobs.length > 0 ? jobs.map((job, index) => (
                  <div key={index} className="px-6 py-4 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        {getStatusIcon(job.status)}
                        <div>
                          <p className="text-sm font-medium text-gray-900">{job.title || job.job_id}</p>
                          <p className="text-sm text-gray-500">{job.description || 'No description'}</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(job.status)}`}>
                          {job.status}
                        </span>
                        <span className="text-sm text-gray-500">
                          {job.submitted_at ? new Date(job.submitted_at).toLocaleDateString() : 'Today'}
                        </span>
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="px-6 py-12 text-center">
                    <CpuChipIcon className="mx-auto h-12 w-12 text-gray-400" />
                    <p className="mt-2 text-sm text-gray-500">No jobs yet</p>
                    <p className="text-sm text-gray-400">Submit your first GPU job to get started</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Hosts Tab (for host users) */}
        {activeTab === 'hosts' && user?.role === 'host' && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-gray-900">My GPU Hosts</h2>
              <button className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 flex items-center">
                <PlusIcon className="h-4 w-4 mr-2" />
                Add Host
              </button>
            </div>

            <div className="bg-white shadow rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Registered Hosts</h3>
              </div>
              <div className="divide-y divide-gray-200">
                {hosts.length > 0 ? hosts.slice(0, 3).map((host, index) => (
                  <div key={index} className="px-6 py-4 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{host.gpu_model}</p>
                        <p className="text-sm text-gray-500">{host.vram} • {host.location}</p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          host.availability === 'online' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {host.availability}
                        </span>
                        <span className="text-sm text-gray-500">${host.price_per_hour}/hr</span>
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="px-6 py-12 text-center">
                    <CpuChipIcon className="mx-auto h-12 w-12 text-gray-400" />
                    <p className="mt-2 text-sm text-gray-500">No hosts registered</p>
                    <p className="text-sm text-gray-400">Register your first GPU to start earning</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}