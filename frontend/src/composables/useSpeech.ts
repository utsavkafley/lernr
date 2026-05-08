/**
 * Speak Spanish text aloud using the browser's SpeechSynthesis API.
 * Picks an es-* voice if available; falls back to whatever the browser
 * provides for `lang: 'es-ES'`.
 */
export function speakSpanish(text: string, opts: { rate?: number } = {}) {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return

  // Cancel anything currently being spoken so rapid Next clicks don't queue up.
  window.speechSynthesis.cancel()

  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'es-ES'
  utterance.rate = opts.rate ?? 0.85

  // Prefer a Spanish voice if one is available
  const voices = window.speechSynthesis.getVoices()
  const spanishVoice = voices.find((v) => v.lang.startsWith('es'))
  if (spanishVoice) utterance.voice = spanishVoice

  window.speechSynthesis.speak(utterance)
}
