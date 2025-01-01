import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Target, ZoomIn, ZoomOut, Bluetooth } from 'lucide-react'
import { Button } from './ui/button'
import { type TrackerData } from '@/lib/api'
import { MAP_STYLE_URLS } from './MapStyleSelector'
import ReactDOMServer from 'react-dom/server'

interface MapSectionProps {
  gpsData: {
    latitude: number
    longitude: number
  }
  zoom: number
  onZoomIn: () => void
  onZoomOut: () => void
  features: TrackerData['geojson']['features']
  mapStyle: string
}

export function MapSection({ gpsData, zoom, onZoomIn, onZoomOut, features, mapStyle }: MapSectionProps) {
  const mapRef = useRef<L.Map | null>(null)
  const gpsLayerRef = useRef<L.LayerGroup | null>(null)
  const bleLayerRef = useRef<L.LayerGroup | null>(null)
  const trailLayerRef = useRef<L.LayerGroup | null>(null)
  const tileLayerRef = useRef<L.TileLayer | null>(null)

  // Update zoom when prop changes
  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.setZoom(zoom)
    }
  }, [zoom])

  useEffect(() => {
    // Initialize map if not already done
    if (!mapRef.current) {
      mapRef.current = L.map('map', {
        zoomControl: false,
        attributionControl: false,
        minZoom: 3,
        maxZoom: 22
      }).setView([37.7122, -0.9892], zoom)

      // Add initial tile layer
      tileLayerRef.current = L.tileLayer(MAP_STYLE_URLS[mapStyle], {
        minZoom: 3,
        maxZoom: 22,
        attribution: ''
      }).addTo(mapRef.current)

      // Create separate layers for GPS, BLE, and trail
      gpsLayerRef.current = L.layerGroup().addTo(mapRef.current)
      bleLayerRef.current = L.layerGroup().addTo(mapRef.current)
      trailLayerRef.current = L.layerGroup().addTo(mapRef.current)
    }

    // Update tile layer when style changes
    if (mapRef.current && tileLayerRef.current) {
      tileLayerRef.current.setUrl(MAP_STYLE_URLS[mapStyle])
    }

    // Clear existing layers
    if (gpsLayerRef.current) gpsLayerRef.current.clearLayers()
    if (bleLayerRef.current) bleLayerRef.current.clearLayers()
    if (trailLayerRef.current) trailLayerRef.current.clearLayers()

    // Filter and sort points by type
    const gpsFeatures = features.filter(f => f.properties.type === 'gps')
    const bufferFeatures = features.filter(f => f.properties.type === 'buffer')

    // Create trail from GPS points
    const trailPoints = gpsFeatures.map(f => [
      f.geometry.coordinates[1],
      f.geometry.coordinates[0]
    ] as [number, number])

    // Add GPS trail first with updated style
    if (trailPoints.length > 1 && trailLayerRef.current) {
      L.polyline(trailPoints, {
        color: 'red',
        weight: 5,
        opacity: 0.7,
        smoothFactor: 1
      }).addTo(trailLayerRef.current)
    }

    // Add markers
    const bounds: L.LatLng[] = []

    // Add GPS points
    gpsFeatures.forEach(feature => {
      try {
        const coords = feature.geometry.coordinates
        if (!coords || coords.length !== 2) return
        
        const latLng: [number, number] = [coords[1], coords[0]]
        bounds.push(L.latLng(latLng[0], latLng[1]))

        if (gpsLayerRef.current) {
          L.circleMarker(latLng, {
            color: '#22c55e',
            fillColor: '#22c55e',
            fillOpacity: 0.5,
            radius: 6,
            weight: 1
          })
          .bindPopup(`
            <div class="p-2">
              <div>Time: ${new Date(feature.properties.timestamp).toLocaleTimeString()}</div>
              <div>Speed: ${feature.properties.speed.toFixed(1)} km/h</div>
            </div>
          `)
          .addTo(gpsLayerRef.current)
        }
      } catch (error) {
        console.error('Error adding GPS marker:', error)
      }
    })

    // Add buffer points with updated style
    bufferFeatures.forEach(feature => {
      try {
        const coords = feature.geometry.coordinates
        if (!coords || coords.length !== 2) return
        
        const latLng: [number, number] = [coords[1], coords[0]]
        bounds.push(L.latLng(latLng[0], latLng[1]))

        if (bleLayerRef.current) {
          // Create custom divIcon for buffer points
          const bufferIcon = L.divIcon({
            className: 'buffer-icon',
            html: `<div class="w-5 h-5 rounded-full bg-black/80 border border-green-500/50 flex items-center justify-center">
              ${ReactDOMServer.renderToString(
                <Bluetooth size={12} color="#22c55e" strokeWidth={1.5} />
              )}
            </div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10],
            popupAnchor: [0, -15]
          })

          L.marker(latLng, { 
            icon: bufferIcon 
          })
          .bindPopup(`
            <div class="p-3 text-green-500">
              <h3 class="text-sm font-bold mb-2">Buffer ${feature.properties.sequence}</h3>
              <p class="text-xs">Devices: ${feature.properties.n_devices}</p>
            </div>
          `, {
            className: 'buffer-popup'
          })
          .addTo(bleLayerRef.current)
        }
      } catch (error) {
        console.error('Error adding buffer marker:', error)
      }
    })

    // Add CSS for popup and buffer icon styling
    const style = document.createElement('style')
    style.textContent = `
      .buffer-icon {
        background: transparent;
        border: none;
      }
      .buffer-popup .leaflet-popup-content-wrapper {
        background: transparent !important;
        box-shadow: none;
        border: none;
        border-radius: 0;
      }
      .buffer-popup .leaflet-popup-tip {
        background: rgba(0, 0, 0, 0.9);
      }
      .leaflet-popup-content {
        margin: 0 !important;
      }
      .buffer-popup .leaflet-popup-content > div {
        background-color: rgba(0, 0, 0, 0.7) !important;
      }
    `
    document.head.appendChild(style)

    return () => {
      document.head.removeChild(style)
    }
  }, [features, mapStyle])

  return (
    <div 
      className="flex-grow relative border border-green-500/20 rounded-lg overflow-hidden min-h-[300px] lg:min-h-0"
      data-map-style={mapStyle}
    >
      <div id="map" className="w-full h-full" />
      
      <div className="absolute top-4 left-4 bg-black/80 p-2 lg:p-3 rounded-lg border border-green-500/30 space-y-1 z-[1000]">
        <p className="text-xs lg:text-sm flex items-center gap-2">
          <Target className="w-3 h-3 lg:w-4 lg:h-4" />
          LAT: {gpsData.latitude.toFixed(6)}
        </p>
        <p className="text-xs lg:text-sm flex items-center gap-2">
          <Target className="w-3 h-3 lg:w-4 lg:h-4" />
          LON: {gpsData.longitude.toFixed(6)}
        </p>
      </div>

      <div className="absolute top-4 right-4 flex flex-col gap-2 z-[1000]">
        <Button onClick={onZoomIn} variant="outline" size="icon" className="h-8 w-8 lg:h-9 lg:w-9 border-green-500/30 bg-black/80 hover:bg-black/60">
          <ZoomIn className="w-3 h-3 lg:w-4 lg:h-4" />
        </Button>
        <Button onClick={onZoomOut} variant="outline" size="icon" className="h-8 w-8 lg:h-9 lg:w-9 border-green-500/30 bg-black/80 hover:bg-black/60">
          <ZoomOut className="w-3 h-3 lg:w-4 lg:h-4" />
        </Button>
      </div>
    </div>
  )
} 