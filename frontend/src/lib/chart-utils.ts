/** Find the index of max and min values for smart annotations on charts. */
export function findPeakValley(data: { value: number }[]) {
  if (data.length < 3) return { peakIdx: -1, valleyIdx: -1 };
  let peakIdx = 0;
  let valleyIdx = 0;
  for (let i = 1; i < data.length; i++) {
    if (data[i].value > data[peakIdx].value) peakIdx = i;
    if (data[i].value < data[valleyIdx].value) valleyIdx = i;
  }
  // Only annotate if there's meaningful variance (peak != valley)
  if (peakIdx === valleyIdx) return { peakIdx: -1, valleyIdx: -1 };
  return { peakIdx, valleyIdx };
}
