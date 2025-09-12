import React, { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function GoogleCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { handleGoogleCallback } = useAuth()

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code')
      const error = searchParams.get('error')

      if (error) {
        console.error('Google OAuth error:', error)
        navigate('/login?error=oauth_failed')
        return
      }

      if (code) {
        try {
          const result = await handleGoogleCallback(code)
          if (result.success) {
            navigate('/dashboard')
          } else {
            navigate('/login?error=auth_failed')
          }
        } catch (error) {
          console.error('Callback error:', error)
          navigate('/login?error=auth_failed')
        }
      } else {
        navigate('/login?error=no_code')
      }
    }

    handleCallback()
  }, [searchParams, handleGoogleCallback, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-md w-full space-y-8 p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600 mx-auto"></div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            Completing Authentication...
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Please wait while we log you in with Google.
          </p>
        </div>
      </div>
    </div>
  )
}