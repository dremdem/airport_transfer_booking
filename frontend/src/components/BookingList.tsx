import { useState } from 'react'
import { api, ApiError, type Booking } from '../lib/api'
import StatusBadge from './StatusBadge'
import styles from './BookingList.module.css'

interface Props {
  onSelect: (booking: Booking) => void
  selectedId?: number
}

type Mode = 'date' | 'id'

export default function BookingList({ onSelect, selectedId }: Props) {
  const [mode, setMode] = useState<Mode>('date')
  const [date, setDate] = useState('')
  const [bookingId, setBookingId] = useState('')
  const [bookings, setBookings] = useState<Booking[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const switchMode = (next: Mode) => {
    setMode(next)
    setBookings(null)
    setError(null)
  }

  const searchByDate = async (e: React.FormEvent) => {
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

  const searchById = async (e: React.FormEvent) => {
    e.preventDefault()
    const id = parseInt(bookingId, 10)
    if (!id) return
    setLoading(true)
    setError(null)
    setBookings(null)
    try {
      const booking = await api.getBooking(id)
      onSelect(booking)
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
        <h2>Find a Booking</h2>
        <span className={styles.ornament}>✦</span>
      </div>

      <div className={styles.modeTabs}>
        <button
          type="button"
          className={`${styles.modeTab} ${mode === 'date' ? styles.modeTabActive : ''}`}
          onClick={() => switchMode('date')}
        >
          By Date
        </button>
        <button
          type="button"
          className={`${styles.modeTab} ${mode === 'id' ? styles.modeTabActive : ''}`}
          onClick={() => switchMode('id')}
        >
          By ID
        </button>
      </div>

      {mode === 'date' ? (
        <form className={styles.searchRow} onSubmit={searchByDate}>
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
      ) : (
        <form className={styles.searchRow} onSubmit={searchById}>
          <input
            type="number"
            min="1"
            placeholder="Booking ID"
            value={bookingId}
            onChange={e => setBookingId(e.target.value)}
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? '…' : 'Find'}
          </button>
        </form>
      )}

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
