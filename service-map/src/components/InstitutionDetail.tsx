import type { Institution } from '../types';

interface Props {
  institution: Institution;
  onClose: () => void;
  isRecommended?: boolean;
}

export default function InstitutionDetail({ institution, onClose, isRecommended }: Props) {
  return (
    <div className="detail-panel">
      <div className="detail-header">
        <h3>{institution.name}</h3>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>
      <p className="detail-city">{institution.city}</p>
      {isRecommended && (
        <span className="badge badge-recommended">Doporučená zastávka</span>
      )}
      <h4>Přístroje ({institution.devices.length})</h4>
      <ul className="device-list">
        {institution.devices.map((d) => (
          <li key={d.id} className="device-item">
            <div className="device-name">{d.name}</div>
            <div className="device-meta">
              <span className="device-type">{d.type}</span>
              <span className="device-service">
                Poslední servis: {new Date(d.lastService).toLocaleDateString('cs-CZ')}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
