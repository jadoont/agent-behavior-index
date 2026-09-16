function describe(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  return `n=${values.length} min=${sorted[0]} max=${sorted[sorted.length - 1]} mean=${mean.toFixed(2)}`;
}

module.exports = { describe };
