import { useState } from 'react'
import { api, ApiError, type Booking } from '../lib/api'
import StatusBadge from './StatusBadge'
import styles from './BookingList.module.css'

interface Props {
  onSelect: (booking: Booking) => void
  selectedId?: number
}

export default function BookingList({ onSelect, selectedId }: Props) {
  const [date, setDate] = useState('')
  const [bookings, setBookings] = useState<Booking[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const search = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!date) return
    setLoading(true)
    setError(null)
    try {
      const list = await api.listBookings(date)
      setBookings(list)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unexpected error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.heading}>
        <span className={styles.ornament}>✦</span>
        <h2>Bookings by Date</h2>
        <span className={styles.ornament}>✦</span>
      </div>

      <form className={styles.searchRow} onSubmit={search}>
        <input
          type="date"
          value={date}
          onChange={e => setDate(e.target.value)}
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? '…' : 'Search'}
        </button>
      </form>

      {error && <p className={styles.error}>{error}</p>}

      {bookings !== null && (
        bookings.length === 0
          ? <p className={styles.empty}>No bookings found for this date.</p>
          : (
            <ul className={styles.list}>
              {bookings.map(b => (
                <li
                  key={b.id}
                  className={`${styles.item} ${b.id === selectedId ? styles.active : ''}`}
                  onClick={() => onSelect(b)}
                >
                  <div className={styles.itemTop}>
                    <span className={styles.name}>{b.passenger_name}</span>
                    <StatusBadge status={b.status} />
                  </div>
                  <div className={styles.itemSub}>
                    <span>{b.flight_number}</span>
                    <span>·</span>
                    <span>{formatTime(b.pickup_time)}</span>
                  </div>
                  <div className={styles.route}>
                    <span>{b.pickup_location}</span>
                    <span className={styles.arrow}>→</span>
                    <span>{b.dropoff_location}</span>
                  </div>
                </li>
              ))}
            </ul>
          )
      )}
    </div>
  )
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
