/* =========================================================
   VEYRA 3D Interactive Mouse Tilt Engine
   Silky smooth perspective tilt & depth parallax on hover
   ========================================================= */

document.addEventListener('DOMContentLoaded', () => {
    init3DTiltEngine();
});

function init3DTiltEngine() {
    const cardSelectors = [
        '.glass-card',
        '.feat-card',
        '.pricing-card-wrap',
        '.review-card',
        '.threat-btn-card',
        '.control-box-sec',
        '.audit-card',
        '.command-box',
        '.server-select-card',
        '.ticket-showcase-box'
    ];

    const cards = document.querySelectorAll(cardSelectors.join(', '));

    cards.forEach(card => {
        if (card.dataset.tiltInitialized) return;
        card.dataset.tiltInitialized = 'true';

        card.classList.add('tilt-card');

        card.addEventListener('mousemove', (e) => {
            card.classList.remove('tilt-card-reset');
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            // Maximum tilt angle (degrees)
            const maxTilt = 10;
            const rotateX = (((centerY - y) / centerY) * maxTilt).toFixed(2);
            const rotateY = (((x - centerX) / centerX) * maxTilt).toFixed(2);

            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
        });

        card.addEventListener('mouseleave', () => {
            card.classList.add('tilt-card-reset');
            card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
        });
    });
}

// Re-observe dynamically added elements
if (typeof window !== 'undefined') {
    window.init3DTiltEngine = init3DTiltEngine;
    const observer = new MutationObserver(() => {
        init3DTiltEngine();
    });
    document.addEventListener('DOMContentLoaded', () => {
        if (document.body) {
            observer.observe(document.body, { childList: true, subtree: true });
        }
    });
}
