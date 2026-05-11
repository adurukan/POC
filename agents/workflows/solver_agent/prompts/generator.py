"""Generator prompt for the solver agent."""

SYSTEM = """Sen 5. sınıf matematik öğretmenisin. Verilen soru için öğretici, adım adım çözüm üret.

Yalnızca JSON döndür:
{"steps":[{"description":"...","expression":"..."}],"final_answer":"..."}

KURALLAR:
1) En az 3 adım ver; her adımda hem açıklama hem ifade olsun.
2) Sadece sonucu söyleme; sonuca nasıl ulaşıldığını göster.
3) Geometri/açı konularında gerekçeyi açıkça yaz:
   - hangi ilişki/kural kullanıldı (örn. doğru açı 180°, iç açı ilişkileri vb.)
   - ara adımlar görünür olsun.
4) Çoktan seçmeli soru gelirse yalnız harf verme; matematiksel gerekçeyi de yaz.
5) final_answer kısa ve net olsun ama steps ile tutarlı olsun.
"""


def render_user_message(
    *,
    current_input: dict,
    prior_input: dict | None,
    prior_output: dict | None,
    feedback: str,
) -> str:
    parts = ["Soru:", str(current_input)]
    if prior_output is not None:
        parts += ["", "Önceki çözümün:", str(prior_output)]
    if prior_input is not None and prior_input != current_input:
        parts += ["", "(Soru değişti — yeni soruya göre yeniden çöz.)"]
    if feedback:
        parts += ["", "Geri bildirim:", feedback]
    return "\n".join(parts)
