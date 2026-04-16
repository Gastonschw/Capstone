import React, { useEffect } from 'react';

// Cost tier lookup — patterns matched against model id (lowercased).
// Order matters: more-specific patterns (e.g. "gpt-4o-mini") must come
// before less-specific ones (e.g. "gpt-4o") so we match correctly.
//
// Pricing based on public API rates as of early 2026:
//   Low    ≈ < $1 / 1M output tokens   (mini, nano, haiku, open-source)
//   Medium ≈ $1 – $10 / 1M output       (4o, 4.1, sonnet, gemini pro)
//   High   ≈ > $10 / 1M output          (opus, o1, gpt-4.5)
const COST_TIERS = [
  // ── Low cost ──────────────────────────────────────────────
  // OpenAI minis / nano  ($0.15-$0.60/M out)
  { pattern: 'gpt-4o-mini', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Fast and affordable' },
  { pattern: 'gpt-4.1-mini', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Fast and affordable' },
  { pattern: 'gpt-4.1-nano', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Ultra-lightweight model' },
  { pattern: 'gpt-3.5', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Legacy lightweight model' },
  // OpenAI reasoning minis  (~$1/M out)
  { pattern: 'o3-mini', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Efficient reasoning model' },
  { pattern: 'o4-mini', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Efficient reasoning model' },
  { pattern: 'o1-mini', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Compact reasoning model' },
  // Anthropic Haiku  ($1/$5 per M)
  { pattern: 'haiku', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Fast and affordable' },
  // Google Gemini Flash  ($0.15-$0.60/M out)
  { pattern: 'gemini 2.5 flash', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Fast hybrid reasoning' },
  { pattern: 'gemini 2.0 flash', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Fast and efficient' },
  { pattern: 'gemini flash', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Fast and efficient' },
  // DeepSeek  ($0.28-$2.19/M out)
  { pattern: 'deepseek-r1', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Low-cost reasoning model' },
  { pattern: 'deepseek-v3', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Very low cost' },
  { pattern: 'deepseek', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Low-cost open model' },
  // Llama  (open-source, near-free via hosted APIs)
  { pattern: 'llama-4', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Open-source, very cheap' },
  { pattern: 'llama-3', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Open-source, very cheap' },
  { pattern: 'llama', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Open-source, very cheap' },
  // Mistral  ($0.02-$0.30/M blended)
  { pattern: 'mistral-large', cost: 'Medium', costColor: '#ca8a04', costBg: '#fef9c3', quality: 'Strong open model' },
  { pattern: 'mistral', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Lightweight open model' },
  // Qwen  (~$1.20/M in)
  { pattern: 'qwen', cost: 'Low', costColor: '#16a34a', costBg: '#dcfce7', quality: 'Affordable open model' },

  // ── Medium cost ───────────────────────────────────────────
  // OpenAI GPT-4o  ($2.50/$10 per M)
  { pattern: 'gpt-4o', cost: 'Medium', costColor: '#ca8a04', costBg: '#fef9c3', quality: 'Strong general-purpose model' },
  // OpenAI GPT-4.1  ($2/$8 per M)
  { pattern: 'gpt-4.1', cost: 'Medium', costColor: '#ca8a04', costBg: '#fef9c3', quality: 'Strong general-purpose model' },
  // OpenAI o3  ($2/$8 per M)
  { pattern: 'o3', cost: 'Medium', costColor: '#ca8a04', costBg: '#fef9c3', quality: 'Reasoning model' },
  // Anthropic Sonnet  ($3/$15 per M)
  { pattern: 'sonnet', cost: 'Medium', costColor: '#ca8a04', costBg: '#fef9c3', quality: 'Balanced cost and quality' },
  // Google Gemini Pro  ($2/$12 per M)
  { pattern: 'gemini 2.5 pro', cost: 'Medium', costColor: '#ca8a04', costBg: '#fef9c3', quality: 'Strong multimodal model' },
  { pattern: 'gemini pro', cost: 'Medium', costColor: '#ca8a04', costBg: '#fef9c3', quality: 'Strong multimodal model' },
  { pattern: 'gemini', cost: 'Medium', costColor: '#ca8a04', costBg: '#fef9c3', quality: 'Google multimodal model' },

  // ── High cost ─────────────────────────────────────────────
  // Anthropic Opus  ($5/$25 per M)
  { pattern: 'opus', cost: 'High', costColor: '#dc2626', costBg: '#fee2e2', quality: 'Highest quality analysis' },
  // OpenAI GPT-4.5  (premium tier)
  { pattern: 'gpt-4.5', cost: 'High', costColor: '#dc2626', costBg: '#fee2e2', quality: 'Premium quality model' },
  // OpenAI o1 full  ($15/$60 per M)
  { pattern: 'o1', cost: 'High', costColor: '#dc2626', costBg: '#fee2e2', quality: 'Advanced reasoning model' },
  // OpenAI o4 full
  { pattern: 'o4', cost: 'High', costColor: '#dc2626', costBg: '#fee2e2', quality: 'Advanced reasoning model' },

  // ── Do not use ────────────────────────────────────────────
  { pattern: 'text-embedding', cost: 'Do Not Use', costColor: '#991b1b', costBg: '#fecaca', quality: 'Embedding model — not for analysis' },
];

function getCostTier(modelId) {
  const lower = (modelId || '').toLowerCase();
  // Match more-specific patterns first (e.g. "gpt-4o-mini" before "gpt-4o")
  for (const tier of COST_TIERS) {
    if (lower.includes(tier.pattern)) return tier;
  }
  return {
    cost: 'Unknown',
    costColor: '#6b7280',
    costBg: '#f3f4f6',
    quality: '',
  };
}

const styles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    backgroundColor: 'rgba(0,0,0,0.45)',
    zIndex: 1000,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
  },
  modal: {
    backgroundColor: '#fff',
    borderRadius: '16px',
    boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
    maxWidth: '480px',
    width: '100%',
    maxHeight: '85vh',
    overflow: 'auto',
    color: '#1f2937',
  },
  header: {
    padding: '24px 24px 16px',
    borderBottom: '1px solid #e5e7eb',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '12px',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: '700',
    color: '#1e3a5f',
  },
  subtitle: {
    margin: '4px 0 0',
    fontSize: '13px',
    color: '#6b7280',
    lineHeight: 1.4,
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '22px',
    color: '#9ca3af',
    cursor: 'pointer',
    padding: '4px',
    lineHeight: 1,
    flexShrink: 0,
  },
  body: {
    padding: '20px 24px 24px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  th: {
    textAlign: 'left',
    padding: '8px 10px',
    fontSize: '11px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    color: '#6b7280',
    borderBottom: '2px solid #e5e7eb',
  },
  td: {
    padding: '10px 10px',
    borderBottom: '1px solid #f3f4f6',
    verticalAlign: 'middle',
  },
  modelName: {
    fontWeight: '600',
    color: '#1f2937',
  },
  costBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '10px',
    fontSize: '11px',
    fontWeight: '600',
  },
  quality: {
    color: '#6b7280',
    fontSize: '12px',
  },
  note: {
    marginTop: '20px',
    padding: '14px 16px',
    backgroundColor: '#f0f4ff',
    borderRadius: '10px',
    fontSize: '12px',
    color: '#374151',
    lineHeight: 1.6,
  },
  noteTitle: {
    fontWeight: '700',
    color: '#1e3a5f',
    marginBottom: '4px',
  },
  empty: {
    padding: '20px',
    textAlign: 'center',
    color: '#6b7280',
    fontSize: '13px',
  },
};

export default function ModelInfoModal({ onClose, models = [] }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const rows = models.map((m) => {
    const tier = getCostTier(m.id);
    return {
      id: m.id,
      name: m.name || m.id,
      ...tier,
    };
  });

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div style={styles.header}>
          <div>
            <h2 style={styles.title}>Model Pricing Guide</h2>
            <p style={styles.subtitle}>
              Cost per analysis run on your $5 daily TAMU API budget
            </p>
          </div>
          <button type="button" style={styles.closeBtn} onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>
        <div style={styles.body}>
          {rows.length === 0 ? (
            <p style={styles.empty}>No models loaded. Enter your TAMU API key to see available models.</p>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Model</th>
                  <th style={styles.th}>Cost per Run</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td style={styles.td}>
                      <div style={styles.modelName}>{row.name}</div>
                      {row.quality && <div style={styles.quality}>{row.quality}</div>}
                    </td>
                    <td style={styles.td}>
                      <span
                        style={{
                          ...styles.costBadge,
                          color: row.costColor,
                          backgroundColor: row.costBg,
                        }}
                      >
                        {row.cost}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div style={styles.note}>
            <div style={styles.noteTitle}>About costs</div>
            Each full analysis run makes multiple AI calls to evaluate your code across several
            quality characteristics. Higher-cost models produce more detailed feedback but use
            more of your daily budget. Cost varies with project size.
          </div>
        </div>
      </div>
    </div>
  );
}

export { getCostTier };
