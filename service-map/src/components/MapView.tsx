import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { Institution, RouteDestination, RecommendedStop } from '../types';
import { useEffect } from 'react';

// Fix default marker icon issue with bundlers
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const targetIcon = new L.Icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  className: 'marker-target',
});

const recommendedIcon = new L.Icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  className: 'marker-recommended',
});

const originIcon = new L.Icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  className: 'marker-origin',
});

interface Props {
  institutions: Institution[];
  selectedRoute: RouteDestination | null;
  recommendations: RecommendedStop[];
  onSelectInstitution: (inst: Institution) => void;
}

function FitBounds({ route }: { route: [number, number][] | null }) {
  const map = useMap();
  useEffect(() => {
    if (route && route.length > 0) {
      const bounds = L.latLngBounds(route.map(([lat, lng]) => [lat, lng]));
      map.fitBounds(bounds, { padding: [40, 40] });
    }
  }, [route, map]);
  return null;
}

function getMarkerIcon(
  inst: Institution,
  selectedRoute: RouteDestination | null,
  recommendations: RecommendedStop[]
) {
  if (inst.id === 'fn-motol') return originIcon;
  if (selectedRoute && inst.id === selectedRoute.targetInstitution) return targetIcon;
  if (recommendations.some((r) => r.id === inst.id)) return recommendedIcon;
  return new L.Icon.Default();
}

export default function MapView({
  institutions,
  selectedRoute,
  recommendations,
  onSelectInstitution,
}: Props) {
  const czCenter: [number, number] = [49.8, 15.5];

  return (
    <MapContainer center={czCenter} zoom={7} className="map-container">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {selectedRoute && (
        <>
          <Polyline
            positions={selectedRoute.route}
            pathOptions={{ color: '#2563eb', weight: 4, opacity: 0.8 }}
          />
          <FitBounds route={selectedRoute.route} />
        </>
      )}

      {institutions.map((inst) => {
        const isRecommended = recommendations.some((r) => r.id === inst.id);
        const isTarget = selectedRoute?.targetInstitution === inst.id;
        const isOrigin = inst.id === 'fn-motol';

        return (
          <Marker
            key={inst.id}
            position={[inst.lat, inst.lng]}
            icon={getMarkerIcon(inst, selectedRoute, recommendations)}
            opacity={
              !selectedRoute ? 1 : isTarget || isRecommended || isOrigin ? 1 : 0.4
            }
            eventHandlers={{ click: () => onSelectInstitution(inst) }}
          >
            <Popup>
              <strong>{inst.name}</strong>
              <br />
              {inst.city}
              <br />
              <em>{inst.devices.length} přístrojů</em>
              {isRecommended && (
                <>
                  <br />
                  <span style={{ color: '#16a34a', fontWeight: 600 }}>
                    Doporučená zastávka
                  </span>
                </>
              )}
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
