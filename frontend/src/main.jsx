import React from 'react'
import ReactDOM from 'react-dom/client'
import { AuthProvider } from 'react-oidc-context'
import App from './App'
import './index.css'

// Cognito OIDC configuration
const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID
const clientId = import.meta.env.VITE_COGNITO_APP_CLIENT_ID
const region = import.meta.env.VITE_COGNITO_REGION || 'us-west-1'
const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN
const appUrl = import.meta.env.VITE_APP_URL || window.location.origin

// Validate required config
if (!userPoolId || !clientId) {
  console.error('❌ Cognito configuration missing!')
  console.error('Missing:', {
    userPoolId: !userPoolId,
    clientId: !clientId
  })
  throw new Error('Cognito configuration is incomplete. Please check your environment variables.')
}

if (!cognitoDomain) {
  console.error('❌ Cognito domain missing!')
  console.error('VITE_COGNITO_DOMAIN is required for OIDC authentication.')
  throw new Error('Cognito domain is required. Please set VITE_COGNITO_DOMAIN in your .env file.')
}

// Build Cognito authority URL - must be the Cognito IDP endpoint for OIDC discovery
// The OIDC discovery endpoint is at: https://cognito-idp.{region}.amazonaws.com/{userPoolId}/.well-known/openid-configuration
// But the authorization endpoint (where users sign in) is at: https://{domain}.auth.{region}.amazoncognito.com/oauth2/authorize

// For OIDC discovery, use the Cognito IDP endpoint
const authority = `https://cognito-idp.${region}.amazonaws.com/${userPoolId}`

// Build the Hosted UI domain for the authorization endpoint
let hostedUIDomain = cognitoDomain
if (hostedUIDomain.startsWith('https://')) {
  hostedUIDomain = hostedUIDomain.replace('https://', '')
} else if (hostedUIDomain.startsWith('http://')) {
  hostedUIDomain = hostedUIDomain.replace('http://', '')
}

if (hostedUIDomain.includes('.amazoncognito.com')) {
  // Already a full Cognito domain, use it as-is
} else if (hostedUIDomain.includes('.amazonaws.com')) {
  // Wrong format - extract prefix
  const match = hostedUIDomain.match(/^([^.]+)\.auth\.([^.]+)\.amazonaws\.com/)
  if (match) {
    const prefix = match[1]
    hostedUIDomain = `${prefix}.auth.${region}.amazoncognito.com`
  } else {
    const prefix = hostedUIDomain.split('.')[0]
    hostedUIDomain = `${prefix}.auth.${region}.amazoncognito.com`
  }
} else {
  // Just the prefix
  hostedUIDomain = `${hostedUIDomain}.auth.${region}.amazoncognito.com`
}

const hostedUIBaseUrl = `https://${hostedUIDomain}`

console.log('Domain processing:', {
  original: cognitoDomain,
  hostedUIDomain: hostedUIDomain,
  authority: authority,
  hostedUIBaseUrl: hostedUIBaseUrl
})

// OIDC configuration
const cognitoAuthConfig = {
  authority: authority,
  client_id: clientId,
  redirect_uri: `${appUrl}/auth/callback`,
  response_type: 'code',
  scope: 'email openid profile',
  // Additional configuration
  automaticSilentRenew: false, // Disable automatic silent renew to prevent auto-login after logout
  loadUserInfo: true,
  // Don't automatically sign in if user was previously signed in
  // This prevents auto-login after logout
  revokeTokensOnSignout: true,
  // Enable PKCE for security (required for public clients)
  // Note: Cognito supports PKCE, but we need to ensure state is handled correctly
  // The state parameter might be missing if the redirect doesn't preserve it
  // We'll let the library handle PKCE automatically
  // Override the authorization endpoint to use Hosted UI domain
  // Cognito's OIDC discovery is on the IDP endpoint, but authorization is on Hosted UI domain
  metadata: {
    authorization_endpoint: `${hostedUIBaseUrl}/oauth2/authorize`,
    token_endpoint: `${hostedUIBaseUrl}/oauth2/token`,
    userinfo_endpoint: `${hostedUIBaseUrl}/oauth2/userInfo`,
    end_session_endpoint: `${hostedUIBaseUrl}/logout`,
    jwks_uri: `https://cognito-idp.${region}.amazonaws.com/${userPoolId}/.well-known/jwks.json`,
    issuer: `https://cognito-idp.${region}.amazonaws.com/${userPoolId}`
  },
  // Ensure we handle the callback properly
  post_logout_redirect_uri: appUrl,
  // Enable automatic callback handling
  onSigninCallback: (user) => {
    console.log('✅ Sign-in callback successful:', user?.profile?.email || 'User')
    console.log('User profile:', user?.profile)
    // Remove the callback URL from the browser history
    window.history.replaceState({}, document.title, window.location.pathname.replace('/auth/callback', '/'))
  },
  onSigninError: (error) => {
    console.error('❌ Sign-in callback error:', error)
    console.error('Error details:', error.error, error.error_description)
  },
}

console.log('Configuring OIDC with:', {
  authority,
  client_id: clientId,
  redirect_uri: cognitoAuthConfig.redirect_uri,
  scope: cognitoAuthConfig.scope
})

const root = ReactDOM.createRoot(document.getElementById('root'))

// Wrap the application with AuthProvider
root.render(
  <React.StrictMode>
    <AuthProvider {...cognitoAuthConfig}>
      <App />
    </AuthProvider>
  </React.StrictMode>,
)