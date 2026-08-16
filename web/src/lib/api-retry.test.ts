import { describe, expect, it } from 'vitest'

import {
  ApiError,
  MAX_API_WAKE_RETRIES,
  apiRetryDelay,
  shouldRetryApiRequest,
} from './api'

describe('API cold-start retries', () => {
  it('retries network and server failures within the retry limit', () => {
    expect(shouldRetryApiRequest(0, new ApiError(0, 'Offline'))).toBe(true)
    expect(shouldRetryApiRequest(3, new ApiError(503, 'Waking'))).toBe(true)
  })

  it('does not retry authentication or exhausted requests', () => {
    expect(shouldRetryApiRequest(0, new ApiError(401, 'Signed out'))).toBe(
      false,
    )
    expect(
      shouldRetryApiRequest(
        MAX_API_WAKE_RETRIES,
        new ApiError(503, 'Still waking'),
      ),
    ).toBe(false)
  })

  it('caps the delay between attempts', () => {
    expect(apiRetryDelay(0)).toBe(1_200)
    expect(apiRetryDelay(10)).toBe(8_000)
  })
})
