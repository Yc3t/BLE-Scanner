import { Map } from 'lucide-react'
import { GPSDataCard } from './DataSection'

const MAP_STYLES = [
  { id: 'default', name: 'Predeterminado', url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', maxZoom: 18 },
  { id: 'dark', name: 'Oscuro', url: 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png', maxZoom: 18 },
  { id: 'satellite', name: 'Satélite', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', maxZoom: 18 },
  { id: 'topo', name: 'Topográfico', url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', maxZoom: 17 },
]

interface MapStyleSelectorProps {
  currentStyle: string
  onStyleChange: (style: string) => void
}

export function MapStyleSelector({ currentStyle, onStyleChange }: MapStyleSelectorProps) {
  return (
    <GPSDataCard 
      title="ESTILO DE MAPA" 
      icon={<Map className="w-4 h-4" />}
    >
      <div className="grid grid-cols-2 gap-2">
        {MAP_STYLES.map(style => (
          <button
            key={style.id}
            onClick={() => onStyleChange(style.id)}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              currentStyle === style.id
                ? 'bg-green-500/20 text-green-500'
                : 'hover:bg-green-500/10 text-green-500/70'
            }`}
          >
            {style.name}
          </button>
        ))}
      </div>
    </GPSDataCard>
  )
}

export const MAP_STYLE_URLS = Object.fromEntries(
  MAP_STYLES.map(style => [style.id, style.url])
) 