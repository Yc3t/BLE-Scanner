export interface GPSData {
  coordinates: {
    latitude: number
    longitude: number
  }
  speed: number
  track_valid: boolean
}

export interface Device {
  mac: string
  addr_type: number
  adv_type: number
  rssi: number
  data_len: number
  data: string
  n_adv: number
}

export interface TrackerData {
  geojson: {
    type: string
    features: Array<{
      type: string
      geometry: {
        type: string
        coordinates: [number, number]
      }
      properties: {
        type: string
        timestamp: string
        speed: number
      }
    }>
  }
  stats: {
    total_buffers: number
    recent_buffers: number
    recent_buffers_label: string
    unique_devices: number
    total_advertisements: number
    last_sequence: number
    last_timestamp: string
  }
  chartData: Array<{
    buffer: number
    devices: number
    timestamp: string
  }>
  systemInfo: {
    wifi_name: string
    signal_strength: number | null
    battery_level: number | null
    power_plugged: boolean | null
  }
}

export type TimeRange = '5m' | '15m' | '30m' | '1h' | '6h' | '12h' | '24h' | '7d' | '30d'

class TrackerAPI {
  private baseUrl: string

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000'
    console.log('API Base URL:', this.baseUrl)
  }

  async getData(timeRange: TimeRange = '30d'): Promise<TrackerData> {
    try {
      console.log(`Fetching data for timeRange: ${timeRange}`)
      const response = await fetch(`${this.baseUrl}/api/data?timeRange=${timeRange}`)
      
      if (!response.ok) {
        console.error('API Error:', response.status, response.statusText)
        const text = await response.text()
        console.error('Error response:', text)
        throw new Error('Network response was not ok')
      }
      
      const data = await response.json()
      console.log('API Response:', data)
      return data
    } catch (error) {
      console.error('Error fetching data:', error)
      throw error
    }
  }
}

export const trackerAPI = new TrackerAPI() 