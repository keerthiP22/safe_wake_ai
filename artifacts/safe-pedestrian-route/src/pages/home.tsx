import { useHealthCheck, getHealthCheckQueryKey } from '@workspace/api-client-react';
import { ArrowDown, ArrowUpRight, Check, CircleAlert, Compass, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react';

function BrandMark() {
  return (
    <div className="flex items-center gap-3" data-testid="brand-mark">
      <div className="relative flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
        <span className="absolute h-4 w-4 rounded-full border-2 border-primary-foreground/80" />
        <span className="absolute h-1.5 w-1.5 rounded-full bg-accent" />
        <span className="absolute bottom-1.5 h-1 w-5 rounded-full bg-secondary" />
      </div>
      <div>
        <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-muted-foreground">SIH foundation</p>
        <p className="display-face text-[17px] font-bold leading-none text-foreground">Nagar / Path</p>
      </div>
    </div>
  );
}

function ConnectionStatus() {
  const health = useHealthCheck({
    query: {
      queryKey: getHealthCheckQueryKey(),
      retry: 1,
      refetchOnWindowFocus: false,
    },
  });

  const isLoading = health.isLoading;
  const isError = health.isError;
  const isSuccess = health.isSuccess;
  const statusLabel = health.data?.status ?? 'No status returned';

  return (
    <section
      id="connection"
      className="relative overflow-hidden rounded-[1.75rem] border border-primary/15 bg-card p-6 shadow-[0_20px_50px_-30px_hsl(221_35%_16%_/_0.45)] sm:p-8"
      aria-labelledby="connection-title"
    >
      <div className="absolute right-6 top-6 h-20 w-20 rounded-full bg-accent/20 blur-2xl" aria-hidden="true" />
      <div className="relative">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="mono-face text-[10px] font-bold uppercase text-muted-foreground">01 / foundation check</p>
            <h2 id="connection-title" className="mt-3 display-face text-2xl font-bold text-foreground">
              Backend connection
            </h2>
          </div>
          <div className="rounded-xl border border-border bg-muted/55 p-2.5 text-secondary-foreground">
            <ShieldCheck size={19} strokeWidth={1.8} />
          </div>
        </div>

        <div
          className="mt-8 min-h-[116px] rounded-2xl border border-border bg-background/65 p-4"
          aria-live="polite"
          data-testid="status-backend-connection"
        >
          {isLoading && (
            <div className="space-y-3" data-testid="status-loading">
              <div className="h-3 w-24 animate-pulse rounded-full bg-muted" />
              <div className="h-7 w-44 animate-pulse rounded-lg bg-muted" />
              <div className="h-3 w-56 max-w-full animate-pulse rounded-full bg-muted" />
            </div>
          )}

          {isSuccess && (
            <div className="flex items-start gap-3" data-testid="status-success">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                <Check size={16} strokeWidth={2.5} />
              </span>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-secondary-foreground">Connected</p>
                <p className="mt-1 text-xl font-semibold text-foreground">{statusLabel}</p>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">The foundation service is answering.</p>
              </div>
            </div>
          )}

          {isError && (
            <div className="flex items-start gap-3" data-testid="status-error">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-destructive/10 text-destructive">
                <CircleAlert size={17} strokeWidth={2} />
              </span>
              <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-destructive">Not connected</p>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                  The service did not respond. That is okay for now — try the check again when your API is running.
                </p>
                <button
                  type="button"
                  onClick={() => health.refetch()}
                  className="mt-3 inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-xs font-bold text-foreground transition-transform hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  data-testid="button-retry-health-check"
                >
                  <RefreshCw size={13} />
                  Retry check
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="mt-5 flex items-center justify-between gap-4 border-t border-border pt-4">
          <p className="text-xs leading-relaxed text-muted-foreground">Live routing is intentionally not enabled.</p>
           <span className="mono-face shrink-0 text-[10px] text-muted-foreground">GET /api/health</span>
        </div>
      </div>
    </section>
  );
}

function RouteSignalIllustration() {
  return (
    <div className="route-board relative min-h-[350px] overflow-hidden rounded-[1.75rem] p-5 text-background-foreground sm:min-h-[430px] sm:p-7" aria-label="Abstract pedestrian route signal illustration">
      <div className="relative z-10 flex items-center justify-between">
        <span className="mono-face rounded-full border border-background/20 px-3 py-1.5 text-[10px] uppercase text-background/75">signal / 001</span>
        <span className="flex items-center gap-2 text-xs text-background/65"><span className="h-2 w-2 animate-pulse-soft rounded-full bg-accent" /> preparing</span>
      </div>

      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 520 460" fill="none" aria-hidden="true">
        <path d="M72 418C133 383 116 331 182 307C248 283 267 335 309 295C354 252 319 203 371 174C413 151 435 121 446 43" stroke="hsl(42 89% 63% / .95)" strokeWidth="3" strokeLinecap="round" className="route-line" />
        <path d="M25 102C92 117 110 171 164 159C214 148 241 85 292 91C339 97 353 143 414 132C457 124 478 101 511 86" stroke="hsl(164 37% 60% / .55)" strokeWidth="2" strokeLinecap="round" />
        <path d="M38 369C97 331 91 263 145 228C197 194 225 224 248 177C275 124 263 74 315 48" stroke="hsl(42 38% 95% / .16)" strokeWidth="1" strokeLinecap="round" />
        <circle cx="72" cy="418" r="8" fill="hsl(42 89% 63%)" />
        <circle cx="446" cy="43" r="8" fill="hsl(164 37% 60%)" />
        <circle cx="309" cy="295" r="5" fill="hsl(42 38% 95%)" />
      </svg>

      <div className="absolute bottom-6 left-5 right-5 z-10 flex items-end justify-between sm:left-7 sm:right-7">
        <div>
          <p className="display-face max-w-[17rem] text-3xl font-bold leading-[0.98] text-background">Make every step count.</p>
          <p className="mt-3 max-w-[18rem] text-sm leading-relaxed text-background/65">A considered beginning for safer urban walking.</p>
        </div>
        <div className="animate-drift hidden h-16 w-16 items-center justify-center rounded-full border border-background/20 bg-background/10 backdrop-blur sm:flex">
          <Compass size={26} strokeWidth={1.3} className="text-accent" />
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <main className="page-shell relative min-h-[100dvh] overflow-hidden">
      <div className="page-grid pointer-events-none absolute inset-x-0 top-0 h-[720px]" aria-hidden="true" />
      <div className="relative mx-auto max-w-7xl px-5 pb-12 sm:px-8 lg:px-12">
        <header className="flex items-center justify-between border-b border-border/70 py-5 sm:py-6">
          <BrandMark />
          <div className="hidden items-center gap-5 sm:flex">
            <span className="mono-face text-[10px] uppercase text-muted-foreground">smart india hackathon</span>
            <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden="true" />
            <span className="text-xs font-semibold text-muted-foreground">Phase 01 / groundwork</span>
          </div>
          <span className="mono-face text-[10px] uppercase text-muted-foreground sm:hidden">phase 01</span>
        </header>

        <div className="grid gap-10 pb-20 pt-12 sm:pt-16 lg:grid-cols-[minmax(0,1.04fr)_minmax(360px,0.96fr)] lg:items-end lg:gap-16 lg:pb-28 lg:pt-24">
          <section className="animate-rise" aria-labelledby="hero-title">
            <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-3 py-1.5 text-xs font-bold text-secondary-foreground shadow-sm">
              <Sparkles size={14} strokeWidth={1.8} />
              An open foundation for safer streets
            </div>
            <h1 id="hero-title" className="display-face mt-7 max-w-3xl text-[clamp(3.35rem,7vw,6.8rem)] font-bold leading-[0.91] text-foreground">
              Walking should feel like a choice, not a calculation.
            </h1>
            <p className="mt-7 max-w-xl text-base leading-8 text-muted-foreground sm:text-lg">
              We are starting with the right question: how might urban pedestrians feel more confident moving through their city? This is the groundwork before the intelligence.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-4">
              <a
                href="#connection"
                className="group inline-flex items-center gap-3 rounded-xl bg-primary px-5 py-3.5 text-sm font-bold text-primary-foreground shadow-[0_14px_25px_-17px_hsl(221_35%_16%_/_0.7)] transition-transform hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                data-testid="link-check-connection"
              >
                Check the foundation
                <ArrowDown size={16} className="transition-transform group-hover:translate-y-0.5" />
              </a>
              <span className="max-w-[190px] text-xs leading-relaxed text-muted-foreground">No routes to plan yet. Just a healthy first step.</span>
            </div>
          </section>

          <div className="animate-rise stagger-2">
            <RouteSignalIllustration />
          </div>
        </div>

        <div className="grid gap-10 border-t border-border/80 pt-10 lg:grid-cols-[0.76fr_1.24fr] lg:gap-16 lg:pt-14">
          <div className="animate-rise stagger-1">
            <p className="mono-face text-[10px] font-bold uppercase text-muted-foreground">A clear starting line</p>
            <h2 className="display-face mt-4 max-w-sm text-3xl font-bold leading-tight text-foreground sm:text-4xl">Build the trust layer first.</h2>
            <p className="mt-4 max-w-sm text-sm leading-7 text-muted-foreground">
              Before maps, models, or recommendations, a civic tool needs to be dependable, legible, and honest about what it can do.
            </p>
            <a href="#principles" className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-secondary-foreground underline decoration-secondary-foreground/35 underline-offset-4 transition-colors hover:text-foreground" data-testid="link-foundation-principles">
              See the principles <ArrowUpRight size={15} />
            </a>
          </div>

          <div id="principles" className="grid gap-3 sm:grid-cols-[1.1fr_0.9fr]">
            <article className="animate-rise stagger-2 rounded-2xl border border-border bg-card/75 p-6 shadow-sm sm:p-7">
              <span className="mono-face text-[10px] text-secondary-foreground">01 — clarity</span>
              <h3 className="mt-8 text-xl font-bold text-foreground">Explain the why.</h3>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">A future recommendation should feel understandable, not mysterious. People deserve to know what makes a path feel safer.</p>
            </article>
            <article className="animate-rise stagger-3 rounded-2xl border border-border bg-secondary/45 p-6 sm:mt-10 sm:p-7">
              <span className="mono-face text-[10px] text-secondary-foreground">02 — care</span>
              <h3 className="mt-8 text-xl font-bold text-foreground">Design for the walk.</h3>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">Every decision starts with the lived experience of the person on the street.</p>
            </article>
          </div>
        </div>

        <div className="mt-14 grid gap-8 border-t border-border/80 pt-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          <div className="flex gap-4">
            <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-foreground">
              <ShieldCheck size={20} strokeWidth={1.8} />
            </div>
            <div>
              <p className="text-sm font-bold text-foreground">A foundation, not a finished promise.</p>
              <p className="mt-1 max-w-xl text-sm leading-7 text-muted-foreground">The next phase will explore the data and methods needed to make pedestrian safety more visible. Today, we are making sure the ground beneath it is steady.</p>
            </div>
          </div>
          <div className="lg:justify-self-end">
            <ConnectionStatus />
          </div>
        </div>

        <footer className="mt-16 flex flex-col gap-3 border-t border-border/70 pt-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>AI-Based Safe Pedestrian Route Recommendation for Urban Cities</p>
          <p className="mono-face text-[10px] uppercase">Prepared for the next phase</p>
        </footer>
      </div>
    </main>
  );
}