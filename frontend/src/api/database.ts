/**
 * Database management API — info, export, and PostgreSQL migration.
 */
import request from './index'

const DB_BASE_URL = '/api/v1/admin/database'

export interface DatabaseInfo {
  backend: string
  table_count: number
  row_counts: Record<string, number>
  file_size_mb: number | null
  alembic_revision: string | null
}

export interface MigrateRequest {
  target_dsn: string
  truncate: boolean
}

export interface MigrateResponse {
  status: string
  message: string
}

export async function getDatabaseInfo(): Promise<DatabaseInfo> {
  return request({
    url: `${DB_BASE_URL}/info`,
    method: 'get',
  })
}

export async function downloadMigrationScript(): Promise<Blob> {
  return request({
    url: `${DB_BASE_URL}/migration-script`,
    method: 'get',
    responseType: 'blob',
  })
}

export async function downloadDatabaseExport(): Promise<Blob> {
  return request({
    url: `${DB_BASE_URL}/export`,
    method: 'get',
    responseType: 'blob',
  })
}

export async function triggerMigration(data: MigrateRequest): Promise<MigrateResponse> {
  return request({
    url: `${DB_BASE_URL}/migrate-to-postgres`,
    method: 'post',
    data,
  })
}
