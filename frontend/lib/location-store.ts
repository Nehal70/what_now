import type { UserLocation } from "./types";

const TTL_MS = 30 * 60 * 1000;

type StoredLocation = UserLocation & { updatedAt: number };

const store = new Map<string, StoredLocation>();

export function setUserLocation(userId: string, location: UserLocation): void {
  store.set(userId, { ...location, updatedAt: Date.now() });
}

export function clearUserLocation(userId: string): void {
  store.delete(userId);
}

export function getUserLocation(userId: string): UserLocation | null {
  const entry = store.get(userId);
  if (!entry) {
    return null;
  }

  if (Date.now() - entry.updatedAt > TTL_MS) {
    store.delete(userId);
    return null;
  }

  return { lat: entry.lat, lng: entry.lng };
}
