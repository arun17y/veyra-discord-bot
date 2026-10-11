/* =================================================================
   VEYRA ULTRA-MODERN HTML5 CANVAS PARTICLE TEXT MORPH ENGINE
   Continuously transforms text phrases using tiny glowing particles
   ================================================================= */

(function () {
    class ParticleTextEngine {
        constructor(containerId) {
            this.container = document.getElementById(containerId);
            if (!this.container) return;

            // Hide fallback text element instead of destroying it
            const fallbackEl = document.getElementById('vaporize-text-headline');
            if (fallbackEl) {
                fallbackEl.style.display = 'none';
            }
            
            // Check if canvas already created
            let existingCanvas = document.getElementById('particle-text-canvas');
            if (existingCanvas) {
                existingCanvas.remove();
            }

            // Create canvas element
            this.canvas = document.createElement('canvas');
            this.canvas.id = 'particle-text-canvas';
            this.canvas.style.display = 'block';
            this.canvas.style.maxWidth = '100%';
            this.canvas.style.height = 'auto';
            this.canvas.style.cursor = 'pointer';
            this.canvas.style.margin = '0 auto';
            this.container.appendChild(this.canvas);

            this.ctx = this.canvas.getContext('2d');
            if (!this.ctx) {
                // Canvas 2d context fallback
                if (fallbackEl) fallbackEl.style.display = 'block';
                return;
            }

            // Offscreen canvas for sampling text pixels
            this.offscreen = document.createElement('canvas');
            this.offCtx = this.offscreen.getContext('2d', { willReadFrequently: true });

            // Word sequence to cycle continuously
            this.phrases = [
                { prefix: 'VEYRA ', word: 'UNSTOPPABLE', suffix: ' DISCORD SUITE' },
                { prefix: 'VEYRA ', word: 'NEXT-GEN', suffix: ' ANTI-NUKE' },
                { prefix: 'VEYRA ', word: 'AIRTIGHT', suffix: ' SECURITY CORES' },
                { prefix: 'VEYRA ', word: 'REAL-TIME', suffix: ' TICKETING' },
                { prefix: 'VEYRA ', word: 'LIGHTNING-FAST', suffix: ' AUTOMATION' }
            ];

            this.phraseIndex = 0;
            this.particles = [];
            this.mouse = { x: -9999, y: -9999, radius: 75 };
            this.isExploding = false;
            this.animFrame = null;
            this.cycleTimer = null;

            this.init();
        }

        init() {
            this.resize();
            window.addEventListener('resize', () => this.resize());

            // Mouse tracking
            this.canvas.addEventListener('mousemove', (e) => {
                const rect = this.canvas.getBoundingClientRect();
                this.mouse.x = (e.clientX - rect.left) * (this.canvas.width / rect.width);
                this.mouse.y = (e.clientY - rect.top) * (this.canvas.height / rect.height);
            });

            this.canvas.addEventListener('mouseleave', () => {
                this.mouse.x = -9999;
                this.mouse.y = -9999;
            });

            // Touch tracking for mobile devices
            this.canvas.addEventListener('touchmove', (e) => {
                if (e.touches.length > 0) {
                    const rect = this.canvas.getBoundingClientRect();
                    this.mouse.x = (e.touches[0].clientX - rect.left) * (this.canvas.width / rect.width);
                    this.mouse.y = (e.touches[0].clientY - rect.top) * (this.canvas.height / rect.height);
                }
            }, { passive: true });

            this.canvas.addEventListener('touchend', () => {
                this.mouse.x = -9999;
                this.mouse.y = -9999;
            });

            // Initial text sampling
            this.samplePhrase(this.phrases[this.phraseIndex]);

            // Start loop
            this.animate();

            // Cycle phrases every 3.8 seconds
            this.startCycle();
        }

        resize() {
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            const containerWidth = Math.min(this.container.clientWidth || 800, 850);
            const width = containerWidth;
            const height = containerWidth < 480 ? 75 : 95;

            this.width = width;
            this.height = height;

            this.canvas.width = width * dpr;
            this.canvas.height = height * dpr;
            this.canvas.style.width = width + 'px';
            this.canvas.style.height = height + 'px';

            this.ctx.scale(dpr, dpr);

            this.offscreen.width = width;
            this.offscreen.height = height;

            // Re-sample text when resized
            if (this.phrases && this.phrases.length > 0) {
                this.samplePhrase(this.phrases[this.phraseIndex]);
            }
        }

        samplePhrase(phraseObj) {
            const w = this.width;
            const h = this.height;

            this.offCtx.clearRect(0, 0, w, h);

            // High-precision responsive font calculation
            let fontSize = Math.max(18, Math.min(Math.floor(w / 18), w < 500 ? 22 : 36));
            this.offCtx.font = `900 ${fontSize}px "Space Grotesk", "Outfit", system-ui, sans-serif`;
            this.offCtx.textAlign = 'center';
            this.offCtx.textBaseline = 'middle';

            const prefixWidth = this.offCtx.measureText(phraseObj.prefix).width;
            const wordWidth = this.offCtx.measureText(phraseObj.word).width;
            const suffixWidth = this.offCtx.measureText(phraseObj.suffix).width;
            const totalWidth = prefixWidth + wordWidth + suffixWidth;

            const startX = (w - totalWidth) / 2;
            const centerY = h / 2;

            // Render crisp text onto offscreen canvas for sampling
            this.offCtx.fillStyle = '#FFFFFF';
            this.offCtx.textAlign = 'left';
            this.offCtx.fillText(phraseObj.prefix, startX, centerY);
            this.offCtx.fillText(phraseObj.word, startX + prefixWidth, centerY);
            this.offCtx.fillText(phraseObj.suffix, startX + prefixWidth + wordWidth, centerY);

            // Scan pixels with high density (step = 2 for ultra-crisp visibility)
            const imgData = this.offCtx.getImageData(0, 0, w, h);
            const data = imgData.data;

            const targetPoints = [];
            const step = w < 500 ? 2 : 2; // Step 2 for solid, sharp text outlines

            for (let y = 0; y < h; y += step) {
                for (let x = 0; x < w; x += step) {
                    const index = (y * w + x) * 4;
                    const alpha = data[index + 3];

                    if (alpha > 120) {
                        // Tag word section (0: prefix, 1: center word, 2: suffix)
                        let wordSection = 0;
                        if (x >= startX + prefixWidth && x < startX + prefixWidth + wordWidth) {
                            wordSection = 1;
                        } else if (x >= startX + prefixWidth + wordWidth) {
                            wordSection = 2;
                        }

                        // Normalized progress across the entire headline width (0.0 to 1.0)
                        const normX = Math.max(0, Math.min(1, (x - startX) / (totalWidth || 1)));

                        targetPoints.push({
                            x: x,
                            y: y,
                            section: wordSection,
                            normX: normX
                        });
                    }
                }
            }

            // Sync particles array with target points
            const currentCount = this.particles.length;
            const targetCount = targetPoints.length;

            for (let i = 0; i < targetCount; i++) {
                const pt = targetPoints[i];
                if (i < currentCount) {
                    this.particles[i].tx = pt.x;
                    this.particles[i].ty = pt.y;
                    this.particles[i].section = pt.section;
                    this.particles[i].normX = pt.normX;
                } else {
                    const angle = Math.random() * Math.PI * 2;
                    const dist = 30 + Math.random() * 80;
                    this.particles.push({
                        x: pt.x + Math.cos(angle) * dist,
                        y: pt.y + Math.sin(angle) * dist,
                        vx: (Math.random() - 0.5) * 4,
                        vy: (Math.random() - 0.5) * 4,
                        tx: pt.x,
                        ty: pt.y,
                        size: 1.1 + Math.random() * 0.9,
                        section: pt.section,
                        normX: pt.normX,
                        alpha: 0.85 + Math.random() * 0.15
                    });
                }
            }

            if (currentCount > targetCount) {
                for (let i = targetCount; i < currentCount; i++) {
                    const p = this.particles[i];
                    p.tx = p.x + (Math.random() - 0.5) * 120;
                    p.ty = p.y + (Math.random() - 0.5) * 120;
                    p.alpha = 0;
                }
                setTimeout(() => {
                    this.particles = this.particles.slice(0, targetCount);
                }, 350);
            }
        }

        triggerExplosion() {
            this.isExploding = true;
            for (let i = 0; i < this.particles.length; i++) {
                const p = this.particles[i];
                const angle = Math.random() * Math.PI * 2;
                const force = 3 + Math.random() * 8;
                p.vx += Math.cos(angle) * force;
                p.vy += Math.sin(angle) * force;
            }

            setTimeout(() => {
                this.isExploding = false;
            }, 250);
        }

        nextPhrase() {
            this.triggerExplosion();
            setTimeout(() => {
                this.phraseIndex = (this.phraseIndex + 1) % this.phrases.length;
                this.samplePhrase(this.phrases[this.phraseIndex]);
            }, 180);
        }

        startCycle() {
            if (this.cycleTimer) clearInterval(this.cycleTimer);
            this.cycleTimer = setInterval(() => {
                this.nextPhrase();
            }, 4200);
        }

        animate() {
            this.ctx.clearRect(0, 0, this.width, this.height);

            const mouse = this.mouse;
            const time = Date.now() * 0.002;

            for (let i = 0; i < this.particles.length; i++) {
                const p = this.particles[i];

                // Mouse push
                if (mouse.x > 0 && mouse.y > 0) {
                    const dx = p.x - mouse.x;
                    const dy = p.y - mouse.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);

                    if (dist < mouse.radius && dist > 0) {
                        const force = (mouse.radius - dist) / mouse.radius;
                        const angle = Math.atan2(dy, dx);
                        p.vx += Math.cos(angle) * force * 3.0;
                        p.vy += Math.sin(angle) * force * 3.0;
                    }
                }

                // Spring physics to target text position
                const ax = (p.tx - p.x) * 0.12;
                const ay = (p.ty - p.y) * 0.12;

                p.vx += ax;
                p.vy += ay;
                p.vx *= 0.72;
                p.vy *= 0.72;

                p.x += p.vx;
                p.y += p.vy;

                // DYNAMIC MULTI-WORD AURORA COLOR ENGINE
                // Calculate distinct hue for each word section:
                // Section 0 (Prefix): Cyan -> Blue -> Teal wave (190° - 230°)
                // Section 1 (Center Highlight Word): Neon Purple -> Hot Magenta -> Pink (270° - 330°)
                // Section 2 (Suffix): Vibrant Amber -> Emerald -> Orange (140° - 40°)
                let baseHue = 200;
                let saturation = 95;
                let lightness = 65;

                const offset = (p.normX || 0) * 120 + time * 40;

                if (p.section === 0) {
                    baseHue = (195 + Math.sin(time * 1.5 + offset * 0.02) * 35 + 360) % 360; // Electric Cyan/Blue
                    lightness = 70;
                } else if (p.section === 1) {
                    baseHue = (275 + Math.sin(time * 2.0 + offset * 0.03) * 45 + 360) % 360; // Neon Purple/Magenta
                    lightness = 68;
                } else {
                    baseHue = (30 + Math.sin(time * 1.8 + offset * 0.025) * 40 + 360) % 360; // Sunburst Gold/Emerald
                    lightness = 65;
                }

                const colorStr = `hsl(${baseHue}, ${saturation}%, ${lightness}%)`;

                // Draw sharp particle
                this.ctx.beginPath();
                this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                this.ctx.fillStyle = colorStr;
                this.ctx.globalAlpha = p.alpha || 0.95;
                this.ctx.shadowBlur = 4;
                this.ctx.shadowColor = colorStr;
                this.ctx.fill();
            }

            this.ctx.shadowBlur = 0;
            this.ctx.globalAlpha = 1.0;

            this.animFrame = requestAnimationFrame(() => this.animate());
        }
    }

    // Auto-initialize when DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.veyraParticleTextEngine = new ParticleTextEngine('particle-headline-container');
        });
    } else {
        window.veyraParticleTextEngine = new ParticleTextEngine('particle-headline-container');
    }
})();
