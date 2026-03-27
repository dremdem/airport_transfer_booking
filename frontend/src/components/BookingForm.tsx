import { useState } from 'react'
import { api, ApiError, type Booking, type BookingCreate } from '../lib/api'
import styles from './BookingForm.module.css'

interface Props {
  onCreated: (booking: Booking) => void
}

const EMPTY: BookingCreate = {
  passenger_name: '',
  flight_number: '',
  pickup_time: '',
  pickup_location: '',
  dropoff_location: '',
}

export default function BookingForm({ onCreated }: Props) {
  const [form, setForm] = useState<BookingCreate>(EMPTY)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = (field: keyof BookingCreate) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [field]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      // datetime-local gives "YYYY-MM-DDTHH:mm" — send as wall-clock time.
      // Avoid toISOString() which converts to UTC and shifts non-UTC locales.
      const pickup_time = form.pickup_time.length === 16
        ? form.pickup_time + ':00'
        : form.pickup_time
      const booking = await api.createBooking({ ...form, pickup_time })
      onCreated(booking)
      setForm(EMPTY)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unexpected error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.heading}>
        <span className={styles.ornament}>✦</span>
        <h2>New Reservation</h2>
        <span className={styles.ornament}>✦</span>
      </div>

      <div className={styles.grid}>
        <Field label="Passenger Name" id="pname">
          <input
            id="pname"
            value={form.passenger_name}
            onChange={set('passenger_name')}
            placeholder="Full name"
            required
          />
        </Field>
        <Field label="Flight Number" id="flight">
          <input
            id="flight"
            value={form.flight_number}
            onChange={set('flight_number')}
            placeholder="e.g. BA123"
            required
          />
        </Field>
        <Field label="Pickup Time" id="ptime" wide>
          <input
            id="ptime"
            type="datetime-local"
            value={form.pickup_time}
            onChange={set('pickup_time')}
            required
          />
        </Field>
        <Field label="Pickup Location" id="ploc">
          <input
            id="ploc"
            value={form.pickup_location}
            onChange={set('pickup_location')}
            placeholder="Terminal, address…"
            required
          />
        </Field>
        <Field label="Dropoff Location" id="dloc">
          <input
            id="dloc"
            value={form.dropoff_location}
            onChange={set('dropoff_location')}
            placeholder="Hotel, address…"
            required
          />
        </Field>
      </div>

      {error && <p className={styles.error}>{error}</p>}

      <button className={styles.submit} type="submit" disabled={loading}>
        {loading ? 'Processing…' : 'Reserve Transfer'}
      </button>
    </form>
  )
}

function Field({ label, id, children, wide }: {
  label: string; id: string; children: React.ReactNode; wide?: boolean
}) {
  return (
    <div className={`${styles.field} ${wide ? styles.wide : ''}`}>
      <label htmlFor={id}>{label}</label>
      {children}
    </div>
  )
}
