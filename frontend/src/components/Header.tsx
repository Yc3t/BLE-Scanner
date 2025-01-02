import { RefreshCw, Signal, Battery, Radio, Satellite, Bluetooth } from 'lucide-react'
import { Button } from './ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'

interface HeaderProps {
  signalStrength: number
  batteryLevel: number
  timeRange: string
  isUpdating: boolean
  onTimeRangeChange: (value: string) => void
  onToggleUpdates: () => void
}

const TIME_RANGES = [
  { value: "5m", label: "Últimos 5 minutos" },
  { value: "15m", label: "Últimos 15 minutos" },
  { value: "30m", label: "Últimos 30 minutos" },
  { value: "1h", label: "Última hora" },
  { value: "6h", label: "Últimas 6 horas" },
  { value: "12h", label: "Últimas 12 horas" },
  { value: "24h", label: "Último día" },
  { value: "7d", label: "Última semana" },
  { value: "30d", label: "Último mes" },
]

export function Header({ 
  signalStrength, 
  batteryLevel, 
  timeRange,
  isUpdating,
  onTimeRangeChange,
  onToggleUpdates
}: HeaderProps) {
  return (
    <div className="flex flex-col gap-2 mb-4 border-b border-green-500/20 pb-4">
      <div className="flex flex-col lg:flex-row lg:justify-between lg:items-center gap-4">
        <div className="flex flex-col gap-2">
          <Select value={timeRange} onValueChange={onTimeRangeChange}>
            <SelectTrigger className="w-full lg:w-[180px] bg-black/40 border-green-500/30 text-green-500">
              <SelectValue placeholder="Select timeframe" />
            </SelectTrigger>
            <SelectContent className="bg-black text-green-500 border-green-500/30">
              {TIME_RANGES.map(range => (
                <SelectItem key={range.value} value={range.value}>
                  {range.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button 
            variant="destructive" 
            className="w-full lg:w-[180px] gap-2"
            onClick={onToggleUpdates}
          >
            <RefreshCw className={`w-4 h-4 ${isUpdating ? 'animate-spin' : ''}`} />
            {isUpdating ? 'Pausar' : 'Reanudar'}
          </Button>
        </div>

        <div className="px-4 lg:px-12 flex items-center border border-green-500/20 rounded-lg bg-black/40 h-[82px]">
          <div className="flex items-center gap-4">
            <Radio className="w-6 lg:w-8 h-6 lg:h-8 text-green-500" />
            <div className="flex flex-col">
              <h1 className="text-2xl lg:text-3xl font-bold tracking-[0.3em]">TRACKER</h1>
              <div className="flex items-center gap-2">
                <Satellite className="w-4 h-4 text-green-500/70" />
                <span className="text-base lg:text-lg font-semibold tracking-wider text-green-500/70">GPS</span>
                <span className="text-green-500/40 mx-1">|</span>
                <Bluetooth className="w-4 h-4 text-green-500/70" />
                <span className="text-base lg:text-lg font-semibold tracking-wider text-green-500/70">BLE</span>
              </div>
            </div>
          </div>
        </div>

        <div className="w-full lg:w-[180px] flex lg:flex-col gap-2">
          <div className="flex-1 lg:flex-none flex items-center gap-2 bg-black/40 px-3 py-1.5 rounded-md border border-green-500/20">
            <Signal className="w-4 h-4 text-green-500/70" />
            <span className="text-sm text-green-500/70">Señal: {signalStrength}%</span>
          </div>
          <div className="flex-1 lg:flex-none flex items-center gap-2 bg-black/40 px-3 py-1.5 rounded-md border border-green-500/20">
            <Battery className="w-4 h-4 text-green-500/70" />
            <span className="text-sm text-green-500/70">Batería: {batteryLevel}%</span>
          </div>
        </div>
      </div>
    </div>
  )
} 