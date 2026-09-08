import { useState } from 'react';

type Coordinates = {
  latitude: number;
  longitude: number;
};

type RouteResponse = {
  status: string;
  start: Coordinates;
  destination: Coordinates;
};

export default function Home() {
  const [startLat, setStartLat] = useState('');
  const [startLon, setStartLon] = useState('');
  const [destinationLat, setDestinationLat] = useState('');
  const [destinationLon, setDestinationLon] = useState('');

  const [response, setResponse] = useState<RouteResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleFindRoute() {
    setError('');
    setResponse(null);

    const startLatitude = Number(startLat);
    const startLongitude = Number(startLon);
    const destinationLatitude = Number(destinationLat);
    const destinationLongitude = Number(destinationLon);

    if (
      !Number.isFinite(startLatitude) ||
      !Number.isFinite(startLongitude) ||
      !Number.isFinite(destinationLatitude) ||
      !Number.isFinite(destinationLongitude)
    ) {
      setError('Please enter valid latitude and longitude values.');
      return;
    }

    setLoading(true);

    try {
      const result = await fetch('/api/routes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          start: {
            latitude: startLatitude,
            longitude: startLongitude,
          },
          destination: {
            latitude: destinationLatitude,
            longitude: destinationLongitude,
          },
        }),
      });

      if (!result.ok) {
        throw new Error(`Request failed with status ${result.status}`);
      }

      const data: RouteResponse = await result.json();
      setResponse(data);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to connect to the backend.',
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-[100dvh] bg-background px-5 py-10 text-foreground sm:px-8">
      <div className="mx-auto max-w-4xl">
        <header className="border-b border-border pb-6">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
            Smart India Hackathon
          </p>

          <h1 className="mt-4 text-4xl font-bold sm:text-5xl">
            Safe Pedestrian Route
          </h1>

          <p className="mt-4 max-w-2xl text-muted-foreground">
            Phase 1 — connect the frontend to the backend route API.
          </p>
        </header>

        <section className="mt-10 rounded-2xl border border-border bg-card p-6 shadow-sm">
          <h2 className="text-xl font-bold">Test a route request</h2>

          <p className="mt-2 text-sm text-muted-foreground">
            Enter real latitude and longitude coordinates. Mapbox routing will
            be added in Phase 2.
          </p>

          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <div>
              <h3 className="font-semibold">Start</h3>

              <div className="mt-3 grid gap-3">
                <input
                  type="number"
                  step="any"
                  placeholder="Latitude"
                  value={startLat}
                  onChange={(event) => setStartLat(event.target.value)}
                  className="rounded-lg border border-border bg-background px-4 py-3 outline-none focus:ring-2 focus:ring-ring"
                />

                <input
                  type="number"
                  step="any"
                  placeholder="Longitude"
                  value={startLon}
                  onChange={(event) => setStartLon(event.target.value)}
                  className="rounded-lg border border-border bg-background px-4 py-3 outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>

            <div>
              <h3 className="font-semibold">Destination</h3>

              <div className="mt-3 grid gap-3">
                <input
                  type="number"
                  step="any"
                  placeholder="Latitude"
                  value={destinationLat}
                  onChange={(event) => setDestinationLat(event.target.value)}
                  className="rounded-lg border border-border bg-background px-4 py-3 outline-none focus:ring-2 focus:ring-ring"
                />

                <input
                  type="number"
                  step="any"
                  placeholder="Longitude"
                  value={destinationLon}
                  onChange={(event) =>
                    setDestinationLon(event.target.value)
                  }
                  className="rounded-lg border border-border bg-background px-4 py-3 outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={handleFindRoute}
            disabled={loading}
            className="mt-6 rounded-lg bg-primary px-5 py-3 font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? 'Sending request...' : 'Find Route'}
          </button>

          {error && (
            <div className="mt-6 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {error}
            </div>
          )}

          {response && (
            <div className="mt-6 rounded-lg border border-border bg-muted/40 p-5">
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Backend response
              </p>

              <p className="mt-2 text-lg font-semibold">
                {response.status}
              </p>

              <div className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <p className="font-semibold">Start</p>
                  <p className="mt-1 text-muted-foreground">
                    {response.start.latitude},{' '}
                    {response.start.longitude}
                  </p>
                </div>

                <div>
                  <p className="font-semibold">Destination</p>
                  <p className="mt-1 text-muted-foreground">
                    {response.destination.latitude},{' '}
                    {response.destination.longitude}
                  </p>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}