import { useEffect, useState } from 'react'
import { Header } from './components/Header'
import { MapSection } from './components/MapSection'
import { DataSection } from './components/DataSection'
import { trackerAPI, type TrackerData, type TimeRange } from './lib/api'

export default function App() {
  const [currentTime, setCurrentTime] = useState('00:00:00')
  const [signalStrength, setSignalStrength] = useState<number | null>(null)
  const [batteryLevel, setBatteryLevel] = useState<number | null>(null)
  const [wifiName, setWifiName] = useState("Unknown")
  const [powerPlugged, setPowerPlugged] = useState<boolean | null>(null)
  const [zoom, setZoom] = useState(12)
  const [timeRange, setTimeRange] = useState<TimeRange>('30d')
  const [isUpdating, setIsUpdating] = useState(true)
  const [data, setData] = useState<TrackerData | null>(null)
  const [mapStyle, setMapStyle] = useState('default')

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 1, 18))
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 1, 3))

  const fetchData = async () => {
    try {
      const newData = await trackerAPI.getData(timeRange)
      setData(newData)
      setSignalStrength(newData.systemInfo.signal_strength)
      setBatteryLevel(newData.systemInfo.battery_level)
      setWifiName(newData.systemInfo.wifi_name)
      setPowerPlugged(newData.systemInfo.power_plugged)
    } catch (error) {
      console.error('Error fetching data:', error)
    }
  }

  useEffect(() => {
    // Initial fetch
    fetchData()

    // Set up polling if updates are enabled
    let interval: number | undefined
    if (isUpdating) {
      interval = setInterval(fetchData, 10000) // Poll every 10 seconds
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [timeRange, isUpdating])

  // Update current time
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date()
      setCurrentTime(now.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }))
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  const handleTimeRangeChange = (value: string) => {
    setTimeRange(value)
  }

  const toggleUpdates = () => {
    setIsUpdating(prev => !prev)
  }

  // Calculate latest GPS position from geojson
  const latestPosition = data?.geojson.features.length 
    ? data.geojson.features[data.geojson.features.length - 1].geometry.coordinates
    : [37.7749, -122.4194]

  return (
    <div className="min-h-screen h-screen bg-[#0a120a] text-green-500 p-4 font-mono flex flex-col">
      <Header 
        signalStrength={signalStrength} 
        batteryLevel={batteryLevel}
        wifiName={wifiName}
        powerPlugged={powerPlugged}
        onTimeRangeChange={handleTimeRangeChange}
        timeRange={timeRange}
        isUpdating={isUpdating}
        onToggleUpdates={toggleUpdates}
      />
      <div className="flex-grow flex gap-4 mt-4">
        <MapSection 
          gpsData={{ 
            latitude: latestPosition[1],
            longitude: latestPosition[0]
          }}
          zoom={zoom} 
          onZoomIn={handleZoomIn} 
          onZoomOut={handleZoomOut}
          features={data?.geojson.features || []}
          mapStyle={mapStyle}
        />
        <DataSection 
          stats={data?.stats}
          chartData={data?.chartData}
          currentTime={currentTime}
          mapStyle={mapStyle}
          onMapStyleChange={setMapStyle}
        />
      </div>
    </div>
  )
}
