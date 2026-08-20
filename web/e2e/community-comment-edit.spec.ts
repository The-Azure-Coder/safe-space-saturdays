import { expect, test, type Page } from '@playwright/test'

const profile = {
  id: 11,
  name: 'Member',
  email: 'member@example.com',
  avatar_url: null,
  is_online: true,
  role: 'member',
  xp: 0,
  streak: 0,
  level: 1,
  is_approved: true,
  email_notifications_enabled: true,
}

function post(commentMine: boolean, commentAuthor: string, postMine = false) {
  return {
    id: 3,
    author: 'Post author',
    initials: 'P',
    avatar_url: null,
    is_online: false,
    text: 'A kind community thought',
    image_url: null,
    created_at: new Date().toISOString(),
    likes: 0,
    dislikes: 0,
    loves: 0,
    my_reaction: null,
    comments: [{
      id: 7,
      post_id: 3,
      author: commentAuthor,
      initials: commentAuthor[0],
      avatar_url: null,
      is_online: false,
      text: 'Original reply',
      created_at: new Date().toISOString(),
      mine: commentMine,
    }],
    liked_by: [],
    is_flagged: false,
    mine: postMine,
    post_type: 'original',
    shared_quote_id: null,
  }
}

async function mockCommunity(page: Page, currentPost: ReturnType<typeof post>) {
  await page.route('**/health/ready**', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready' }) }))
  await page.route('**/api/auth/me', (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(profile) }))
  await page.route('**/api/community/announcements', (route) => route.fulfill({ contentType: 'application/json', body: '[]' }))
  await page.route('**/api/community/posts**', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify([currentPost]) })
  })
}

test('a member can edit their own community reply', async ({ page }) => {
  await mockCommunity(page, post(true, 'Member'))
  await page.goto('/community')
  await page.getByRole('button', { name: 'View 1 reply' }).click()
  await page.getByRole('button', { name: 'Edit' }).click()
  await page.getByLabel('Edit reply').fill('Updated reply')
  await page.route('**/api/community/comments/7', async (route) => {
    expect(route.request().method()).toBe('PATCH')
    expect(route.request().postDataJSON()).toEqual({ text: 'Updated reply' })
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ...post(true, 'Member').comments[0], text: 'Updated reply' }) })
  })
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page.getByText('Updated reply')).toBeVisible()
})

test('a member cannot edit a reply that is not theirs even when names match', async ({ page }) => {
  await mockCommunity(page, post(false, 'Member'))
  await page.goto('/community')
  await page.getByRole('button', { name: 'View 1 reply' }).click()
  await expect(page.getByRole('button', { name: 'Edit' })).toHaveCount(0)
})

test('a member can edit their own community post', async ({ page }) => {
  const currentPost = post(false, 'Other member', true)
  await mockCommunity(page, currentPost)
  await page.goto('/community')
  await page.getByRole('button', { name: 'Edit post' }).click()
  await page.getByLabel('Edit post').fill('Updated community post')
  await page.route('**/api/community/posts/3', async (route) => {
    expect(route.request().method()).toBe('PATCH')
    expect(route.request().postDataJSON()).toEqual({ text: 'Updated community post' })
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ...currentPost, text: 'Updated community post' }) })
  })
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page.getByText('Updated community post')).toBeVisible()
})

test('a member cannot edit another member\'s community post', async ({ page }) => {
  await mockCommunity(page, post(false, 'Other member'))
  await page.goto('/community')
  await expect(page.getByRole('button', { name: 'Edit post' })).toHaveCount(0)
})

test('recent winners show game and level without presence or streak indicators', async ({ page }) => {
  await page.route('**/health/ready**', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready' }) }))
  await page.route('**/api/auth/me', (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(profile) }))
  await page.route('**/api/games?*', async (route) => {
    if (route.request().url().includes('/winners')) {
      await route.fulfill({ contentType: 'application/json', body: JSON.stringify([{ position: 1, name: 'Member', avatar_url: null, points: 5, match_points: 5, wins: 1, level: 3, streak: 4, game: 'Checkers', created_at: new Date().toISOString() }]) })
      return
    }
    await route.fulfill({ contentType: 'application/json', body: '[]' })
  })
  await page.route('**/api/games/winners?*', (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify([{ position: 1, name: 'Member', avatar_url: null, points: 5, match_points: 5, wins: 1, level: 3, streak: 4, game: 'Checkers', created_at: new Date().toISOString() }]) }))
  await page.route('**/api/games/rooms?*', (route) => route.fulfill({ contentType: 'application/json', body: '[]' }))
  await page.goto('/games')
  const winner = page.locator('.winner-row').filter({ hasText: 'Member' })
  await expect(winner).toContainText('Checkers · Level 3')
  await expect(winner).not.toContainText('streak')
  await expect(winner.locator('.avatar__presence')).toHaveCount(0)
})
