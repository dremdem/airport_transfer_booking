import { useState } from 'react'
import type { Booking } from './lib/api'
import BookingForm from './components/BookingForm'
import BookingList from './components/BookingList'
import BookingDetails from './components/BookingDetails'
import styles from './App.module.css'

type View = 'home' | 'details'

export default function App() {
  const [view, setView] = useState<View>('home')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [tab, setTab] = useState<'create' | 'search'>('search')

  const openBooking = (booking: Booking) => {
    setSelectedId(booking.id)
    setView('details')
  }

  const handleCreated = (booking: Booking) => {
    openBooking(booking)
  }

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.logo}>
            <span className={styles.logoMark}>✈</span>
            <div>
              <h1 className={styles.brand}>Prestige Transfers</h1>
              <p className={styles.tagline}>Premium Airport Transfer Management</p>
            </div>
          </div>
          <nav className={styles.nav}>
            <button
              className={`${styles.navBtn} ${tab === 'search' && view === 'home' ? styles.navActive : ''}`}
              onClick={() => { setTab('search'); setView('home') }}
            >
              Reservations
            </button>
            <button
              className={`${styles.navBtn} ${tab === 'create' && view === 'home' ? styles.navActive : ''}`}
              onClick={() => { setTab('create'); setView('home') }}
            >
              New Booking
            </button>
          </nav>
        </div>
        <div className={styles.headerRule} />
      </header>

      <main className={styles.main}>
        {view === 'details' && selectedId !== null ? (
          <div className={styles.detailsWrap}>
            <BookingDetails
              bookingId={selectedId}
              onBack={() => setView('home')}
              onUpdated={() => {}}
            />
          </div>
        ) : (
          <div className={styles.homeGrid}>
            {tab === 'create' ? (
              <BookingForm onCreated={handleCreated} />
            ) : (
              <BookingList
                onSelect={openBooking}
                selectedId={selectedId ?? undefined}
              />
            )}
          </div>
        )}
      </main>

      <footer className={styles.footer}>
        <div className={styles.footerRule} />
        <p>Prestige Transfers &copy; {new Date().getFullYear()}</p>
      </footer>
    </div>
  )
}
