// Cognito configuration
const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID
const userPoolWebClientId = import.meta.env.VITE_COGNITO_APP_CLIENT_ID
const region = import.meta.env.VITE_COGNITO_REGION || 'us-west-1'
const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN
const appUrl = import.meta.env.VITE_APP_URL || window.location.origin

// Debug: Log configuration values (remove in production)
console.log('Cognito Config:', {
  userPoolId: userPoolId ? '✓ Set' : '✗ Missing',
  userPoolWebClientId: userPoolWebClientId ? '✓ Set' : '✗ Missing',
  region: region,
  cognitoDomain: cognitoDomain ? '✓ Set' : '✗ Missing',
  appUrl: appUrl
})

// Validate required config
if (!userPoolId || !userPoolWebClientId) {
  console.error('❌ Cognito configuration missing!')
  console.error('Missing:', {
    userPoolId: !userPoolId,
    userPoolWebClientId: !userPoolWebClientId
  })
  throw new Error('Cognito configuration is incomplete. Please check your environment variables.')
}

// Build full domain URL
// Cognito domain should be: {prefix}.auth.{region}.amazoncognito.com
let oauthDomain = null

if (cognitoDomain) {
  // Remove protocol if present
  let domain = cognitoDomain
  if (domain.startsWith('https://')) {
    domain = domain.replace('https://', '')
  } else if (domain.startsWith('http://')) {
    domain = domain.replace('http://', '')
  }
  
  // Check if it's already a full Cognito domain
  if (domain.includes('.amazoncognito.com')) {
    // Already a full Cognito domain, use it as-is
    oauthDomain = domain
  } else if (domain.includes('.amazonaws.com')) {
    // This is wrong - extract the prefix
    // Format might be: {prefix}.auth.{region}.amazonaws.com
    // We need: {prefix}.auth.{region}.amazoncognito.com
    const match = domain.match(/^([^.]+)\.auth\.([^.]+)\.amazonaws\.com/)
    if (match) {
      const prefix = match[1]
      oauthDomain = `${prefix}.auth.${region}.amazoncognito.com`
    } else {
      // Try to extract just the prefix (everything before first dot)
      const prefix = domain.split('.')[0]
      oauthDomain = `${prefix}.auth.${region}.amazoncognito.com`
    }
  } else {
    // It's just the prefix, construct the full domain
    oauthDomain = `${domain}.auth.${region}.amazoncognito.com`
  }
  
  console.log('Domain processing:', {
    original: cognitoDomain,
    processed: oauthDomain
  })
}

export const cognitoConfig = {
  userPoolId: userPoolId,
  userPoolWebClientId: userPoolWebClientId,
  region: region,
  ...(oauthDomain && {
    oauth: {
      domain: oauthDomain,
      scopes: ['email', 'openid', 'profile'],
      redirectSignIn: [appUrl + '/auth/callback', appUrl],
      redirectSignOut: [appUrl],
      responseType: 'code'
    }
  })
}

console.log('Final Cognito Config:', {
  ...cognitoConfig,
  oauth: cognitoConfig.oauth ? { 
    ...cognitoConfig.oauth, 
    domain: cognitoConfig.oauth.domain 
  } : undefined
})

// Validate OAuth configuration if domain is provided
if (cognitoDomain && !cognitoConfig.oauth) {
  console.warn('⚠️ Warning: Cognito domain is set but OAuth configuration is missing!')
  console.warn('This will prevent social sign-in (Google) from working.')
}

