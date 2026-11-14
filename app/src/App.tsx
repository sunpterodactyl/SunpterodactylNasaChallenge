import { useEffect } from 'react'
import { useStore } from './store'
import TopBar from './components/TopBar'
import QueryStrip from './components/QueryStrip'
import MapView from './components/MapView'
import TerrainView from './components/TerrainView'
import LocationPanel from './components/LocationPanel'

export default function App() {
  const loadCatalog = useStore((s) => s.loadCatalog)
  const viewMode = useStore((s) => s.viewMode)

  useEffect(() => {
    void loadCatalog()
  }, [loadCatalog])

  return (
    <div className="app">
      <TopBar />
      <div className="search-page">
        <div className="map-stage">
          <QueryStrip />
          <div className="view-body">
            {viewMode === 'map' ? <MapView /> : <TerrainView />}
          </div>
        </div>
        <LocationPanel />
      </div>
    </div>
  )
}
