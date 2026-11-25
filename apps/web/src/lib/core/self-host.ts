import { isFeatureEnabled, selfHost } from '@core/constant/featureFlags';

/**
 * Nav destinations a self-hosted server does not run. Docs and tasks stay.
 * GitHub and Slack stay on the integrations page, not in this list.
 */
const HIDDEN_NAV = new Set([
  'mail',
  'channels',
  'calendar',
  'passwords',
  'agents',
  'companies',
  'calls',
  'reviews',
  'activity',
  'booking-links',
  'external',
  'for-you',
  'notifications',
  'routines',
  'search',
  'recent',
]);

/** Settings tabs whose services or billing screens are not in the self-host stack. */
const HIDDEN_SETTINGS = new Set([
  'Billing',
  'Usage',
  'Email',
  'Calendar',
  'CRM',
  'Agent',
  'Harness',
  'Agents',
  'Routines',
  'Bots',
]);

/** Whether this bundle was built for the self-hosted product. */
export function selfHostEnabled(): boolean {
  return isFeatureEnabled(selfHost);
}

/** Whether a sidebar destination is shown. Hosted builds show everything. */
export function selfHostShowsNav(id: string): boolean {
  return !selfHostEnabled() || !HIDDEN_NAV.has(id);
}

/** Whether a settings tab is shown. */
export function selfHostShowsSettings(tab: string): boolean {
  return !selfHostEnabled() || !HIDDEN_SETTINGS.has(tab);
}
