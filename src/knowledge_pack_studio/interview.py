"""Inline widget-based clarification interview for notebook authors."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING, Any

import ipywidgets as widgets

if TYPE_CHECKING:
    from .notebook import NotebookStudio


def _escape(value: Any) -> str:
    return html.escape(str(value)).replace("\n", "<br>")


def build_clarification_interview(studio: NotebookStudio, run_id: str):
    questions = studio.clarification_questions(run_id)
    state = studio.clarification_state(run_id)
    answers: dict[str, str] = dict(state["answers"])
    skipped: set[str] = set(state["skipped"])
    position = 0

    transcript = widgets.HTML()
    progress = widgets.HTML()
    response = widgets.Textarea(
        placeholder="Type your response here…",
        layout=widgets.Layout(width="100%", min_height="90px"),
    )
    previous_button = widgets.Button(description="← Previous")
    next_button = widgets.Button(description="Next →")
    save_button = widgets.Button(description="Send response", button_style="primary")
    suggestion_button = widgets.Button(description="Use suggested answer")
    skip_button = widgets.Button(description="Skip optional")
    approve_button = widgets.Button(description="Approve brief", button_style="success")
    status = widgets.HTML()

    def unresolved() -> list[dict[str, Any]]:
        return [
            row
            for row in questions
            if row["question_id"] not in answers and row["question_id"] not in skipped
        ]

    def required_missing() -> list[dict[str, Any]]:
        return [
            row
            for row in questions
            if row["required"] and not answers.get(row["question_id"], "").strip()
        ]

    def render() -> None:
        nonlocal position
        if questions:
            position = max(0, min(position, len(questions) - 1))
        bubbles: list[str] = []
        for index, row in enumerate(questions):
            question_id = row["question_id"]
            marker = "Required" if row["required"] else "Optional"
            active = " border:2px solid #6d5dfc;" if index == position else ""
            bubbles.append(
                f'<div style="padding:12px;margin:8px 0;border-radius:12px;'
                f'background:#f2f4f8;color:#15171a;{active}">'
                f"<strong>Interviewer · {marker}</strong><br>{_escape(row['question'])}"
                f'<div style="font-size:12px;margin-top:6px;color:#555">'
                f"{_escape(row['why_it_matters'])}</div></div>"
            )
            if question_id in answers:
                bubbles.append(
                    '<div style="padding:12px;margin:8px 0 8px 12%;border-radius:12px;'
                    'background:#e7f6ea;color:#15331d"><strong>You</strong><br>'
                    f"{_escape(answers[question_id])}</div>"
                )
            elif question_id in skipped:
                bubbles.append(
                    '<div style="margin:4px 0 8px 12%;color:#666"><em>Skipped</em></div>'
                )
        transcript.value = "".join(bubbles) or (
            '<div style="padding:12px">No clarification questions were generated. '
            "You may approve the drafted brief.</div>"
        )

        current = questions[position] if questions else None
        current_id = current["question_id"] if current else None
        response.value = answers.get(current_id, "") if current_id else ""
        suggested = current.get("suggested_answer", "") if current else ""
        suggestion_button.disabled = not bool(suggested)
        suggestion_button.tooltip = suggested or "No suggested answer is available"
        skip_button.disabled = not current or current["required"]
        save_button.disabled = not bool(current)
        previous_button.disabled = position <= 0
        next_button.disabled = not questions or position >= len(questions) - 1
        remaining = unresolved()
        missing = required_missing()
        approve_button.disabled = bool(remaining or missing)
        progress.value = (
            f"<strong>Question {position + 1} of {len(questions)}</strong> · "
            f"{len(remaining)} unresolved · {len(missing)} required remaining"
            if questions
            else "<strong>Brief ready for approval</strong>"
        )

    def persist_answer(_: Any = None) -> None:
        if not questions:
            return
        current = questions[position]
        try:
            studio.save_clarification_answer(current["question_id"], response.value, run_id)
            answers[current["question_id"]] = response.value.strip()
            skipped.discard(current["question_id"])
            status.value = "<span style='color:#19713b'>Response saved to the run.</span>"
            go_next()
        except Exception as exc:
            status.value = f"<span style='color:#a51d2d'>{_escape(exc)}</span>"

    def use_suggestion(_: Any = None) -> None:
        if questions:
            response.value = questions[position].get("suggested_answer", "")

    def skip_current(_: Any = None) -> None:
        if not questions:
            return
        current = questions[position]
        try:
            studio.skip_clarification_question(current["question_id"], run_id)
            answers.pop(current["question_id"], None)
            skipped.add(current["question_id"])
            status.value = "<span style='color:#555'>Optional question skipped.</span>"
            go_next()
        except Exception as exc:
            status.value = f"<span style='color:#a51d2d'>{_escape(exc)}</span>"

    def go_previous(_: Any = None) -> None:
        nonlocal position
        position -= 1
        render()

    def go_next(_: Any = None) -> None:
        nonlocal position
        if position < len(questions) - 1:
            position += 1
        render()

    def approve(_: Any = None) -> None:
        try:
            studio.approve({}, run_id)
            approve_button.disabled = True
            for button in (save_button, suggestion_button, skip_button):
                button.disabled = True
            status.value = (
                "<strong style='color:#19713b'>Brief approved and checkpointed. "
                "Continue to grounded research.</strong>"
            )
        except Exception as exc:
            status.value = f"<span style='color:#a51d2d'>{_escape(exc)}</span>"

    previous_button.on_click(go_previous)
    next_button.on_click(go_next)
    save_button.on_click(persist_answer)
    suggestion_button.on_click(use_suggestion)
    skip_button.on_click(skip_current)
    approve_button.on_click(approve)
    render()

    return widgets.VBox(
        [
            widgets.HTML(
                "<h3>Clarification interview</h3><p>Responses checkpoint immediately. "
                "Resolve or explicitly skip every question, then approve the brief.</p>"
            ),
            progress,
            transcript,
            response,
            widgets.HBox([save_button, suggestion_button, skip_button]),
            widgets.HBox([previous_button, next_button, approve_button]),
            status,
        ],
        layout=widgets.Layout(width="100%"),
    )
