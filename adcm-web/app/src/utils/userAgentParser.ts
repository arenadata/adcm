/**
 * List of rules for recognizing browsers and tools.
 * Order is important: more specific patterns should come first.
 */
const UA_RULES = [
  // Tools and libraries (check first)
  { regex: /python-requests\/([\d.]+)/i, name: 'Python Requests' },
  { regex: /curl\/([\d.]+)/i, name: 'cURL' },
  { regex: /axios\/([\d.]+)/i, name: 'Axios' },
  { regex: /wget\/([\d.]+)/i, name: 'Wget' },
  { regex: /postmanruntime\/([\d.]+)/i, name: 'Postman' },
  { regex: /okhttp\/([\d.]+)/i, name: 'OkHttp' },

  // Browsers
  // YaBrowser and Edge contain the substring "Chrome", so they come before it.
  { regex: /YaBrowser\/([\d.]+)/i, name: 'Yandex Browser' },
  { regex: /Edg\/([\d.]+)/i, name: 'Edge' },
  { regex: /SberBrowser\/([\d.]+)/i, name: 'SberBrowser' },
  { regex: /OPR\/([\d.]+)/i, name: 'Opera' },
  { regex: /Firefox\/([\d.]+)/i, name: 'Firefox' },
  { regex: /Chrome\/([\d.]+)/i, name: 'Chrome' },
  { regex: /Safari\/([\d.]+)/i, name: 'Safari' },
];

/**
 * Parses the User-Agent string and returns a short name with the full version.
 * @param userAgent - Raw User-Agent string from audit log
 * @returns Formatted string like "Chrome 154.0.0.0" or "Unknown Browser"
 */
export function getShortBrowserName(userAgent: string ): string {

  for (const rule of UA_RULES) {
    const match = userAgent.match(rule.regex);
    const version = match?.[1];
    if (version) {
      return `${rule.name} ${version}`;
    }
  }

  return 'Unknown Client';
}
