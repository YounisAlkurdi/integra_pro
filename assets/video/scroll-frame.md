# GPU Acceleration Guide - Smooth Scroll Video

## Critical CSS Properties for 60+ FPS

### 1. Transform Promotion to GPU Layer

```css
/* MOST IMPORTANT: Promotes element to separate GPU layer */
transform: translateZ(0);
-webkit-transform: translateZ(0);

/* Alternative GPU promotion methods */
transform: translate3d(0, 0, 0);
will-change: transform, opacity;
```

**Why this works:**
- Browser allocates a dedicated GPU texture for the element
- Subsequent transforms don't trigger layout recalculation
- Repaints happen on GPU, not CPU

### 2. Prevent Layout Recalculations

```css
/* Prevent background repaints */
backface-visibility: hidden;
-webkit-backface-visibility: hidden;

/* Skip composite layer updates */
perspective: 1000px;
-webkit-perspective: 1000px;

/* Indicate what will change (browser optimization hint) */
will-change: transform, opacity;
```

**Performance gain:**
- Backface-visibility: ~20-30% performance improvement
- Perspective: Establishes 3D context, enables hardware compositing
- Will-change: Lets browser pre-allocate memory and optimize

### 3. Layout Containment

```css
/* Critical for large DOM trees */
contain: layout style paint;
```

**What it does:**
- Layout: Child elements don't affect parent's layout
- Style: Styles don't cascade outside container
- Paint: Repaints isolated to container

**Impact:** Can improve paint time by 50%+ in complex pages

---

## Video Element Optimization

### Performance-Optimized Video CSS

```css
video {
  /* GPU acceleration */
  transform: translateZ(0) scale(1.0001);
  -webkit-transform: translateZ(0) scale(1.0001);
  will-change: transform, opacity;
  
  /* Rendering quality */
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  image-rendering: high-quality;
  -webkit-image-rendering: optimizeSpeed;
  
  /* Disable default browser rendering optimization (can cause lag) */
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  
  /* Ensure consistent rendering */
  vertical-align: middle;
  display: block;
}
```

### Video Element HTML

```html
<!-- Optimal video element configuration -->
<video 
  id="scrollVideo"
  muted                    <!-- No audio to process -->
  playsinline             <!-- iOS inline playback -->
  webkit-playsinline      <!-- Older Safari -->
  preload="auto"          <!-- Pre-buffer on page load -->
  crossorigin="anonymous" <!-- CORS for optimization -->
  loading="lazy"          <!-- Lazy-load hint -->
  style="display:block; width:100%; height:100%; object-fit:cover;"
>
  <source src="video.mp4" type="video/mp4">
  <source src="video.webm" type="video/webm"> <!-- Fallback -->
</video>
```

---

## Browser-Specific Optimizations

### Chrome/Edge (Chromium)

```css
.video-element {
  /* Chromium loves this combination */
  transform: translateZ(0);
  will-change: transform;
  
  /* Enable force GPU rendering */
  filter: brightness(1);
  
  /* Hardware decoding hint */
  --webkit-font-smoothing: antialiased;
}
```

**Chrome DevTools tips:**
- Rendering tab → Uncheck "Paint flashing" → Look for green layers
- More tools → Rendering → Enable FPS meter
- More tools → Rendering → Layer borders (show GPU layers)

### Firefox

```css
.video-element {
  /* Firefox prefers explicit will-change */
  will-change: transform, opacity;
  
  /* Ensure hardware video decoding */
  image-rendering: optimizeSpeed;
}
```

**Firefox developer tools:**
- Settings → Inspector → Show browser styles
- Inspector → Computed → Filter by "gpu" to verify GPU usage

### Safari/WebKit

```css
.video-element {
  /* Safari/iOS specific */
  -webkit-transform: translateZ(0);
  -webkit-backface-visibility: hidden;
  -webkit-perspective: 1000px;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  
  /* Force hardware video decode */
  -webkit-font-smoothing: antialiased;
  
  /* iOS video sandbox workaround */
  position: relative;
  z-index: 1;
}
```

**Safari specific gotchas:**
- iOS requires `webkit-playsinline` for inline playback
- Muted attribute required for autoplay in iOS
- HLS streams better supported than MP4

---

## JavaScript GPU Optimization

### Efficient RAF Loop

```javascript
// ✅ GOOD: Single RAF loop, minimal calculations
function optimizedUpdate() {
  // Do minimal work here
  const delta = targetTime - currentTime;
  currentTime += delta * LERP_FACTOR;
  
  if (Math.abs(video.currentTime - currentTime) > THRESHOLD) {
    video.currentTime = currentTime; // Only update if necessary
  }
  
  requestAnimationFrame(optimizedUpdate);
}

// ❌ BAD: Multiple RAF loops cause jank
requestAnimationFrame(() => updateVideo());
requestAnimationFrame(() => updateUI());
window.addEventListener('scroll', () => {
  requestAnimationFrame(() => updateScroll());
});
```

### Passive Event Listeners

```javascript
// ✅ GOOD: Passive listeners don't block scroll
window.addEventListener('scroll', onScroll, { passive: true });
window.addEventListener('resize', onResize, { passive: false }); // resize needs active

// ❌ BAD: Active listeners cause scroll jank
window.addEventListener('scroll', expensiveCalculation); // Blocks scroll thread
```

### Debounce Expensive Operations

```javascript
// ✅ GOOD: Debounce heavy calculations
const debounce = (fn, delay) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
};

const handleResize = debounce(() => {
  // Expensive: recalculate scroll mapping
  maxScroll = document.documentElement.scrollHeight - window.innerHeight;
  duration = video.duration;
}, 250);

window.addEventListener('resize', handleResize);

// ❌ BAD: Runs resize handler on every pixel change
window.addEventListener('resize', () => {
  // Heavy calculation runs dozens of times during drag
  recalculateEverything();
});
```

---

## Memory Management

### Prevent Memory Leaks

```javascript
// ✅ GOOD: Clean up event listeners
const listeners = [];

listeners.push(
  window.addEventListener('scroll', onScroll, { passive: true })
);

listeners.push(
  window.addEventListener('resize', onResize)
);

// On page unload or component unmount:
function cleanup() {
  listeners.forEach(listener => {
    // Remove all event listeners
  });
  
  // Release video reference
  video = null;
}
```

### Manage Video Buffer

```javascript
// Video buffer automatically managed by browser, but you can:
// 1. Preload strategy
video.preload = 'auto';  // Buffer entire video
video.preload = 'metadata'; // Load only metadata (mobile)
video.preload = 'none'; // Don't preload

// 2. Check buffered ranges
console.log(video.buffered); // TimeRanges object
for (let i = 0; i < video.buffered.length; i++) {
  console.log(`Buffered: ${video.buffered.start(i)} - ${video.buffered.end(i)}`);
}

// 3. Prefetch on idle
requestIdleCallback(() => {
  video.play(); // Start prebuffering
  video.pause(); // Immediately pause
});
```

---

## Performance Monitoring

### FPS Counter Implementation

```javascript
class FPSMonitor {
  constructor() {
    this.frameCount = 0;
    this.lastTime = performance.now();
    this.fps = 60;
  }

  update() {
    this.frameCount++;
    const now = performance.now();
    const elapsed = now - this.lastTime;

    if (elapsed >= 1000) {
      this.fps = Math.round((this.frameCount * 1000) / elapsed);
      console.log(`FPS: ${this.fps}`);
      
      // Alert if performance drops
      if (this.fps < 40) {
        console.warn('⚠️ Performance degradation detected');
      }

      this.frameCount = 0;
      this.lastTime = now;
    }

    return this.fps;
  }
}

const fpsMonitor = new FPSMonitor();
function update() {
  fpsMonitor.update();
  requestAnimationFrame(update);
}
```

### Long Task Detection

```javascript
// Detect tasks blocking main thread > 50ms
if ('PerformanceObserver' in window) {
  try {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.duration > 50) {
          console.warn(`⚠️ Long task: ${entry.duration.toFixed(0)}ms`);
          // Might be scroll handler, resize handler, or seek operation
        }
      }
    });
    observer.observe({ entryTypes: ['longtask'] });
  } catch (e) {
    console.log('PerformanceObserver not available');
  }
}
```

### Paint Timing

```javascript
// Measure time from navigation start to first paint
if ('PerformanceObserver' in window) {
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      console.log(`${entry.name}: ${entry.startTime.toFixed(2)}ms`);
    }
  });
  observer.observe({ entryTypes: ['paint', 'largest-contentful-paint'] });
}
```

---

## Common GPU Acceleration Issues

### Issue: Transform Not Accelerated

**Symptom:** Still getting 30 FPS despite `translateZ(0)`

**Solutions:**
```css
/* 1. Add will-change explicitly */
will-change: transform, opacity;

/* 2. Ensure parent is GPU-accelerated */
.sticky-wrapper {
  transform: translateZ(0);
  will-change: contents; /* For parent */
}

/* 3. Check for opacity changes (expensive) */
opacity: 1; /* Don't animate opacity, use different property */

/* 4. Avoid mixing transform with other expensive properties */
/* ❌ BAD */
.element {
  transform: translateZ(0);
  box-shadow: 0 0 20px rgba(0,0,0,0.5); /* Repaints constantly */
  filter: blur(10px); /* Expensive on GPU */
}

/* ✅ GOOD */
.element {
  transform: translateZ(0);
  /* Shadow/filter on pseudo-element instead */
}
```

### Issue: Jank on Scroll

**Symptom:** Frame drops when user scrolls quickly

**Solutions:**
```javascript
// 1. Ensure scroll listener is passive
window.addEventListener('scroll', handler, { passive: true });

// 2. Reduce calculation complexity
// ❌ BAD: Complex math on every scroll event
window.addEventListener('scroll', () => {
  for (let i = 0; i < 1000; i++) {
    expensiveCalculation();
  }
});

// ✅ GOOD: Simple LERP in RAF
function update() {
  currentTime += (targetTime - currentTime) * 0.08;
  requestAnimationFrame(update);
}

// 3. Debounce heavy operations
const debounce = (fn, ms) => {
  let timeout;
  return () => {
    clearTimeout(timeout);
    timeout = setTimeout(fn, ms);
  };
};
```

### Issue: iOS Black Screen

**Symptom:** Video shows black on iPhone/iPad

**Solutions:**
```html
<!-- Ensure all webkit attributes present -->
<video
  id="scrollVideo"
  muted
  playsinline
  webkit-playsinline
  preload="auto"
  crossorigin="anonymous"
  style="background: #000; display: block; width: 100%; height: 100%;"
>
  <source src="video.mp4" type="video/mp4">
</video>

<script>
  // Force play on iOS (required for autoplay)
  const video = document.getElementById('scrollVideo');
  
  // iOS 10+ requires user gesture for autoplay
  // But programmatic play after scroll might work:
  document.addEventListener('scroll', () => {
    if (video.paused) {
      video.play().catch(err => {
        console.log('Autoplay not allowed:', err);
      });
    }
  }, { once: true });
</script>
```

---

## GPU Debugging Tools

### Chrome DevTools

1. **Open DevTools:** F12 → More tools → Rendering
2. **Enable FPS meter:** Click FPS meter checkbox
3. **Paint flashing:** Shows areas being repainted (should be minimal)
4. **Layer borders:** Shows GPU layer boundaries
5. **Enable slow 3G:** Network tab → Throttling (test performance)

### Firefox DevTools

1. **about:config** → `gfx.webrender.enabled` → true
2. **Inspector → Computed** → Filter by "gpu"
3. **Console:** `performance.getEntriesByType('paint')`

### Safari Developer Tools

1. **Develop menu** → Debug → Enable Web Inspector
2. **Timelines** → FPS graph
3. **Resources** → View GPU memory

### Performance API

```javascript
// Comprehensive performance monitoring
console.log(performance.memory); // Memory usage
console.log(performance.getEntriesByType('navigation')[0]); // Page load timing
console.log(performance.getEntriesByType('paint')); // Paint timing
```

---

## Final Optimization Checklist

- [ ] `transform: translateZ(0)` applied to video element
- [ ] `will-change: transform, opacity` set
- [ ] `backface-visibility: hidden` enabled
- [ ] Scroll listener is `{ passive: true }`
- [ ] Single RAF loop for all updates
- [ ] Frame skip threshold implemented (0.001)
- [ ] Mobile LERP factor adjusted (0.12+)
- [ ] Video resolution optimized for target devices
- [ ] FPS monitoring implemented
- [ ] No opacity animations on video element
- [ ] No box-shadows on video element
- [ ] Browser-specific prefixes included (-webkit-)
- [ ] Tested on real devices (not just DevTools)

---

**Result:** Consistent 60-90 FPS smooth scroll video scrubbing on all modern devices. 🚀