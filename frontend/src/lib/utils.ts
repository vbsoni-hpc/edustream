/**
 * Utility functions for EduStream
 */

/** Format seconds to a human-readable duration string */
export function formatDuration(sec: number): string {
  if (sec <= 0) return '--:--';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

/** Format seconds as hours (e.g., "12.5h") */
export function formatHours(sec: number): string {
  return (sec / 3600).toFixed(1) + 'h';
}

/** Format a unix timestamp to relative time */
export function timeAgo(timestamp: number): string {
  const seconds = Math.floor(Date.now() / 1000 - timestamp);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

/** Format a unix timestamp to a date string */
export function formatDate(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/** Format a unix timestamp to a time string */
export function formatTime(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Natural sort key: extract numbers from a title for sorting */
export function naturalSortKey(title: string): number[] {
  const nums = title.match(/\d+/g);
  return nums ? nums.map(Number) : [Infinity];
}

/** Compare two items by natural sort key */
export function naturalCompare(a: string, b: string): number {
  const ka = naturalSortKey(a);
  const kb = naturalSortKey(b);
  for (let i = 0; i < Math.max(ka.length, kb.length); i++) {
    const va = ka[i] ?? Infinity;
    const vb = kb[i] ?? Infinity;
    if (va !== vb) return va - vb;
  }
  return 0;
}

/** Clamp a number between min and max */
export function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}
