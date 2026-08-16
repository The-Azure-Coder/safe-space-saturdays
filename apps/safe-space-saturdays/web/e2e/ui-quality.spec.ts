import { expect, test } from '@playwright/test'

const routes = [
  ['Home', '/'], ['Login', '/login'], ['Registration', '/registration'],
  ['Daily Check-In', '/check-in'], ['Challenges', '/challenges'], ['Quotes', '/quotes'], ['Community', '/community'],
  ['Games', '/games'], ['Leaderboard', '/leaderboard'], ['Profile', '/profile'],
  ['Admin', '/admin'],
] as const

for (const [name, route] of routes) {
  test(`${name}: accessibility and interaction baseline`, async ({ page }) => {
    await page.goto(route, { waitUntil: 'networkidle' })
    const missingAlt = await page.locator('img').evaluateAll((images) => images.filter((image) => !image.hasAttribute('alt')).map((image) => image.outerHTML.slice(0, 180)))
    expect(missingAlt, `${name} has images without alt text`).toHaveLength(0)
    const unlabeledControls = await page.locator('input:not([type="hidden"]), textarea, select').evaluateAll((controls) => controls.filter((control) => {
      const id = control.getAttribute('id')
      return !control.closest('label') && !control.getAttribute('aria-label') && !control.getAttribute('aria-labelledby') && !(id && document.querySelector(`label[for="${id}"]`))
    }).map((control) => control.outerHTML.slice(0, 180)))
    expect(unlabeledControls, `${name} has unlabeled form controls`).toHaveLength(0)
    expect(await page.locator('form button:not([type])').count(), `${name} has a form button without an explicit type`).toBe(0)
    const placeholderLinks = await page.locator('a[href]').evaluateAll((links) => links.filter((link) => {
      const href = link.getAttribute('href')
      return href !== null && ['#', 'javascript:void(0)', 'javascript:void(0);'].includes(href.trim().toLowerCase())
    }).map((link) => String(link.textContent).trim() || 'unnamed link'))
    if (placeholderLinks.length > 0) console.warn(`${name} placeholder links: ${placeholderLinks.join(', ')}`)
    const hasFocusRule = await page.evaluate(() => Array.from(document.styleSheets).some((sheet) => {
      try { return Array.from(sheet.cssRules).some((rule) => rule.cssText.includes(':focus-visible')) } catch { return false }
    }))
    expect(hasFocusRule, `${name} is missing a :focus-visible style rule`).toBe(true)
  })

  test(`${name}: no horizontal overflow on mobile`, async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto(route, { waitUntil: 'networkidle' })
    const dimensions = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }))
    expect(dimensions.scrollWidth, `${name} overflows horizontally at mobile width`).toBeLessThanOrEqual(dimensions.clientWidth)
  })
}

test('Mobile navigation is left-aligned when opened', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 })
  await page.goto('/community', { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: 'Open navigation menu' }).click()
  const navigation = page.locator('#main-navigation')
  await expect(navigation).toBeVisible()
  const alignment = await navigation.evaluate((element) => {
    const nav = getComputedStyle(element)
    const firstLink = element.querySelector('a')
    return { justifyItems: nav.justifyItems, justifyContent: nav.justifyContent, linkJustify: firstLink ? getComputedStyle(firstLink).justifyContent : '' }
  })
  expect(alignment).toEqual({ justifyItems: 'start', justifyContent: 'start', linkJustify: 'flex-start' })
})

test('Community stacks into one column on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 })
  await page.goto('/community', { waitUntil: 'networkidle' })
  const layout = await page.locator('.community-layout').evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(' ').length)
  expect(layout).toBe(1)
})
