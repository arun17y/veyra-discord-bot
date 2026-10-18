// web/public/js/shaders/eyeShaders.js - Shaders for EvilEye purple-chrome rendering
export const EyeShader = {
    vertexShader: `
        varying vec2 vUv;
        varying vec3 vNormal;
        varying vec3 vViewPosition;
        
        void main() {
            vUv = uv;
            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            vNormal = normalize(normalMatrix * normal);
            vViewPosition = -mvPosition.xyz;
            gl_Position = projectionMatrix * mvPosition;
        }
    `,
    fragmentShader: `
        uniform float uTime;
        uniform float uEyeOpen;
        uniform float uBrightness;
        uniform vec3 uResolution;
        uniform sampler2D uNoiseTexture;
        uniform float uPupilSize;
        uniform float uIrisWidth;
        uniform float uGlowIntensity;
        uniform float uIntensity;
        uniform float uScale;
        uniform float uNoiseScale;
        uniform vec2 uMouse;
        uniform float uPupilFollow;
        uniform float uFlameSpeed;
        uniform vec3 uEyeColor;
        uniform vec3 uBgColor;
        varying vec2 vUv;

        void main() {
            // Eyelid crop animation logic
            float halfOpen = uEyeOpen * 0.5;
            if (vUv.y > (0.5 + halfOpen) || vUv.y < (0.5 - halfOpen)) {
                discard; 
            }

            // Map coordinate space centered at (0, 0)
            vec2 uv = (vUv * 2.0 - 1.0) * vec2(uResolution.z, 1.0);
            uv /= uScale;
            float ft = uTime * uFlameSpeed;

            float polarRadius = length(uv) * 2.0;
            float polarAngle = (2.0 * atan(uv.x, uv.y)) / 6.28 * 0.3;
            vec2 polarUv = vec2(polarRadius, polarAngle);

            vec4 noiseA = texture2D(uNoiseTexture, polarUv * vec2(0.2, 7.0) * uNoiseScale + vec2(-ft * 0.1, 0.0));
            vec4 noiseB = texture2D(uNoiseTexture, polarUv * vec2(0.3, 4.0) * uNoiseScale + vec2(-ft * 0.2, 0.0));
            vec4 noiseC = texture2D(uNoiseTexture, polarUv * vec2(0.1, 5.0) * uNoiseScale + vec2(-ft * 0.1, 0.0));

            float distanceMask = 1.0 - length(uv);

            // Inner ring
            float innerRing = clamp(-1.0 * ((distanceMask - 0.7) / uIrisWidth), 0.0, 1.0);
            innerRing = (innerRing * distanceMask - 0.2) / 0.28;
            innerRing += noiseA.r - 0.5;
            innerRing *= 1.3;
            innerRing = clamp(innerRing, 0.0, 1.0);

            float outerRing = clamp(-1.0 * ((distanceMask - 0.5) / 0.2), 0.0, 1.0);
            outerRing = (outerRing * distanceMask - 0.1) / 0.38;
            outerRing += noiseC.r - 0.5;
            outerRing *= 1.3;
            outerRing = clamp(outerRing, 0.0, 1.0);

            innerRing += outerRing;

            // Inner eye
            float innerEye = distanceMask - 0.1 * 2.0;
            innerEye *= noiseB.r * 2.0;

            // Pupil with cursor tracking
            vec2 pupilOffset = uMouse * uPupilFollow * 0.12;
            vec2 pupilUv = uv - pupilOffset;
            float pupil = 1.0 - length(pupilUv * vec2(9.0, 2.3));
            pupil *= uPupilSize;
            pupil = clamp(pupil, 0.0, 1.0);
            pupil /= 0.35;

            // Outer eye
            float outerEyeGlow = 1.0 - length(uv * vec2(0.5, 1.5));
            outerEyeGlow = clamp(outerEyeGlow + 0.5, 0.0, 1.0);
            outerEyeGlow += noiseC.r - 0.5;
            float outerBgGlow = outerEyeGlow;
            outerEyeGlow = pow(outerEyeGlow, 2.0);
            outerEyeGlow += distanceMask;
            outerEyeGlow *= uGlowIntensity;
            outerEyeGlow = clamp(outerEyeGlow, 0.0, 1.0);
            outerEyeGlow *= pow(1.0 - distanceMask, 2.0) * 2.5;

            // Outer eye bg glow
            outerBgGlow += distanceMask;
            outerBgGlow = pow(outerBgGlow, 0.5);
            outerBgGlow *= 0.15;

            // Calculate eye color intensity (excluding pupil core)
            vec3 color = uEyeColor * uIntensity * clamp(max(innerRing + innerEye, outerEyeGlow + outerBgGlow) - pupil, 0.0, 3.0);

            // Compute transparency alpha dynamically based on shape and glow bounds
            float alpha = clamp(max(innerRing + innerEye, outerEyeGlow * 1.5) - pupil * 0.5, 0.0, 1.0);

            // Apply flash/explosion brightness flare multiplier
            color *= uBrightness;

            gl_FragColor = vec4(color, alpha);
        }
    `
};
