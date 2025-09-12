import React from 'react'
import { Link } from 'react-router-dom'
import { 
  CpuChipIcon, 
  CloudIcon, 
  CurrencyDollarIcon,
  ShieldCheckIcon,
  BoltIcon,
  UsersIcon
} from '@heroicons/react/24/outline'

export default function LandingPage() {
  const features = [
    {
      icon: CpuChipIcon,
      title: 'High-Performance GPUs',
      description: 'Access RTX 4090s, A100s, and other powerful GPUs from community hosts worldwide.'
    },
    {
      icon: CurrencyDollarIcon,
      title: 'Fair Pricing',
      description: 'Competitive hourly rates set by hosts. Only pay for what you use.'
    },
    {
      icon: ShieldCheckIcon,
      title: 'Secure & Reliable',
      description: 'End-to-end encrypted connections with isolated job execution environments.'
    },
    {
      icon: BoltIcon,
      title: 'Instant Deployment',
      description: 'Submit Docker containers or Python scripts and start training immediately.'
    },
    {
      icon: CloudIcon,
      title: 'Global Network',
      description: 'GPU hosts available across different regions for optimal performance.'
    },
    {
      icon: UsersIcon,
      title: 'Community Driven',
      description: 'Share and discover AI models in our public repository.'
    }
  ]

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="relative bg-gradient-to-r from-blue-600 to-purple-700 text-white">
        <div className="absolute inset-0 bg-black opacity-10"></div>
        <div className="relative max-w-7xl mx-auto px-4 py-24 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-5xl font-bold mb-6">
              Rent GPU Power from Anywhere
            </h1>
            <p className="text-xl mb-8 text-blue-100 max-w-3xl mx-auto">
              Access powerful GPUs for AI training, research, and computation from community hosts. 
              No setup required—just submit your job and start computing.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link 
                to="/register"
                className="bg-white text-blue-600 px-8 py-3 rounded-lg text-lg font-semibold hover:bg-gray-100 transition duration-200"
              >
                Start Computing
              </Link>
              <Link 
                to="/marketplace"
                className="border-2 border-white text-white px-8 py-3 rounded-lg text-lg font-semibold hover:bg-white hover:text-blue-600 transition duration-200"
              >
                Browse GPUs
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Why Choose P2P GPU Cloud?
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Our decentralized platform connects you with GPU owners worldwide, 
              providing affordable and accessible computing power for everyone.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="p-6 border border-gray-200 rounded-lg hover:shadow-lg transition duration-200">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                  <feature.icon className="h-6 w-6 text-blue-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-lg text-gray-600">
              Get started in three simple steps
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                1
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Choose Your GPU
              </h3>
              <p className="text-gray-600">
                Browse available GPUs by model, price, and location. Filter by your specific requirements.
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                2
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Submit Your Job
              </h3>
              <p className="text-gray-600">
                Upload your code or Docker container, specify resource requirements, and submit your job.
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                3
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Monitor & Download
              </h3>
              <p className="text-gray-600">
                Watch real-time logs, monitor progress, and download your results when complete.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-16 bg-blue-600">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Get Started?
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            Join thousands of researchers and developers using our platform for AI training and computation.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link 
              to="/register"
              className="bg-white text-blue-600 px-8 py-3 rounded-lg text-lg font-semibold hover:bg-gray-100 transition duration-200"
            >
              Create Account
            </Link>
            <Link 
              to="/login"
              className="border-2 border-white text-white px-8 py-3 rounded-lg text-lg font-semibold hover:bg-white hover:text-blue-600 transition duration-200"
            >
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}