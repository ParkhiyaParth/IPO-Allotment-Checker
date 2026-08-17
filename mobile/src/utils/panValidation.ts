const PAN_PATTERN = /^[A-Z]{5}[0-9]{4}[A-Z]$/;

export function isValidPan(pan: string): boolean {
  return PAN_PATTERN.test(pan.trim().toUpperCase());
}

export function normalizePan(pan: string): string {
  return pan.trim().toUpperCase();
}
