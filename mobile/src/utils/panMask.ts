export function maskPan(pan: string): string {
  if (pan.length !== 10) return pan;
  return `${pan.slice(0, 5)}••••${pan.slice(9)}`;
}
