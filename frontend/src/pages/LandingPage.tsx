import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

const NAV = [
  { label: "Home", href: "#top" },
  { label: "Product", href: "#product" },
  { label: "Case Studies", href: "#cases" },
  { label: "Contact", href: "#contact" },
];

const STATS = [
  { symbol: "<", value: 120, suffix: "ms", label: "Inference Time" },
  { symbol: "%", value: 99.99, suffix: "%", label: "Platform Uptime", decimals: 2 },
  { symbol: "*", value: 24, suffix: "/7", label: "Autonomous Runtime" },
  { symbol: "#", value: 2.4, suffix: "M", label: "Context Windows", decimals: 1 },
];

function useCountUp(target: number, decimals = 0) {
  const ref = useRef<HTMLSpanElement>(null);
  const [display, setDisplay] = useState("0");

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setDisplay(target.toFixed(decimals));
      return;
    }
    let raf = 0;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting)) return;
        observer.disconnect();
        const start = performance.now();
        const duration = 1500;
        const tick = (now: number) => {
          const t = Math.min(1, (now - start) / duration);
          const eased = 1 - Math.pow(1 - t, 3);
          setDisplay((target * eased).toFixed(decimals));
          if (t < 1) raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
      },
      { threshold: 0.25 }
    );
    observer.observe(el);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [target, decimals]);

  return { ref, display };
}

function Stat({
  symbol,
  value,
  suffix,
  label,
  decimals = 0,
}: {
  symbol: string;
  value: number;
  suffix: string;
  label: string;
  decimals?: number;
}) {
  const { ref, display } = useCountUp(value, decimals);
  return (
    <div className="flex flex-col gap-1">
      <span ref={ref} className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
        <span className="mr-1.5 text-muted-foreground">{symbol}</span>
        {display}
        {suffix}
      </span>
      <span className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{label}</span>
    </div>
  );
}

function Logo({ size = 36 }: { size?: number }) {
  return (
    <span
      className="flex items-center justify-center rounded-full bg-white font-bold text-black shadow-md"
      style={{ width: size, height: size, fontSize: size * 0.4 }}
      aria-hidden="true"
    >
      Fx
    </span>
  );
}

export function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMenuOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  return (
    <main id="top" className="relative min-h-screen overflow-hidden bg-black text-white">
      {/* Background Video */}
      <video
        className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-60"
        autoPlay
        muted
        loop
        playsInline
        aria-hidden="true"
      >
        <source
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260809_012548_ef22562c-c0ae-4816-ad9d-f8922af4e6a7.mp4"
          type="video/mp4"
        />
      </video>
      <div
        className="absolute inset-0 bg-black/60"
        aria-hidden="true"
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.40) 45%, rgba(0,0,0,0.90) 100%)",
        }}
      />

      <div className="relative z-10 flex min-h-screen flex-col px-5 py-6 sm:px-8 max-w-7xl mx-auto">
        {/* Header */}
        <header className="fx-slide-down flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Logo />
            <span className="text-sm font-semibold tracking-tight text-white">FinExplain</span>
          </div>

          <nav
            className="hidden items-center gap-1 rounded-full bg-white px-2.5 py-1.5 md:flex shadow-lg"
            aria-label="Primary Navigation"
          >
            {NAV.map((item, idx) => (
              <a
                key={item.label}
                href={item.href}
                className={`rounded-full px-4 py-1.5 text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  idx === 0
                    ? "text-black hover:bg-black/5"
                    : "text-black/70 hover:text-black hover:bg-black/5"
                }`}
              >
                {idx === 0 && <span className="inline-flex gap-0.5"><span className="h-1 w-1 rounded-full bg-black"></span><span className="h-1 w-1 rounded-full bg-black"></span><span className="h-1 w-1 rounded-full bg-black"></span></span>}
                {item.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <Link
              to="/app"
              className="hidden rounded-full bg-pill-dark px-5 py-2 text-xs font-semibold text-white border border-white/15 transition-all hover:bg-surface-3 hover:border-white/30 md:inline-flex"
            >
              Sign in
            </Link>
            <button
              type="button"
              aria-label="Open menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(true)}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-pill-dark text-white border border-white/15 md:hidden"
            >
              <i className="fa-solid fa-bars text-sm" aria-hidden="true" />
            </button>
          </div>
        </header>

        {/* Hero */}
        <div className="flex flex-1 flex-col items-center justify-center py-16 text-center">
          <h1 className="fx-headline max-w-4xl text-display text-4xl leading-[1.05] text-white sm:text-6xl lg:text-7xl">
            Intelligence Designed To Evolve
          </h1>
          <p className="fx-reveal fx-delay-2 mt-6 max-w-xl text-sm text-muted-foreground sm:text-base leading-relaxed">
            Build applications that reason, adapt and collaborate using a modular AI platform
            designed for production.
          </p>
          <Link
            to="/app"
            className="fx-reveal fx-delay-3 mt-9 inline-flex items-center gap-2.5 rounded-full bg-white px-8 py-3.5 text-sm font-bold text-black transition-transform duration-300 hover:-translate-y-0.5 hover:scale-[1.02] shadow-[0_0_40px_-8px_rgba(255,255,255,0.45)]"
          >
            <span>Get Started</span>
            <i className="fa-solid fa-arrow-right text-xs" aria-hidden="true" />
          </Link>

          {/* Trust row */}
          <div id="product" className="fx-reveal fx-delay-4 mt-14 flex items-center gap-4">
            <div className="flex -space-x-2.5">
              {[
                { icon: "fa-brands fa-microsoft", label: "Microsoft" },
                { icon: "fa-brands fa-amazon", label: "Amazon" },
                { icon: "fa-brands fa-google", label: "Google" }
              ].map((brand) => (
                <span
                  key={brand.label}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-pill-dark border border-white/20 shadow-md"
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-black">
                    <i className={`${brand.icon} text-[10px]`} aria-hidden="true" />
                  </span>
                </span>
              ))}
            </div>
            <span className="text-xs text-muted-foreground font-medium sm:text-sm">
              Trusted by 2000+ Enterprises
            </span>
          </div>
        </div>

        {/* Stats Section */}
        <section
          id="cases"
          className="fx-reveal grid grid-cols-2 gap-8 border-t border-white/10 pt-8 lg:grid-cols-4"
          aria-label="Platform metrics"
        >
          {STATS.map((s) => (
            <Stat key={s.label} {...s} />
          ))}
        </section>

        {/* Footer */}
        <footer
          id="contact"
          className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-5 pb-4 text-xs text-muted-foreground"
        >
          <span>© {new Date().getFullYear()} FinExplain — Evidence-first financial intelligence</span>
          <a href="mailto:contact@finexplain.ai" className="hover:text-white transition-colors">
            contact@finexplain.ai
          </a>
        </footer>
      </div>

      {/* Mobile menu sheet */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
            className="absolute inset-0 bg-black/70 backdrop-blur-md"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Menu"
            className="absolute inset-x-4 top-4 rounded-3xl bg-white p-6 text-black shadow-2xl"
          >
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Logo size={28} />
                <span className="text-sm font-bold text-black">FinExplain</span>
              </div>
              <button
                type="button"
                aria-label="Close menu"
                onClick={() => setMenuOpen(false)}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-black text-white"
              >
                <i className="fa-solid fa-xmark text-xs" aria-hidden="true" />
              </button>
            </div>
            <nav className="flex flex-col divide-y divide-black/10" aria-label="Mobile Navigation">
              {NAV.map((item) => (
                <a
                  key={item.label}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  className="py-3 text-sm font-medium text-black/80 hover:text-black"
                >
                  {item.label}
                </a>
              ))}
            </nav>
            <Link
              to="/app"
              onClick={() => setMenuOpen(false)}
              className="mt-5 flex items-center justify-center rounded-full bg-black px-5 py-3 text-sm font-semibold text-white"
            >
              Sign in to Console
            </Link>
          </div>
        </div>
      )}
    </main>
  );
}
