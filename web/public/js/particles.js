// web/public/js/particles.js - Generates floating volumetric background particle system
import * as THREE from 'three';
import { ParticleShader } from './shaders/particleShaders.js';

export class ParticleSystem {
    constructor(scene) {
        this.scene = scene;
        this.count = 15000;
        this.create();
    }

    create() {
        this.geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(this.count * 3);
        const sizes = new Float32Array(this.count);
        const randoms = new Float32Array(this.count * 3);

        for (let i = 0; i < this.count; i++) {
            let r = 1.2 + Math.random() * 4.0;
            let theta = Math.random() * Math.PI * 2;
            let phi = Math.acos((Math.random() * 2) - 1);

            positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = r * Math.cos(phi);

            sizes[i] = Math.random() * 0.15 + 0.02;

            randoms[i * 3] = (Math.random() - 0.5) * 2;
            randoms[i * 3 + 1] = (Math.random() - 0.5) * 2;
            randoms[i * 3 + 2] = (Math.random() - 0.5) * 2;
        }

        this.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        this.geometry.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1));
        this.geometry.setAttribute('aRandoms', new THREE.BufferAttribute(randoms, 3));

        this.material = new THREE.ShaderMaterial({
            vertexShader: ParticleShader.vertexShader,
            fragmentShader: ParticleShader.fragmentShader,
            uniforms: {
                uTime: { value: 0 },
                uExplode: { value: 0.0 }
            },
            transparent: true,
            depthWrite: false,
            blending: THREE.AdditiveBlending
        });

        this.points = new THREE.Points(this.geometry, this.material);
        this.scene.add(this.points);
    }

    update(time) {
        if(this.material) this.material.uniforms.uTime.value = time;
    }
}
