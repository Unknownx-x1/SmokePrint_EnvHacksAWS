import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'Smokeprint | Delhi-NCR Air Inspection Decision System',
  description: 'Deterministic atmospheric plume attribution and inspection dispatch prototype for Delhi-NCR inspection officers and field teams.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-[#fbfbfc] text-stone-900 selection:bg-stone-200">
        <header className="border-b border-stone-200 bg-white sticky top-0 z-50 w-full overflow-hidden">
          <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-2 sm:py-0 sm:h-14 flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-4">
            <div className="flex items-center justify-between sm:justify-start gap-4">
              <Link href="/" className="flex items-center gap-2 group">
                <span className="font-mono font-bold text-sm tracking-wider uppercase bg-stone-900 text-white px-2 py-0.5 rounded">
                  SMOKEPRINT
                </span>
                <span className="text-xs text-stone-500 hidden md:inline">
                  Air Inspection Decision System
                </span>
              </Link>

              <div className="flex sm:hidden items-center gap-1.5 text-[10px] font-mono text-stone-600 bg-stone-50 border border-stone-200 px-1.5 py-0.5 rounded">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>SYSTEM ACTIVE</span>
              </div>
            </div>

            <nav className="flex items-center gap-1 overflow-x-auto text-xs font-medium whitespace-nowrap py-0.5 scrollbar-none">
              <Link
                href="/"
                className="px-2 py-1 rounded text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
              >
                Landing
              </Link>
              <Link
                href="/officer"
                className="px-2 py-1 rounded text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
              >
                Officer Desk
              </Link>
              <Link
                href="/field/case_anand_vihar_20251102"
                className="px-2 py-1 rounded text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
              >
                Field Mobile
              </Link>
              <Link
                href="/evidence"
                className="px-2 py-1 rounded text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
              >
                Evidence
              </Link>
              <Link
                href="/architecture"
                className="px-2 py-1 rounded text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
              >
                Architecture
              </Link>
            </nav>

            <div className="hidden sm:flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-[11px] font-mono text-stone-600 bg-stone-50 border border-stone-200 px-2 py-0.5 rounded">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>Demo build</span>
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
              Smokeprint · Built for air quality inspection officers and field teams. OpenFreeMap / OSM tiles.
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
