import React from 'react';
import Link from 'next/link';
import { AlertTriangle, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="flex-1 bg-stone-100 min-h-[500px] p-8 flex flex-col items-center justify-center text-center">
      <div className="bg-white border border-stone-300 rounded-xl p-8 max-w-md w-full shadow-sm flex flex-col items-center">
        <AlertTriangle className="w-12 h-12 text-stone-600 mb-3" />
        <h1 className="text-xl font-bold text-stone-900">Case Not Found</h1>
        <p className="text-xs text-stone-600 mt-2 leading-relaxed">
          The requested inspection case or URL could not be found in the Smokeprint active catalog.
        </p>
        <div className="mt-6 flex flex-col sm:flex-row gap-3 w-full">
          <Link
            href="/officer"
            className="flex-1 px-4 py-2.5 bg-stone-900 hover:bg-stone-800 text-white rounded text-xs font-semibold text-center transition-colors min-h-[44px] flex items-center justify-center"
          >
            Officer Desk
          </Link>
          <Link
            href="/field/case_anand_vihar_20251102"
            className="flex-1 px-4 py-2.5 bg-stone-100 hover:bg-stone-200 text-stone-800 rounded border border-stone-300 text-xs font-semibold text-center transition-colors min-h-[44px] flex items-center justify-center"
          >
            Field Mobile
          </Link>
        </div>
      </div>
    </div>
  );
}
