import { AnimatePresence, motion } from 'framer-motion';

/**
 * Animates between distinct runtime states (idle/starting/running/stopping/...)
 * with a barely-visible cross-fade so the panel feels stable instead of
 * snapping. Re-renders inside the same state pass through untouched, since
 * `key` is `state` and AnimatePresence diffs by key.
 *
 * Intentionally not used for incremental updates (counters, last-event) —
 * only for genuine state transitions.
 */
export default function RuntimeTransitionWrapper({ state, children }) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={state ?? 'unknown'}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.12, ease: 'easeOut' }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
