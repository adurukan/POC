"""Feedback classifier prompt. PLACEHOLDER.

Splits a single Turkish teacher message into per-agent slices. Slices MUST be
verbatim — no paraphrasing — and a single message may legitimately target one,
two, or three agents at once.

Output JSON shape:
    {
      "targets": ["question"|"solver"|"game", ...],
      "slices":  {"question": "<verbatim slice>", ...}
    }
"""

SYSTEM = """Sen bir öğretmen geri bildirim sınıflandırıcısısın.

Verilen Türkçe geri bildirim mesajını üç ajan için ayrıştır:
- "question": soru üretimine yönelik geri bildirim
- "solver": çözüm adımlarına yönelik geri bildirim
- "game": p5.js oyunu/görselleştirmesine yönelik geri bildirim

KURAL: Dilimleri ASLA başka kelimelerle ifade etme — orijinal cümleyi/parçayı
KELİMESİ KELİMESİNE kopyala. Bir mesaj birden fazla ajanı hedefleyebilir.

JSON formatında yanıt ver:
{"targets": ["..."], "slices": {"question": "...", "solver": "...", "game": "..."}}

PLACEHOLDER — gerçek prompt follow-up planında tanımlanacak."""


def render_user_message(feedback_text: str) -> str:
    return f"Geri bildirim:\n{feedback_text}"
