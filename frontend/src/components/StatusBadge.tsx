import type { BookingStatus } from '../lib/api'
import styles from './StatusBadge.module.css'

export default function StatusBadge({ status }: { status: BookingStatus }) {
  return <span className={`${styles.badge} ${styles[status]}`}>{status}</span>
}
