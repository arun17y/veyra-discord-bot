// web/public/js/eye.js - Veyra cybernetic eyeball mesh setup and material configuration
import * as THREE from 'three';
import { EyeShader } from './shaders/eyeShaders.js';

// Procedural Noise generator matching React Bits EvilEye
function generateNoiseTexture(size = 256) {
  const data = new Uint8Array(size * size * 4);

  function hash(x, y, s) {
    let n = x * 374761393 + y * 668265263 + s * 1274126177;
    n = Math.imul(n ^ (n >>> 13), 1274126177);
    return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
  }

  function noise(px, py, freq, seed) {
    const fx = (px / size) * freq;
    const fy = (py / size) * freq;
    const ix = Math.floor(fx);
    const iy = Math.floor(fy);
    const tx = fx - ix;
    const ty = fy - iy;
    const w = freq | 0;
    const v00 = hash(((ix % w) + w) % w, ((iy % w) + w) % w, seed);
    const v10 = hash((((ix + 1) % w) + w) % w, ((iy % w) + w) % w, seed);
    const v01 = hash(((ix % w) + w) % w, (((iy + 1) % w) + w) % w, seed);
    const v11 = hash((((ix + 1) % w) + w) % w, (((iy + 1) % w) + w) % w, seed);
    return v00 * (1 - tx) * (1 - ty) + v10 * tx * (1 - ty) + v01 * (1 - tx) * ty + v11 * tx * ty;
  }

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let v = 0;
      let amp = 0.4;
      let totalAmp = 0;
      for (let o = 0; o < 8; o++) {
        const f = 32 * (1 << o);
        v += amp * noise(x, y, f, o * 31);
        totalAmp += amp;
        amp *= 0.65;
      }
      v /= totalAmp;
      v = (v - 0.5) * 2.2 + 0.5;
      v = Math.max(0, Math.min(1, v));
      const val = Math.round(v * 255);
      const i = (y * size + x) * 4;
      data[i] = val;
      data[i + 1] = val;
      data[i + 2] = val;
      data[i + 3] = 255;
    }
  }

  return data;
}

export class VeyraEye {
    constructor(scene) {
        this.scene = scene;
        this.mesh = null;
        this.mouse = { x: 0, y: 0, tx: 0, ty: 0 };
        this.create();
        this.setupMouseTracking();
    }

    create() {
        this.group = new THREE.Group();

        // 1. Generate Noise Texture
        const noiseData = generateNoiseTexture(256);
        this.noiseTexture = new THREE.DataTexture(noiseData, 256, 256, THREE.RGBAFormat);
        this.noiseTexture.minFilter = THREE.LinearFilter;
        this.noiseTexture.magFilter = THREE.LinearFilter;
        this.noiseTexture.wrapS = THREE.RepeatWrapping;
        this.noiseTexture.wrapT = THREE.RepeatWrapping;
        this.noiseTexture.needsUpdate = true;

        // 2. Set Up Shader Material
        this.eyeMat = new THREE.ShaderMaterial({
            vertexShader: EyeShader.vertexShader,
            fragmentShader: EyeShader.fragmentShader,
            uniforms: {
                uTime: { value: 0 },
                uEyeOpen: { value: 0.0 },
                uBrightness: { value: 1.0 },
                uResolution: { value: new THREE.Vector3(window.innerWidth, window.innerHeight, window.innerWidth / window.innerHeight) },
                uNoiseTexture: { value: this.noiseTexture },
                uPupilSize: { value: 0.7 }, // pupilSize
                uIrisWidth: { value: 0.3 }, // irisWidth
                uGlowIntensity: { value: 0.35 }, // glowIntensity
                uIntensity: { value: 1.1 }, // intensity
                uScale: { value: 0.6 }, // scale
                uNoiseScale: { value: 1.0 }, // noiseScale
                uMouse: { value: new THREE.Vector2(0, 0) },
                uPupilFollow: { value: 1.0 }, // pupilFollow
                uFlameSpeed: { value: 1.0 }, // flameSpeed
                uEyeColor: { value: new THREE.Vector3(225.0 / 255.0, 0.0 / 255.0, 254.0 / 255.0) }, // #e100fe
                uBgColor: { value: new THREE.Vector3(0.0, 0.0, 0.0) } // #000000
            },
            transparent: true,
            depthWrite: false,
            side: THREE.DoubleSide
        });

        // 3. Flat Plane Geometry for 2D Shader Presentation
        const eyeGeo = new THREE.PlaneGeometry(3.5, 3.5);
        this.mesh = new THREE.Mesh(eyeGeo, this.eyeMat);
        this.group.add(this.mesh);

        this.scene.add(this.group);

        // Listen for resize to update uResolution
        window.addEventListener('resize', () => {
            if (this.eyeMat) {
                this.eyeMat.uniforms.uResolution.value.set(
                    window.innerWidth,
                    window.innerHeight,
                    window.innerWidth / window.innerHeight
                );
            }
        });
    }

    setupMouseTracking() {
        window.addEventListener('mousemove', (e) => {
            this.mouse.tx = (e.clientX / window.innerWidth) * 2 - 1;
            this.mouse.ty = -(e.clientY / window.innerHeight) * 2 + 1;
        }, { passive: true });

        window.addEventListener('mouseleave', () => {
            this.mouse.tx = 0;
            this.mouse.ty = 0;
        });
    }

    update(time) {
        // Smooth mouse coords interpolation
        this.mouse.x += (this.mouse.tx - this.mouse.x) * 0.08;
        this.mouse.y += (this.mouse.ty - this.mouse.y) * 0.08;

        if (this.eyeMat) {
            this.eyeMat.uniforms.uMouse.value.set(this.mouse.x, this.mouse.y);
            this.eyeMat.uniforms.uTime.value = time;
        }
    }
}
