import torch
import cv2
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg') # ضروري لعمل الرسومات خلف الكواليس
import matplotlib.pyplot as plt
import io
import base64
from transformers import ViTForImageClassification, ViTImageProcessor
from facenet_pytorch import MTCNN

class FullDeepfakeDetector:
    def __init__(self):
        # تم استخدام نفس الموديل والمعايير من ملفك الأصلي
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model_id = 'prithivMLmods/Deep-Fake-Detector-v2-Model'
        
        print(f'⏳ Loading ViT from HuggingFace on {self.device}...')
        self.processor = ViTImageProcessor.from_pretrained(self.model_id)
        self.model = ViTForImageClassification.from_pretrained(self.model_id).to(self.device)
        self.model.eval()
        
        print('⏳ Loading MTCNN...')
        self.mtcnn = MTCNN(image_size=224, margin=20, keep_all=False, device=self.device)

    @torch.no_grad()
    def predict_face(self, pil_face):
        inputs = self.processor(images=pil_face, return_tensors='pt').to(self.device)
        logits = self.model(**inputs).logits
        probs  = torch.softmax(logits, dim=1)[0]
        pred   = torch.argmax(probs).item()
        label  = self.model.config.id2label[pred]
        
        # منطق توحيد الـ Fake Probability من ملفك الأصلي
        fake_idx = [k for k,v in self.model.config.id2label.items() if 'deep' in v.lower() or 'fake' in v.lower()]
        fake_prob = probs[fake_idx[0]].item() if fake_idx else probs[pred].item()
        return label, fake_prob

    def analyze(self, video_path):
        cap = cv2.VideoCapture(video_path)
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            interval = max(1, int(fps * 0.5)) # فريم كل نص ثانية كما طلبت
            MAX_FRAMES = 60

            results, faces_shown = [], []
            frame_idx, analyzed = 0, 0

            while analyzed < MAX_FRAMES:
                ret, frame = cap.read()
                if not ret: break
                frame_idx += 1
                if frame_idx % interval != 0: continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)

                try:
                    boxes, _ = self.mtcnn.detect(pil_img)
                    if boxes is None: continue
                    x1,y1,x2,y2 = [max(0,int(v)) for v in boxes[0]]
                    face_pil = pil_img.crop((x1,y1,x2,y2)).resize((224,224))
                except: continue

                label, fake_prob = self.predict_face(face_pil)
                results.append({'frame': frame_idx, 'time': frame_idx/fps, 'label': label, 'fake_prob': fake_prob})
                
                if len(faces_shown) < 8:
                    faces_shown.append((face_pil, label, fake_prob, frame_idx/fps))
                analyzed += 1
        finally:
            cap.release() # تحرير الملف فوراً لويندوز

        if not results:
            return {"error": "لم يتم اكتشاف أي وجه في الفيديو!"}

        # --- الحسابات (نفس منطق الخلية 5 بزبط) ---
        scores  = np.array([r['fake_prob'] for r in results])
        times   = np.array([r['time']      for r in results])
        mean_sc = scores.mean()
        high_pct = (scores > 0.60).mean() * 100

        # المعادلة المجمعة الأصلية: 60% للمتوسط و 40% للفريمات العالية
        final = mean_sc * 0.6 + (high_pct/100) * 0.4

        # حدود الحكم الأصلية (0.35 و 0.55)
        if   final < 0.35: verdict='REAL'; vc='#22c55e'
        elif final < 0.55: verdict='UNCERTAIN'; vc='#f59e0b'
        else:              verdict='DEEPFAKE'; vc='#ef4444'

        # --- توليد الرسومات بنفس ثيم الألوان الغامق (Dark Theme) ---
        BG, SFC = '#0f172a', '#1e293b'
        fig = plt.figure(figsize=(14, 8))
        fig.patch.set_facecolor(BG)

        # 1. الرسم البياني (Score Over Time)
        ax1 = plt.subplot(2, 2, 1)
        ax1.set_facecolor(SFC)
        ax1.fill_between(times, scores, alpha=0.2, color=vc)
        ax1.plot(times, scores, color='white', lw=1.5)
        ax1.axhline(0.55, color='#ef4444', ls='--', lw=1.2, alpha=0.8)
        ax1.axhline(0.35, color='#f59e0b', ls='--', lw=1.2, alpha=0.8)
        ax1.set_ylim(0, 1)
        ax1.set_title('ViT Deepfake Score — Time', color='#f1f5f9')
        ax1.tick_params(colors='#cbd5e1')

        # 2. التوزيع التكراري (Distribution)
        ax2 = plt.subplot(2, 2, 2)
        ax2.set_facecolor(SFC)
        n, bins, patches_list = ax2.hist(scores, bins=min(20, len(scores)), edgecolor='#1e293b')
        for patch, left in zip(patches_list, bins[:-1]):
            patch.set_facecolor('#ef4444' if left>0.55 else '#f59e0b' if left>0.35 else '#22c55e')
        ax2.set_title('Score Distribution', color='#f1f5f9')
        ax2.tick_params(colors='#cbd5e1')

        # 3. الوجوه المحللة (نفس طريقة العرض الأصلية)
        n_faces = len(faces_shown)
        if n_faces > 0:
            cols = min(4, n_faces)
            for i in range(n_faces):
                ax = plt.subplot(4, cols, 8 + i + 1)
                ax.set_facecolor(SFC); ax.axis('off')
                face, lbl, prob, t = faces_shown[i]
                c = '#ef4444' if prob>0.55 else '#f59e0b' if prob>0.35 else '#22c55e'
                ax.imshow(face)
                ax.set_title(f'{prob*100:.0f}% t={t:.1f}s', color=c, fontsize=8, fontweight='bold')

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, facecolor=BG)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

        return {
            "verdict": verdict,
            "final_score": round(final * 100, 1),
            "mean_sc": round(mean_sc * 100, 1),
            "high_pct": round(high_pct, 1),
            "frames_analyzed": len(results),
            "report_image": img_base64
        }