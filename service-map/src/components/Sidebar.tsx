import type { RouteDestination, RecommendedStop, Institution } from '../types';

interface Props {
  destinations: RouteDestination[];
  selectedRoute: RouteDestination | null;
  onSelectRoute: (dest: RouteDestination | null) => void;
  recommendations: RecommendedStop[];
  onSelectInstitution: (inst: Institution) => void;
  selectedInstitution: Institution | null;
}

export default function Sidebar({
  destinations,
  selectedRoute,
  onSelectRoute,
  recommendations,
  onSelectInstitution,
}: Props) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>Servisní mapa ČR</h1>
        <p className="sidebar-subtitle">Interní nástroj pro servisní techniky</p>
      </div>

      <div className="sidebar-section">
        <label className="section-label">Výchozí bod</label>
        <div className="origin-box">
          <span className="origin-dot" />
          Praha — FN Motol
        </div>
      </div>

      <div className="sidebar-section">
        <label className="section-label">Servisní cíl</label>
        <select
          className="route-select"
          value={selectedRoute?.id ?? ''}
          onChange={(e) => {
            const dest = destinations.find((d) => d.id === e.target.value) ?? null;
            onSelectRoute(dest);
          }}
        >
          <option value="">— Vyberte cíl —</option>
          {destinations.map((d) => (
            <option key={d.id} value={d.id}>
              {d.label}
            </option>
          ))}
        </select>
      </div>

      {selectedRoute && (
        <div className="sidebar-section">
          <label className="section-label">
            Doporučené zastávky ({recommendations.length})
          </label>
          {recommendations.length === 0 ? (
            <p className="empty-text">Žádné instituce v blízkosti trasy.</p>
          ) : (
            <ul className="recommendation-list">
              {recommendations.map((rec) => (
                <li
                  key={rec.id}
                  className="recommendation-item"
                  onClick={() => onSelectInstitution(rec)}
                >
                  <div className="rec-name">{rec.name}</div>
                  <div className="rec-meta">
                    <span>{rec.city}</span>
                    <span className="rec-distance">{rec.reason}</span>
                  </div>
                  <div className="rec-devices">
                    {rec.devices.map((d) => (
                      <span key={d.id} className="device-tag">{d.type}</span>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
