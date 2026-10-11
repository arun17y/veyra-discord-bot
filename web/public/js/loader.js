// web/public/js/loader.js - Handles structural loading fallback routines
export class AssetLoader {
    constructor() {
        this.isReady = true;
    }
    async loadAll() {
        return new Promise((resolve) => setTimeout(resolve, 100));
    }
}
