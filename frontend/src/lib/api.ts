const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

export type BookingStatus = 'pending' | 'confirmed' | 'completed' | 'cancelled'

export interface Booking {
  id: number
  passenger_name: string
  flight_number: string
  pickup_time: string
  pickup_location: string
  dropoff_location: string
  status: BookingStatus
  created_at: string
  updated_at: string
}

export interface BookingCreate {
  passenger_name: string
  flight_number: string
  pickup_time: string
  pickup_location: string
  dropoff_location: string
}

export interface TimelineEntry {
  booking_id: number
  passenger_name: string
  flight_number: string
  pickup_time: string
  pickup_location: string
  dropoff_location: string
  current_status: BookingStatus
  old_status: BookingStatus | null
  new_status: BookingStatus
  transitioned_at: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body?.detail ?? 'Request failed')
  }
  return res.json() as Promise<T>
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export const api = {
  createBooking: (data: BookingCreate) =>
    request<Booking>('/bookings', { method: 'POST', body: JSON.stringify(data) }),

  listBookings: (date: string) =>
    request<Booking[]>(`/bookings?date=${date}`),

  getBooking: (id: number) =>
    request<Booking>(`/bookings/${id}`),

  updateStatus: (id: number, status: BookingStatus) =>
    request<Booking>(`/bookings/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),

  getTimeline: (id: number) =>
    request<TimelineEntry[]>(`/bookings/${id}/timeline`),
}

export const VALID_TRANSITIONS: Record<BookingStatus, BookingStatus[]> = {
  pending: ['confirmed', 'cancelled'],
  confirmed: ['completed', 'cancelled'],
  completed: [],
  cancelled: [],
}
