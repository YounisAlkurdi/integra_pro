High-Performance Canvas Frame Player
Category: Frontend / Web Engineering

Optimization: GPU-Accelerated / Zero-Latency Scrubbing

Use Case: Integra AI Identity Reveal (Morphing Sequence)

1. Overview
This skill replaces the heavy <video> tag with a Buffered Image Sequence rendered on an HTML5 <canvas>. It eliminates the "Keyframe-seeking" delay found in standard MP4 playback, allowing the user to scrub through the woman-to-robot transition with perfect fluidity.

2. Component Structure
Container: A sticky wrapper that keeps the canvas in view while the user scrolls.

Buffer: An array of pre-loaded Image objects stored in RAM.

Logic: A scroll-to-index mapping function synchronized with requestAnimationFrame.

3. Implementation Code
JavaScript
/**
 * INTEGRA SCROLL SKILL v1.0
 * Logic: Map PageScroll % to ImageSequence Index
 */

class FramePlayer {
    constructor(config) {
        this.canvas = document.getElementById(config.id);
        this.ctx = this.canvas.getContext('2d');
        this.totalFrames = config.totalFrames;
        this.frames = [];
        this.currentFrame = 0;
        this.init();
    }

    init() {
        // Step 1: Preload to RAM
        for (let i = 1; i <= this.totalFrames; i++) {
            const img = new Image();
            // Matching EZGIF naming convention (frame-001.jpg)
            img.src = `./frames/frame-${i.toString().padStart(3, '0')}.jpg`;
            this.frames.push(img);
        }
        
        // Step 2: Listen to Scroll
        window.addEventListener('scroll', () => this.onScroll());
        
        // Initial Draw
        this.frames[0].onload = () => this.draw(0);
    }

    onScroll() {
        const scrollPos = window.scrollY;
        const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
        const scrollPercent = scrollPos / maxScroll;
        
        const frameIndex = Math.floor(scrollPercent * (this.totalFrames - 1));
        
        if (frameIndex !== this.currentFrame) {
            this.currentFrame = frameIndex;
            requestAnimationFrame(() => this.draw(frameIndex));
        }
    }

    draw(index) {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.drawImage(this.frames[index], 0, 0, this.canvas.width, this.canvas.height);
    }
}

// Initialization
new FramePlayer({ id: 'integra-canvas', totalFrames: 80 });
4. Performance Checklist
[x] GOP-Independent: No dependence on video keyframes.

[x] Memory Safe: Images are loaded once and cached.

[x] CPU-Light: No active video decoders running in the background.

[x] Bi-Directional: Perfect smoothness when scrolling up (Rewind).

5. Deployment Notes
Assets: Ensure the frames/ folder contains all .jpg files extracted from the EZGIF ZIP.

Canvas Scale: Set canvas.width and canvas.height to match the source frames (1280x720) for 1:1 pixel rendering.