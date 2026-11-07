// Modified for the English text/TXT demo; scope and behavior are documented in README.md.
"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

interface ReviewResult {
  review_id: string;
  status: string;
  contract_type: string;
  clauses_count: number;
  risk_summary: string;
  overall_risk_level: string;
  overall_compliance: string;
  knowledge_status: string;
  suggestions_count: number;
}

interface DetailedResult {
  review_id: string;
  status: string;
  contract_type: string;
  jurisdiction: string;
  as_of_date: string;
  knowledge_status: string;
  knowledge_version: string;
  clauses: Array<{ id: string; title: string; content: string; category: string }>;
  risk_findings: Array<{
    evidence?: { start: number; end: number; quote: string } | null;
    clause_id: string;
    risk_level: string;
    risk_type: string;
    description: string;
    rationale: string;
  }>;
  risk_summary: string;
  overall_risk_level: string;
  compliance_findings: Array<{
    evidence?: { start: number; end: number; quote: string } | null;
    knowledge_citations?: Array<{ chunk_id: string; title?: string; url?: string; quote?: string; english_gloss?: string; english_gloss_status?: string }>;
    clause_id: string;
    status: string;
    regulation: string;
    issue: string;
    recommendation: string;
  }>;
  missing_clauses: string[];
  overall_compliance: string;
  suggestions: Array<{
    clause_id: string;
    original_text: string;
    suggested_text: string;
    reason: string;
    priority: string;
  }>;
  version_diff: string;
  errors: string[];
  failed_stage: string;
  diagnostics: Array<{ stage?: string; status?: string; error_code?: string }>;
}

const RISK_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-800 border-red-300",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-300",
  low: "bg-blue-100 text-blue-800 border-blue-300",
  none: "bg-green-100 text-green-800 border-green-300",
};

const COMPLIANCE_COLORS: Record<string, string> = {
  compliant: "bg-green-100 text-green-800",
  non_compliant: "bg-red-100 text-red-800",
  needs_review: "bg-yellow-100 text-yellow-800",
};

export default function Home() {
  const [contractText, setContractText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [detail, setDetail] = useState<DetailedResult | null>(null);
  const [activeTab, setActiveTab] = useState("clauses");
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async () => {
    if (!contractText.trim()) return;
    setLoading(true);
    setResult(null);
    setDetail(null);
    setErrorMessage("");
    try {
      const resp = await fetch(`${API_BASE}/api/v1/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: contractText }),
        cache: "no-store",
      });
      const data = await resp.json();
      if (Array.isArray(data.clauses) && Array.isArray(data.diagnostics)) {
        setDetail(data);
      }
      if (!resp.ok) {
        setErrorMessage(data.message || data.detail?.message || "Review failed. Check the input and service configuration.");
        return;
      }
      setResult(data);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Cannot connect to the review service.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            Multi-Agent Contract Review
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Extraction → Risk → Compliance → Suggestions
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Contract input */}
          <div>
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">English purchase contract</h2>
              <p className="mb-3 text-sm text-gray-500">Mainland China · Purchase/sale contracts · Knowledge cutoff: 2026-10-20. Use fictional data. Real reviews send text to the configured model provider and may incur charges. Canadian law is not supported. Results stay on this page only; the backend keeps no review history.</p>
              <textarea
                className="w-full h-96 border rounded-lg p-4 text-sm font-mono resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Paste a fictional English purchase/sale contract..."
                value={contractText}
                onChange={(e) => setContractText(e.target.value)}
              />
              <div className="mt-4 flex items-center justify-between">
                <span className="text-sm text-gray-500">
                  {contractText.length} characters
                </span>
                <button
                  onClick={handleSubmit}
                  disabled={loading || !contractText.trim()}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  {loading ? "Reviewing..." : "Start review"}
                </button>
              </div>
            </div>
          </div>

          {/* Review results */}
          <div>
            {loading && (
              <div className="bg-white rounded-lg shadow p-12 text-center">
                <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
                <p className="mt-4 text-gray-600">
                  The four-agent workflow is reviewing your contract...
                </p>
                <p className="text-sm text-gray-400 mt-2">
                  Extraction → Risk → Compliance → Suggestions
                </p>
              </div>
            )}

            {errorMessage && !loading && (
              <div role="alert" className="mb-4 rounded border border-red-300 bg-red-50 p-4 text-red-800">
                {errorMessage}
                {detail?.failed_stage && <p className="mt-1 text-sm">Failed stage: {detail.failed_stage}</p>}
              </div>
            )}
            {(result || detail) && !loading && (
              <div className="space-y-4">
                {/* Review overview */}
                {result && <div className="bg-white rounded-lg shadow p-6">
                  <h2 className="text-lg font-semibold mb-4">Review overview</h2>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-gray-50 rounded">
                      <div className="text-2xl font-bold text-blue-600">
                        {result.clauses_count}
                      </div>
                      <div className="text-sm text-gray-500">Clauses</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded">
                      <div className="text-2xl font-bold text-orange-600">
                        {result.suggestions_count}
                      </div>
                      <div className="text-sm text-gray-500">Suggestions</div>
                    </div>
                    <div
                      className={`text-center p-3 rounded border ${RISK_COLORS[result.overall_risk_level] || ""}`}
                    >
                      <div className="text-sm font-semibold">Risk level</div>
                      <div className="text-lg font-bold uppercase">
                        {result.overall_risk_level}
                      </div>
                    </div>
                    <div
                      className={`text-center p-3 rounded ${COMPLIANCE_COLORS[result.overall_compliance] || ""}`}
                    >
                      <div className="text-sm font-semibold">Compliance status</div>
                      <div className="text-lg font-bold">
                        {result.overall_compliance === "compliant"
                          ? "No candidate issue"
                          : result.overall_compliance === "non_compliant"
                            ? "Candidate non-compliance"
                            : "Needs review"}
                      </div>
                    </div>
                  </div>
                  <p className="mt-4 text-sm text-gray-600">
                    {result.risk_summary}
                  </p>
                  {result.status === "partial" && <p className="mt-2 text-amber-700">Partially completed; review the diagnostics.</p>}
                  <p className="mt-2 text-xs text-gray-500">
                    Knowledge: {result.knowledge_status === "grounded" ? "Reviewed source summaries retrieved" : result.knowledge_status === "evidence_insufficient" ? "No matching sources" : result.knowledge_status === "invalid_citations" ? "Some citations failed validation" : result.knowledge_status === "out_of_scope_findings" ? "Some compliance claims were outside the supported scope" : "Not checked"}. Source matching does not verify legal conclusions. Candidate findings require human review.
                  </p>
                </div>}

                {detail && <details className="rounded border bg-white p-3 text-sm">
                  <summary>Execution diagnostics</summary>
                  <p className="mt-2">Status: {detail.status}; failed stage: {detail.failed_stage || "none"}</p>
                  {detail.diagnostics.map((row, index) => <p key={index}>{row.stage}: {row.status} {row.error_code || ""}</p>)}
                  {detail.errors.map((error, index) => <p key={index} className="text-red-700">{error}</p>)}
                </details>}
                {/* Result tabs */}
                {detail && (
                  <div className="bg-white rounded-lg shadow">
                    <div className="border-b flex">
                      {["clauses", "risks", "compliance", "suggestions"].map(
                        (tab) => (
                          <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-4 py-3 text-sm font-medium border-b-2 transition ${
                              activeTab === tab
                                ? "border-blue-500 text-blue-600"
                                : "border-transparent text-gray-500 hover:text-gray-700"
                            }`}
                          >
                            {tab === "clauses"
                              ? "Clauses"
                              : tab === "risks"
                                ? "Risks"
                                : tab === "compliance"
                                  ? "Compliance"
                                  : "Suggestions"}
                          </button>
                        )
                      )}
                    </div>

                    <div className="p-4 max-h-96 overflow-y-auto">
                      {activeTab === "clauses" &&
                        detail.clauses.map((c, i) => (
                          <div key={i} className="mb-3 p-3 bg-gray-50 rounded">
                            <div className="flex justify-between items-center">
                              <span className="font-medium text-sm">
                                {c.title}
                              </span>
                              <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                                {c.category}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600 mt-1 line-clamp-3">
                              {c.content}
                            </p>
                          </div>
                        ))}

                      {activeTab === "risks" &&
                        detail.risk_findings.map((r, i) => (
                          <div
                            key={i}
                            className={`mb-3 p-3 rounded border ${RISK_COLORS[r.risk_level] || ""}`}
                          >
                            <div className="flex justify-between">
                              <span className="font-medium text-sm">
                                {r.risk_type}
                              </span>
                              <span className="text-xs font-bold uppercase">
                                {r.risk_level}
                              </span>
                            </div>
                            <p className="text-sm mt-1">{r.description}</p>
                            {r.evidence?.quote && <p className="mt-1 text-xs">Contract evidence: {r.evidence.quote}</p>}
                            {r.rationale && (
                              <p className="text-xs mt-1 opacity-75">
                                Rationale: {r.rationale}
                              </p>
                            )}
                          </div>
                        ))}

                      {activeTab === "compliance" && (
                        <>
                          <p className="mb-3 text-xs text-gray-500">Drafting and completeness candidates only. The available summaries do not establish legal validity or mandatory terms.</p>
                          <p className="mb-3 text-xs text-gray-500">Jurisdiction: {detail.jurisdiction}; knowledge cutoff: {detail.as_of_date}; version: {detail.knowledge_version || "No applicable summaries"}</p>
                          {detail.missing_clauses.length > 0 && (
                            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded">
                              <p className="font-medium text-red-800 text-sm">
                                Potential missing information:
                              </p>
                              <ul className="list-disc list-inside text-sm text-red-700">
                                {detail.missing_clauses.map((m, i) => (
                                  <li key={i}>{m}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {detail.compliance_findings.map((f, i) => (
                            <div
                              key={i}
                              className={`mb-3 p-3 rounded ${COMPLIANCE_COLORS[f.status] || ""}`}
                            >
                              <p className="font-medium text-sm">{f.issue}</p>
                              <p className="text-xs mt-1">
                                Source: {f.regulation}
                              </p>
                              {f.evidence?.quote && <p className="text-xs mt-1">Contract evidence: {f.evidence.quote}</p>}
                              {f.knowledge_citations?.map((cite) => (
                                <p key={cite.chunk_id} className="text-xs mt-1">
                                  Source: {cite.url ? <a href={cite.url} target="_blank" rel="noreferrer" className="underline">{cite.title || cite.chunk_id}</a> : (cite.title || cite.chunk_id)}
                                  {cite.quote && <span lang="zh-CN">; original Chinese summary quote: {cite.quote}</span>}
                                  {cite.english_gloss && <span className="block">English explanation (unreviewed translation of the full summary): {cite.english_gloss}</span>}
                                </p>
                              ))}
                              {f.recommendation && (
                                <p className="text-xs mt-1">
                                  Recommendation: {f.recommendation}
                                </p>
                              )}
                            </div>
                          ))}
                        </>
                      )}

                      {activeTab === "suggestions" &&
                        detail.suggestions.map((s, i) => (
                          <div
                            key={i}
                            className="mb-3 p-3 bg-gray-50 rounded border"
                          >
                            <div className="flex justify-between items-center">
                              <span className="font-medium text-sm">
                                {s.reason}
                              </span>
                              <span
                                className={`text-xs px-2 py-1 rounded ${RISK_COLORS[s.priority] || ""}`}
                              >
                                {s.priority}
                              </span>
                            </div>
                            {s.original_text && (
                              <div className="mt-2 text-sm">
                                <span className="text-red-600 line-through">
                                  {s.original_text}
                                </span>
                              </div>
                            )}
                            <div className="mt-1 text-sm text-green-700">
                              {s.suggested_text}
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
