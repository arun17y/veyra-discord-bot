// web/public/js/transition.js - Coordinates opening sequence and accelerated entry transition (2-3 seconds)
import { gsap } from 'gsap';

export class CinematicController {
    constructor(appContext) {
        this.app = appContext;
        this.isTriggered = false;
    }

    playOpeningSequence() {
        // Fast opening unmasking of the cybernetic iris
        gsap.to(this.app.eye.eyeMat.uniforms.uEyeOpen, {
            value: 1.0,
            duration: 0.8,
            delay: 0.1,
            ease: "power3.out"
        });

        gsap.to(this.app.cinematicScene.directionalLight, {
            intensity: 2.5,
            duration: 1.0,
            delay: 0.2
        });

        // Fast camera zoom creep
        gsap.to(this.app.cinematicScene.camera.position, {
            z: 5.0,
            duration: 1.5,
            ease: "power2.out"
        });
    }

    triggerExplosion() {
        if (this.isTriggered) return;
        this.isTriggered = true;

        const timeline = gsap.timeline();

        // UI overlay fades out instantly (0.15s)
        timeline.to('#ui-layer', {
            opacity: 0,
            duration: 0.15,
            pointerEvents: 'none'
        }, 0);

        // Core flash brightness flare
        timeline.to(this.app.eye.eyeMat.uniforms.uBrightness, {
            value: 15.0,
            duration: 0.2,
            ease: "power2.in"
        }, 0);

        timeline.to(this.app.cinematicScene.bloomPass, {
            strength: 8.0,
            radius: 1.5,
            duration: 0.2
        }, 0);

        // Snappy camera vibration shake
        timeline.to(this.app.cinematicScene.camera.position, {
            x: "+=0.12",
            y: "-=0.08",
            duration: 0.03,
            yoyo: true,
            repeat: 5
        }, 0.1);

        // Volumetric particle dissolution matrix trigger (1.0s)
        timeline.to(this.app.particles.material.uniforms.uExplode, {
            value: 1.0,
            duration: 1.0,
            ease: "power3.out"
        }, 0.15);

        // Eyeball mesh scales down quickly
        timeline.to(this.app.eye.group.scale, {
            x: 0.0,
            y: 0.0,
            z: 0.0,
            duration: 0.4,
            ease: "power3.in"
        }, 0.15);

        // Transition layout background and trigger element reveals
        timeline.to('body', {
            backgroundColor: "#050505",
            duration: 0.4,
            onComplete: () => {
                console.log("WebGL Entry Transition resolved.");
                
                const webglCanvas = document.getElementById('webgl-canvas');
                const uiLayer = document.getElementById('ui-layer');
                const mainContent = document.getElementById('main-content');
                
                if (webglCanvas) {
                    webglCanvas.style.transition = 'opacity 0.6s ease';
                    webglCanvas.style.opacity = '0';
                    setTimeout(() => {
                        webglCanvas.style.display = 'none';
                    }, 600);
                }
                if (uiLayer) {
                    uiLayer.style.display = 'none';
                }

                // Smoothly reveal home page elements
                if (mainContent) {
                    mainContent.style.opacity = '1';
                    mainContent.style.pointerEvents = 'auto';
                }
                sessionStorage.setItem('hasEntered', 'true');
                
                // Initialize animated reveal footer triggers
                if (typeof window.initAnimatedRevealFooter === 'function') {
                    window.initAnimatedRevealFooter();
                }
            }
        }, "+=0.1");
    }
}
