import postgres from 'postgres';
import { env } from './env';

const globalForDb = globalThis as unknown as { handfontSql?: ReturnType<typeof postgres> };
export const sql = globalForDb.handfontSql ?? postgres(env.databaseUrl, {
  max: process.env.NODE_ENV === 'production' ? 5 : 2,
  idle_timeout: 20,
  connect_timeout: 15,
  prepare: false,
  ssl: env.databaseUrl.includes('localhost') ? false : 'require',
});
if (process.env.NODE_ENV !== 'production') globalForDb.handfontSql = sql;

export type DbRow = Record<string, unknown>;
