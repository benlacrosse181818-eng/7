import type { Institution, RecommendedStop } from '../types';

/**
 * Haversine distance between two points in km.
 */
function haversineKm(
  lat1: number, lng1: number,
  lat2: number, lng2: number
): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Minimum distance from a point to any segment of the route polyline.
 * Simplified: checks distance to each route point (not true point-to-segment).
 */
function minDistanceToRoute(
  lat: number, lng: number,
  route: [number, number][]
): number {
  let min = Infinity;
  for (const [rLat, rLng] of route) {
    const d = haversineKm(lat, lng, rLat, rLng);
    if (d < min) min = d;
  }
  return min;
}

/**
 * Recommend institutions near the route.
 * - Excludes the origin (Praha / fn-motol) and the target institution.
 * - Threshold: 30 km from any route point.
 * - Sorts by distance ascending.
 */
export function getRecommendations(
  institutions: Institution[],
  route: [number, number][],
  targetId: string,
  originId: string = 'fn-motol',
  thresholdKm: number = 30
): RecommendedStop[] {
  const results: RecommendedStop[] = [];

  for (const inst of institutions) {
    if (inst.id === targetId || inst.id === originId) continue;

    const dist = minDistanceToRoute(inst.lat, inst.lng, route);
    if (dist <= thresholdKm) {
      let reason = `${Math.round(dist)} km od trasy`;
      if (inst.devices.length >= 3) {
        reason += `, ${inst.devices.length} přístrojů`;
      }
      results.push({ ...inst, distanceFromRoute: dist, reason });
    }
  }

  results.sort((a, b) => a.distanceFromRoute - b.distanceFromRoute);
  return results;
}
