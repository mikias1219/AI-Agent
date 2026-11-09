/** Labels for /api/status inference fields (Phase 2 dual-path). */

export function inferenceLabel(status) {
  if (!status) return 'Connecting…';
  const runtime = status.active_runtime;
  if (runtime === 'fake' || status.provider === 'fake') return 'Offline test provider';
  if (runtime === 'openai_compat' || status.provider === 'openai') {
    return `Cloud agent · ${status.model}`;
  }
  if (runtime === 'hermes') return `Hermes · ${status.model}`;
  if (runtime === 'ollama_agent') {
    if (status.provider === 'hermes') return `Ollama agent · ${status.model}`;
    return `Ollama · ${status.model}`;
  }
  if (status.provider === 'hermes') return `Hermes · ${status.model}`;
  if (status.provider === 'ollama') return `Ollama · ${status.model}`;
  return status.model || status.provider;
}

export function ollamaReachableLabel(status) {
  if (!status) return 'Ollama · Unknown';
  if (status.provider === 'fake' || status.active_runtime === 'fake') return 'Ollama · N/A';
  if (status.provider === 'openai' || status.active_runtime === 'openai_compat') {
    return 'Inference · Cloud';
  }
  return status.ollama_reachable ? 'Ollama · Reachable' : 'Ollama · Unreachable';
}
