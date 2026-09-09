const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

/**
 * Format an ISO-8601 UTC timestamp as "01 Jan 2025".
 */
export function formatAcquisitionDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso

  const day = String(date.getUTCDate()).padStart(2, '0')
  const month = MONTHS[date.getUTCMonth()]
  const year = date.getUTCFullYear()

  return `${day} ${month} ${year}`
}

/**
 * Format an ISO-8601 UTC timestamp as "06:10 UTC".
 */
export function formatAcquisitionTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso

  const hours = String(date.getUTCHours()).padStart(2, '0')
  const minutes = String(date.getUTCMinutes()).padStart(2, '0')

  return `${hours}:${minutes} UTC`
}

/**
 * Format a signed latitude as "18.52° N".
 */
export function formatLatitude(latitude: number): string {
  const direction = latitude >= 0 ? 'N' : 'S'
  return `${Math.abs(latitude).toFixed(2)}° ${direction}`
}

/**
 * Format a signed longitude as "72.85° E".
 */
export function formatLongitude(longitude: number): string {
  const direction = longitude >= 0 ? 'E' : 'W'
  return `${Math.abs(longitude).toFixed(2)}° ${direction}`
}