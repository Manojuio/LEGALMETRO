export const ROLES = {
  ADMIN: {
    label: 'Administrator',
    short: 'Admin',
    icon: '🛡️',
    tagline: 'Manage LMOs & review their compliance reports',
  },
  LMO: {
    label: 'Legal Metrology Officer',
    short: 'LMO',
    icon: '⚖️',
    tagline: 'Field inspections, enforcement & compliance review',
  },
  MANUFACTURER: {
    label: 'Manufacturer',
    short: 'Manufacturer',
    icon: '🏭',
    tagline: 'Manage your products and package compliance',
  },
  RETAILER: {
    label: 'Retailer',
    short: 'Retailer',
    icon: '🏬',
    tagline: 'Verify packaged goods before they hit your shelves',
  },
  CONSUMER: {
    label: 'Consumer',
    short: 'Consumer',
    icon: '🛒',
    tagline: 'Scan and verify packaged products you buy',
  },
}

export function roleConfig(role) {
  return ROLES[role] || ROLES.CONSUMER
}
