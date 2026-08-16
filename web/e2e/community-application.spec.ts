import { expect, test } from '@playwright/test'

test('a visitor can submit a community application and see the confirmation state', async ({ page }) => {
  await page.route('**/health/ready**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready' }) }),
  )
  await page.route('**/api/community-applications', async (route) => {
    expect(route.request().method()).toBe('POST')
    const body = route.request().postDataJSON()
    expect(body).toMatchObject({ name: 'Community Applicant', email: 'applicant@example.com', consent: true })
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ id: 1, ...body, status: 'pending', admin_note: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), reviewed_at: null, email_sent_at: null }),
    })
  })
  await page.goto('/contact')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  await expect(page.getByRole('heading', { name: /Join the Safe Space circle/i })).toBeVisible({ timeout: 110_000 })
  await page.getByLabel('Full name').fill('Community Applicant')
  await page.getByLabel('Email address').fill('applicant@example.com')
  await page.getByLabel(/Why would you like to join/i).fill('I would love a warm, supportive community.')
  await page.getByLabel(/I’m happy for Safe Space Saturdays/i).check()
  await page.getByRole('button', { name: 'Send application' }).click()
  await expect(page.getByRole('heading', { name: 'Application received.' })).toBeVisible()
})

test('the application form explains that consent is required before sending', async ({ page }) => {
  await page.route('**/health/ready**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready' }) }),
  )
  let submitted = false
  await page.route('**/api/community-applications', () => { submitted = true })
  await page.goto('/contact')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  await page.getByLabel('Full name').fill('Community Applicant')
  await page.getByLabel('Email address').fill('applicant@example.com')
  await page.getByLabel(/Why would you like to join/i).fill('I would love a warm, supportive community.')
  await expect(page.getByRole('button', { name: 'Send application' })).toBeEnabled()
  await page.getByRole('button', { name: 'Send application' }).click()
  await expect(page.getByLabel(/I’m happy for Safe Space Saturdays/i)).toBeFocused()
  expect(submitted).toBe(false)
})
