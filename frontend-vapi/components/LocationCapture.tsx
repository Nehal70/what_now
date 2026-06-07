"use client";

import { useEffect, useRef } from "react";

export default function LocationCapture() {
  const postedRef = useRef(false);

  useEffect(() => {
    if (postedRef.current || typeof navigator === "undefined") {
      return;
    }

    if (!navigator.geolocation) {
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        postedRef.current = true;
        void fetch("/api/location", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
          }),
        });
      },
      () => {
        postedRef.current = true;
        void fetch("/api/location", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lat: null, lng: null }),
        });
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
    );
  }, []);

  return null;
}
