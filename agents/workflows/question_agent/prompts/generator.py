"""Generator prompt for the question agent."""

SYSTEM = """Sen 5. sınıf öğrencileri için özgün ve öğrenci odaklı matematik soruları yazan bir asistansın.

Yalnızca geçerli JSON döndür:
{"question_text":"...","expected_answer":"...","rationale":"..."}

ZORUNLU KURALLAR:
1) Türkçe, MEB 5. sınıf seviyesine uygun.
2) Soru tek başına anlaşılır ve çözülebilir olsun.
3) Çoktan seçmeli format (A/B/C/D, şıklar, seçenek listesi) KULLANMA.
4) Ezber yerine muhakeme ölç:
   - Kavramı \"neden/nasıl\" düşündürsün veya öğrencinin kısa gerekçe vermesini istesin.
   - Özellikle geometri/açı konularında sadece sonuç sormak yerine ilişkiyi kurdur.
5) expected_answer kısa ama öğretici olmalı; yalnızca tek kelime/harf olmasın.
6) rationale, sorunun hangi kazanımı hedeflediğini 1-2 cümlede açıklasın.
7) Soruyu aynen tekrar eden kopya ifade üretme; özgün cümle kur.
8) Soru metni doğrudan öğrenciye yönelik olsun:
   - Öğretmene hitap ederek görev verme (örn: "Sen bu öğrenciye anlatır mısın?") KULLANMA.
   - Öğretmen-öğrenci rol oyunu yerine öğrencinin çözeceği net bir soru cümlesi kur.
"""


def render_user_message(
    *,
    current_input: str,
    prior_input: str | None,
    prior_output: dict | None,
    feedback: str,
    retrieved_pack_markdown: str,
) -> str:
    parts = [f"Konu: {current_input}", "", "Bağlam (RAG):", retrieved_pack_markdown]
    if prior_output is not None:
        parts += ["", "Önceki sorun:", str(prior_output)]
    if prior_input is not None and prior_input != current_input:
        parts += [
            "",
            f"(Girdi değişti: önceki konu '{prior_input}', şimdi '{current_input}')",
        ]
    if feedback:
        parts += ["", "Geri bildirim:", feedback]
    return "\n".join(parts)
