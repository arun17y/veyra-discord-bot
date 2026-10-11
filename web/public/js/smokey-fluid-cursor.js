/* Dummy no-op file to globally deactivate the Smokey Fluid cursor */
const SmokyFluid = {
    initFluid: function(options) {
        console.log("[VEYRA] Smokey Fluid cursor deactivated globally.");
        // Hide the canvas if it exists to be completely clean
        if (options && options.id) {
            const canvas = document.getElementById(options.id);
            if (canvas) {
                canvas.style.display = 'none';
                canvas.remove();
            }
        }
    }
};
window.SmokyFluid = SmokyFluid;
