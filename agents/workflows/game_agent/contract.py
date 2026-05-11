"""Game artifact contract + deterministic validation helpers.

This module defines the structured game artifact shape expected from the game
agent and lightweight deterministic checks used before qualitative LLM review.
"""

from __future__ import annotations

import re
from typing import Any

ALLOWED_GAME_TYPES = {"manipulation", "button_step", "mixed"}
TARGET_PANEL = "top_right_30pct"
# Conservative defaults for embedding into a smaller UI pane.
MAX_CANVAS_WIDTH = 640
MAX_CANVAS_HEIGHT = 420
MIN_CANVAS_WIDTH = 320
MIN_CANVAS_HEIGHT = 220
MIN_BOX_WIDTH = 24
MIN_BOX_HEIGHT = 20

_EVENT_HOOKS = (
    "mousePressed",
    "mouseDragged",
    "mouseReleased",
    "mouseClicked",
    "touchStarted",
    "touchMoved",
    "touchEnded",
    "keyPressed",
    "keyTyped",
    "keyReleased",
)

# Common patterns for static quiz replicas we want to block.
# Keep these strict to avoid false positives in raw JS code (e.g. "cos(a)").
_QUIZ_PATTERNS = [
    r"(?m)^\s*[A-D]\)\s+\S",
    r"(?m)^\s*\d+\)\s+\S",
    r"\bşık\b",
    r"\bseçenek\b",
    r"\bdoğru seçenek\b",
    r"\bmultiple\s*choice\b",
    r"\boption\b",
]


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_str_list(value: Any) -> bool:
    return (
        isinstance(value, list) and value and all(_is_non_empty_str(v) for v in value)
    )


def validate_game_artifact_schema(artifact: dict) -> list[str]:
    """Validate required fields + nested shape.

    We keep the contract strict to make downstream UI integration predictable.
    """
    errors: list[str] = []

    if not isinstance(artifact.get("should_render"), bool):
        errors.append("should_render alanı boolean olmalı.")

    should_render = bool(artifact.get("should_render"))

    if not _is_non_empty_str(artifact.get("game_type")):
        errors.append("game_type zorunlu bir string olmalı.")
    elif artifact["game_type"] not in ALLOWED_GAME_TYPES:
        errors.append(
            "game_type 'manipulation'|'button_step'|'mixed' değerlerinden biri olmalı."
        )

    for key in (
        "learning_goal",
        "instructions_short",
        "success_condition",
        "rationale",
    ):
        if not _is_non_empty_str(artifact.get(key)):
            errors.append(f"{key} zorunlu ve boş olmayan string olmalı.")

    interaction_model = artifact.get("interaction_model")
    if not isinstance(interaction_model, dict):
        errors.append("interaction_model nesne olmalı.")
    else:
        for key in ("inputs", "affordances", "user_actions"):
            if not _is_str_list(interaction_model.get(key)):
                errors.append(
                    f"interaction_model.{key} boş olmayan string listesi olmalı."
                )

    feedback_model = artifact.get("feedback_model")
    if not isinstance(feedback_model, dict):
        errors.append("feedback_model nesne olmalı.")
    else:
        if not _is_non_empty_str(feedback_model.get("on_correct")):
            errors.append("feedback_model.on_correct zorunlu string olmalı.")
        if not _is_non_empty_str(feedback_model.get("on_incorrect")):
            errors.append("feedback_model.on_incorrect zorunlu string olmalı.")

    state_model = artifact.get("state_model")
    if not isinstance(state_model, dict):
        errors.append("state_model nesne olmalı.")
    elif not _is_str_list(state_model.get("tracked_vars")):
        errors.append("state_model.tracked_vars boş olmayan string listesi olmalı.")

    layout_model = artifact.get("layout_model")
    if not isinstance(layout_model, dict):
        errors.append("layout_model nesne olmalı.")
    else:
        if layout_model.get("target_panel") != TARGET_PANEL:
            errors.append(f"layout_model.target_panel '{TARGET_PANEL}' olmalı.")
        if not isinstance(layout_model.get("canvas_width"), int):
            errors.append("layout_model.canvas_width integer olmalı.")
        if not isinstance(layout_model.get("canvas_height"), int):
            errors.append("layout_model.canvas_height integer olmalı.")
        if not isinstance(layout_model.get("boxes"), list) or not layout_model.get(
            "boxes"
        ):
            errors.append("layout_model.boxes boş olmayan liste olmalı.")
        else:
            for i, box in enumerate(layout_model["boxes"]):
                if not isinstance(box, dict):
                    errors.append(f"layout_model.boxes[{i}] nesne olmalı.")
                    continue
                if not _is_non_empty_str(box.get("id")):
                    errors.append(f"layout_model.boxes[{i}].id zorunlu string olmalı.")
                for k in ("x", "y", "w", "h"):
                    if not isinstance(box.get(k), (int, float)):
                        errors.append(
                            f"layout_model.boxes[{i}].{k} sayısal değer olmalı."
                        )

    if should_render:
        if not _is_non_empty_str(artifact.get("p5_sketch")):
            errors.append(
                "should_render=true ise p5_sketch zorunlu ve boş olmayan string olmalı."
            )
    else:
        # Keep field present for stable contract, even when no render.
        if "p5_sketch" not in artifact:
            errors.append(
                "should_render=false olsa da p5_sketch alanı mevcut olmalı (boş string olabilir)."
            )

    return errors


def interaction_evidence_errors(p5_sketch: str) -> list[str]:
    """Heuristics to reject static, non-interactive sketches."""
    errors: list[str] = []

    if not _is_non_empty_str(p5_sketch):
        return ["p5_sketch boş."]

    if "function draw" not in p5_sketch:
        errors.append("Sürekli güncellenen bir draw döngüsü bulunmalı.")

    if not any(f"function {hook}" in p5_sketch for hook in _EVENT_HOOKS):
        errors.append(
            "Etkileşim için en az bir olay fonksiyonu gerekli (mouse/touch/keyboard)."
        )

    # Interaction state often uses conditionals or updates (stage/score/selection vars).
    if "if (" not in p5_sketch and "if(" not in p5_sketch:
        errors.append(
            "Etkileşim sonucuna göre durum değişimi için koşullu akış gerekli."
        )

    update_markers = (
        "+=",
        "-=",
        "++",
        "--",
        "= true",
        "= false",
        "selected",
        "drag",
        "stage",
        "score",
    )
    if not any(marker in p5_sketch for marker in update_markers):
        errors.append("Etkileşimle değişen durum (state update) kanıtı bulunamadı.")

    return errors


def question_replay_errors(artifact: dict, *, current_input: dict) -> list[str]:
    """Ban direct question/options replay in game output."""
    errors: list[str] = []

    # For code blocks, inspect only user-facing literals; scanning raw JS causes
    # false positives on syntax fragments.
    p5_literals = _extract_user_visible_literals(str(artifact.get("p5_sketch", "")))
    text_blob_parts = [
        str(artifact.get("instructions_short", "")),
        str(artifact.get("learning_goal", "")),
        str(artifact.get("rationale", "")),
        str(artifact.get("success_condition", "")),
        "\n".join(p5_literals),
    ]

    blob = "\n".join(text_blob_parts).lower()

    for pat in _QUIZ_PATTERNS:
        if re.search(pat, blob, flags=re.IGNORECASE):
            errors.append("Soru/şık temelli statik quiz deseni bulundu (yasak).")
            break

    if isinstance(artifact.get("options"), list) or isinstance(
        artifact.get("choices"), list
    ):
        errors.append(
            "options/choices alanları yasak; oyun soruyu şıklarla tekrar etmemeli."
        )

    q = _extract_question_text(current_input)
    if q:
        # Compare a normalized, punctuation-light stem to catch near verbatim replay.
        q_norm = re.sub(
            r"\s+", " ", re.sub(r"[^\wçğıöşüÇĞİÖŞÜ ]", "", q.lower())
        ).strip()
        if len(q_norm) >= 30 and q_norm in re.sub(
            r"\s+", " ", re.sub(r"[^\wçğıöşüÇĞİÖŞÜ ]", "", blob)
        ):
            errors.append(
                "Oyun içinde özgün sorunun metni doğrudan tekrar edilmiş (yasak)."
            )

    return errors


def _extract_user_visible_literals(p5_sketch: str) -> list[str]:
    """Extract quoted string literals likely to be shown in UI text calls."""
    literals: list[str] = []
    if not _is_non_empty_str(p5_sketch):
        return literals

    for m in re.finditer(r"(?<!\\)(['\"])((?:\\.|(?!\1).)*)\1", p5_sketch):
        s = m.group(2).strip()
        if len(s) < 2:
            continue
        literals.append(s)
    return literals


def _extract_question_text(current_input: dict) -> str:
    if not isinstance(current_input, dict):
        return ""

    # current_input may be {question: {...}, solution: {...}} in orchestrator flow.
    q = current_input.get("question")
    if isinstance(q, dict) and _is_non_empty_str(q.get("question_text")):
        return q["question_text"]

    if _is_non_empty_str(current_input.get("question_text")):
        return str(current_input["question_text"])

    return ""


def context_alignment_errors(artifact: dict, *, current_input: dict) -> list[str]:
    """Require game artifact to stay tied to question/solution concept."""
    errors: list[str] = []

    q_text = _extract_question_text(current_input).lower()
    if not q_text:
        return errors

    labels = []
    for key in ("learning_goal", "instructions_short", "success_condition", "p5_sketch"):
        val = artifact.get(key)
        if isinstance(val, str):
            labels.append(val.lower())
    blob = "\n".join(labels)

    # Lightweight topic anchors for geometric interior-angle style tasks.
    anchors = []
    if "üçgen" in q_text or "ücgen" in q_text:
        anchors.append("üçgen")
    if "açı" in q_text:
        anchors.append("açı")
    if "180" in q_text:
        anchors.append("180")
    if "iç açı" in q_text:
        anchors.append("iç açı")

    # If we discovered anchors, at least half should appear in the output blob.
    if anchors:
        hits = sum(1 for a in set(anchors) if a in blob)
        required = max(1, len(set(anchors)) // 2)
        if hits < required:
            errors.append(
                "Oyun içeriği soru/çözüm bağlamıyla zayıf ilişkili görünüyor; kavram etiketleri yeterince yansıtılmamış."
            )

    return errors


def layout_quality_errors(artifact: dict) -> list[str]:
    """Check canvas fit, visibility bounds, and box overlap risks."""
    errors: list[str] = []
    lm = artifact.get("layout_model")
    if not isinstance(lm, dict):
        return ["layout_model bulunamadı."]

    cw = lm.get("canvas_width")
    ch = lm.get("canvas_height")
    boxes = lm.get("boxes")
    if not isinstance(cw, int) or not isinstance(ch, int):
        return ["layout_model.canvas_width/canvas_height integer olmalı."]
    if not isinstance(boxes, list):
        return ["layout_model.boxes liste olmalı."]

    if cw < MIN_CANVAS_WIDTH or ch < MIN_CANVAS_HEIGHT:
        errors.append(
            f"Canvas çok küçük ({cw}x{ch}). En az {MIN_CANVAS_WIDTH}x{MIN_CANVAS_HEIGHT} olmalı."
        )
    if cw > MAX_CANVAS_WIDTH or ch > MAX_CANVAS_HEIGHT:
        errors.append(
            f"Canvas panel hedefini aşıyor ({cw}x{ch}); en fazla {MAX_CANVAS_WIDTH}x{MAX_CANVAS_HEIGHT} olmalı."
        )

    norm_boxes: list[tuple[str, float, float, float, float]] = []
    for i, b in enumerate(boxes):
        if not isinstance(b, dict):
            continue
        bid = str(b.get("id", f"box_{i}"))
        try:
            x = float(b["x"])
            y = float(b["y"])
            w = float(b["w"])
            h = float(b["h"])
        except Exception:
            continue

        if w < MIN_BOX_WIDTH or h < MIN_BOX_HEIGHT:
            errors.append(f"{bid} kutusu çok küçük ({w}x{h}); görünürlük riski var.")
        if x < 0 or y < 0 or x + w > cw or y + h > ch:
            errors.append(f"{bid} kutusu canvas dışına taşıyor.")

        norm_boxes.append((bid, x, y, w, h))

    # Pairwise overlap check: allow small overlap, reject heavy overlaps.
    for i in range(len(norm_boxes)):
        id1, x1, y1, w1, h1 = norm_boxes[i]
        a1 = max(1.0, w1 * h1)
        for j in range(i + 1, len(norm_boxes)):
            id2, x2, y2, w2, h2 = norm_boxes[j]
            inter_w = max(0.0, min(x1 + w1, x2 + w2) - max(x1, x2))
            inter_h = max(0.0, min(y1 + h1, y2 + h2) - max(y1, y2))
            inter = inter_w * inter_h
            if inter <= 0:
                continue
            a2 = max(1.0, w2 * h2)
            # If overlap covers >15% of either box area, treat as layout problem.
            if (inter / a1) > 0.15 or (inter / a2) > 0.15:
                errors.append(
                    f"{id1} ve {id2} kutuları aşırı çakışıyor (okunabilirlik riski)."
                )

    return errors


def p5_canvas_size_errors(p5_sketch: str, artifact: dict) -> list[str]:
    """Cross-check createCanvas size against layout model and panel constraints."""
    errors: list[str] = []
    if not _is_non_empty_str(p5_sketch):
        return ["p5_sketch boş."]

    lm = artifact.get("layout_model") if isinstance(artifact, dict) else None
    lw = lm.get("canvas_width") if isinstance(lm, dict) else None
    lh = lm.get("canvas_height") if isinstance(lm, dict) else None

    m = re.search(r"createCanvas\(\s*(\d+)\s*,\s*(\d+)\s*\)", p5_sketch)
    if not m:
        errors.append(
            "p5_sketch içinde sayısal createCanvas(width,height) çağrısı bulunamadı."
        )
        return errors

    sw = int(m.group(1))
    sh = int(m.group(2))
    if sw > MAX_CANVAS_WIDTH or sh > MAX_CANVAS_HEIGHT:
        errors.append(
            f"createCanvas {sw}x{sh} panel limitini aşıyor (max {MAX_CANVAS_WIDTH}x{MAX_CANVAS_HEIGHT})."
        )
    if isinstance(lw, int) and isinstance(lh, int):
        if sw != lw or sh != lh:
            errors.append(
                f"createCanvas ({sw}x{sh}) ile layout_model ({lw}x{lh}) uyuşmuyor."
            )

    return errors


def control_button_logic_errors(p5_sketch: str) -> list[str]:
    """Catch non-working 'Kontrol/Sıfırla' UI controls."""
    errors: list[str] = []
    lower = p5_sketch.lower()

    mentions_control = ("kontrol" in lower) or ("check" in lower)
    mentions_reset = ("sıfırla" in lower) or ("sifirla" in lower) or ("reset" in lower)
    if not (mentions_control or mentions_reset):
        return errors

    has_pointer_handler = any(
        f"function {hook}" in p5_sketch for hook in ("mousePressed", "mouseClicked", "touchStarted")
    )
    if not has_pointer_handler:
        return [
            "Buton metinleri var ancak tıklama/touch olay yakalayıcısı yok; Kontrol/Sıfırla çalışmaz."
        ]

    # Require coordinate-based click handling and state mutation evidence.
    if "mouseX" not in p5_sketch or "mouseY" not in p5_sketch:
        errors.append("Butonlar için mouseX/mouseY tabanlı tıklama alanı kontrolü eksik.")

    has_if_bounds = ("if (" in p5_sketch or "if(" in p5_sketch) and any(
        token in p5_sketch for token in ("<=", ">=", "<", ">")
    )
    if not has_if_bounds:
        errors.append("Buton hit-test (sınır kontrolü) bulunamadı.")

    if not any(tok in p5_sketch for tok in ("=", "+=", "-=", "++", "--")):
        errors.append("Buton etkileşimi state değişikliği üretmiyor.")

    return errors


def initial_state_errors(artifact: dict) -> list[str]:
    """Heuristic: game should not start already solved."""
    errors: list[str] = []
    sketch = str(artifact.get("p5_sketch", ""))
    lower = sketch.lower()
    if not lower:
        return errors

    # Common solved-at-start anti-patterns.
    solved_patterns = (
        "iscorrect = true",
        "completed = true",
        "win = true",
        "selected = 1",
        "correctchoice =",
        "sum = 180",
        "angle3 = 180 -",
    )
    if any(p in lower for p in solved_patterns):
        errors.append(
            "Oyun başlangıçta çözülmüş görünüyor; başlangıç state'i etkileşim öncesi nötr/çözülmemiş olmalı."
        )

    # Prefer explicit reset/init path for interactive puzzles.
    if "function setup" in sketch and not any(
        fn in sketch for fn in ("initialize", "initGame", "resetGame", "newRound")
    ):
        errors.append(
            "Başlangıç/yeniden başlatma akışı belirsiz; initialize/reset benzeri net bir fonksiyon gerekli."
        )

    return errors


def is_game_friendly_concept(current_input: dict) -> bool:
    """Heuristic: topics likely suitable for interactive mini-games.

    We intentionally keep this broad to bias toward renderable output.
    """
    q_text = _extract_question_text(current_input).lower()
    sol_text = (
        str(current_input.get("solution", "")).lower()
        if isinstance(current_input, dict)
        else ""
    )
    haystack = f"{q_text}\n{sol_text}"

    keywords = (
        "açı",
        "üçgen",
        "geometr",
        "şekil",
        "çember",
        "doğru",
        "alan",
        "çevre",
        "uzunluk",
        "ölç",
        "toplam",
        "karşılaştır",
        "sayı doğrusu",
        "kesir",
    )
    return any(k in haystack for k in keywords)
