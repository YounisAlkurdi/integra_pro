// ╔══════════════════════════════════════════════════════════════╗
// ║      ملف إعدادات الموديلات — مأخوذ من D:\Voiser\tts         ║
// ║         غيّر هون براحتك بدون ما تلمس باقي الكود             ║
// ╚══════════════════════════════════════════════════════════════╝

window.PROVIDER_MODELS = {
  openai: [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "o1",
    "o1-mini",
    "o3-mini",
  ],

  anthropic: [
    "claude-opus-4-5",
    "claude-sonnet-4-5",
    "claude-haiku-3-5",
    "claude-3-7-sonnet-latest",
    "claude-3-5-sonnet-20241022",
  ],

  google: [
    "gemini-3.1-flash-live-preview",
    "gemini-3.1-pro-preview",
    "gemini-2.5-pro",
    "gemini-pro-latest",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
  ],

  groq: [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "deepseek-r1-distill-llama-70b",
  ],
};

// قائمة نماذج HuggingFace الشائعة
window.HF_MODELS = [
  "mistralai/Mistral-7B-Instruct-v0.3",
  "mistralai/Mixtral-8x7B-Instruct-v0.1",
  "meta-llama/Meta-Llama-3-8B-Instruct",
  "Qwen/Qwen2.5-7B-Instruct",
  "google/gemma-2-9b-it",
];
