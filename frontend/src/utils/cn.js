// Tiny class-name joiner. Avoids pulling in `clsx` for one helper.
export function cn(...parts) {
  return parts.filter(Boolean).join(' ');
}
