import { NextRequest, NextResponse } from 'next/server';
import {
  CognitoIdentityProviderClient,
  InitiateAuthCommand,
} from '@aws-sdk/client-cognito-identity-provider';

const REGION = process.env.COGNITO_REGION || process.env.AWS_REGION || 'us-east-2';
const CLIENT_ID = process.env.COGNITO_APP_CLIENT_ID!;

export async function POST(request: NextRequest) {
  try {
    const { username, password } = await request.json();
    if (!username || !password) {
      return NextResponse.json({ error: 'Username and password required' }, { status: 400 });
    }

    const client = new CognitoIdentityProviderClient({ region: REGION });
    const result = await client.send(new InitiateAuthCommand({
      AuthFlow: 'USER_PASSWORD_AUTH',
      ClientId: CLIENT_ID,
      AuthParameters: { USERNAME: username, PASSWORD: password },
    }));

    const accessToken = result.AuthenticationResult?.AccessToken;
    if (!accessToken) {
      return NextResponse.json({ error: 'Authentication failed' }, { status: 401 });
    }

    const response = NextResponse.json({ success: true });
    response.cookies.set('auth_token', accessToken, {
      httpOnly: true,
      secure: true,
      sameSite: 'lax',
      path: '/',
      maxAge: result.AuthenticationResult?.ExpiresIn ?? 43200,
    });
    return response;
  } catch (error: any) {
    if (error.name === 'NotAuthorizedException' || error.name === 'UserNotFoundException') {
      return NextResponse.json({ error: 'Invalid username or password' }, { status: 401 });
    }
    console.error('[auth/login] error:', error);
    return NextResponse.json({ error: 'Login failed' }, { status: 500 });
  }
}
