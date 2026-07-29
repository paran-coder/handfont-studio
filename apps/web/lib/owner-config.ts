export const OWNER_COOKIE_NAME = 'handfont_owner';
export const OWNER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{40,128}$/;

export function isValidOwnerToken(token: string | undefined): token is string {
  return Boolean(token && TOKEN_PATTERN.test(token));
}
