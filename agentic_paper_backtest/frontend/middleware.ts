import { NextRequest, NextResponse } from 'next/server';
import { createRemoteJWKSet, jwtVerify } from 'jose';

const REGION = process.env.COGNITO_REGION || process.env.AWS_REGION || 'us-east-2';
const USER_POOL_ID = process.env.COGNITO_USER_POOL_ID!;
const CLIENT_ID = process.env.COGNITO_APP_CLIENT_ID!;

const ISSUER = `https://cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}`;
const JWKS = createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks.json`));

// Paths reachable without authentication
const PUBLIC_PATHS = ['/login', '/api/auth/login', '/api/health'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith(p + '/'))) {
    return NextResponse.next();
  }

  const token = request.cookies.get('auth_token')?.value;
  if (token) {
    try {
      const { payload } = await jwtVerify(token, JWKS, { issuer: ISSUER });
      // Cognito access tokens carry client_id (not aud) and token_use=access
      if (payload.client_id === CLIENT_ID && payload.token_use === 'access') {
        return NextResponse.next();
      }
    } catch {
      // fall through to redirect/401
    }
  }

  if (pathname.startsWith('/api/')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }
  const loginUrl = new URL('/login', request.url);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  // Protect everything except Next.js internals and static assets
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:js|css|png|jpg|svg|ico)$).*)'],
};
