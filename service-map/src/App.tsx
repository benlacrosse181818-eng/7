import { useState, useMemo } from 'react';
import MapView from './components/MapView';
import Sidebar from './components/Sidebar';
import InstitutionDetail from './components/InstitutionDetail';
import { getRecommendations } from './utils/recommend';

import institutionsData from './data/institutions.json';
import routesData from './data/routes.json';

import type { Institution, RouteDestination, RecommendedStop } from './types';

import 'leaflet/dist/leaflet.css';
import './App.css';

const institutions: Institution[] = institutionsData as Institution[];
const destinations: RouteDestination[] = routesData.destinations as RouteDestination[];

export default function App() {
  const [selectedRoute, setSelectedRoute] = useState<RouteDestination | null>(null);
  const [selectedInstitution, setSelectedInstitution] = useState<Institution | null>(null);

  const recommendations: RecommendedStop[] = useMemo(() => {
    if (!selectedRoute) return [];
    return getRecommendations(
      institutions,
      selectedRoute.route,
      selectedRoute.targetInstitution
    );
  }, [selectedRoute]);

  return (
    <div className="app-layout">
      <Sidebar
        destinations={destinations}
        selectedRoute={selectedRoute}
        onSelectRoute={(dest) => {
          setSelectedRoute(dest);
          setSelectedInstitution(null);
        }}
        recommendations={recommendations}
        onSelectInstitution={setSelectedInstitution}
        selectedInstitution={selectedInstitution}
      />

      <div className="map-wrapper">
        <MapView
          institutions={institutions}
          selectedRoute={selectedRoute}
          recommendations={recommendations}
          onSelectInstitution={setSelectedInstitution}
        />

        {selectedInstitution && (
          <InstitutionDetail
            institution={selectedInstitution}
            onClose={() => setSelectedInstitution(null)}
            isRecommended={recommendations.some((r) => r.id === selectedInstitution.id)}
          />
        )}
      </div>
    </div>
  );
}
