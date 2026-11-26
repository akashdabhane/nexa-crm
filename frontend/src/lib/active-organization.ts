/**
 * The organization the user is working in, remembered in this browser.
 *
 * It's only a preference: the API checks membership on every request (the
 * X-Organization-Id header) and answers 404 for organizations you're not in.
 * Switching organizations reloads the app, so no cached data from the
 * previous one survives.
 */

const STORAGE_KEY = "nexa.activeOrganizationId";

export const ORGANIZATIONS_PATH = "/organizations";

export function getActiveOrganizationId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

export function clearActiveOrganization() {
  if (typeof window !== "undefined") window.localStorage.removeItem(STORAGE_KEY);
}

/** Switch to an organization and open its dashboard with a clean page load. */
export function enterOrganization(id: string, path = "/dashboard") {
  window.localStorage.setItem(STORAGE_KEY, id);
  window.location.assign(path);
}

/** Go back to the organization picker (e.g. access was removed), forgetting the current choice. */
export function leaveToOrganizationPicker() {
  clearActiveOrganization();
  // A full page load (not router.push) so no cached data from the old organization survives.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  if (window.location.pathname !== ORGANIZATIONS_PATH) window.location.assign(ORGANIZATIONS_PATH);
}
