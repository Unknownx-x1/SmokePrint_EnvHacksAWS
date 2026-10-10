import React from 'react';
import Link from 'next/link';
import {
  Layers,
  Server,
  Database,
  Cpu,
  Workflow,
  ShieldCheck,
  FileText,
  Cloud,
  CheckCircle2,
  HardDrive
} from 'lucide-react';

export default function ArchitecturePage() {
  return (
    <div className="flex-1 max-w-5xl mx-auto w-full px-4 py-8 sm:py-12 space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-stone-100 text-stone-700 border border-stone-200 mb-3">
          <Layers className="w-3.5 h-3.5 text-stone-700" />
          <span>SYSTEM ARCHITECTURE & INFRASTRUCTURE TOPOLOGY</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-stone-900 tracking-tight">
          System Architecture: What Runs Where
        </h1>
        <p className="mt-2 text-sm text-stone-600 max-w-3xl">
          Clean separation of concerns: frozen deterministic physics running locally and in replayed artifacts, lightweight serverless orchestration on AWS Free Tier, and local Strands agents with strict validation barriers.
        </p>
      </div>

      {/* Visual System Architecture Diagram */}
      <div className="bg-white rounded-lg border border-stone-200 shadow-sm p-6 space-y-6">
        <h2 className="text-base font-bold text-stone-900">
          Component Topology Diagram
        </h2>

        {/* Responsive Diagram Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          {/* Layer 1: Edge & Client */}
          <div className="border border-stone-200 rounded-lg p-4 bg-stone-50 space-y-3">
            <div className="flex items-center gap-2 font-bold text-stone-900 border-b border-stone-200 pb-2">
              <Cloud className="w-4 h-4 text-stone-700" />
              <span>1. CLIENT & EDGE</span>
            </div>
            <div className="p-2.5 bg-white rounded border border-stone-200 space-y-1">
              <div className="font-semibold text-stone-800">CloudFront CDN</div>
              <div className="text-[11px] text-stone-500 font-sans">
                Global edge caching · HTTPS · 1 TB/month transfer (AWS Free Tier)
              </div>
            </div>
            <div className="p-2.5 bg-white rounded border border-stone-200 space-y-1">
              <div className="font-semibold text-stone-800">Next.js Static Export</div>
              <div className="text-[11px] text-stone-500 font-sans">
                Hosted on S3 Static Website · Pre-rendered HTML/JS · Zero server compute
              </div>
            </div>
            <div className="p-2.5 bg-white rounded border border-stone-200 space-y-1">
              <div className="font-semibold text-stone-800">OpenFreeMap / OSM</div>
              <div className="text-[11px] text-stone-500 font-sans">
                Keyless light vector & raster tiles · No API key, no tracking, free tier
              </div>
            </div>
          </div>

          {/* Layer 2: AWS Cloud Backend */}
          <div className="border border-stone-200 rounded-lg p-4 bg-stone-50 space-y-3">
            <div className="flex items-center gap-2 font-bold text-stone-900 border-b border-stone-200 pb-2">
              <Server className="w-4 h-4 text-stone-700" />
              <span>2. AWS BACKEND</span>
            </div>
            <div className="p-2.5 bg-white rounded border border-stone-200 space-y-1">
              <div className="font-semibold text-stone-800">API Gateway (HTTP API v2)</div>
              <div className="text-[11px] text-stone-500 font-sans">
                Sub-millisecond routing · CORS enabled · Public endpoints
              </div>
            </div>
            <div className="p-2.5 bg-white rounded border border-stone-200 space-y-1">
              <div className="font-semibold text-stone-800">AWS Lambda Functions</div>
              <div className="text-[11px] text-stone-500 font-sans">
                <code>ApiFunction</code> (routes) + 5 Step Functions task lambdas (Python 3.12)
              </div>
            </div>
            <div className="p-2.5 bg-white rounded border border-stone-200 space-y-1">
              <div className="font-semibold text-stone-800">Step Functions</div>
              <div className="text-[11px] text-stone-500 font-sans">
                Standard state machine (LoadBundle → RunCore → AgentReview → Store)
              </div>
            </div>
            <div className="p-2.5 bg-white rounded border border-stone-200 space-y-1">
              <div className="font-semibold text-stone-800">DynamoDB & S3</div>
              <div className="text-[11px] text-stone-500 font-sans">
                <code>smokeprint-cases</code>, <code>smokeprint-runs</code> + S3 data bucket
              </div>
            </div>
          </div>

          {/* Layer 3: Local AI & Strands Agents */}
          <div className="border border-stone-200 rounded-lg p-4 bg-stone-50 space-y-3">
            <div className="flex items-center gap-2 font-bold text-stone-900 border-b border-stone-200 pb-2">
              <Cpu className="w-4 h-4 text-stone-700" />
              <span>3. LOCAL AGENTS & CORE</span>
            </div>
            <div className="p-2.5 bg-white rounded border border-stone-200 space-y-1">
              <div className="font-semibold text-stone-800">Frozen Core v2.7</div>
              <div className="text-[11px] text-stone-500 font-sans">
                Deterministic forward-plume Gaussian dispersion kernel + signature gating
              </div>
            </div>
            <div className="p-2.5 bg-white rounded border border-stone-200 space-y-1">
              <div className="font-semibold text-stone-800">Strands Agents SDK</div>
              <div className="text-[11px] text-stone-500 font-sans">
                Investigator + Adversarial Critic running locally against Ollama (llama3.2:latest)
              </div>
            </div>
            <div className="p-2.5 bg-white rounded border border-stone-200 space-y-1">
              <div className="font-semibold text-stone-800">Strict Validator Barrier</div>
              <div className="text-[11px] text-stone-500 font-sans">
                Zero hallucination: rejects ungrounded candidate IDs, numbers, and closure years
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Free Tier Audit & Limits */}
      <div className="bg-white rounded-lg border border-stone-200 shadow-sm p-6 space-y-4">
        <h2 className="text-base font-bold text-stone-900">
          AWS Free Tier Budget & Resource Limits
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-sans">
          <div className="border border-stone-200 rounded p-3 bg-stone-50 space-y-1.5">
            <div className="font-bold text-stone-900 font-mono text-[11px]">S3 & CLOUDFRONT</div>
            <ul className="list-disc list-inside text-stone-600 space-y-1 text-[11px]">
              <li><strong>CloudFront:</strong> 1 TB data transfer out/month + 10,000,000 requests permanently free.</li>
              <li><strong>S3 Storage:</strong> 5 GB standard storage free (Smokeprint total bundle is &lt; 5 MB).</li>
              <li><strong>S3 Requests:</strong> 20,000 GET requests free per month.</li>
            </ul>
          </div>

          <div className="border border-stone-200 rounded p-3 bg-stone-50 space-y-1.5">
            <div className="font-bold text-stone-900 font-mono text-[11px]">LAMBDA & STEP FUNCTIONS</div>
            <ul className="list-disc list-inside text-stone-600 space-y-1 text-[11px]">
              <li><strong>AWS Lambda:</strong> 1,000,000 invocations and 3,200,000 seconds of compute per month free.</li>
              <li><strong>Step Functions:</strong> 4,000 free state transitions per month for Standard workflows.</li>
              <li><strong>DynamoDB:</strong> 25 GB of storage free forever with on-demand capacity.</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Transparency & Security Policy */}
      <div className="bg-white rounded-lg border border-stone-200 shadow-sm p-6 space-y-3 text-xs text-stone-700">
        <h2 className="text-base font-bold text-stone-900">
          Public Interface Transparency & Security Standard
        </h2>
        <ul className="list-disc list-inside space-y-1.5 text-stone-600">
          <li><strong>No AWS Account IDs or ARNs:</strong> Sanitization middleware intercepts every API response and strips raw IAM roles, account IDs, and ARNs before transmission.</li>
          <li><strong>Honest Provenance:</strong> Step Functions and API replay endpoints always declare <code>source: "replayed"</code> and <code>mode: "replayed_from_canonical_output"</code>.</li>
          <li><strong>No Live Bedrock Billing:</strong> Strands agents execute locally on the developer machine; no Bedrock API calls are initiated from cloud Lambdas.</li>
        </ul>
      </div>
    </div>
  );
}
