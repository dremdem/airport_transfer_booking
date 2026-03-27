import { useEffect, useState } from 'react'
import { api, ApiError, type Booking, type TimelineEntry, type BookingStatus, VALID_TRANSITIONS } from '../lib/api'
import StatusBadge from './StatusBadge'
import BookingTimeline from './BookingTimeline'
import styles from './BookingDetails.module.css'

interface Props {
  bookingId: number
  onBack: () => void
  onUpdated: (booking: Booking) => void
}

export default function BookingDetails({ bookingId, onBack, onUpdated }: Props) {
  const [booking, setBooking] = useState<Booking | null>(null)
  const [timeline, setTimeline] = useState<TimelineEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [transitioning, setTransitioning] = useState<BookingStatus | null>(null)

  const load = async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const [b, t] = await Promise.all([api.getBooking(bookingId), api.getTimeline(bookingId)])
      setBooking(b)
      setTimeline(t)
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : 'Failed to load booking')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [bookingId])

  const handleTransition = async (newStatus: BookingStatus) => {
    setTransitioning(newStatus)
    setActionError(null)
    try {
      const updated = await api.updateStatus(bookingId, newStatus)
      setBooking(updated)
      onUpdated(updated)
      const t = await api.getTimeline(bookingId)
      setTimeline(t)
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Unexpected error')
    } finally {
      setTransitioning(null)
    }
  }

  if (loading) return <div className={styles.loading}><div className={styles.spinner} /></div>

  if (loadError) return (
    <div className={styles.container}>
      <button className={styles.back} onClick={onBack}>← Back</button>
      <div className={styles.loadError}>
        <p>{loadError}</p>
        <button className={styles.retryBtn} onClick={load}>Retry</button>
      </div>
    </div>
  )

  if (!booking) return null

  const nextStatuses = VALID_TRANSITIONS[booking.status]

  return (
    <div className={styles.container}>
      <button className={styles.back} onClick={onBack}>← Back</button>

      <div className={styles.header}>
        <div>
          <h2 className={styles.name}>{booking.passenger_name}</h2>
          <p className={styles.sub}>Booking #{booking.id}</p>
        </div>
        <StatusBadge status={booking.status} />
      </div>

      <div className={styles.divider} />

      <div className={styles.fields}>
        <DetailRow label="Flight" value={booking.flight_number} />
        <DetailRow label="Pickup" value={`${formatDateTime(booking.pickup_time)}`} />
        <DetailRow label="From" value={booking.pickup_location} />
        <DetailRow label="To" value={booking.dropoff_location} />
        <DetailRow label="Created" value={formatDateTime(booking.created_at)} />
      </div>

      {nextStatuses.length > 0 && (
        <div className={styles.actions}>
          <p className={styles.actionsLabel}>Update Status</p>
          <div className={styles.actionButtons}>
            {nextStatuses.map(s => (
              <button
                key={s}
                className={`${styles.actionBtn} ${styles[s]}`}
                onClick={() => handleTransition(s)}
                disabled={transitioning !== null}
              >
                {transitioning === s ? '…' : s}
              </button>
            ))}
          </div>
          {actionError && <p className={styles.error}>{actionError}</p>}
        </div>
      )}

      <div className={styles.timelineSection}>
        <h3 className={styles.timelineTitle}>
          <span className={styles.ornament}>✦</span>
          Journey Timeline
          <span className={styles.ornament}>✦</span>
        </h3>
        <BookingTimeline entries={timeline} />
      </div>
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.row}>
      <span className={styles.rowLabel}>{label}</span>
      <span className={styles.rowValue}>{value}</span>
    </div>
  )
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString([], {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
