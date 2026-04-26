import { useEffect, useRef, useState } from "react";
import type { UserLocation } from "../types";

export function useUserLocation() {
  const [location, setLocation] = useState<UserLocation | null>(null);
  const [status, setStatus] = useState<"idle" | "locating" | "ready" | "denied" | "unsupported">(
    "idle",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const startedRef = useRef(false);

  const requestLocation = () => {
    if (!navigator.geolocation) {
      setStatus("unsupported");
      setErrorMessage("Geolocation is not supported in this browser.");
      return;
    }

    setStatus("locating");
    setErrorMessage(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          label: "Your current location",
        });
        setStatus("ready");
      },
      (error) => {
        setStatus("denied");
        setErrorMessage(error.message || "Location permission was denied.");
      },
      {
        enableHighAccuracy: true,
        timeout: 8000,
        maximumAge: 60000,
      },
    );
  };

  useEffect(() => {
    if (startedRef.current) {
      return;
    }

    startedRef.current = true;
    requestLocation();
  }, []);

  return {
    location,
    status,
    errorMessage,
    requestLocation,
  };
}
