// ...existing code...
// Live compute cashback and final total; only display computed text after BOTH fields have values.

(function () {
  const beforeInput = document.getElementById("total_before_tax");
  const pctInput = document.getElementById("cashback_pct");

  const cashbackDisplay = document.getElementById("cashback_amount_display");
  const totalAfterDisplay = document.getElementById("total_after_display");

  const hiddenTotalAfter = document.getElementById("total_after_cashback");
  const hiddenCashbackAmt = document.getElementById("cashback_amount");

  function parseNum(el) {
    if (!el) return null;
    const v = el.value;
    if (v === null || v === undefined || v === "") return null;
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : null;
  }

  function formatMoney(n) {
    if (n === null) return "";
    return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function recompute() {
    const totalBefore = parseNum(beforeInput);
    const pct = parseNum(pctInput);

    // only show computed values once both fields have valid numeric input
    if (totalBefore === null || pct === null) {
      if (cashbackDisplay) cashbackDisplay.textContent = "—";
      if (totalAfterDisplay) totalAfterDisplay.textContent = "—";
      if (hiddenTotalAfter) hiddenTotalAfter.value = "";
      if (hiddenCashbackAmt) hiddenCashbackAmt.value = "";
      return;
    }

    if (totalBefore < 0) {
      if (cashbackDisplay) cashbackDisplay.textContent = "—";
      if (totalAfterDisplay) totalAfterDisplay.textContent = "—";
      if (hiddenTotalAfter) hiddenTotalAfter.value = "";
      if (hiddenCashbackAmt) hiddenCashbackAmt.value = "";
      return;
    }

    const cashbackAmt = (pct >= 0) ? +(totalBefore * (pct / 100.0)) : 0;
    const totalAfter = +(totalBefore - cashbackAmt);

    const finalCashback = Math.max(0, cashbackAmt);
    const finalTotalAfter = Math.max(0, totalAfter);

    if (cashbackDisplay) cashbackDisplay.textContent = "$" + formatMoney(finalCashback);
    if (totalAfterDisplay) totalAfterDisplay.textContent = "$" + formatMoney(finalTotalAfter);

    if (hiddenTotalAfter) hiddenTotalAfter.value = finalTotalAfter.toFixed(2);
    if (hiddenCashbackAmt) hiddenCashbackAmt.value = finalCashback.toFixed(2);
  }

  // attach listeners; safe if elements missing
  [beforeInput, pctInput].forEach((el) => {
    if (!el) return;
    el.addEventListener("input", recompute);
    el.addEventListener("change", recompute);
  });

  // initial check on load
  document.addEventListener("DOMContentLoaded", recompute);
  // also call once in case script executed after DOM is ready
  recompute();
})();
// ...existing