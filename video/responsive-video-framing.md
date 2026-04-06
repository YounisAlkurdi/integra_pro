# Skill: Responsive Video Framing

## Metadata
- **Category:** UI/UX Components
- **Framework:** Framer / Tailwind / React
- **Compatibility:** HTML5 Video, MP4, WebM
- **Performance Target:** 60+ FPS

---

## What This Skill Does
Creates a responsive, GPU-accelerated video container that:
- Locks aspect ratio without distortion (`object-fit: cover`)
- Promotes the video to a dedicated GPU layer for smooth rendering
- Prevents layout recalculations on scroll or resize
- Works across Chrome, Firefox, and Safari/iOS

---

## When to Use
- Hero sections with background video
- Scroll-driven video scrubbing
- Any video that needs to fill a container at a fixed ratio
- Video cards, thumbnails, or modals

---

## Code Snippet

### Tailwind / HTML
```html
<div class="relative w-full aspect-video overflow-hidden rounded-2xl border-2 border-white/10"
     style="contain: layout style paint; transform: translateZ(0);">
  <video
    class="absolute inset-0 w-full h-full object-cover"
    muted
    playsinline
    webkit-playsinline
    preload="auto"
    loop
    style="
      transform: translateZ(0);
      will-change: transform, opacity;
      backface-visibility: hidden;
      -webkit-backface-visibility: hidden;
      display: block;
    "
  >
    <source src="your-video.mp4"  type="video/mp4">
    <source src="your-video.webm" type="video/webm">
  </video>
</div>
```

### React Component
```jsx
export function VideoFrame({ src, webmSrc, className = "" }) {
  return (
    <div
      className={`relative w-full aspect-video overflow-hidden rounded-2xl border-2 border-white/10 ${className}`}
      style={{ contain: "layout style paint", transform: "translateZ(0)" }}
    >
      <video
        className="absolute inset-0 w-full h-full object-cover"
        muted
        playsInline
        preload="auto"
        loop
        style={{
          transform: "translateZ(0)",
          willChange: "transform, opacity",
          backfaceVisibility: "hidden",
          WebkitBackfaceVisibility: "hidden",
          display: "block",
        }}
      >
        {webmSrc && <source src={webmSrc} type="video/webm" />}
        <source src={src} type="video/mp4" />
      </video>
    </div>
  );
}
```

---

## Why Each Property

| Property | Reason |
|---|---|
| `transform: translateZ(0)` | Promotes element to GPU layer |
| `will-change: transform, opacity` | Browser pre-allocates memory |
| `backface-visibility: hidden` | Prevents unnecessary repaints (~20-30% gain) |
| `contain: layout style paint` | Isolates repaints to container (~50% paint improvement) |
| `playsinline` + `webkit-playsinline` | Required for iOS inline playback |
| `muted` | Required for autoplay in all browsers |
| `preload="auto"` | Pre-buffers video on page load |
| WebM source first | Better compression, fallback to MP4 |

---

## Common Pitfalls

- ❌ Don't add `box-shadow` or `filter` directly on the video — causes constant repaints
- ❌ Don't animate `opacity` on the video element
- ❌ Missing `muted` will break autoplay on Chrome and iOS
- ❌ Missing `playsinline` causes fullscreen takeover on iPhone
- ✅ Always provide both `.webm` and `.mp4` sources

---

## Checklist
- [ ] `transform: translateZ(0)` on video and wrapper
- [ ] `will-change` set
- [ ] `backface-visibility: hidden` enabled
- [ ] `muted` + `playsinline` + `webkit-playsinline` present
- [ ] Both MP4 and WebM sources provided
- [ ] `contain: layout style paint` on wrapper
- [ ] Tested on real iOS device (not just DevTools)
