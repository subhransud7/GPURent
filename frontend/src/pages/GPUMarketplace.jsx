import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { CpuChipIcon, MapPinIcon, CurrencyDollarIcon, CheckBadgeIcon } from '@heroicons/react/24/outline'

export default function GPUMarketplace() {
  const [hosts, setHosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    gpu_model: '',
    max_price: '',
    location: ''
  })

  useEffect(() => {
    const fetchHosts = async () => {
      try {
        const response = await axios.get('/api/hosts')
        setHosts(response.data.hosts || [])
      } catch (error) {
        console.error('Error fetching hosts:', error)
        // Set some demo data if API fails
        setHosts([
          {
            id: 'demo-1',
            gpu_model: 'RTX 4090',
            vram: '24GB',
            gpu_count: 1,
            price_per_hour: 2.50,
            availability: 'online',
            location: 'US-West',
            uptime: 99.8,
            jobs_completed: 142
          },
          {
            id: 'demo-2',
            gpu_model: 'RTX 3080',
            vram: '10GB',
            gpu_count: 2,
            price_per_hour: 1.80,
            availability: 'online',
            location: 'EU-Central',
            uptime: 97.5,
            jobs_completed: 89
          }
        ])
      } finally {
        setLoading(false)
      }
    }

    fetchHosts()
  }, [])

  const filteredHosts = hosts.filter(host => {
    return (
      (!filters.gpu_model || host.gpu_model.toLowerCase().includes(filters.gpu_model.toLowerCase())) &&
      (!filters.max_price || host.price_per_hour <= parseFloat(filters.max_price)) &&
      (!filters.location || host.location.toLowerCase().includes(filters.location.toLowerCase()))
    )
  })

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
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">GPU Marketplace</h1>
          <p className="mt-2 text-gray-600">
            Browse and rent powerful GPUs from hosts around the world
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white p-6 rounded-lg shadow mb-8">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Filters</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                GPU Model
              </label>
              <input
                type="text"
                placeholder="e.g., RTX 4090"
                value={filters.gpu_model}
                onChange={(e) => setFilters({...filters, gpu_model: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Max Price ($/hour)
              </label>
              <input
                type="number"
                placeholder="e.g., 5.00"
                step="0.10"
                value={filters.max_price}
                onChange={(e) => setFilters({...filters, max_price: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Location
              </label>
              <input
                type="text"
                placeholder="e.g., US-West"
                value={filters.location}
                onChange={(e) => setFilters({...filters, location: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* GPU Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredHosts.map((host) => (
            <div key={host.id} className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow duration-300">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-2">
                    <CpuChipIcon className="h-6 w-6 text-blue-600" />
                    <h3 className="text-lg font-semibold text-gray-900">{host.gpu_model}</h3>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    host.availability === 'online' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {host.availability}
                  </span>
                </div>

                <div className="space-y-3 mb-6">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Memory</span>
                    <span className="font-medium">{host.vram}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">GPUs</span>
                    <span className="font-medium">{host.gpu_count}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Location</span>
                    <div className="flex items-center">
                      <MapPinIcon className="h-4 w-4 text-gray-400 mr-1" />
                      <span className="font-medium">{host.location}</span>
                    </div>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Uptime</span>
                    <span className="font-medium text-green-600">{host.uptime}%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Jobs Completed</span>
                    <div className="flex items-center">
                      <CheckBadgeIcon className="h-4 w-4 text-blue-500 mr-1" />
                      <span className="font-medium">{host.jobs_completed}</span>
                    </div>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <CurrencyDollarIcon className="h-5 w-5 text-gray-400 mr-1" />
                      <span className="text-2xl font-bold text-gray-900">
                        ${host.price_per_hour}
                      </span>
                      <span className="text-gray-500 ml-1">/hour</span>
                    </div>
                    <button 
                      className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
                      disabled={host.availability !== 'online'}
                    >
                      {host.availability === 'online' ? 'Rent Now' : 'Unavailable'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredHosts.length === 0 && (
          <div className="text-center py-12">
            <CpuChipIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No GPUs found</h3>
            <p className="mt-1 text-sm text-gray-500">
              Try adjusting your filters or check back later for new hosts.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}