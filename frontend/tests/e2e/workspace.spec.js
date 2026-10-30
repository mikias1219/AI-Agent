import { test, expect } from '@playwright/test';

test('registered workspace persists chat/tasks and manages a mocked Telegram bot', async ({
  page,
}) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Make space for a better day.' })).toBeVisible();
  await page.getByLabel('Your name').fill('Mikias');
  await page.getByLabel('Email address').fill('owner@example.com');
  await page.getByLabel('Password', { exact: true }).fill('browser-only-password');
  await page.getByRole('button', { name: 'Create my workspace' }).click();
  await expect(page.getByRole('heading', { name: /Hey Mikias/ })).toBeVisible();
  await page.getByLabel('Ask your agent').fill('Help me organize today.');
  await page.getByRole('button', { name: 'Ask my agent' }).click();
  await expect(page.getByText('Okay.', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', { name: /Dashboard · / }).first()).toBeVisible();
  await page
    .getByRole('button', { name: /Dashboard · / })
    .first()
    .click();
  await expect(page.getByText('Help me organize today.', { exact: true })).toBeVisible();
  await page.getByRole('navigation').getByRole('button', { name: 'Tasks & approvals' }).click();
  await page.getByLabel('New task', { exact: true }).fill('Prepare my Telegram agent');
  await page.getByRole('button', { name: 'Add task', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Prepare my Telegram agent' })).toBeVisible();
  await page.getByLabel('Change status of Prepare my Telegram agent').selectOption('in_progress');
  await expect(page.getByText('in progress', { exact: true })).toBeVisible();
  await page.getByRole('navigation').getByRole('button', { name: 'Telegram', exact: true }).click();
  await page.getByRole('button', { name: 'Verify bot token' }).click();
  await expect(page.getByRole('heading', { name: '@fixture_bot' })).toBeVisible();
  await page.getByRole('button', { name: 'Start bot', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Stop bot', exact: true })).toBeVisible();
  await expect(page.getByText('reply sent', { exact: true })).toBeVisible({ timeout: 10000 });
  await page.getByRole('button', { name: 'Stop bot', exact: true }).click();
  await expect(page.getByText('Stopped', { exact: true })).toBeVisible({ timeout: 10000 });
  await page.getByRole('button', { name: 'Read conversation →' }).first().click();
  await expect(
    page.getByText('Hello from Telegram browser fixture', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Log out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
  await page.goto('/#telegram');
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
  await page.getByLabel('Email address').fill('owner@example.com');
  await page.getByLabel('Password', { exact: true }).fill('incorrect');
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Incorrect password');
  await page.getByLabel('Password', { exact: true }).fill('browser-only-password');
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(page.getByRole('heading', { name: /Hey Mikias/ })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Open menu' }).click();
  await page.getByRole('navigation').getByRole('button', { name: 'Telegram', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your agent, right in Telegram.' })).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
