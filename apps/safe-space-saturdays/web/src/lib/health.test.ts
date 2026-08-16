import { describe, expect, it } from 'vitest'

import { healthLabel, isHealthState } from './health'

describe('health helpers', () => {
  it('accepts the API health shape', () => {
    expect(isHealthState({ status: 'ready', service: 'api' })).toBe(true)
  })

  it('rejects untrusted payloads', () => {
    expect(isHealthState({ status: 'ready' })).toBe(false)
    expect(healthLabel({ status: 'unavailable', service: 'api' })).toBe(
      'API unavailable',
    )
  })
})
