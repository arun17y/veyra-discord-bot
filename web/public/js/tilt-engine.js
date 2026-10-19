/* =========================================================
   VEYRA 3D Tilt Engine - DISABLED
   ========================================================= */

function init3DTiltEngine() {
    // Tilt effect disabled globally
    document.querySelectorAll('.tilt-card, .tilt-card-reset').forEach(el => {
        el.style.transform = 'none';
        el.classList.remove('tilt-card', 'tilt-card-reset');
    });
}

if (typeof window !== 'undefined') {
    window.init3DTiltEngine = init3DTiltEngine;
}
