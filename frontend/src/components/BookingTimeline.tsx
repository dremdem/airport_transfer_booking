import type { TimelineEntry } from '../lib/api'
import StatusBadge from './StatusBadge'
import styles from './BookingTimeline.module.css'

interface Props {
  entries: TimelineEntry[]
}

export default function BookingTimeline({ entries }: Props) {
  if (entries.length === 0) return null

  return (
    <div className={styles.timeline}>
      {entries.map((e, i) => (
        <div key={i} className={styles.entry}>
          <div className={styles.spine}>
            <div className={styles.dot} />
            {i < entries.length - 1 && <div className={styles.line} />}
          </div>
          <div className={styles.content}>
            <div className={styles.transition}>
              {e.old_status
                ? <><StatusBadge status={e.old_status} /><span className={styles.arrow}>→</span></>
                : <span className={styles.creation}>Created</span>
              }
              <StatusBadge status={e.new_status} />
            </div>
            <time className={styles.time}>{formatDateTime(e.transitioned_at)}</time>
          </div>
        </div>
      ))}
    </div>
  )
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString([], {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
