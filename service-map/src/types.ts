export interface Device {
  id: string;
  name: string;
  type: string;
  lastService: string;
}

export interface Institution {
  id: string;
  name: string;
  city: string;
  lat: number;
  lng: number;
  devices: Device[];
}

export interface RouteDestination {
  id: string;
  label: string;
  targetInstitution: string;
  route: [number, number][];
}

export interface RecommendedStop extends Institution {
  distanceFromRoute: number; // km
  reason: string;
}
