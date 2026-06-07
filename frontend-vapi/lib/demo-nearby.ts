import { emitEvent } from "@/lib/events";
import type { SSEEvent } from "@/lib/types";

/** Demo default when geolocation / IP unavailable */
export const DEMO_LOCATION = {
  lat: 37.7749,
  lng: -122.4194,
};

export const DEMO_MEDICAL_PLACES = [
  {
    name: "Concentra Urgent Care",
    address: "342 Kearny St",
    phone: "(415) 362-8383",
    rating: 4.7,
    distance: "0.3 mi",
    open_now: true,
    maps_url: "https://maps.google.com",
  },
  {
    name: "Carbon Health",
    address: "590 California St",
    phone: "(415) 967-3461",
    rating: 4.8,
    distance: "0.4 mi",
    open_now: true,
    maps_url: "https://maps.google.com",
  },
  {
    name: "One Medical",
    address: "1 Embarcadero",
    phone: "(415) 288-1245",
    rating: 4.6,
    distance: "0.6 mi",
    open_now: true,
    maps_url: "https://maps.google.com",
  },
  {
    name: "UCSF Urgent Care",
    address: "400 Parnassus Ave",
    phone: "(415) 353-2000",
    rating: 4.5,
    distance: "1.8 mi",
    open_now: true,
    maps_url: "https://maps.google.com",
  },
  {
    name: "SF General ER",
    address: "995 Potrero Ave",
    phone: "(415) 206-8000",
    rating: 4.2,
    distance: "1.2 mi",
    open_now: true,
    maps_url: "https://maps.google.com",
  },
];

export const DEMO_LEGAL_PLACES = [
  {
    name: "Bay Area Injury Law",
    address: "555 Market St, San Francisco, CA",
    phone: "(415) 555-0101",
    rating: 4.9,
    distance: "0.5 mi",
    open_now: true,
    maps_url: "https://maps.google.com",
  },
  {
    name: "SF Personal Injury Group",
    address: "100 Pine St, San Francisco, CA",
    phone: "(415) 555-0102",
    rating: 4.8,
    distance: "0.7 mi",
    open_now: true,
    maps_url: "https://maps.google.com",
  },
  {
    name: "Golden Gate Legal",
    address: "50 California St, San Francisco, CA",
    phone: "(415) 555-0103",
    rating: 4.7,
    distance: "0.4 mi",
    open_now: true,
    maps_url: "https://maps.google.com",
  },
  {
    name: "Pacific Coast Attorneys",
    address: "201 Mission St, San Francisco, CA",
    phone: "(415) 555-0104",
    rating: 4.6,
    distance: "0.8 mi",
    open_now: true,
    maps_url: "https://maps.google.com",
  },
  {
    name: "Embarcadero Injury Lawyers",
    address: "1 Embarcadero Center, San Francisco, CA",
    phone: "(415) 555-0105",
    rating: 4.5,
    distance: "0.6 mi",
    open_now: true,
    maps_url: "https://maps.google.com",
  },
];

let medicalShown = false;
let legalShown = false;

export function markNearbyShown(type: "nearby_medical" | "nearby_legal"): void {
  if (type === "nearby_medical") medicalShown = true;
  if (type === "nearby_legal") legalShown = true;
}

export function resetNearbyDemoState(): void {
  medicalShown = false;
  legalShown = false;
}

/** Fire mock urgent-care cards 5s after call start if Apify hasn't delivered. */
export function scheduleDemoNearbyFallback(): void {
  setTimeout(() => {
    if (!medicalShown) {
      console.log("[DEMO] Emitting fallback nearby_medical");
      emitEvent({
        type: "nearby_medical",
        data: { places: DEMO_MEDICAL_PLACES, query: "urgent care open now" },
        timestamp: Date.now(),
      } satisfies SSEEvent);
      medicalShown = true;
    }
  }, 5000);
}

/** Fire mock attorney cards after legal_tool if Apify hasn't delivered. */
export function scheduleDemoLegalFallback(delayMs = 3000): void {
  setTimeout(() => {
    if (!legalShown) {
      console.log("[DEMO] Emitting fallback nearby_legal");
      emitEvent({
        type: "nearby_legal",
        data: {
          places: DEMO_LEGAL_PLACES,
          query: "personal injury attorney free consultation",
        },
        timestamp: Date.now(),
      } satisfies SSEEvent);
      legalShown = true;
    }
  }, delayMs);
}
