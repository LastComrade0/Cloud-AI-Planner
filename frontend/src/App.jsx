import React, { useState, useEffect } from 'react'
import { useAuth } from 'react-oidc-context'
import UploadForm from './components/UploadForm'
import PlannerView from './components/PlannerView'
import { setAuthTokenGetter } from './services/api'
import './index.css'

function AppContent() {
  const [refreshKey, setRefreshKey] = useState(0)

  const handleUploadSuccess = () => {
    // Trigger planner refresh
    if (window.refreshPlanner) {
      window.refreshPlanner()
    }
    setRefreshKey(k => k + 1)
  }

  return (
    <div className="container">
      <div className="header">
        <h1>🎓 AI Academic Planner</h1>
        <p>Automatically organize your assignments, exams, and important dates from course syllabi</p>
      </div>

      <UploadForm onUploadSuccess={handleUploadSuccess} />
      <PlannerView key={refreshKey} />
    </div>
  )
}

function App() {
  const auth = useAuth()
  const [mounted, setMounted] = useState(false)
  const [forceLogout, setForceLogout] = useState(false)

  // Set up token getter for API interceptor
  useEffect(() => {
    setAuthTokenGetter(async () => {
      if (auth.user?.id_token) {
        return auth.user.id_token
      }
      return null
    })
    setMounted(true)
  }, [auth.user])

  // Check if we should force logout (after manual logout)
  useEffect(() => {
    const wasLoggedOut = sessionStorage.getItem('oidc.force_logout')
    if (wasLoggedOut === 'true') {
      if (auth.isAuthenticated) {
        // User was logged out but library restored session - clear it
        console.log('🔄 Clearing restored session after logout')
        auth.removeUser()
        sessionStorage.removeItem('oidc.force_logout')
      }
    } else if (auth.isAuthenticated && window.location.pathname === '/auth/callback') {
      // User successfully signed in via callback - clear the flag if it exists
      sessionStorage.removeItem('oidc.force_logout')
      // Redirect to home page to clean up the URL
      window.history.replaceState({}, document.title, '/')
    }
  }, [auth.isAuthenticated, auth])

  // Handle OAuth callback - react-oidc-context should handle this automatically
  useEffect(() => {
    if (window.location.pathname === '/auth/callback') {
      console.log('🔵 OAuth callback detected')
      console.log('URL params:', window.location.search)
      console.log('URL hash:', window.location.hash)
      console.log('Full URL:', window.location.href)
      console.log('Auth state:', {
        isLoading: auth.isLoading,
        isAuthenticated: auth.isAuthenticated,
        error: auth.error,
        user: auth.user ? 'present' : 'null'
      })
      
      // Check if there's an error in the URL
      const urlParams = new URLSearchParams(window.location.search)
      const error = urlParams.get('error')
      const errorDescription = urlParams.get('error_description')
      const code = urlParams.get('code')
      const state = urlParams.get('state')
      
      if (error) {
        console.error('❌ OAuth callback error:', error, errorDescription)
        // Don't show alert here, let the error state handle it
        return
      }
      
      // Check if we have an authorization code
      if (code) {
        console.log('✅ Authorization code found in callback')
        console.log('Code:', code.substring(0, 20) + '...')
        console.log('State:', state)
        
        // Wait for authentication to complete, then redirect
        // This prevents the "jump back to login" issue
        const checkAuth = setInterval(() => {
          if (auth.isAuthenticated && auth.user) {
            console.log('✅ Authentication complete, redirecting to home...')
            clearInterval(checkAuth)
            // Small delay to ensure state is fully updated
            setTimeout(() => {
              window.history.replaceState({}, document.title, '/')
            }, 100)
          } else if (auth.error) {
            console.error('❌ Authentication error:', auth.error)
            clearInterval(checkAuth)
          }
        }, 100) // Check every 100ms
        
        // Cleanup after 10 seconds
        const timeout = setTimeout(() => {
          clearInterval(checkAuth)
          if (!auth.isAuthenticated && !auth.error) {
            console.warn('⚠️ Callback processing taking longer than expected')
          }
        }, 10000)
        
        return () => {
          clearInterval(checkAuth)
          clearTimeout(timeout)
        }
      } else {
        console.warn('⚠️ No authorization code found in callback URL')
        console.log('This might be a verification redirect or error redirect')
        console.log('After email verification, you need to sign in with your credentials')
      }
    }
  }, [auth.isLoading, auth.isAuthenticated, auth.error, auth.user])

  // Handle sign out - use Cognito's logout endpoint directly
  const signOutRedirect = async () => {
    try {
      console.log('🔴 Signing out...')
      const clientId = import.meta.env.VITE_COGNITO_APP_CLIENT_ID
      const logoutUri = import.meta.env.VITE_APP_URL || window.location.origin
      const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN
      const region = import.meta.env.VITE_COGNITO_REGION || 'us-west-1'
      
      // Build full Cognito Hosted UI domain
      let domain = cognitoDomain
      if (domain) {
        if (domain.startsWith('https://')) {
          domain = domain.replace('https://', '')
        } else if (domain.startsWith('http://')) {
          domain = domain.replace('http://', '')
        }
        
        if (domain.includes('.amazoncognito.com')) {
          // Already correct
        } else if (domain.includes('.amazonaws.com')) {
          const match = domain.match(/^([^.]+)\.auth\.([^.]+)\.amazonaws\.com/)
          if (match) {
            const prefix = match[1]
            domain = `${prefix}.auth.${region}.amazoncognito.com`
          } else {
            const prefix = domain.split('.')[0]
            domain = `${prefix}.auth.${region}.amazoncognito.com`
          }
        } else {
          domain = `${domain}.auth.${region}.amazoncognito.com`
        }
      }
      
      if (domain) {
        // Set flag to prevent auto-login after logout
        sessionStorage.setItem('oidc.force_logout', 'true')
        
        // Clear local auth state and storage first
        await auth.removeUser()
        
        // Clear any cached tokens in localStorage/sessionStorage
        // react-oidc-context stores tokens with keys like 'oidc.user:...'
        Object.keys(localStorage).forEach(key => {
          if (key.startsWith('oidc.user:') || key.startsWith('oidc.')) {
            localStorage.removeItem(key)
          }
        })
        Object.keys(sessionStorage).forEach(key => {
          if (key.startsWith('oidc.user:') && !key.includes('force_logout')) {
            sessionStorage.removeItem(key)
          }
          if (key.startsWith('oidc.') && !key.includes('force_logout')) {
            sessionStorage.removeItem(key)
          }
        })
        
        // Use Cognito's logout endpoint with correct parameters
        const logoutUrl = `https://${domain}/logout?client_id=${encodeURIComponent(clientId)}&logout_uri=${encodeURIComponent(logoutUri)}`
        console.log('Logout URL:', logoutUrl)
        
        // Redirect to Cognito logout (this will clear Cognito session cookies)
        window.location.href = logoutUrl
      } else {
        // Fallback: just clear local state
        await auth.removeUser()
        // Clear storage
        Object.keys(localStorage).forEach(key => {
          if (key.startsWith('oidc.user:') || key.startsWith('oidc.')) {
            localStorage.removeItem(key)
          }
        })
        Object.keys(sessionStorage).forEach(key => {
          if (key.startsWith('oidc.user:') || key.startsWith('oidc.')) {
            sessionStorage.removeItem(key)
          }
        })
        window.location.href = logoutUri
      }
    } catch (error) {
      console.error('Error signing out:', error)
      // Fallback: remove user locally if redirect fails
      await auth.removeUser()
      // Clear storage
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('oidc.user:') || key.startsWith('oidc.')) {
          localStorage.removeItem(key)
        }
      })
      Object.keys(sessionStorage).forEach(key => {
        if (key.startsWith('oidc.user:') || key.startsWith('oidc.')) {
          sessionStorage.removeItem(key)
        }
      })
      window.location.href = import.meta.env.VITE_APP_URL || window.location.origin
    }
  }

  // Show loading state
  // If we're on the callback route and loading, show a specific message
  const isCallbackRoute = window.location.pathname === '/auth/callback'
  
  if (!mounted || auth.isLoading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <h2>Loading...</h2>
        <p>{isCallbackRoute ? 'Completing sign-in...' : 'Initializing authentication...'}</p>
        {isCallbackRoute && (
          <p style={{ fontSize: '0.9rem', color: '#666', marginTop: '1rem' }}>
            Please wait while we process your authentication.
          </p>
        )}
      </div>
    )
  }

  // Show error state
  if (auth.error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <h2>Authentication Error</h2>
        <p>Encountering error: {auth.error.message}</p>
        <button 
          onClick={() => auth.signinRedirect()}
          style={{
            padding: '0.5rem 1rem',
            marginTop: '1rem',
            backgroundColor: '#4285f4',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Try Again
        </button>
      </div>
    )
  }

  // Show authenticated state
  if (auth.isAuthenticated) {
    return (
      <div>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          padding: '1rem',
          backgroundColor: '#f5f5f5',
          borderBottom: '1px solid #ddd'
        }}>
          <div>
            <span>Welcome, {auth.user?.profile?.email || auth.user?.profile?.name || 'User'}</span>
          </div>
          <button 
            onClick={signOutRedirect}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Sign out
          </button>
        </div>
        <AppContent />
      </div>
    )
  }

  // Show login state
  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '2rem'
    }}>
      <div style={{
        maxWidth: '400px',
        width: '100%',
        padding: '2rem',
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
      }}>
        <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Sign in to your account</h2>
        
        <button
          onClick={async () => {
            try {
              console.log('🔵 Initiating Google sign-in...')
              // Use react-oidc-context's signinRedirect with extraQueryParams
              // prompt=select_account forces Google to show account picker
              // This ensures the library properly handles the callback
              await auth.signinRedirect({
                extraQueryParams: {
                  identity_provider: 'Google',
                  prompt: 'select_account' // Force Google to show account selection
                }
              })
            } catch (error) {
              console.error('❌ Error signing in with Google:', error)
              alert(`Failed to sign in with Google: ${error.message || 'Unknown error'}`)
            }
          }}
          style={{
            width: '100%',
            padding: '0.75rem',
            marginBottom: '1rem',
            backgroundColor: '#4285f4',
            color: 'white',
            border: '2px solid #4285f4',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem',
            fontWeight: '500',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem'
          }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/>
            <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z" fill="#34A853"/>
            <path d="M3.964 10.707c-.18-.54-.282-1.117-.282-1.707s.102-1.167.282-1.707V4.961H.957C.348 6.175 0 7.55 0 9s.348 2.825.957 4.039l3.007-2.332z" fill="#FBBC05"/>
            <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.961L3.964 7.293C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
          </svg>
          Sign in with Google
        </button>

        <button
          onClick={async () => {
            try {
              console.log('🔵 Initiating regular sign-in...')
              // Use react-oidc-context's signinRedirect() WITHOUT identity_provider parameter
              // This ensures PKCE state is properly set up for callback processing
              // The Hosted UI should show both Google and username/password options
              // (assuming "Cognito user pool" is enabled in app client settings)
              await auth.signinRedirect({
                // Don't specify identity_provider - this will show the Hosted UI with all options
                // The user can then choose username/password or Google
              })
            } catch (error) {
              console.error('❌ Error signing in:', error)
              alert(`Failed to sign in: ${error.message || 'Unknown error'}`)
            }
          }}
          style={{
            width: '100%',
            padding: '0.75rem',
            backgroundColor: '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem',
            fontWeight: '500'
          }}
        >
          Sign in with Email/Username
        </button>
      </div>
    </div>
  )
}

export default App
