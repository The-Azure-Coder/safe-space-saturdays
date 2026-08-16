export type HealthState = {
  status: 'ready' | 'unavailable'
  service: string
}

export function isHealthState(value: unknown): value is HealthState {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Record<string, unknown>
  return (
    (candidate.status === 'ready' || candidate.status === 'unavailable') &&
    typeof candidate.service === 'string'
  )
}

export function healthLabel(state: HealthState): string {
  return state.status === 'ready' ? 'Systems ready' : 'API unavailable'
}
