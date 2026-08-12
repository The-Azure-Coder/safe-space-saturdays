import { expect, test } from '@playwright/test'

test.setTimeout(120_000)

const email = `browser-${Date.now()}@example.com`
const password = 'safe-space-password-123'

test('a visitor can register and reach the authenticated home screen', async ({ page }) => {
  await page.goto('/registration')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  await page.getByLabel('Full name').fill('Browser Member')
  await page.getByLabel('Email').fill(email)
  await page.locator('input[name="password"]').fill(password)
  await page.locator('input[name="confirm-password"]').fill(password)
  await expect(page.locator('[aria-label="Passwords match"]')).toBeVisible()
  await page.getByLabel(/I agree to the Safe Space Saturdays/).check()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/$/)
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  const profileButton = page.getByRole('button', { name: /Open .* profile menu/ })
  await expect(profileButton).toBeVisible()
  await profileButton.click()
  await expect(page.getByRole('menuitem', { name: 'Profile & settings' })).toBeVisible()
  await expect(page.getByRole('menuitem', { name: 'Log out' })).toBeVisible()
})

test('registration explains invalid password input before sending it', async ({ page }) => {
  await page.goto('/registration')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  await page.getByLabel('Full name').fill('Browser Member')
  await page.getByLabel('Email').fill(`invalid-${Date.now()}@example.com`)
  await page.locator('input[name="password"]').fill('short')
  await page.locator('input[name="confirm-password"]').fill('short')
  await page.getByLabel(/I agree to the Safe Space Saturdays/).check()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByRole('alert')).toHaveText('Your password must be at least 10 characters.')
})

test('Google sign-in is accessible and preserves the mobile auth layout', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route('**/api/auth/google/status', (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({ enabled: true }) }),
  )
  await page.goto('/login?oauth_error=failed')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })

  const googleLink = page.getByRole('link', { name: 'Continue with Google' })
  await expect(googleLink).toBeVisible()
  await expect(googleLink).toHaveAttribute('href', 'http://localhost:8000/api/auth/google/start')
  await expect(page.getByRole('alert')).toHaveText('Google sign-in could not be completed. Please try again.')
  await expect(page).toHaveURL(/\/login$/)

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)

  await page.goto('/registration')
  await expect(page.getByRole('link', { name: 'Sign up with Google' })).toBeVisible()
})
