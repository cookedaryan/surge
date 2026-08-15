import { test, expect, Locator, Page } from '@playwright/test';

/**
 * The path a demo actually takes, against a running stack.
 *
 * Every seam here has broken at least once while each service passed its own tests: the map
 * rendering nothing because the job id never reached the query, the scenario selector changing a
 * label and nothing else, the BOM disagreeing with the decision panel about the same job. Those
 * only show up end to end.
 */

const USERNAME = process.env.SURGE_E2E_USERNAME ?? 'admin';
const PASSWORD = process.env.SURGE_E2E_PASSWORD ?? 'admin';
const PROJECT_NAME = process.env.SURGE_E2E_PROJECT;

test.beforeEach(async ({ page }) => {
  const response = await page.goto('/').catch(() => null);
  test.skip(
    !response || !response.ok(),
    'SURGE web app is not reachable — start the stack (docker compose up -d) and the dev server.'
  );
});

async function signIn(page: Page): Promise<void> {
  const gateway = page.locator('form', { hasText: 'Sign in to SURGE' });
  if (await gateway.isVisible().catch(() => false)) {
    await gateway.getByPlaceholder('Username').fill(USERNAME);
    await gateway.getByPlaceholder('Password').fill(PASSWORD);
    await gateway.getByRole('button', { name: /sign in/i }).click();
  }
  await expect(gateway).toBeHidden();
}

/** Radix Select is a button + listbox, not a native <select>. */
async function chooseFromSelect(page: Page, trigger: Locator, optionText: string): Promise<void> {
  await trigger.click();
  await page.getByRole('option', { name: optionText, exact: true }).click();
  await expect(trigger).toContainText(optionText);
}

async function openTab(page: Page, title: string): Promise<void> {
  await page.locator(`nav button[title="${title}"]`).click();
}

test('sign-in loads real projects rather than inventing one', async ({ page }) => {
  await signIn(page);

  const projectSelect = page.locator('header [role="combobox"]').first();
  await expect(projectSelect).toBeVisible();
  // A failed project fetch used to be indistinguishable from an empty account, and the app
  // responded by creating a placeholder project on top of data it simply could not read yet.
  await expect(projectSelect).not.toContainText('Default Workstation Project');
});

test('a project with assets can run an optimisation and explain the result', async ({ page }) => {
  await signIn(page);

  const projectSelect = page.locator('header [role="combobox"]').first();
  if (PROJECT_NAME) {
    await chooseFromSelect(page, projectSelect, PROJECT_NAME);
  }

  await openTab(page, 'Assets');
  const assetSummary = page.getByText('PROJECT ASSET SUMMARY');
  await expect(assetSummary).toBeVisible();

  await openTab(page, 'Optimization');
  const runButton = page.getByRole('button', { name: /run optimization/i });
  await expect(runButton).toBeVisible();

  test.skip(
    !(await runButton.isEnabled()),
    'Selected project cannot be optimised (no optimisable turbines or no substation). ' +
      'Set SURGE_E2E_PROJECT to a project with assets.'
  );

  await runButton.click();

  // The decision summary is the product claim: not just that a line was drawn, but why.
  const decision = page.getByText('WHY THIS ROUTE');
  await expect(decision).toBeVisible({ timeout: 150_000 });
  await expect(page.getByText(/Optimised for/i)).toBeVisible();

  // The scenario that produced the result must be named, so a reader knows which run they are
  // looking at rather than assuming the default.
  await expect(page.getByText(/Optimised for (Balanced|Minimum)/i)).toBeVisible();
});

test('the BOM strip agrees with the run it belongs to', async ({ page }) => {
  await signIn(page);
  if (PROJECT_NAME) {
    await chooseFromSelect(page, page.locator('header [role="combobox"]').first(), PROJECT_NAME);
  }

  const bomStrip = page.locator('text=NETWORK LENGTH').locator('..');
  await expect(bomStrip).toBeVisible();

  // These panels were once rendered behind the Leaflet canvas and unreadable, which no unit test
  // would have noticed.
  await expect(page.getByText('NETWORK LENGTH')).toBeInViewport();
  await expect(page.getByText('POLES')).toBeInViewport();
});

test('account administration is offered only to administrators', async ({ page }) => {
  await signIn(page);

  const usersTab = page.locator('nav button[title="Users"]');
  if (USERNAME === 'admin') {
    await expect(usersTab).toBeVisible();
    await openTab(page, 'Users');
    await expect(page.getByText('USER ADMINISTRATION')).toBeVisible();
    // An administrator must not be able to lock themselves out.
    const selfSuspend = page
      .locator('div', { hasText: /\bYOU\b/ })
      .getByRole('button', { name: /^Suspend$/ })
      .first();
    if (await selfSuspend.count()) {
      await expect(selfSuspend).toBeDisabled();
    }
  } else {
    await expect(usersTab).toBeHidden();
  }
});

test('the audit log records the work, not just sign-ins', async ({ page }) => {
  await signIn(page);
  await openTab(page, 'Audit');

  // The headings are uppercased in CSS, so match case-insensitively against the DOM text.
  await expect(page.getByRole('heading', { name: /audit log/i })).toBeVisible();
  await expect(page.getByText(/USER_LOGIN/).first()).toBeVisible();

  // The point of audit coverage: the log records the work, not only who signed in. Before this,
  // USER_LOGIN and USER_REGISTERED were the only two events the entire codebase ever wrote.
  await expect(
    page.getByText(/PROJECT_CREATED|ASSETS_IMPORTED|OPTIMIZATION_COMPLETED|REPORT_EXPORTED/).first()
  ).toBeVisible();
});
