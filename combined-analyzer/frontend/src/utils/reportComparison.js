export const ISO_CHARACTERISTIC_FIELDS = {
  integrity: [
    'confidentiality_report',
    'data_integrity_report',
    'authenticity_report',
    'non_repudiation_report',
    'accountability_report',
    'resistance_report',
  ],
  compliance: [
    'functional_completeness_report',
    'functional_correctness_report',
    'functional_appropriateness_report',
  ],
  correctness: [
    'functional_completeness_correctness_report',
    'functional_correctness_accuracy_report',
    'functional_appropriateness_correctness_report',
  ],
  usability: [
    'appropriateness_recognizability_report',
    'learnability_report',
    'operability_report',
    'user_error_protection_report',
    'user_engagement_report',
    'self_descriptiveness_report',
    'inclusivity_report',
    'user_assistance_report',
  ],
  maintainability: [
    'modularity_report',
    'reusability_report',
    'analysability_report',
    'modifiability_report',
    'testability_report',
  ],
};

export function normalizeText(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

function normalizePath(path) {
  return normalizeText(path).replace(/\\/g, '/');
}

export function findingFingerprint(finding) {
  return [
    normalizeText(finding.characteristic),
    normalizeText(finding.type),
    normalizePath(finding.file_path),
    String(finding.line_number ?? ''),
    normalizeText(finding.explanation),
  ].join('|');
}

export function extractIsoFindings(analysis, type) {
  const fields = ISO_CHARACTERISTIC_FIELDS[type] || [];
  const extracted = [];

  fields.forEach((field) => {
    const characteristicReport = analysis?.[field];
    const characteristic = characteristicReport?.characteristic || field.replace(/_report$/, '');
    const findings = Array.isArray(characteristicReport?.findings) ? characteristicReport.findings : [];

    findings.forEach((item) => {
      extracted.push({
        characteristic,
        type: item?.type || 'unknown',
        file_path: item?.file_path || '',
        line_number: item?.line_number ?? null,
        explanation: item?.explanation || '',
      });
    });
  });

  return extracted;
}

export function summarizeFindings(findings) {
  const byType = { positive: 0, negative: 0, warning: 0, unknown: 0 };
  findings.forEach((item) => {
    const key = String(item.type || 'unknown').toLowerCase();
    if (Object.prototype.hasOwnProperty.call(byType, key)) {
      byType[key] += 1;
    } else {
      byType.unknown += 1;
    }
  });
  return {
    total: findings.length,
    byType,
  };
}

export function deterministicCompareFindings(baselineFindings, currentFindings) {
  const baselineByFingerprint = new Map();
  const currentByFingerprint = new Map();

  baselineFindings.forEach((finding, index) => {
    const fp = findingFingerprint(finding);
    const queue = baselineByFingerprint.get(fp) || [];
    queue.push(index);
    baselineByFingerprint.set(fp, queue);
  });

  currentFindings.forEach((finding, index) => {
    const fp = findingFingerprint(finding);
    const queue = currentByFingerprint.get(fp) || [];
    queue.push(index);
    currentByFingerprint.set(fp, queue);
  });

  const unchanged = [];
  const matchedBaseline = new Set();
  const matchedCurrent = new Set();

  baselineByFingerprint.forEach((baselineIndices, fp) => {
    const currentIndices = currentByFingerprint.get(fp) || [];
    const pairCount = Math.min(baselineIndices.length, currentIndices.length);
    for (let i = 0; i < pairCount; i += 1) {
      const baselineIndex = baselineIndices[i];
      const currentIndex = currentIndices[i];
      matchedBaseline.add(baselineIndex);
      matchedCurrent.add(currentIndex);
      unchanged.push({
        baseline: baselineFindings[baselineIndex],
        current: currentFindings[currentIndex],
        match_source: 'deterministic',
      });
    }
  });

  const unmatchedBaseline = baselineFindings
    .map((finding, index) => ({ finding, index }))
    .filter(({ index }) => !matchedBaseline.has(index));

  const unmatchedCurrent = currentFindings
    .map((finding, index) => ({ finding, index }))
    .filter(({ index }) => !matchedCurrent.has(index));

  return {
    unchanged,
    unmatchedBaseline,
    unmatchedCurrent,
  };
}

export function mergeAiMatches(deterministicResult, aiMatches, confidenceThreshold = 0.75) {
  const acceptedBaseline = new Set();
  const acceptedCurrent = new Set();
  const aiUnchanged = [];

  (Array.isArray(aiMatches) ? aiMatches : []).forEach((match) => {
    const baselineIndex = Number(match?.baseline_index);
    const currentIndex = Number(match?.current_index);
    const confidence = Number(match?.confidence ?? 0);

    if (!Number.isInteger(baselineIndex) || !Number.isInteger(currentIndex)) return;
    if (confidence < confidenceThreshold) return;
    if (acceptedBaseline.has(baselineIndex) || acceptedCurrent.has(currentIndex)) return;

    const baselineEntry = deterministicResult.unmatchedBaseline[baselineIndex];
    const currentEntry = deterministicResult.unmatchedCurrent[currentIndex];
    if (!baselineEntry || !currentEntry) return;

    acceptedBaseline.add(baselineIndex);
    acceptedCurrent.add(currentIndex);
    aiUnchanged.push({
      baseline: baselineEntry.finding,
      current: currentEntry.finding,
      match_source: 'ai',
      confidence,
      reason: String(match?.reason || ''),
    });
  });

  const resolved = deterministicResult.unmatchedBaseline
    .filter((_entry, idx) => !acceptedBaseline.has(idx))
    .map((entry) => entry.finding);

  const newlyAdded = deterministicResult.unmatchedCurrent
    .filter((_entry, idx) => !acceptedCurrent.has(idx))
    .map((entry) => entry.finding);

  return {
    unchanged: [...deterministicResult.unchanged, ...aiUnchanged],
    resolved,
    newFindings: newlyAdded,
    aiMatchedCount: aiUnchanged.length,
  };
}
