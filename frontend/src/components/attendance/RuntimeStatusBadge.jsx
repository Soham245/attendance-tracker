/**
 * Re-export of the shared common badge. Kept in the attendance namespace
 * because the Phase 3 spec lists it under components/attendance, but the
 * implementation lives in components/common so other modules can use it too.
 */
export { default } from '../common/RuntimeStatusBadge.jsx';
