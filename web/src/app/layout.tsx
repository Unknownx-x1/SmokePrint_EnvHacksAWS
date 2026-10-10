import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'Smokeprint | Delhi-NCR Air Inspection Decision System',
  description: 'Deterministic atmospheric plume attribution and inspection dispatch for Delhi-NCR regulatory officers and field inspectors.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-[#fbfbfc] text-stone-900 selection:bg-stone-200">
        <header className="border-b border-stone-200 bg-white sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
            <div className="flex items-center gap-6">
              <Link href="/" className="flex items-center gap-2 group">
                <span className="font-mono font-bold text-sm tracking-wider uppercase bg-stone-900 text-white px-2 py-0.5 rounded">
                  SMOKEPRINT
                </span>
                <span className="text-xs text-stone-500 hidden md:inline">
                  Air Inspection Decision System
                </span>
              </Link>

              <nav className="flex items-center gap-1 sm:gap-2 text-xs font-medium">
                <Link
                  href="/"
                  className="px-2.5 py-1.5 rounded text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
                >
                  Landing
                </Link>
                <Link
                  href="/officer"
                  className="px-2.5 py-1.5 rounded text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
                >
                  Officer Desk
                </Link>
                <Link
                  href="/field/case_anand_vihar_20251102"
                  className="px-2.5 py-1.5 rounded text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
                >
                  Field Mobile
                </Link>
                <Link
                  href="/evidence"
                  className="px-2.5 py-1.5 rounded text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
                >
                  Evidence & Backtest
                </Link>
                <Link
                  href="/architecture"
                  className="px-2.5 py-1.5 rounded text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
                >
                  Architecture
                </Link>
              </nav>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-[11px] font-mono text-stone-500 bg-stone-50 border border-stone-200 px-2 py-0.5 rounded">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>FROZEN CORE v2.7</span>
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 flex flex-col">
          {children}
        </main>

        <footer className="border-t border-stone-200 bg-white py-4 text-xs text-stone-500">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
            <div>
              Smokeprint · Built for regulatory inspection officers and field teams. OpenFreeMap / OSM tiles.
            </div>
            <div className="font-mono text-[11px] text-stone-400">
              Replayed from validated core output · Never claims a single culprit
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
