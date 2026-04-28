/**
 * Frontend version for troubleshooting
 * Can be overridden by NEXT_PUBLIC_APP_VERSION env var
 */
export const FRONTEND_VERSION = process.env.NEXT_PUBLIC_APP_VERSION || new Date().toISOString().replace(/[-:]/g, '').slice(0, 15).replace('T', '_');
