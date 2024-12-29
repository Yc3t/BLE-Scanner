import { Bluetooth, Satellite, BarChart2 } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'
import type { TrackerData } from '@/lib/api'
import { MapStyleSelector } from './MapStyleSelector'

interface DataSectionProps {
  stats: TrackerData['stats'] | undefined
  chartData: TrackerData['chartData'] | undefined
  currentTime: string
  mapStyle: string
  onMapStyleChange: (style: string) => void
}

export function DataSection({ 
  stats, 
  chartData, 
  currentTime,
  mapStyle,
  onMapStyleChange
}: DataSectionProps) {
  if (!stats) {
    return (
      <div className="w-96 space-y-3">
        <div className="bg-black/40 border border-green-500/20 rounded-lg p-4">
          Loading data...
        </div>
      </div>
    )
  }

  return (
    <div className="w-96 space-y-3">
      <GPSDataCard 
        title={`BLE STATUS - ${currentTime}`}
        icon={<Bluetooth className="w-4 h-4" />}
      >
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>Total Buffers: {stats.total_buffers.toLocaleString()}</div>
          <div>{stats.recent_buffers_label}: {stats.recent_buffers.toLocaleString()}</div>
          <div>Dispositivos: {stats.unique_devices.toLocaleString()}</div>
          <div>Advertisements: {stats.total_advertisements.toLocaleString()}</div>
        </div>
      </GPSDataCard>

      <GPSDataCard 
        title="LAST UPDATE" 
        icon={<Satellite className="w-4 h-4" />}
      >
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>Seq: #{stats.last_sequence}</div>
          <div>Time: {new Date(stats.last_timestamp).toLocaleTimeString()}</div>
          <div>Devices: {stats.last_n_mac}</div>
          <div>Speed: {(stats.last_speed * 1.852).toFixed(1)} km/h</div>
          <div>Lat: {stats.last_latitude.toFixed(6)}°</div>
          <div>Lon: {stats.last_longitude.toFixed(6)}°</div>
        </div>
      </GPSDataCard>

      <GPSDataCard 
        title="Dispositivos por buffer" 
        icon={<BarChart2 className="w-4 h-4" />}
      >
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis 
                dataKey="buffer" 
                stroke="#22c55e" 
                strokeOpacity={0.5}
                fontSize={10}
              />
              <YAxis 
                stroke="#22c55e" 
                strokeOpacity={0.5}
                fontSize={10}
                domain={['auto', 'auto']}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(0, 0, 0, 0.8)',
                  border: '1px solid rgba(34, 197, 94, 0.2)',
                  borderRadius: '4px'
                }}
                labelStyle={{ color: '#22c55e' }}
                itemStyle={{ color: '#22c55e' }}
              />
              <Line 
                type="monotone" 
                dataKey="devices" 
                stroke="#22c55e" 
                strokeWidth={2}
                dot={{ fill: '#22c55e', r: 2 }}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </GPSDataCard>

      <MapStyleSelector 
        currentStyle={mapStyle}
        onStyleChange={onMapStyleChange}
      />
    </div>
  )
}

interface GPSDataCardProps {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
}

export function GPSDataCard({ title, icon, children }: GPSDataCardProps) {
  return (
    <div className="bg-black/40 border border-green-500/20 rounded-lg p-4">
      <h3 className="text-green-500/70 text-sm flex items-center gap-2 mb-2">
        {icon}
        {title}
      </h3>
      {children}
    </div>
  )
} 