// web/public/js/shaders/particleShaders.js - Shader for purple volumetric entry particles explosion
export const ParticleShader = {
    vertexShader: `
        uniform float uTime;
        uniform float uExplode;
        attribute float aSize;
        attribute vec3 aRandoms;
        varying float vAlpha;
        varying vec3 vColor;

        void main() {
            vec3 pos = position;
            
            // Organic subtle ambient float
            pos.x += sin(uTime * aRandoms.x + aRandoms.y) * 0.15;
            pos.y += cos(uTime * aRandoms.y + aRandoms.z) * 0.25;
            pos.z += sin(uTime * aRandoms.z + aRandoms.x) * 0.15;

            // Explosion dynamic simulation matrix
            if (uExplode > 0.0) {
                pos += aRandoms * uExplode * 35.0;
            }

            vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
            gl_Position = projectionMatrix * mvPosition;
            
            // Distance attenuation computations
            gl_PointSize = aSize * (300.0 / -mvPosition.z);
            
            vAlpha = smoothstep(0.0, 0.2, aSize) * (1.0 - (uExplode * 0.4));
            // Shift colors to purple/violet sparks
            vColor = vec3(0.65, 0.15, 1.0) * (aRandoms.x * 0.4 + 0.6) + vec3(0.05, 0.05, 0.1);
        }
    `,
    fragmentShader: `
        varying float vAlpha;
        varying vec3 vColor;

        void main() {
            // Transform square particles into anti-aliased mathematical point circles
            float dist = length(gl_PointCoord - vec2(0.5));
            if (dist > 0.5) discard;
            
            float intensity = smoothstep(0.5, 0.0, dist);
            gl_FragColor = vec4(vColor, vAlpha * intensity);
        }
    `
};
