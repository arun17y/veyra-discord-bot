// web/public/js/main.js - Bootstrap WebGL application subsystems and animation loop
import * as THREE from 'three';
import { CinematicScene } from './scene.js';
import { VeyraEye } from './eye.js';
import { ParticleSystem } from './particles.js';
import { CinematicController } from './transition.js';

class Application {
    constructor() {
        this.canvas = document.getElementById('webgl-canvas');
        if (!this.canvas) {
            console.warn("WebGL Canvas context (#webgl-canvas) not found.");
            return;
        }
        this.clock = new THREE.Clock();
        this.init();
    }

    init() {
        this.cinematicScene = new CinematicScene(this.canvas);
        this.eye = new VeyraEye(this.cinematicScene.scene);
        this.particles = new ParticleSystem(this.cinematicScene.scene);
        this.controller = new CinematicController(this);

        this.setupEventHandlers();
        this.animate();

        // Run opening zoom/open sequence
        this.controller.playOpeningSequence();
    }

    setupEventHandlers() {
        const uiLayer = document.getElementById('ui-layer');
        if (uiLayer) {
            uiLayer.addEventListener('click', () => {
                playEntrySound();
                this.controller.triggerExplosion();
            });
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        const elapsedTime = this.clock.getElapsedTime();

        // Eye breathing system scaling
        if (this.eye && this.eye.group && !this.controller.isTriggered) {
            const breathingScale = 1.0 + Math.sin(elapsedTime * 1.5) * 0.015;
            this.eye.group.scale.set(breathingScale, breathingScale, breathingScale);
        }

        this.eye.update(elapsedTime);
        this.particles.update(elapsedTime);
        this.cinematicScene.render();
    }
}

// Procedural 2.5-second Cybernetic Power-On Chime & Reactor Bass Swell sound synthesizer
function playEntrySound() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        const ctx = new AudioContext();
        const now = ctx.currentTime;

        // --- 1. CRYSTAL CHIME (Additive harmonic major chord bells) ---
        const frequencies = [440, 554.37, 659.25, 880, 1200, 1760]; 
        frequencies.forEach((f, idx) => {
            const osc = ctx.createOscillator();
            const gainNode = ctx.createGain();
            
            osc.type = 'sine';
            osc.frequency.setValueAtTime(f, now);
            osc.frequency.linearRampToValueAtTime(f + (Math.random() * 8 - 4), now + 2.0);
            
            osc.connect(gainNode);
            gainNode.connect(ctx.destination);
            
            gainNode.gain.setValueAtTime(0.001, now);
            gainNode.gain.linearRampToValueAtTime(0.12 / frequencies.length, now + 0.05); 
            gainNode.gain.exponentialRampToValueAtTime(0.001, now + 2.2 - (idx * 0.15)); 
            
            osc.start(now);
            osc.stop(now + 2.3);
        });

        // --- 2. REACTOR SWELL (Low-frequency warm sub-bass engine) ---
        const subOsc = ctx.createOscillator();
        const subGain = ctx.createGain();
        
        subOsc.type = 'triangle';
        subOsc.frequency.setValueAtTime(45, now);
        subOsc.frequency.exponentialRampToValueAtTime(85, now + 0.8);
        subOsc.frequency.exponentialRampToValueAtTime(30, now + 2.5);
        
        const subFilter = ctx.createBiquadFilter();
        subFilter.type = 'lowpass';
        subFilter.frequency.setValueAtTime(120, now);
        
        subOsc.connect(subFilter);
        subFilter.connect(subGain);
        subGain.connect(ctx.destination);
        
        subGain.gain.setValueAtTime(0.001, now);
        subGain.gain.linearRampToValueAtTime(0.45, now + 0.2); 
        subGain.gain.exponentialRampToValueAtTime(0.001, now + 2.5);
        
        subOsc.start(now);
        subOsc.stop(now + 2.6);

        // --- 3. SPACE WHOOSH (Filtered noise ambient wave) ---
        const bufferSize = ctx.sampleRate * 2.5;
        const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }
        
        const noiseNode = ctx.createBufferSource();
        noiseNode.buffer = buffer;
        
        const noiseFilter = ctx.createBiquadFilter();
        noiseFilter.type = 'lowpass';
        noiseFilter.frequency.setValueAtTime(80, now);
        noiseFilter.frequency.exponentialRampToValueAtTime(1200, now + 0.4); 
        noiseFilter.frequency.exponentialRampToValueAtTime(50, now + 2.2); 
        
        const noiseGain = ctx.createGain();
        noiseNode.connect(noiseFilter);
        noiseFilter.connect(noiseGain);
        noiseGain.connect(ctx.destination);
        
        noiseGain.gain.setValueAtTime(0.001, now);
        noiseGain.gain.linearRampToValueAtTime(0.25, now + 0.15); 
        noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 2.2);
        
        noiseNode.start(now);
        noiseNode.stop(now + 2.4);

    } catch (e) {
        console.warn("Web Audio API failed or restricted:", e);
    }
}

// Safely instantiate WebGL Application when DOM loads
window.addEventListener('DOMContentLoaded', () => {
    new Application();
});
