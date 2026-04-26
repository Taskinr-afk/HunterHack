import { useEffect, useRef, useState } from "react";
import type { UserLocation } from "../types";

export function useUserLocation() {
  const [location, setLocation] = useState<UserLocation | null>(null);
  const [status, setStatus] = useState<"idle" | "locating" | "ready" | "denied" | "unsupported">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const startedRef = useRef(false);

  const requestLocation = () => {
    if (!navigator.geolocation) { setStatus("unsupported"); return; }
    setStatus("locating"); setErrorMessage(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => { setLocation({ latitude: pos.coords.latitude, longitude: pos.coords.longitude, label: "Your current location" }); setStatus("ready"); },
      (err) => { setStatus("denied"); setErrorMessage(err.message || "Location permission was denied."); },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
    );
  };

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    requestLocation();
  }, []);

  return { location, status, errorMessage, requestLocation };
}
